<template>
  <svg
    class="v2-sunmoon"
    :class="{ 'v2-sunmoon-dark': dark }"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
    focusable="false"
  >
    <mask :id="maskId">
      <rect width="24" height="24" fill="#ffffff" />
      <circle class="v2-sm-cut" cx="22" cy="2" r="7" fill="#000000" />
    </mask>
    <circle class="v2-sm-core" cx="12" cy="12" r="4.75" fill="currentColor" :mask="`url(#${maskId})`" />
    <g class="v2-sm-rays" stroke="currentColor" stroke-width="1.7" stroke-linecap="round">
      <line x1="12" y1="2.6" x2="12" y2="4.4" />
      <line x1="12" y1="19.6" x2="12" y2="21.4" />
      <line x1="2.6" y1="12" x2="4.4" y2="12" />
      <line x1="19.6" y1="12" x2="21.4" y2="12" />
      <line x1="5.4" y1="5.4" x2="6.7" y2="6.7" />
      <line x1="17.3" y1="17.3" x2="18.6" y2="18.6" />
      <line x1="5.4" y1="18.6" x2="6.7" y2="17.3" />
      <line x1="17.3" y1="6.7" x2="18.6" y2="5.4" />
    </g>
  </svg>
</template>

<script setup>
// Animated sun <-> moon morph. Pure CSS transitions on SVG geometry
// properties (r / cx / cy) + a rotation, driven by the `dark` prop.
// Never touches theme state itself — the parent calls services/theme.
import { useId } from 'vue'

defineProps({
  dark: { type: Boolean, default: false }
})

const maskId = `${useId()}-v2-sm-mask`
</script>

<style scoped>
.v2-sunmoon {
  display: block;
  width: 1.25rem;
  height: 1.25rem;
  transform: rotate(0deg);
  transition: transform var(--v2-dur-slow) var(--v2-ease-spring);
}

.v2-sunmoon-dark {
  transform: rotate(-42deg);
}

/* Sun core grows into the moon disc. */
.v2-sm-core {
  transition: r var(--v2-dur-slow) var(--v2-ease-spring);
}

.v2-sunmoon-dark .v2-sm-core {
  r: 8px;
}

/* The mask circle slides in to carve the crescent. */
.v2-sm-cut {
  transition:
    cx var(--v2-dur-slow) var(--v2-ease),
    cy var(--v2-dur-slow) var(--v2-ease),
    r var(--v2-dur-slow) var(--v2-ease);
}

.v2-sunmoon-dark .v2-sm-cut {
  cx: 17px;
  cy: 7px;
  r: 6.5px;
}

/* Rays pop back in slightly after the crescent retracts. */
.v2-sm-rays {
  transform-box: view-box;
  transform-origin: 12px 12px;
  opacity: 1;
  transform: scale(1) rotate(0deg);
  transition:
    transform var(--v2-dur-slow) var(--v2-ease-spring),
    opacity var(--v2-dur) var(--v2-ease);
  transition-delay: 110ms;
}

.v2-sunmoon-dark .v2-sm-rays {
  opacity: 0;
  transform: scale(0.4) rotate(32deg);
  transition-delay: 0ms;
}
</style>
