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
    <SoftAuroraBackground
      v-else-if="backgroundId === 'aurora'"
      :speed="auroraSettings.speed"
      :scale="auroraSettings.scale"
      :brightness="auroraSettings.brightness"
      :color1="auroraSettings.color1"
      :color2="auroraSettings.color2"
      :noise-frequency="auroraSettings.noiseFrequency"
      :noise-amplitude="preview ? auroraSettings.noiseAmplitude * 0.85 : auroraSettings.noiseAmplitude"
      :band-height="auroraSettings.bandHeight"
      :band-spread="auroraSettings.bandSpread"
      :octave-decay="auroraSettings.octaveDecay"
      :layer-offset="auroraSettings.layerOffset"
      :color-speed="auroraSettings.colorSpeed"
      :enable-mouse-interaction="false"
      :mouse-influence="auroraSettings.mouseInfluence"
    />
    <LineWavesBackground
      v-else-if="backgroundId === 'line-waves'"
      :speed="lineWavesSettings.speed"
      :inner-line-count="preview ? 14 : lineWavesSettings.innerLineCount"
      :outer-line-count="preview ? 16 : lineWavesSettings.outerLineCount"
      :warp-intensity="lineWavesSettings.warpIntensity"
      :rotation="lineWavesSettings.rotation"
      :edge-fade-width="lineWavesSettings.edgeFadeWidth"
      :color-cycle-speed="lineWavesSettings.colorCycleSpeed"
      :brightness="lineWavesSettings.brightness"
      :color1="lineWavesSettings.color1"
      :color2="lineWavesSettings.color2"
      :color3="lineWavesSettings.color3"
      :enable-mouse-interaction="false"
      :mouse-influence="lineWavesSettings.mouseInfluence"
    />
    <GalaxyBackground
      v-else-if="backgroundId === 'galaxy'"
      :focal="galaxySettings.focal"
      :rotation="galaxySettings.rotation"
      :star-speed="galaxySettings.starSpeed"
      :density="preview ? galaxySettings.density * 0.85 : galaxySettings.density"
      :hue-shift="galaxySettings.hueShift"
      :disable-animation="galaxySettings.disableAnimation"
      :speed="galaxySettings.speed"
      :mouse-interaction="false"
      :glow-intensity="galaxySettings.glowIntensity"
      :saturation="galaxySettings.saturation"
      :mouse-repulsion="false"
      :twinkle-intensity="galaxySettings.twinkleIntensity"
      :rotation-speed="galaxySettings.rotationSpeed"
      :repulsion-strength="galaxySettings.repulsionStrength"
      :auto-center-repulsion="galaxySettings.autoCenterRepulsion"
      :transparent="galaxySettings.transparent"
    />
    <DotFieldBackground
      v-else-if="backgroundId === 'dot-field'"
      :dot-radius="dotFieldSettings.dotRadius"
      :dot-spacing="preview ? dotFieldSettings.dotSpacing + 4 : dotFieldSettings.dotSpacing"
      :cursor-radius="dotFieldSettings.cursorRadius"
      :cursor-force="dotFieldSettings.cursorForce"
      :bulge-only="dotFieldSettings.bulgeOnly"
      :bulge-strength="dotFieldSettings.bulgeStrength"
      :glow-radius="preview ? dotFieldSettings.glowRadius * 0.7 : dotFieldSettings.glowRadius"
      :sparkle="dotFieldSettings.sparkle"
      :wave-amplitude="dotFieldSettings.waveAmplitude"
      :gradient-from="dotFieldSettings.gradientFrom"
      :gradient-to="dotFieldSettings.gradientTo"
      :glow-color="dotFieldSettings.glowColor"
      :enable-mouse-interaction="false"
    />
    <ThreadsBackground
      v-else-if="backgroundId === 'threads'"
      :color="threadsSettings.color"
      :amplitude="preview ? threadsSettings.amplitude * 0.85 : threadsSettings.amplitude"
      :distance="threadsSettings.distance"
      :enable-mouse-interaction="false"
    />
    <OrbBackground
      v-else-if="backgroundId === 'orb'"
      :hue="orbSettings.hue"
      :hover-intensity="orbSettings.hoverIntensity"
      :rotate-on-hover="orbSettings.rotateOnHover"
      :force-hover-state="orbSettings.forceHoverState"
      :background-color="orbSettings.backgroundColor"
      :enable-mouse-interaction="false"
    />
    <ShapeGridBackground
      v-else-if="backgroundId === 'shape-grid'"
      :direction="shapeGridSettings.direction"
      :speed="shapeGridSettings.speed"
      :border-color="shapeGridSettings.borderColor"
      :square-size="preview ? shapeGridSettings.squareSize + 8 : shapeGridSettings.squareSize"
      :hover-fill-color="shapeGridSettings.hoverFillColor"
      :shape="shapeGridSettings.shape"
      :hover-trail-amount="shapeGridSettings.hoverTrailAmount"
      :enable-mouse-interaction="false"
    />
    <FloatingLinesBackground
      v-else-if="backgroundId === 'floating-lines'"
      :lines-gradient="floatingLinesSettings.linesGradient"
      :enabled-waves="floatingLinesSettings.enabledWaves"
      :line-count="preview ? 3 : floatingLinesSettings.lineCount"
      :line-distance="floatingLinesSettings.lineDistance"
      :animation-speed="floatingLinesSettings.animationSpeed"
      :interactive="false"
      :bend-radius="floatingLinesSettings.bendRadius"
      :bend-strength="floatingLinesSettings.bendStrength"
      :parallax="false"
      :mix-blend-mode="floatingLinesSettings.mixBlendMode"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import ConstellationCanvas from './ConstellationCanvas.vue'
import DotFieldBackground from './DotFieldBackground.vue'
import DriftFieldCanvas from './DriftFieldCanvas.vue'
import FloatingLinesBackground from './FloatingLinesBackground.vue'
import GalaxyBackground from './GalaxyBackground.vue'
import LineWavesBackground from './LineWavesBackground.vue'
import OrbBackground from './OrbBackground.vue'
import OrbitRingsCanvas from './OrbitRingsCanvas.vue'
import ShapeGridBackground from './ShapeGridBackground.vue'
import SoftAuroraBackground from './SoftAuroraBackground.vue'
import ThreadsBackground from './ThreadsBackground.vue'
import WaveGridCanvas from './WaveGridCanvas.vue'
import { onThemeChange, isDarkTheme } from '../utils/canvasTheme'
import {
  getBetaAuroraSettings,
  getBetaBackgroundPalette,
  getBetaDotFieldSettings,
  getBetaFloatingLinesSettings,
  getBetaGalaxySettings,
  getBetaLineWavesSettings,
  getBetaOrbSettings,
  getBetaShapeGridSettings,
  getBetaThreadsSettings
} from '../utils/betaBackgroundPalettes'

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

const auroraSettings = computed(() => {
  themeTick.value
  return getBetaAuroraSettings()
})

const lineWavesSettings = computed(() => {
  themeTick.value
  return getBetaLineWavesSettings()
})

const galaxySettings = computed(() => {
  themeTick.value
  return getBetaGalaxySettings()
})

const dotFieldSettings = computed(() => {
  themeTick.value
  return getBetaDotFieldSettings()
})

const threadsSettings = computed(() => {
  themeTick.value
  return getBetaThreadsSettings()
})

const orbSettings = computed(() => {
  themeTick.value
  return getBetaOrbSettings()
})

const shapeGridSettings = computed(() => {
  themeTick.value
  return getBetaShapeGridSettings()
})

const floatingLinesSettings = computed(() => {
  themeTick.value
  return getBetaFloatingLinesSettings()
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

.beta-chat-bg :deep(canvas),
.beta-chat-bg :deep(.soft-aurora-container),
.beta-chat-bg :deep(.line-waves-container),
.beta-chat-bg :deep(.galaxy-container),
.beta-chat-bg :deep(.dot-field-container),
.beta-chat-bg :deep(.threads-container),
.beta-chat-bg :deep(.orb-container),
.beta-chat-bg :deep(.floating-lines-container) {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
}
</style>
