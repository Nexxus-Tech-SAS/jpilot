<template>
  <nav class="v2-bottomnav" aria-label="Primary">
    <RouterLink
      v-for="(item, i) in navItems"
      :key="item.path"
      :to="item.path"
      replace
      class="v2-bottomnav-item"
      :class="{ 'v2-bottomnav-item-active': isActive(item) }"
      :style="{ '--stagger': i }"
    >
      <span class="v2-bottomnav-icon">
        <i :class="item.icon" aria-hidden="true" />
        <span v-if="isCopilotNavItem(item) && busy" class="v2-busy-dot" aria-hidden="true" />
      </span>
      <span class="v2-bottomnav-label">{{ item.shortLabel }}</span>
    </RouterLink>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { NAV_ITEMS, isCopilotNavItem, isNavItemActive } from './navModel'

defineProps({
  busy: { type: Boolean, default: false }
})

const route = useRoute()
const navItems = NAV_ITEMS

function isActive(item) {
  return isNavItemActive(item.path, route.path)
}
</script>

<style scoped>
/* Phone-only floating glass dock (<768px). Hidden on the chat route by the
   parent (immersive chat). Fixed chrome stays <= 1100 (cookie banner: 9999). */
.v2-bottomnav,
.v2-bottomnav * {
  box-sizing: border-box;
}

.v2-bottomnav {
  position: fixed;
  left: max(0.75rem, env(safe-area-inset-left, 0px));
  right: max(0.75rem, env(safe-area-inset-right, 0px));
  bottom: calc(0.625rem + env(safe-area-inset-bottom, 0px));
  z-index: 1080;
  display: none;
  align-items: stretch;
  padding: 0.3rem 0.4rem;
  border: 1px solid var(--v2-border);
  border-radius: var(--v2-radius-xl);
  background: var(--v2-surface-glass-strong);
  backdrop-filter: blur(var(--v2-blur)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--v2-blur)) saturate(140%);
  box-shadow: var(--v2-shadow-2);
  animation: v2-bottomnav-in var(--v2-dur-slow) var(--v2-ease) both;
}

@media (max-width: 767.98px) {
  .v2-bottomnav {
    display: flex;
  }
}

@keyframes v2-bottomnav-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.v2-bottomnav-item {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: var(--v2-touch-target);
  padding: 0.3rem 0.125rem;
  border-radius: var(--v2-radius-lg);
  color: var(--v2-text-2);
  text-decoration: none;
  -webkit-tap-highlight-color: transparent;
  transition: color var(--v2-dur) var(--v2-ease);
  animation: v2-bottomnav-item-in var(--v2-dur-slow) var(--v2-ease) both;
  animation-delay: calc(80ms + var(--stagger, 0) * 40ms);
}

@keyframes v2-bottomnav-item-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.v2-bottomnav-item:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: -2px;
}

.v2-bottomnav-icon {
  position: relative;
  display: grid;
  place-items: center;
  width: 3.25rem;
  height: 1.9rem;
  border-radius: var(--v2-radius-full);
  transition: transform var(--v2-dur-fast) var(--v2-ease-spring);
}

/* Active pill scales in behind the icon. */
.v2-bottomnav-icon::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--v2-gradient-brand-soft);
  border: 1px solid color-mix(in srgb, var(--v2-accent) 24%, transparent);
  opacity: 0;
  transform: scale(0.6);
  transition:
    opacity var(--v2-dur) var(--v2-ease),
    transform var(--v2-dur-slow) var(--v2-ease-spring);
}

.v2-bottomnav-item-active .v2-bottomnav-icon::before {
  opacity: 1;
  transform: scale(1);
}

.v2-bottomnav-icon i {
  position: relative;
  font-size: 1.1rem;
  line-height: 1;
  transition: color var(--v2-dur) var(--v2-ease), transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-bottomnav-item:active .v2-bottomnav-icon {
  transform: scale(0.9);
}

.v2-bottomnav-item-active {
  color: var(--v2-text);
}

.v2-bottomnav-item-active .v2-bottomnav-icon i {
  color: var(--p-primary-color);
}

.v2-bottomnav-label {
  max-width: 100%;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v2-busy-dot {
  position: absolute;
  top: 0.05rem;
  right: 0.55rem;
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--v2-gradient-brand);
  box-shadow: 0 0 0 3px var(--v2-accent-soft);
  animation: v2-busy-pulse-dock 1.5s var(--v2-ease) infinite;
}

@keyframes v2-busy-pulse-dock {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.45;
    transform: scale(0.78);
  }
}

@media (prefers-reduced-motion: reduce) {
  .v2-bottomnav,
  .v2-bottomnav-item,
  .v2-busy-dot {
    animation: none !important;
  }

  .v2-bottomnav-icon,
  .v2-bottomnav-icon::before,
  .v2-bottomnav-icon i {
    transition: none !important;
  }
}
</style>
