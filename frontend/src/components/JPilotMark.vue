<template>
  <svg
    class="jp-mark"
    :class="{ 'jp-tone-dark': tone === 'dark' }"
    :width="sizePx"
    :height="sizePx"
    viewBox="0 0 300 300"
    role="img"
    aria-label="JPilot"
  >
    <defs>
      <linearGradient :id="`${uid}-ring`" x1="86" y1="86" x2="214" y2="214" gradientUnits="userSpaceOnUse">
        <stop class="jp-s1" offset="0" />
        <stop class="jp-s2" offset="1" />
      </linearGradient>
      <radialGradient :id="`${uid}-glow`" cx="0.5" cy="0.5" r="0.5">
        <stop class="jp-g1" offset="0" />
        <stop class="jp-g2" offset="1" />
      </radialGradient>
      <radialGradient :id="`${uid}-core`" cx="0.4" cy="0.35" r="0.9">
        <stop offset="0" stop-color="#14536b" />
        <stop offset="1" stop-color="#0b1426" />
      </radialGradient>
    </defs>

    <template v-if="variant === 'full'">
      <circle cx="150" cy="150" r="95" :fill="`url(#${uid}-glow)`" class="jp-breath" />
      <path d="M 150 92 L 150 62" class="jp-link" style="animation-delay: 0s" />
      <path d="M 102.8 183.7 L 74.8 203.7" class="jp-link" style="animation-delay: 0.35s" />
      <path d="M 197.2 183.7 L 225.2 203.7" class="jp-link" style="animation-delay: 0.7s" />
      <circle cx="150" cy="150" r="52" :fill="`url(#${uid}-core)`" :stroke="`url(#${uid}-ring)`" stroke-width="7" />
      <g class="jp-wave">
        <rect x="127" y="139" width="9" height="22" rx="4.5" style="transform-origin: 131.5px 150px; animation-delay: 0s" />
        <rect x="141" y="128" width="9" height="44" rx="4.5" style="transform-origin: 145.5px 150px; animation-delay: 0.2s" />
        <rect x="155" y="122" width="9" height="56" rx="4.5" style="transform-origin: 159.5px 150px; animation-delay: 0.4s" />
        <rect x="169" y="134" width="9" height="32" rx="4.5" style="transform-origin: 173.5px 150px; animation-delay: 0.6s" />
      </g>
      <g>
        <rect x="130" y="20" width="40" height="40" rx="10" class="jp-node jp-c1" />
        <path d="M 140 36 H 160 M 140 45 H 160" class="jp-ports" />
        <rect x="32" y="200" width="40" height="40" rx="10" class="jp-node jp-c2" />
        <path d="M 42 216 H 62 M 42 225 H 62" class="jp-ports" />
        <rect x="228" y="200" width="40" height="40" rx="10" class="jp-node jp-c3" />
        <path d="M 238 216 H 258 M 238 225 H 258" class="jp-ports" />
      </g>
    </template>

    <template v-else>
      <circle cx="150" cy="150" r="90" :fill="`url(#${uid}-glow)`" class="jp-breath" />
      <circle cx="150" cy="150" r="61" :fill="`url(#${uid}-core)`" />
      <circle cx="150" cy="150" r="66" fill="none" :stroke="`url(#${uid}-ring)`" stroke-width="10" />
      <path d="M 150 82 L 150 62" class="jp-stub" />
      <path d="M 92.8 183 L 75.5 193" class="jp-stub" />
      <path d="M 207.2 183 L 224.5 193" class="jp-stub" />
      <circle cx="150" cy="48" r="12" class="jp-dot jp-c1" style="animation-delay: 0s" />
      <circle cx="63.4" cy="200" r="12" class="jp-dot jp-c2" style="animation-delay: 1s" />
      <circle cx="236.6" cy="200" r="12" class="jp-dot jp-c3" style="animation-delay: 2s" />
      <g class="jp-wave">
        <rect x="127" y="139" width="9" height="22" rx="4.5" style="transform-origin: 131.5px 150px; animation-delay: 0s" />
        <rect x="141" y="128" width="9" height="44" rx="4.5" style="transform-origin: 145.5px 150px; animation-delay: 0.2s" />
        <rect x="155" y="122" width="9" height="56" rx="4.5" style="transform-origin: 159.5px 150px; animation-delay: 0.4s" />
        <rect x="169" y="134" width="9" height="32" rx="4.5" style="transform-origin: 173.5px 150px; animation-delay: 0.6s" />
      </g>
    </template>
  </svg>
</template>

<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'icon' },
  size: { type: [Number, String], default: 56 },
  tone: { type: String, default: 'auto' }
})

const uid = useId()

const sizePx = computed(() =>
  typeof props.size === 'number' ? `${props.size}` : props.size
)
</script>

<style scoped>
.jp-mark {
  display: block;
  --jp-a: #0891b2;
  --jp-mid: #0284c7;
  --jp-b: #4f46e5;
  --jp-link: #0e7490;
  --jp-glow-o: 0.2;
}

:global(html.app-dark) .jp-mark,
.jp-mark.jp-tone-dark {
  --jp-a: #22d3ee;
  --jp-mid: #38bdf8;
  --jp-b: #6366f1;
  --jp-link: #67e8f9;
  --jp-glow-o: 0.38;
}

.jp-mark * {
  transform-box: view-box;
}

.jp-s1 {
  stop-color: var(--jp-a);
}

.jp-s2 {
  stop-color: var(--jp-b);
}

.jp-g1 {
  stop-color: var(--jp-a);
  stop-opacity: var(--jp-glow-o);
}

.jp-g2 {
  stop-color: var(--jp-a);
  stop-opacity: 0;
}

.jp-breath {
  transform-origin: 150px 150px;
  animation: jp-breath 4s ease-in-out infinite;
}

.jp-link {
  fill: none;
  stroke: var(--jp-link);
  stroke-width: 6;
  stroke-linecap: round;
  stroke-dasharray: 5 11;
  animation: jp-flow 1.1s linear infinite;
}

.jp-stub {
  fill: none;
  stroke: var(--jp-link);
  stroke-width: 7;
  stroke-linecap: round;
}

.jp-node {
  fill: #0c1524;
  stroke-width: 4.5;
}

.jp-node.jp-c1 {
  stroke: var(--jp-a);
}

.jp-node.jp-c2 {
  stroke: var(--jp-mid);
}

.jp-node.jp-c3 {
  stroke: var(--jp-b);
}

.jp-dot.jp-c1 {
  fill: var(--jp-a);
}

.jp-dot.jp-c2 {
  fill: var(--jp-mid);
}

.jp-dot.jp-c3 {
  fill: var(--jp-b);
}

.jp-ports {
  fill: none;
  stroke: #7dd3fc;
  stroke-width: 3.5;
}

.jp-wave rect {
  fill: #a5f3fc;
  animation: jp-eq 1.4s ease-in-out infinite;
}

.jp-dot {
  animation: jp-pulse 3s ease-in-out infinite;
}

@keyframes jp-breath {
  0%,
  100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
}

@keyframes jp-flow {
  to {
    stroke-dashoffset: -32;
  }
}

@keyframes jp-eq {
  0%,
  100% {
    transform: scaleY(0.45);
  }
  50% {
    transform: scaleY(1);
  }
}

@keyframes jp-pulse {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .jp-breath,
  .jp-link,
  .jp-wave rect,
  .jp-dot {
    animation: none;
  }
}
</style>
