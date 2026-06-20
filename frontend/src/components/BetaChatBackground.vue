<template>
  <div class="beta-chat-bg" aria-hidden="true">
    <div class="beta-chat-bg-base" :class="{ 'beta-chat-bg-base--dark': isDark }" />
    <ConstellationCanvas
      v-if="backgroundId === 'constellation'"
      :particle-count="preview ? 28 : 72"
      :link-distance="preview ? 90 : 150"
      :line-color="palette.line"
      :dot-color="palette.dot"
      :line-opacity="palette.lineOpacity"
      :dot-opacity="palette.dotOpacity"
    />
    <DriftFieldCanvas
      v-else-if="backgroundId === 'drift'"
      :dot-color="palette.dot"
      :dot-opacity="palette.opacity"
      :density="preview ? 1.4 : 2.2"
      monochrome
    />
    <WaveGridCanvas
      v-else-if="backgroundId === 'waves'"
      :line-color="palette.line"
      :line-opacity="palette.opacity"
    />
    <OrbitRingsCanvas
      v-else-if="backgroundId === 'orbit'"
      :ring-color="palette.ring"
      :dot-color="palette.dot"
      :ring-opacity="palette.ringOpacity"
      :dot-opacity="palette.dotOpacity"
      :ring-count="preview ? 6 : 9"
      :center-count="preview ? 2 : 3"
      :density="preview ? 1.2 : 1.65"
      monochrome
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import ConstellationCanvas from './ConstellationCanvas.vue'
import DriftFieldCanvas from './DriftFieldCanvas.vue'
import OrbitRingsCanvas from './OrbitRingsCanvas.vue'
import WaveGridCanvas from './WaveGridCanvas.vue'
import { onThemeChange, isDarkTheme } from '../utils/canvasTheme'
import { getBetaBackgroundPalette } from '../utils/betaBackgroundPalettes'

const props = defineProps({
  backgroundId: { type: String, default: 'constellation' },
  preview: { type: Boolean, default: false }
})

const themeTick = ref(0)
let themeCleanup = null

onMounted(() => {
  themeCleanup = onThemeChange(() => {
    themeTick.value += 1
  })
})

onBeforeUnmount(() => {
  themeCleanup?.()
})

const palette = computed(() => {
  themeTick.value
  return getBetaBackgroundPalette(props.backgroundId)
})

const isDark = computed(() => {
  themeTick.value
  return isDarkTheme()
})
</script>

<style scoped>
.beta-chat-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.beta-chat-bg-base {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: #ffffff;
}

.beta-chat-bg-base--dark {
  background: #000000;
}

.beta-chat-bg :deep(canvas) {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
}
</style>
