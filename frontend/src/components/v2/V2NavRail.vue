<template>
  <aside
    class="v2-rail"
    :class="{ 'v2-rail-collapsed': collapsed }"
    aria-label="Main navigation"
  >
    <div class="v2-rail-brand v2-rail-stagger" style="--stagger: 0">
      <RouterLink to="/" replace class="v2-rail-brand-link" aria-label="JPilot dashboard">
        <span class="v2-rail-mark-box">
          <JPilotMark variant="full" :size="38" class="v2-rail-mark" />
        </span>
        <span class="v2-rail-label v2-rail-word jp-wordmark">JPilot</span>
      </RouterLink>

      <button
        type="button"
        class="v2-rail-collapse"
        :aria-label="collapsed ? 'Expand navigation' : 'Collapse navigation'"
        :aria-expanded="!collapsed"
        @click="$emit('toggle-collapse')"
      >
        <i class="pi pi-angle-left" aria-hidden="true" />
      </button>
    </div>

    <!-- Tablet-only hamburger: opens the labelled drawer from the icon rail. -->
    <button
      type="button"
      class="v2-rail-menu"
      aria-label="Open menu"
      @click="$emit('open-drawer')"
    >
      <i class="pi pi-bars" aria-hidden="true" />
    </button>

    <nav ref="navEl" class="v2-rail-nav" aria-label="Primary">
      <span
        class="v2-nav-indicator"
        :class="{ 'v2-nav-indicator-ready': indicatorReady }"
        :style="indicatorStyle"
        aria-hidden="true"
      />

      <RouterLink
        v-for="(item, i) in primaryItems"
        :key="item.path"
        :ref="(el) => setItemRef(item.path, el)"
        v-tooltip.right="labelsHidden ? item.label : null"
        :to="item.path"
        replace
        class="v2-nav-item v2-rail-stagger"
        :class="{ 'v2-nav-item-active': isActive(item) }"
        :style="{ '--stagger': i + 1 }"
      >
        <span class="v2-nav-icon">
          <i :class="item.icon" aria-hidden="true" />
          <span v-if="isCopilotNavItem(item) && busy" class="v2-busy-dot" aria-hidden="true" />
        </span>
        <span class="v2-rail-label v2-nav-text">{{ item.label }}</span>
      </RouterLink>

      <div
        class="v2-rail-divider v2-rail-stagger"
        :style="{ '--stagger': primaryItems.length + 1 }"
        aria-hidden="true"
      />

      <RouterLink
        v-for="(item, i) in secondaryItems"
        :key="item.path"
        :ref="(el) => setItemRef(item.path, el)"
        v-tooltip.right="labelsHidden ? item.label : null"
        :to="item.path"
        replace
        class="v2-nav-item v2-rail-stagger"
        :class="{ 'v2-nav-item-active': isActive(item) }"
        :style="{ '--stagger': i + primaryItems.length + 2 }"
      >
        <span class="v2-nav-icon">
          <i :class="item.icon" aria-hidden="true" />
          <span v-if="isCopilotNavItem(item) && busy" class="v2-busy-dot" aria-hidden="true" />
        </span>
        <span class="v2-rail-label v2-nav-text">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="v2-rail-footer">
      <button
        v-tooltip.right="'Switch back to the classic UI'"
        type="button"
        class="v2-beta-pill v2-rail-stagger"
        :style="{ '--stagger': navItemCount + 2 }"
        @click="$emit('switch-classic')"
      >
        <span class="v2-nav-icon"><i class="pi pi-sparkles" aria-hidden="true" /></span>
        <span class="v2-rail-label v2-beta-pill-text">New UI · Beta</span>
      </button>

      <div class="v2-rail-actions v2-rail-stagger" :style="{ '--stagger': navItemCount + 3 }">
        <button
          v-tooltip.right="isDark ? 'Switch to light' : 'Switch to dark'"
          type="button"
          class="v2-rail-action"
          :aria-label="isDark ? 'Switch to light theme' : 'Switch to dark theme'"
          @click="$emit('toggle-theme')"
        >
          <V2SunMoonIcon :dark="isDark" />
        </button>

        <button
          v-tooltip.right="isFullscreen ? 'Exit full screen' : 'Full screen'"
          type="button"
          class="v2-rail-action"
          :aria-label="isFullscreen ? 'Exit full screen' : 'Enter full screen'"
          @click="$emit('toggle-fullscreen')"
        >
          <i :class="isFullscreen ? 'pi pi-window-minimize' : 'pi pi-window-maximize'" aria-hidden="true" />
        </button>
      </div>

      <button
        v-tooltip.right="labelsHidden ? (user?.username || 'Account') : null"
        type="button"
        class="v2-user-card v2-rail-stagger"
        :style="{ '--stagger': navItemCount + 4 }"
        :aria-label="user?.username || 'Account'"
        @click="(event) => $emit('open-user-menu', event)"
      >
        <span class="v2-nav-icon v2-user-avatar-box">
          <Avatar :label="userInitials" shape="circle" class="v2-avatar" />
        </span>
        <span class="v2-rail-label v2-user-meta">
          <span class="v2-user-name">{{ userName }}</span>
          <span class="v2-user-sub">{{ userSub }}</span>
        </span>
        <i class="pi pi-ellipsis-v v2-rail-label v2-user-caret" aria-hidden="true" />
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Avatar from 'primevue/avatar'
import JPilotMark from '../JPilotMark.vue'
import V2SunMoonIcon from './V2SunMoonIcon.vue'
import { NAV_ITEMS, NAV_PRIMARY, NAV_SECONDARY, isCopilotNavItem, isNavItemActive } from './navModel'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  isDark: { type: Boolean, default: false },
  isFullscreen: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  user: { type: Object, default: null }
})

defineEmits([
  'toggle-collapse',
  'toggle-theme',
  'toggle-fullscreen',
  'open-user-menu',
  'switch-classic',
  'open-drawer'
])

const route = useRoute()

const primaryItems = NAV_PRIMARY
const secondaryItems = NAV_SECONDARY
const navItemCount = NAV_ITEMS.length

// Tablet band (768-991px) shows the icon-only rail without the collapsed
// prop being set — labels are hidden there too, so tooltips must engage.
const TABLET_BAND_MQL = '(min-width: 768px) and (max-width: 991.98px)'
const tabletBandMedia = typeof window !== 'undefined' ? window.matchMedia(TABLET_BAND_MQL) : null
const isTabletBand = ref(Boolean(tabletBandMedia?.matches))
function onTabletBandChange(event) {
  isTabletBand.value = event.matches
}
const labelsHidden = computed(() => props.collapsed || isTabletBand.value)

const userInitials = computed(() => (props.user?.username || 'A').slice(0, 2).toUpperCase())
const userName = computed(() => props.user?.displayName || props.user?.username || 'Account')
const userSub = computed(() => {
  const role = props.user?.role
  if (role) return role.charAt(0).toUpperCase() + role.slice(1)
  return 'Signed in'
})

function isActive(item) {
  return isNavItemActive(item.path, route.path)
}

/* ------------------------------------------------------------------ *
 * Sliding active indicator: an accent pill measured against the real
 * item positions so it glides between entries on every route change.
 * ------------------------------------------------------------------ */
const navEl = ref(null)
const itemEls = new Map()
const indicatorReady = ref(false)
const indicatorVisible = ref(false)
const indicatorY = ref(0)
const indicatorH = ref(44)
let mounted = false

const indicatorStyle = computed(() => ({
  opacity: indicatorVisible.value ? '1' : '0',
  transform: `translateY(${indicatorY.value}px)`,
  height: `${indicatorH.value}px`
}))

function setItemRef(path, el) {
  const node = el?.$el ?? el
  if (node) itemEls.set(path, node)
  else itemEls.delete(path)
}

function updateIndicator() {
  if (!mounted || !navEl.value) return
  const active = NAV_ITEMS.find((item) => isNavItemActive(item.path, route.path))
  const node = active ? itemEls.get(active.path) : null
  if (!node) {
    indicatorVisible.value = false
    return
  }
  indicatorVisible.value = true
  indicatorY.value = node.offsetTop
  indicatorH.value = node.offsetHeight
}

function onWindowResize() {
  updateIndicator()
}

watch(
  () => route.path,
  () => {
    nextTick(updateIndicator)
  }
)

watch(
  () => props.collapsed,
  () => {
    nextTick(updateIndicator)
    // Re-measure once the width transition has settled, just in case.
    window.setTimeout(updateIndicator, 460)
  }
)

onMounted(() => {
  mounted = true
  window.addEventListener('resize', onWindowResize)
  nextTick(() => {
    updateIndicator()
    // Enable transitions only after the first placement so the pill does
    // not animate in from the top of the rail on mount.
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        indicatorReady.value = true
      })
    })
  })
  try {
    document.fonts?.ready?.then(() => updateIndicator())
  } catch {
    /* older browsers: initial measure is good enough */
  }
  tabletBandMedia?.addEventListener('change', onTabletBandChange)
})

onBeforeUnmount(() => {
  mounted = false
  window.removeEventListener('resize', onWindowResize)
  tabletBandMedia?.removeEventListener('change', onTabletBandChange)
})
</script>

<style scoped>
/* ==========================================================================
   Rail geometry is driven by a single --compact custom property (0 = wide,
   1 = icon rail) so the desktop collapse *and* the tablet CSS-only compact
   band share the exact same math and animate coherently.
   ========================================================================== */
.v2-rail,
.v2-rail * {
  box-sizing: border-box;
}

.v2-rail {
  --compact: 0;
  --rail-pad-x: calc(0.75rem - var(--compact) * 0.3125rem);
  position: relative;
  z-index: 40;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  width: calc(15.5rem - var(--compact) * 10.75rem);
  height: 100%;
  padding-left: env(safe-area-inset-left, 0px);
  background: var(--v2-surface-glass);
  backdrop-filter: blur(var(--v2-blur)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--v2-blur)) saturate(140%);
  border-right: 1px solid var(--v2-border);
  transition: width var(--v2-dur-slow) var(--v2-ease);
}

.v2-rail-collapsed {
  --compact: 1;
}

/* Labels collapse smoothly with the rail: width, gap and opacity together. */
.v2-rail-label {
  flex: 0 1 auto;
  min-width: 0;
  max-width: calc((1 - var(--compact)) * 11rem);
  margin-left: calc((1 - var(--compact)) * 0.625rem);
  opacity: calc(1 - var(--compact));
  transform: translateX(calc(var(--compact) * -0.5rem));
  white-space: nowrap;
  overflow: hidden;
  transition:
    max-width var(--v2-dur-slow) var(--v2-ease),
    margin-left var(--v2-dur-slow) var(--v2-ease),
    opacity var(--v2-dur) var(--v2-ease),
    transform var(--v2-dur-slow) var(--v2-ease);
}

/* --- Brand ---------------------------------------------------------- */
.v2-rail-brand {
  position: relative;
  display: flex;
  align-items: center;
  padding: 0.875rem var(--rail-pad-x) 0.5rem;
  transition: padding var(--v2-dur-slow) var(--v2-ease);
}

.v2-rail-brand-link {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  border-radius: var(--v2-radius-md);
  text-decoration: none;
}

.v2-rail-brand-link:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
}

.v2-rail-mark-box {
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  flex-shrink: 0;
}

.v2-rail-word {
  font-size: 1.125rem;
  letter-spacing: 0.01em;
}

/* Collapse chevron: hangs off the rail edge, appears on hover. */
.v2-rail-collapse {
  position: absolute;
  top: 50%;
  right: -0.8125rem;
  z-index: 6;
  display: grid;
  place-items: center;
  width: 1.625rem;
  height: 1.625rem;
  margin-top: -0.8125rem;
  padding: 0;
  border: 1px solid var(--v2-border-strong);
  border-radius: var(--v2-radius-full);
  background: var(--v2-surface);
  color: var(--v2-text-2);
  box-shadow: var(--v2-shadow-1);
  cursor: pointer;
  transition:
    opacity var(--v2-dur-fast) var(--v2-ease),
    color var(--v2-dur-fast) var(--v2-ease),
    border-color var(--v2-dur-fast) var(--v2-ease),
    box-shadow var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-rail-collapse i {
  font-size: 0.8rem;
  transition: transform var(--v2-dur-slow) var(--v2-ease-spring);
}

/* Touch devices need the full 44px hit area (visual stays a small chip). */
@media (pointer: coarse) {
  .v2-rail-collapse {
    width: var(--v2-touch-target);
    height: var(--v2-touch-target);
    margin-top: calc(var(--v2-touch-target) / -2);
    right: calc(var(--v2-touch-target) / -2);
  }
}

.v2-rail-collapsed .v2-rail-collapse i {
  transform: rotate(180deg);
}

.v2-rail-collapse:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
  opacity: 1;
}

.v2-rail-collapse:active {
  transform: scale(0.9);
}

@media (hover: hover) {
  .v2-rail-collapse {
    opacity: 0;
  }

  .v2-rail:hover .v2-rail-collapse,
  .v2-rail-collapse:focus-visible,
  .v2-rail-collapsed .v2-rail-collapse {
    opacity: 1;
  }

  .v2-rail-collapse:hover {
    color: var(--p-primary-color);
    border-color: var(--v2-accent);
    box-shadow: var(--v2-glow-accent);
  }
}

/* --- Tablet hamburger (hidden outside 768-991px) --------------------- */
.v2-rail-menu {
  display: none;
  place-items: center;
  width: calc(100% - 2 * var(--rail-pad-x));
  min-height: var(--v2-touch-target);
  margin: 0.125rem var(--rail-pad-x) 0;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--v2-radius-md);
  background: transparent;
  color: var(--v2-text-2);
  cursor: pointer;
  transition: background var(--v2-dur-fast) var(--v2-ease), color var(--v2-dur-fast) var(--v2-ease);
}

.v2-rail-menu i {
  font-size: 1.05rem;
}

.v2-rail-menu:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
}

/* --- Nav ------------------------------------------------------------- */
.v2-rail-nav {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-height: 0;
  padding: 0.5rem var(--rail-pad-x) 0.75rem;
  overflow-y: auto;
  overflow-x: hidden;
  transition: padding var(--v2-dur-slow) var(--v2-ease);
}

.v2-nav-item {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  min-height: var(--v2-touch-target);
  padding: 0 0.5rem;
  border-radius: var(--v2-radius-md);
  color: var(--v2-text-2);
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  overflow: hidden;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
  cursor: pointer;
  transition:
    color var(--v2-dur-fast) var(--v2-ease),
    background var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-nav-item:active {
  transform: scale(0.97);
}

.v2-nav-item:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: -2px;
}

.v2-nav-icon {
  position: relative;
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  flex-shrink: 0;
}

.v2-nav-icon i {
  font-size: 1.05rem;
  line-height: 1;
  transition:
    transform var(--v2-dur-fast) var(--v2-ease-spring),
    color var(--v2-dur-fast) var(--v2-ease);
}

@media (hover: hover) {
  .v2-nav-item:hover {
    background: var(--v2-surface-hover);
    color: var(--v2-text);
  }

  .v2-nav-item:hover .v2-nav-icon i {
    transform: translateX(1px) scale(1.12);
    color: var(--p-primary-color);
  }
}

.v2-nav-item:active .v2-nav-icon i {
  transform: scale(0.88);
}

.v2-nav-item-active {
  color: var(--v2-text);
}

.v2-nav-item-active .v2-nav-icon i {
  color: var(--p-primary-color);
}

.v2-nav-text {
  text-overflow: ellipsis;
}

/* Sliding accent pill behind the active item. */
.v2-nav-indicator {
  position: absolute;
  z-index: 0;
  top: 0;
  left: var(--rail-pad-x);
  right: var(--rail-pad-x);
  height: 2.75rem;
  border-radius: var(--v2-radius-md);
  background: var(--v2-gradient-brand-soft);
  border: 1px solid color-mix(in srgb, var(--v2-accent) 26%, transparent);
  box-shadow: 0 2px 12px color-mix(in srgb, var(--v2-accent) 12%, transparent);
  opacity: 0;
  pointer-events: none;
}

.v2-nav-indicator::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--rail-pad-x));
  top: 24%;
  bottom: 24%;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--v2-gradient-brand);
}

.v2-nav-indicator-ready {
  transition:
    transform var(--v2-dur-slow) var(--v2-ease-spring),
    height var(--v2-dur) var(--v2-ease),
    opacity var(--v2-dur) var(--v2-ease),
    left var(--v2-dur-slow) var(--v2-ease),
    right var(--v2-dur-slow) var(--v2-ease);
}

.v2-rail-divider {
  height: 1px;
  margin: 0.5rem 0.25rem;
  background: var(--v2-border);
  flex-shrink: 0;
}

/* Busy pulse dot (Chat while runs are in flight). */
.v2-busy-dot {
  position: absolute;
  top: 0.45rem;
  right: 0.45rem;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--v2-gradient-brand);
  box-shadow: 0 0 0 3px var(--v2-accent-soft);
  animation: v2-busy-pulse 1.5s var(--v2-ease) infinite;
}

@keyframes v2-busy-pulse {
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

/* --- Footer ----------------------------------------------------------- */
.v2-rail-footer {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.625rem var(--rail-pad-x) calc(0.75rem + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--v2-border);
  transition: padding var(--v2-dur-slow) var(--v2-ease);
}

.v2-beta-pill {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 2.75rem;
  padding: 0 0.5rem;
  border: 1px solid color-mix(in srgb, var(--v2-accent) 35%, transparent);
  border-radius: var(--v2-radius-full);
  background: var(--v2-gradient-brand-soft);
  color: var(--v2-text);
  cursor: pointer;
  overflow: hidden;
  -webkit-tap-highlight-color: transparent;
  transition:
    border-color var(--v2-dur-fast) var(--v2-ease),
    box-shadow var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-beta-pill .v2-nav-icon i {
  color: var(--p-primary-color);
}

.v2-beta-pill-text {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

/* Occasional shimmer sweep across the pill. */
.v2-beta-pill::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -60%;
  width: 45%;
  background: linear-gradient(
    105deg,
    transparent 0%,
    color-mix(in srgb, var(--v2-accent) 18%, transparent) 50%,
    transparent 100%
  );
  transform: skewX(-18deg);
  animation: v2-shimmer 6s var(--v2-ease) infinite;
  pointer-events: none;
}

@keyframes v2-shimmer {
  0%,
  72% {
    left: -60%;
  }
  100% {
    left: 130%;
  }
}

.v2-beta-pill:active {
  transform: scale(0.97);
}

.v2-beta-pill:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
}

@media (hover: hover) {
  .v2-beta-pill:hover {
    border-color: var(--v2-accent);
    box-shadow: var(--v2-glow-accent);
  }
}

/* Theme + fullscreen: a row when wide, auto-wraps to a column when compact. */
.v2-rail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.v2-rail-action {
  flex: 1 1 2.75rem;
  display: grid;
  place-items: center;
  min-height: 2.75rem;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--v2-radius-md);
  background: transparent;
  color: var(--v2-text-2);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    background var(--v2-dur-fast) var(--v2-ease),
    color var(--v2-dur-fast) var(--v2-ease),
    border-color var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-rail-action i {
  font-size: 1.05rem;
}

.v2-rail-action:active {
  transform: scale(0.92);
}

.v2-rail-action:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: -2px;
}

@media (hover: hover) {
  .v2-rail-action:hover {
    background: var(--v2-surface-hover);
    color: var(--v2-text);
    border-color: var(--v2-border);
  }
}

/* User card. */
.v2-user-card {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 3.25rem;
  padding: 0.25rem 0.375rem;
  border: 1px solid var(--v2-border);
  border-radius: var(--v2-radius-md);
  background: var(--v2-surface-hover);
  color: var(--v2-text);
  text-align: left;
  overflow: hidden;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    border-color var(--v2-dur-fast) var(--v2-ease),
    background var(--v2-dur-fast) var(--v2-ease),
    box-shadow var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-user-card:active {
  transform: scale(0.98);
}

.v2-user-card:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
}

@media (hover: hover) {
  .v2-user-card:hover {
    border-color: var(--v2-border-strong);
    background: var(--v2-surface-active);
    box-shadow: var(--v2-shadow-1);
  }
}

.v2-user-avatar-box {
  width: 2.5rem;
  height: 2.5rem;
}

.v2-avatar {
  width: 2.125rem !important;
  height: 2.125rem !important;
  background: var(--v2-gradient-brand) !important;
  color: var(--v2-text-on-accent) !important;
  font-size: 0.7rem !important;
  font-weight: 700 !important;
}

.v2-user-meta {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  gap: 1px;
}

.v2-user-name {
  font-size: 0.8125rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v2-user-sub {
  font-size: 0.6875rem;
  color: var(--v2-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
}

.v2-user-caret {
  flex: 0 0 auto;
  font-size: 0.8rem;
  color: var(--v2-text-3);
  margin-left: calc((1 - var(--compact)) * 0.25rem);
}

/* --- Staggered entrance ----------------------------------------------- */
.v2-rail-stagger {
  animation: v2-rail-in var(--v2-dur-slow) var(--v2-ease) backwards;
  animation-delay: calc(60ms + var(--stagger, 0) * 40ms);
}

@keyframes v2-rail-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* --- Responsive bands -------------------------------------------------- */
/* Tablet 768-991px: always the compact icon rail (pure CSS, no JS state). */
@media (min-width: 768px) and (max-width: 991.98px) {
  .v2-rail {
    --compact: 1;
    width: 4.75rem;
  }

  .v2-rail-collapse {
    display: none;
  }

  .v2-rail-menu {
    display: grid;
  }
}

/* Phones: the rail disappears entirely (topbar + drawer + bottom nav). */
@media (max-width: 767.98px) {
  .v2-rail {
    display: none;
  }
}

/* Short viewports: tighten vertical rhythm so all controls stay reachable. */
@media (max-height: 600px) {
  .v2-rail-brand {
    padding-top: 0.5rem;
    padding-bottom: 0.25rem;
  }

  .v2-rail-nav {
    gap: 0.125rem;
  }

  .v2-rail-footer {
    gap: 0.25rem;
    padding-top: 0.375rem;
  }
}

/* --- Reduced motion ------------------------------------------------------ */
@media (prefers-reduced-motion: reduce) {
  .v2-rail-stagger,
  .v2-busy-dot,
  .v2-beta-pill::after {
    animation: none !important;
  }

  .v2-rail,
  .v2-rail-label,
  .v2-nav-indicator-ready,
  .v2-nav-item,
  .v2-nav-icon i,
  .v2-rail-collapse,
  .v2-rail-collapse i {
    transition: none !important;
  }
}
</style>
