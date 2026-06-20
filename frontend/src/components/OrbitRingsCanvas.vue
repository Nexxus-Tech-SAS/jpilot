<template>
  <canvas ref="canvasRef" class="orbit-rings-canvas" aria-hidden="true" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { bindCanvasResize } from '../utils/canvasResize'
import { onThemeChange, prefersReducedMotion, resolveCanvasColors } from '../utils/canvasTheme'

const props = defineProps({
  ringColor: { type: String, default: '' },
  dotColor: { type: String, default: '' },
  ringOpacity: { type: Number, default: null },
  dotOpacity: { type: Number, default: null },
  ringCount: { type: Number, default: 4 },
  centerCount: { type: Number, default: 1 },
  density: { type: Number, default: 1 },
  monochrome: { type: Boolean, default: false }
})

const canvasRef = ref(null)
let animationId = null
let resizeCleanup = null
let themeCleanup = null
let angle = 0

function themeColors() {
  if (props.ringColor) {
    return {
      ring: props.ringColor,
      dot: props.dotColor || props.ringColor,
      ringOpacity: props.ringOpacity ?? 0.5,
      dotOpacity: props.dotOpacity ?? 0.8
    }
  }
  return resolveCanvasColors(
    { ring: '0,123,167', dot: '0,168,224', ringOpacity: 0.16, dotOpacity: 0.5 },
    { ring: '80,160,200', dot: '120,200,230', ringOpacity: 0.14, dotOpacity: 0.42 }
  )
}

function resizeCanvas(canvas) {
  canvas.width = canvas.offsetWidth
  canvas.height = canvas.offsetHeight
}

function drawFrame(canvas, ctx, animate = true) {
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  const colors = themeColors()
  const centers = []
  const count = Math.max(1, props.centerCount)

  for (let c = 0; c < count; c += 1) {
    const col = c % 2
    const row = Math.floor(c / 2)
    const cols = count === 1 ? 1 : 2
    const rows = Math.ceil(count / cols)
    centers.push({
      cx: canvas.width * (0.28 + (col / Math.max(cols - 1, 1)) * 0.44),
      cy: canvas.height * (0.3 + (row / Math.max(rows - 1, 1)) * 0.4),
      phase: c * 1.7
    })
  }

  const base = Math.min(canvas.width, canvas.height) * (0.14 / Math.max(props.density, 0.5))

  if (animate) angle += 0.0035 * props.density

  centers.forEach((center, centerIndex) => {
    for (let i = 0; i < props.ringCount; i += 1) {
      const radius = base + i * base * 0.34
      const ringAngle =
        angle * (i % 2 === 0 ? 1 : -0.72) + i * 0.38 + center.phase + centerIndex * 0.55

      ctx.beginPath()
      ctx.arc(center.cx, center.cy, radius, 0, Math.PI * 2)
      ctx.strokeStyle = `rgba(${colors.ring}, ${colors.ringOpacity * (1 - i * 0.07)})`
      ctx.lineWidth = props.monochrome ? 0.85 : props.ringColor ? 1.25 : 0.9
      ctx.stroke()

      const dotX = center.cx + Math.cos(ringAngle) * radius
      const dotY = center.cy + Math.sin(ringAngle) * radius
      ctx.beginPath()
      ctx.arc(dotX, dotY, Math.max(1.2, 2.1 - i * 0.12), 0, Math.PI * 2)
      ctx.fillStyle = `rgba(${colors.dot}, ${colors.dotOpacity})`
      ctx.fill()
    }
  })
}

function startAnimation() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const reducedMotion = prefersReducedMotion()
  let loopStarted = false

  const syncSize = () => {
    if (canvas.offsetWidth === 0 || canvas.offsetHeight === 0) return false
    resizeCanvas(canvas)
    return true
  }

  const ensureRunning = () => {
    if (!syncSize()) return
    if (reducedMotion) {
      drawFrame(canvas, ctx, false)
      return
    }
    if (loopStarted) return
    loopStarted = true
    const loop = () => {
      drawFrame(canvas, ctx, true)
      animationId = requestAnimationFrame(loop)
    }
    loop()
  }

  resizeCleanup = bindCanvasResize(canvas, ensureRunning)
  themeCleanup = onThemeChange(() => {
    if (syncSize()) drawFrame(canvas, ctx, false)
  })
  ensureRunning()
}

onMounted(() => startAnimation())

onBeforeUnmount(() => {
  if (animationId) cancelAnimationFrame(animationId)
  resizeCleanup?.()
  themeCleanup?.()
})
</script>

<style scoped>
.orbit-rings-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
