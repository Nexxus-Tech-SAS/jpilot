<template>
  <canvas ref="canvasRef" class="shapegrid-canvas" aria-hidden="true" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { prefersReducedMotion } from '../utils/canvasTheme'

const props = defineProps({
  direction: {
    type: String,
    default: 'right',
    validator: (value) => ['diagonal', 'up', 'right', 'down', 'left'].includes(value)
  },
  speed: { type: Number, default: 1 },
  borderColor: { type: String, default: '#999' },
  squareSize: { type: Number, default: 40 },
  hoverFillColor: { type: String, default: '#222' },
  shape: {
    type: String,
    default: 'square',
    validator: (value) => ['square', 'hexagon', 'circle', 'triangle'].includes(value)
  },
  hoverTrailAmount: { type: Number, default: 0 },
  enableMouseInteraction: { type: Boolean, default: true }
})

const canvasRef = ref(null)

let cleanup = null

function mountShapeGrid() {
  const canvas = canvasRef.value
  if (!canvas) return null

  const ctx = canvas.getContext('2d')
  const numSquaresX = { value: 0 }
  const numSquaresY = { value: 0 }
  const gridOffset = { x: 0, y: 0 }
  const hoveredSquare = { current: null }
  const trailCells = []
  const cellOpacities = new Map()
  let requestId = 0
  let animationDisabled = prefersReducedMotion()

  function readProps() {
    return {
      direction: props.direction,
      speed: props.speed,
      borderColor: props.borderColor,
      squareSize: props.squareSize,
      hoverFillColor: props.hoverFillColor,
      shape: props.shape,
      hoverTrailAmount: props.enableMouseInteraction ? props.hoverTrailAmount : 0
    }
  }

  function resizeCanvas() {
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight
    const p = readProps()
    numSquaresX.value = Math.ceil(canvas.width / p.squareSize) + 1
    numSquaresY.value = Math.ceil(canvas.height / p.squareSize) + 1
  }

  function drawHex(cx, cy, size) {
    ctx.beginPath()
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i
      const vx = cx + size * Math.cos(angle)
      const vy = cy + size * Math.sin(angle)
      if (i === 0) ctx.moveTo(vx, vy)
      else ctx.lineTo(vx, vy)
    }
    ctx.closePath()
  }

  function drawCircle(cx, cy, size) {
    ctx.beginPath()
    ctx.arc(cx, cy, size / 2, 0, Math.PI * 2)
    ctx.closePath()
  }

  function drawTriangle(cx, cy, size, flip) {
    ctx.beginPath()
    if (flip) {
      ctx.moveTo(cx, cy + size / 2)
      ctx.lineTo(cx + size / 2, cy - size / 2)
      ctx.lineTo(cx - size / 2, cy - size / 2)
    } else {
      ctx.moveTo(cx, cy - size / 2)
      ctx.lineTo(cx + size / 2, cy + size / 2)
      ctx.lineTo(cx - size / 2, cy + size / 2)
    }
    ctx.closePath()
  }

  function drawGrid() {
    const p = readProps()
    const { squareSize, borderColor, hoverFillColor, shape } = p
    const isHex = shape === 'hexagon'
    const isTri = shape === 'triangle'
    const hexHoriz = squareSize * 1.5
    const hexVert = squareSize * Math.sqrt(3)

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    if (isHex) {
      const colShift = Math.floor(gridOffset.x / hexHoriz)
      const offsetX = ((gridOffset.x % hexHoriz) + hexHoriz) % hexHoriz
      const offsetY = ((gridOffset.y % hexVert) + hexVert) % hexVert
      const cols = Math.ceil(canvas.width / hexHoriz) + 3
      const rows = Math.ceil(canvas.height / hexVert) + 3

      for (let col = -2; col < cols; col++) {
        for (let row = -2; row < rows; row++) {
          const cx = col * hexHoriz + offsetX
          const cy = row * hexVert + ((col + colShift) % 2 !== 0 ? hexVert / 2 : 0) + offsetY
          const cellKey = `${col},${row}`
          const alpha = cellOpacities.get(cellKey)
          if (alpha) {
            ctx.globalAlpha = alpha
            drawHex(cx, cy, squareSize)
            ctx.fillStyle = hoverFillColor
            ctx.fill()
            ctx.globalAlpha = 1
          }
          drawHex(cx, cy, squareSize)
          ctx.strokeStyle = borderColor
          ctx.stroke()
        }
      }
    } else if (isTri) {
      const halfW = squareSize / 2
      const colShift = Math.floor(gridOffset.x / halfW)
      const rowShift = Math.floor(gridOffset.y / squareSize)
      const offsetX = ((gridOffset.x % halfW) + halfW) % halfW
      const offsetY = ((gridOffset.y % squareSize) + squareSize) % squareSize
      const cols = Math.ceil(canvas.width / halfW) + 4
      const rows = Math.ceil(canvas.height / squareSize) + 4

      for (let col = -2; col < cols; col++) {
        for (let row = -2; row < rows; row++) {
          const cx = col * halfW + offsetX
          const cy = row * squareSize + squareSize / 2 + offsetY
          const flip = ((col + colShift + row + rowShift) % 2 + 2) % 2 !== 0
          const cellKey = `${col},${row}`
          const alpha = cellOpacities.get(cellKey)
          if (alpha) {
            ctx.globalAlpha = alpha
            drawTriangle(cx, cy, squareSize, flip)
            ctx.fillStyle = hoverFillColor
            ctx.fill()
            ctx.globalAlpha = 1
          }
          drawTriangle(cx, cy, squareSize, flip)
          ctx.strokeStyle = borderColor
          ctx.stroke()
        }
      }
    } else if (shape === 'circle') {
      const offsetX = ((gridOffset.x % squareSize) + squareSize) % squareSize
      const offsetY = ((gridOffset.y % squareSize) + squareSize) % squareSize
      const cols = Math.ceil(canvas.width / squareSize) + 3
      const rows = Math.ceil(canvas.height / squareSize) + 3

      for (let col = -2; col < cols; col++) {
        for (let row = -2; row < rows; row++) {
          const cx = col * squareSize + squareSize / 2 + offsetX
          const cy = row * squareSize + squareSize / 2 + offsetY
          const cellKey = `${col},${row}`
          const alpha = cellOpacities.get(cellKey)
          if (alpha) {
            ctx.globalAlpha = alpha
            drawCircle(cx, cy, squareSize)
            ctx.fillStyle = hoverFillColor
            ctx.fill()
            ctx.globalAlpha = 1
          }
          drawCircle(cx, cy, squareSize)
          ctx.strokeStyle = borderColor
          ctx.stroke()
        }
      }
    } else {
      const offsetX = ((gridOffset.x % squareSize) + squareSize) % squareSize
      const offsetY = ((gridOffset.y % squareSize) + squareSize) % squareSize
      const cols = Math.ceil(canvas.width / squareSize) + 3
      const rows = Math.ceil(canvas.height / squareSize) + 3

      for (let col = -2; col < cols; col++) {
        for (let row = -2; row < rows; row++) {
          const sx = col * squareSize + offsetX
          const sy = row * squareSize + offsetY
          const cellKey = `${col},${row}`
          const alpha = cellOpacities.get(cellKey)
          if (alpha) {
            ctx.globalAlpha = alpha
            ctx.fillStyle = hoverFillColor
            ctx.fillRect(sx, sy, squareSize, squareSize)
            ctx.globalAlpha = 1
          }
          ctx.strokeStyle = borderColor
          ctx.strokeRect(sx, sy, squareSize, squareSize)
        }
      }
    }

    const gradient = ctx.createRadialGradient(
      canvas.width / 2,
      canvas.height / 2,
      0,
      canvas.width / 2,
      canvas.height / 2,
      Math.sqrt(canvas.width ** 2 + canvas.height ** 2) / 2
    )
    gradient.addColorStop(0, 'rgba(0, 0, 0, 0)')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }

  function updateCellOpacities() {
    const p = readProps()
    const targets = new Map()

    if (hoveredSquare.current) {
      targets.set(`${hoveredSquare.current.x},${hoveredSquare.current.y}`, 1)
    }

    if (p.hoverTrailAmount > 0) {
      for (let i = 0; i < trailCells.length; i++) {
        const t = trailCells[i]
        const key = `${t.x},${t.y}`
        if (!targets.has(key)) {
          targets.set(key, (trailCells.length - i) / (trailCells.length + 1))
        }
      }
    }

    for (const key of targets.keys()) {
      if (!cellOpacities.has(key)) {
        cellOpacities.set(key, 0)
      }
    }

    for (const [key, opacity] of cellOpacities) {
      const target = targets.get(key) || 0
      const next = opacity + (target - opacity) * 0.15
      if (next < 0.005) {
        cellOpacities.delete(key)
      } else {
        cellOpacities.set(key, next)
      }
    }
  }

  function updateAnimation() {
    const p = readProps()
    const isHex = p.shape === 'hexagon'
    const isTri = p.shape === 'triangle'
    const hexHoriz = p.squareSize * 1.5
    const hexVert = p.squareSize * Math.sqrt(3)

    if (!animationDisabled) {
      const effectiveSpeed = Math.max(p.speed, 0.1)
      const wrapX = isHex ? hexHoriz * 2 : p.squareSize
      const wrapY = isHex ? hexVert : isTri ? p.squareSize * 2 : p.squareSize

      switch (p.direction) {
        case 'right':
          gridOffset.x = (gridOffset.x - effectiveSpeed + wrapX) % wrapX
          break
        case 'left':
          gridOffset.x = (gridOffset.x + effectiveSpeed + wrapX) % wrapX
          break
        case 'up':
          gridOffset.y = (gridOffset.y + effectiveSpeed + wrapY) % wrapY
          break
        case 'down':
          gridOffset.y = (gridOffset.y - effectiveSpeed + wrapY) % wrapY
          break
        case 'diagonal':
          gridOffset.x = (gridOffset.x - effectiveSpeed + wrapX) % wrapX
          gridOffset.y = (gridOffset.y - effectiveSpeed + wrapY) % wrapY
          break
        default:
          break
      }
    }

    updateCellOpacities()
    drawGrid()
    requestId = requestAnimationFrame(updateAnimation)
  }

  function handleMouseMove(event) {
    if (!props.enableMouseInteraction) return
    const p = readProps()
    const { squareSize, shape, hoverTrailAmount } = p
    const isHex = shape === 'hexagon'
    const isTri = shape === 'triangle'
    const hexHoriz = squareSize * 1.5
    const hexVert = squareSize * Math.sqrt(3)

    const rect = canvas.getBoundingClientRect()
    const mouseX = event.clientX - rect.left
    const mouseY = event.clientY - rect.top

    let col
    let row

    if (isHex) {
      const colShift = Math.floor(gridOffset.x / hexHoriz)
      const offsetX = ((gridOffset.x % hexHoriz) + hexHoriz) % hexHoriz
      const offsetY = ((gridOffset.y % hexVert) + hexVert) % hexVert
      const adjustedX = mouseX - offsetX
      const adjustedY = mouseY - offsetY
      col = Math.round(adjustedX / hexHoriz)
      const rowOffset = (col + colShift) % 2 !== 0 ? hexVert / 2 : 0
      row = Math.round((adjustedY - rowOffset) / hexVert)
    } else if (isTri) {
      const halfW = squareSize / 2
      const offsetX = ((gridOffset.x % halfW) + halfW) % halfW
      const offsetY = ((gridOffset.y % squareSize) + squareSize) % squareSize
      col = Math.round((mouseX - offsetX) / halfW)
      row = Math.floor((mouseY - offsetY) / squareSize)
    } else if (shape === 'circle') {
      const offsetX = ((gridOffset.x % squareSize) + squareSize) % squareSize
      const offsetY = ((gridOffset.y % squareSize) + squareSize) % squareSize
      col = Math.round((mouseX - offsetX) / squareSize)
      row = Math.round((mouseY - offsetY) / squareSize)
    } else {
      const offsetX = ((gridOffset.x % squareSize) + squareSize) % squareSize
      const offsetY = ((gridOffset.y % squareSize) + squareSize) % squareSize
      col = Math.floor((mouseX - offsetX) / squareSize)
      row = Math.floor((mouseY - offsetY) / squareSize)
    }

    if (!hoveredSquare.current || hoveredSquare.current.x !== col || hoveredSquare.current.y !== row) {
      if (hoveredSquare.current && hoverTrailAmount > 0) {
        trailCells.unshift({ ...hoveredSquare.current })
        if (trailCells.length > hoverTrailAmount) trailCells.length = hoverTrailAmount
      }
      hoveredSquare.current = { x: col, y: row }
    }
  }

  function handleMouseLeave() {
    const p = readProps()
    if (hoveredSquare.current && p.hoverTrailAmount > 0) {
      trailCells.unshift({ ...hoveredSquare.current })
      if (trailCells.length > p.hoverTrailAmount) trailCells.length = p.hoverTrailAmount
    }
    hoveredSquare.current = null
  }

  window.addEventListener('resize', resizeCanvas, { passive: true })
  resizeCanvas()

  if (props.enableMouseInteraction) {
    canvas.addEventListener('mousemove', handleMouseMove)
    canvas.addEventListener('mouseleave', handleMouseLeave)
  }

  requestId = requestAnimationFrame(updateAnimation)

  return () => {
    window.removeEventListener('resize', resizeCanvas)
    cancelAnimationFrame(requestId)
    canvas.removeEventListener('mousemove', handleMouseMove)
    canvas.removeEventListener('mouseleave', handleMouseLeave)
  }
}

onMounted(() => {
  cleanup = mountShapeGrid()
})

onBeforeUnmount(() => {
  cleanup?.()
  cleanup = null
})

watch(
  () => [
    props.direction,
    props.speed,
    props.borderColor,
    props.hoverFillColor,
    props.squareSize,
    props.shape,
    props.hoverTrailAmount,
    props.enableMouseInteraction
  ],
  () => {
    cleanup?.()
    cleanup = mountShapeGrid()
  }
)
</script>

<style scoped>
.shapegrid-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  pointer-events: none;
}
</style>
