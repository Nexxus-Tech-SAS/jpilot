<template>
  <div ref="containerRef" class="dot-field-container" aria-hidden="true">
    <canvas ref="canvasRef" class="dot-field-canvas" />
    <svg class="dot-field-glow" aria-hidden="true">
      <defs>
        <radialGradient :id="glowId">
          <stop offset="0%" :stop-color="glowColor" />
          <stop offset="100%" stop-color="transparent" />
        </radialGradient>
      </defs>
      <circle
        ref="glowRef"
        cx="-9999"
        cy="-9999"
        :r="glowRadius"
        :fill="`url(#${glowId})`"
        class="dot-field-glow-circle"
      />
    </svg>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { prefersReducedMotion } from '../utils/canvasTheme'

const props = defineProps({
  dotRadius: { type: Number, default: 1.5 },
  dotSpacing: { type: Number, default: 14 },
  cursorRadius: { type: Number, default: 500 },
  cursorForce: { type: Number, default: 0.1 },
  bulgeOnly: { type: Boolean, default: true },
  bulgeStrength: { type: Number, default: 67 },
  glowRadius: { type: Number, default: 160 },
  sparkle: { type: Boolean, default: false },
  waveAmplitude: { type: Number, default: 0 },
  gradientFrom: { type: String, default: 'rgba(168, 85, 247, 0.35)' },
  gradientTo: { type: String, default: 'rgba(180, 151, 207, 0.25)' },
  glowColor: { type: String, default: '#120F17' },
  enableMouseInteraction: { type: Boolean, default: true }
})

const TWO_PI = Math.PI * 2
let glowInstanceCounter = 0

const containerRef = ref(null)
const canvasRef = ref(null)
const glowRef = ref(null)
const glowId = `dot-field-glow-${++glowInstanceCounter}`

let cleanup = null
let rebuildDots = null

function mountDotField() {
  const container = containerRef.value
  const canvas = canvasRef.value
  const glowEl = glowRef.value
  if (!container || !canvas) return null

  const ctx = canvas.getContext('2d', { alpha: true })
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const dots = []
  const mouse = { x: -9999, y: -9999, prevX: -9999, prevY: -9999, speed: 0 }
  const size = { w: 0, h: 0, offsetX: 0, offsetY: 0 }
  const glowOpacity = { value: 0 }
  const engagement = { value: 0 }
  let resizeTimer = null
  let animationFrameId = null
  let speedInterval = null
  let frameCount = 0
  let animationDisabled = prefersReducedMotion()

  function currentProps() {
    return {
      dotRadius: props.dotRadius,
      dotSpacing: props.dotSpacing,
      cursorRadius: props.cursorRadius,
      cursorForce: props.cursorForce,
      bulgeOnly: props.bulgeOnly,
      bulgeStrength: props.bulgeStrength,
      sparkle: props.sparkle,
      waveAmplitude: animationDisabled ? 0 : props.waveAmplitude,
      gradientFrom: props.gradientFrom,
      gradientTo: props.gradientTo
    }
  }

  function buildDots(w, h) {
    const p = currentProps()
    const step = p.dotRadius + p.dotSpacing
    const cols = Math.floor(w / step)
    const rows = Math.floor(h / step)
    const padX = (w % step) / 2
    const padY = (h % step) / 2
    dots.length = 0

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const ax = padX + col * step + step / 2
        const ay = padY + row * step + step / 2
        dots.push({ ax, ay, sx: ax, sy: ay, vx: 0, vy: 0, x: ax, y: ay })
      }
    }
  }

  function doResize() {
    const rect = container.getBoundingClientRect()
    const w = rect.width
    const h = rect.height

    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = `${w}px`
    canvas.style.height = `${h}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    size.w = w
    size.h = h
    size.offsetX = rect.left + window.scrollX
    size.offsetY = rect.top + window.scrollY

    buildDots(w, h)
  }

  function resize() {
    clearTimeout(resizeTimer)
    resizeTimer = setTimeout(doResize, 100)
  }

  function onMouseMove(e) {
    if (!props.enableMouseInteraction) return
    mouse.x = e.pageX - size.offsetX
    mouse.y = e.pageY - size.offsetY
  }

  function updateMouseSpeed() {
    const dx = mouse.prevX - mouse.x
    const dy = mouse.prevY - mouse.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    mouse.speed += (dist - mouse.speed) * 0.5
    if (mouse.speed < 0.001) mouse.speed = 0
    mouse.prevX = mouse.x
    mouse.prevY = mouse.y
  }

  function tick() {
    frameCount++
    const p = currentProps()
    const len = dots.length
    const t = frameCount * 0.02

    const targetEngagement = props.enableMouseInteraction ? Math.min(mouse.speed / 5, 1) : 0
    engagement.value += (targetEngagement - engagement.value) * 0.06
    if (engagement.value < 0.001) engagement.value = 0
    const eng = engagement.value

    glowOpacity.value += (eng - glowOpacity.value) * 0.08

    if (glowEl) {
      glowEl.setAttribute('cx', String(mouse.x))
      glowEl.setAttribute('cy', String(mouse.y))
      glowEl.style.opacity = String(glowOpacity.value)
    }

    ctx.clearRect(0, 0, size.w, size.h)

    const grad = ctx.createLinearGradient(0, 0, size.w, size.h)
    grad.addColorStop(0, p.gradientFrom)
    grad.addColorStop(1, p.gradientTo)
    ctx.fillStyle = grad

    const cr = p.cursorRadius
    const crSq = cr * cr
    const rad = p.dotRadius / 2
    const isBulge = p.bulgeOnly

    ctx.beginPath()

    for (let i = 0; i < len; i++) {
      const d = dots[i]
      const dx = mouse.x - d.ax
      const dy = mouse.y - d.ay
      const distSq = dx * dx + dy * dy

      if (distSq < crSq && eng > 0.01) {
        const dist = Math.sqrt(distSq)
        if (isBulge) {
          const factor = 1 - dist / cr
          const push = factor * factor * p.bulgeStrength * eng
          const angle = Math.atan2(dy, dx)
          d.sx += (d.ax - Math.cos(angle) * push - d.sx) * 0.15
          d.sy += (d.ay - Math.sin(angle) * push - d.sy) * 0.15
        } else {
          const angle = Math.atan2(dy, dx)
          const move = (500 / dist) * (mouse.speed * p.cursorForce)
          d.vx += Math.cos(angle) * -move
          d.vy += Math.sin(angle) * -move
        }
      } else if (isBulge) {
        d.sx += (d.ax - d.sx) * 0.1
        d.sy += (d.ay - d.sy) * 0.1
      }

      if (!isBulge) {
        d.vx *= 0.9
        d.vy *= 0.9
        d.x = d.ax + d.vx
        d.y = d.ay + d.vy
        d.sx += (d.x - d.sx) * 0.1
        d.sy += (d.y - d.sy) * 0.1
      }

      let drawX = d.sx
      let drawY = d.sy
      if (p.waveAmplitude > 0) {
        drawY += Math.sin(d.ax * 0.03 + t) * p.waveAmplitude
        drawX += Math.cos(d.ay * 0.03 + t * 0.7) * p.waveAmplitude * 0.5
      }

      if (p.sparkle) {
        const hash = ((i * 2654435761) ^ (frameCount >> 3)) >>> 0
        if (hash % 100 < 3) {
          ctx.moveTo(drawX + rad * 1.8, drawY)
          ctx.arc(drawX, drawY, rad * 1.8, 0, TWO_PI)
        } else {
          ctx.moveTo(drawX + rad, drawY)
          ctx.arc(drawX, drawY, rad, 0, TWO_PI)
        }
      } else {
        ctx.moveTo(drawX + rad, drawY)
        ctx.arc(drawX, drawY, rad, 0, TWO_PI)
      }
    }

    ctx.fill()
    animationFrameId = requestAnimationFrame(tick)
  }

  doResize()
  window.addEventListener('resize', resize, { passive: true })
  if (props.enableMouseInteraction) {
    window.addEventListener('mousemove', onMouseMove, { passive: true })
    speedInterval = setInterval(updateMouseSpeed, 20)
  }
  animationFrameId = requestAnimationFrame(tick)

  rebuildDots = () => {
    if (size.w > 0 && size.h > 0) buildDots(size.w, size.h)
  }

  return () => {
    cancelAnimationFrame(animationFrameId)
    clearInterval(speedInterval)
    clearTimeout(resizeTimer)
    window.removeEventListener('resize', resize)
    window.removeEventListener('mousemove', onMouseMove)
  }
}

onMounted(() => {
  cleanup = mountDotField()
})

onBeforeUnmount(() => {
  cleanup?.()
  cleanup = null
  rebuildDots = null
})

watch(
  () => [props.dotRadius, props.dotSpacing],
  () => {
    rebuildDots?.()
  }
)

watch(
  () => props.enableMouseInteraction,
  () => {
    cleanup?.()
    cleanup = mountDotField()
  }
)
</script>

<style scoped>
.dot-field-container {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.dot-field-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.dot-field-glow {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.dot-field-glow-circle {
  opacity: 0;
  will-change: opacity;
}
</style>
