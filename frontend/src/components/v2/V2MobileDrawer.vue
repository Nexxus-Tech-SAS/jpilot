<template>
  <Drawer
    :visible="visible"
    position="left"
    :modal="true"
    :dismissable="true"
    :show-close-icon="false"
    class="v2-drawer"
    @update:visible="(value) => $emit('update:visible', value)"
  >
    <div class="v2-drawer-body">
      <div class="v2-drawer-header v2-drawer-stagger" style="--stagger: 0">
        <RouterLink to="/" replace class="v2-drawer-brand" aria-label="JPilot dashboard" @click="close">
          <JPilotMark variant="full" :size="40" />
          <span class="jp-wordmark v2-drawer-word">JPilot</span>
        </RouterLink>
        <button type="button" class="v2-drawer-close" aria-label="Close menu" @click.stop="close">
          <i class="pi pi-times" aria-hidden="true" />
        </button>
      </div>

      <nav class="v2-drawer-nav" aria-label="Primary">
        <RouterLink
          v-for="(item, i) in navItems"
          :key="item.path"
          :to="item.path"
          replace
          class="v2-drawer-link v2-drawer-stagger"
          :class="{ 'v2-drawer-link-active': isActive(item) }"
          :style="{ '--stagger': i + 1 }"
          @click="close"
        >
          <span class="v2-drawer-link-icon">
            <i :class="item.icon" aria-hidden="true" />
            <span v-if="isCopilotNavItem(item) && busy" class="v2-busy-dot" aria-hidden="true" />
          </span>
          <span class="v2-drawer-link-text">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="v2-drawer-divider v2-drawer-stagger" :style="{ '--stagger': navItems.length + 1 }" aria-hidden="true" />

      <div class="v2-drawer-actions">
        <button
          type="button"
          class="v2-drawer-link v2-drawer-action v2-drawer-stagger"
          :style="{ '--stagger': navItems.length + 2 }"
          @click="$emit('toggle-theme')"
        >
          <span class="v2-drawer-link-icon"><V2SunMoonIcon :dark="isDark" /></span>
          <span class="v2-drawer-link-text">{{ isDark ? 'Switch to light' : 'Switch to dark' }}</span>
        </button>

        <button
          type="button"
          class="v2-drawer-link v2-drawer-action v2-drawer-stagger"
          :style="{ '--stagger': navItems.length + 3 }"
          @click="onFullscreen"
        >
          <span class="v2-drawer-link-icon">
            <i :class="isFullscreen ? 'pi pi-window-minimize' : 'pi pi-window-maximize'" aria-hidden="true" />
          </span>
          <span class="v2-drawer-link-text">{{ isFullscreen ? 'Exit full screen' : 'Full screen' }}</span>
        </button>

        <button
          type="button"
          class="v2-drawer-link v2-drawer-action v2-drawer-beta v2-drawer-stagger"
          :style="{ '--stagger': navItems.length + 4 }"
          @click="$emit('switch-classic')"
        >
          <span class="v2-drawer-link-icon"><i class="pi pi-sparkles" aria-hidden="true" /></span>
          <span class="v2-drawer-link-text">
            New UI · Beta
            <span class="v2-drawer-link-sub">Switch back to classic</span>
          </span>
        </button>

        <button
          type="button"
          class="v2-drawer-link v2-drawer-action v2-drawer-logout v2-drawer-stagger"
          :style="{ '--stagger': navItems.length + 5 }"
          @click="$emit('logout')"
        >
          <span class="v2-drawer-link-icon"><i class="pi pi-sign-out" aria-hidden="true" /></span>
          <span class="v2-drawer-link-text">Logout</span>
        </button>
      </div>

      <div class="v2-drawer-foot v2-drawer-stagger" :style="{ '--stagger': navItems.length + 6 }">
        <nav class="v2-drawer-legal" aria-label="Legal">
          <RouterLink v-for="link in legalLinks" :key="link.path" :to="link.path" @click="close">
            {{ link.label }}
          </RouterLink>
        </nav>
        <span class="v2-drawer-copy">
          © {{ currentYear }}
          <a :href="NEXXUS_TECH.websiteUrl" target="_blank" rel="noopener noreferrer">Nexxus Tech</a>
        </span>
      </div>
    </div>
  </Drawer>
</template>

<script setup>
import { useRoute } from 'vue-router'
import Drawer from 'primevue/drawer'
import JPilotMark from '../JPilotMark.vue'
import V2SunMoonIcon from './V2SunMoonIcon.vue'
import { NEXXUS_TECH } from '../../config/nexxusTech'
import { LEGAL_LINKS, NAV_ITEMS, isCopilotNavItem, isNavItemActive } from './navModel'

defineProps({
  visible: { type: Boolean, default: false },
  isDark: { type: Boolean, default: false },
  isFullscreen: { type: Boolean, default: false },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits([
  'update:visible',
  'toggle-theme',
  'toggle-fullscreen',
  'switch-classic',
  'logout'
])

const route = useRoute()
const navItems = NAV_ITEMS
const legalLinks = LEGAL_LINKS
const currentYear = new Date().getFullYear()

function isActive(item) {
  return isNavItemActive(item.path, route.path)
}

function close() {
  emit('update:visible', false)
}

function onFullscreen() {
  close()
  emit('toggle-fullscreen')
}
</script>

<!-- Teleported PrimeVue Drawer chrome (rendered on <body>, outside the scope
     hash). Only exists when the V2 shell is mounted; scoped to html.ui-v2 as
     extra insurance against any leak into the classic UI. -->
<style>
html.ui-v2 .p-drawer.v2-drawer {
  width: min(20rem, 88vw);
  border-right: 1px solid var(--v2-border);
  background: var(--v2-surface-glass-strong);
  backdrop-filter: blur(calc(var(--v2-blur) + 6px)) saturate(140%);
  -webkit-backdrop-filter: blur(calc(var(--v2-blur) + 6px)) saturate(140%);
  color: var(--v2-text);
  box-shadow: var(--v2-shadow-3);
}

html.ui-v2 .p-drawer.v2-drawer .p-drawer-header {
  display: none;
}

html.ui-v2 .p-drawer.v2-drawer .p-drawer-content {
  display: flex;
  padding: 0;
}
</style>

<style scoped>
.v2-drawer-body,
.v2-drawer-body * {
  box-sizing: border-box;
}

.v2-drawer-body {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  width: 100%;
  min-height: 100%;
  padding:
    calc(env(safe-area-inset-top, 0px) + 0.875rem)
    max(1rem, env(safe-area-inset-right, 0px))
    calc(env(safe-area-inset-bottom, 0px) + 1rem)
    max(1rem, env(safe-area-inset-left, 0px));
  overflow-y: auto;
}

.v2-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.v2-drawer-brand {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  min-width: 0;
  border-radius: var(--v2-radius-md);
  text-decoration: none;
}

.v2-drawer-brand:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
}

.v2-drawer-word {
  font-size: 1.25rem;
  letter-spacing: 0.01em;
}

.v2-drawer-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--v2-touch-target);
  height: var(--v2-touch-target);
  padding: 0;
  border: 1px solid var(--v2-border);
  border-radius: var(--v2-radius-full);
  background: transparent;
  color: var(--v2-text-2);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    background var(--v2-dur-fast) var(--v2-ease),
    color var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-drawer-close:active {
  transform: scale(0.9);
}

.v2-drawer-close:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
}

@media (hover: hover) {
  .v2-drawer-close:hover {
    background: var(--v2-surface-hover);
    color: var(--v2-text);
  }
}

.v2-drawer-nav,
.v2-drawer-actions {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.v2-drawer-link {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: var(--v2-touch-target);
  padding: 0.25rem 0.5rem;
  border: 1px solid transparent;
  border-radius: var(--v2-radius-md);
  background: transparent;
  color: var(--v2-text);
  font-size: 0.9375rem;
  font-weight: 500;
  font-family: inherit;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    background var(--v2-dur-fast) var(--v2-ease),
    border-color var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-drawer-link:active {
  transform: scale(0.98);
}

.v2-drawer-link:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: -2px;
}

@media (hover: hover) {
  .v2-drawer-link:hover {
    background: var(--v2-surface-hover);
    border-color: var(--v2-border);
  }
}

.v2-drawer-link-icon {
  position: relative;
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  margin-right: 0.5rem;
  flex-shrink: 0;
  color: var(--v2-text-2);
}

.v2-drawer-link-icon i {
  font-size: 1.1rem;
  line-height: 1;
}

.v2-drawer-link-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.v2-drawer-link-sub {
  font-size: 0.6875rem;
  font-weight: 500;
  color: var(--v2-text-3);
}

.v2-drawer-link-active {
  background: var(--v2-gradient-brand-soft);
  border-color: color-mix(in srgb, var(--v2-accent) 26%, transparent);
}

.v2-drawer-link-active .v2-drawer-link-icon,
.v2-drawer-link-active .v2-drawer-link-icon i {
  color: var(--p-primary-color);
}

.v2-drawer-beta {
  border-color: color-mix(in srgb, var(--v2-accent) 35%, transparent);
  background: var(--v2-gradient-brand-soft);
}

.v2-drawer-beta .v2-drawer-link-icon i {
  color: var(--p-primary-color);
}

.v2-drawer-logout,
.v2-drawer-logout .v2-drawer-link-icon {
  color: var(--p-red-500, #ef4444);
}

@media (hover: hover) {
  .v2-drawer-logout:hover {
    background: color-mix(in srgb, var(--p-red-500, #ef4444) 10%, transparent);
    border-color: color-mix(in srgb, var(--p-red-500, #ef4444) 30%, transparent);
  }
}

.v2-busy-dot {
  position: absolute;
  top: 0.4rem;
  right: 0.4rem;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--v2-gradient-brand);
  box-shadow: 0 0 0 3px var(--v2-accent-soft);
  animation: v2-busy-pulse-drawer 1.5s var(--v2-ease) infinite;
}

@keyframes v2-busy-pulse-drawer {
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

.v2-drawer-divider {
  height: 1px;
  margin: 0.5rem 0.25rem;
  background: var(--v2-border);
  flex-shrink: 0;
}

.v2-drawer-foot {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 1rem;
}

.v2-drawer-legal {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem 1rem;
}

.v2-drawer-legal a {
  color: var(--v2-text-2);
  font-size: 0.75rem;
  text-decoration: none;
  min-height: 1.75rem;
  display: inline-flex;
  align-items: center;
  transition: color var(--v2-dur-fast) var(--v2-ease);
}

.v2-drawer-legal a:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
  border-radius: var(--v2-radius-sm);
}

@media (hover: hover) {
  .v2-drawer-legal a:hover {
    color: var(--p-primary-color);
  }
}

.v2-drawer-copy {
  font-size: 0.75rem;
  color: var(--v2-text-3);
}

.v2-drawer-copy a {
  color: var(--v2-text-2);
  font-weight: 600;
  text-decoration: none;
}

@media (hover: hover) {
  .v2-drawer-copy a:hover {
    color: var(--p-primary-color);
  }
}

/* Staggered entrance replays on every open (Drawer mounts its content). */
.v2-drawer-stagger {
  animation: v2-drawer-in var(--v2-dur-slow) var(--v2-ease) backwards;
  animation-delay: calc(40ms + var(--stagger, 0) * 35ms);
}

@keyframes v2-drawer-in {
  from {
    opacity: 0;
    transform: translateX(-14px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .v2-drawer-stagger,
  .v2-busy-dot {
    animation: none !important;
  }
}
</style>
