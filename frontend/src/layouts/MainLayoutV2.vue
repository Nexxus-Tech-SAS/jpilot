<template>
  <div
    class="v2-shell"
    :class="{
      'v2-shell-immersive': isImmersiveChat,
      'app-shell-beta-immersive': isImmersiveChat,
      'v2-shell-collapsed': navCollapsed && isDesktopLayout
    }"
  >
    <V2NavRail
      :collapsed="navCollapsed && isDesktopLayout"
      :is-dark="isDark"
      :is-fullscreen="isFullscreen"
      :busy="hasActiveChatRuns"
      :user="currentUser"
      @toggle-collapse="onToggleNavCollapsed"
      @toggle-theme="onToggleTheme"
      @toggle-fullscreen="onToggleFullscreen"
      @open-user-menu="toggleUserMenu"
      @switch-classic="switchToClassic"
      @open-drawer="openMobileNav"
    />

    <div class="v2-shell-body">
      <V2TopBar
        v-if="!isImmersiveChat"
        :initials="userInitials"
        :username="currentUser?.username"
        @open-drawer="openMobileNav"
        @open-user-menu="toggleUserMenu"
      />

      <main
        class="v2-main main-content"
        :class="{ 'main-content-atmosphere': showAtmosphere }"
      >
        <BetaChatBackground
          v-if="showAtmosphere && isDesktopLayout"
          background-id="orbit"
          class="v2-atmosphere"
        />
        <div v-else-if="showAtmosphere" class="v2-atmosphere v2-atmosphere-lite" aria-hidden="true" />

        <div class="main-view">
          <router-view v-slot="{ Component }">
            <Transition name="v2-page" mode="out-in">
              <component :is="Component" :key="route.path" class="route-page" />
            </Transition>
          </router-view>
        </div>

        <footer v-if="!isImmersiveChat" class="v2-legal">
          <span class="v2-legal-copy">
            © {{ currentYear }}
            <a
              :href="NEXXUS_TECH.websiteUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="v2-legal-brand"
            >Nexxus Tech</a>
          </span>
          <nav class="v2-legal-links" aria-label="Legal">
            <RouterLink v-for="link in legalLinks" :key="link.path" :to="link.path">
              {{ link.short }}
            </RouterLink>
          </nav>
        </footer>
      </main>
    </div>

    <V2BottomNav v-if="!isImmersiveChat" :busy="hasActiveChatRuns" />

    <V2MobileDrawer
      v-model:visible="mobileNavOpen"
      :is-dark="isDark"
      :is-fullscreen="isFullscreen"
      :busy="hasActiveChatRuns"
      @toggle-theme="onToggleTheme"
      @toggle-fullscreen="onToggleFullscreen"
      @switch-classic="switchToClassic"
      @logout="logout"
    />

    <Menu ref="userMenu" :model="userMenuItems" popup />
    <ConfirmDialog />
    <Toast position="top-right" />
  </div>
</template>

<script setup>
// JPilot UI V2 shell. Contracts mirrored from the classic MainLayout:
// - nav item set / routes / `replace` navigation / isActive() semantics
// - onMounted GET /auth/me -> currentUser; 401/403 -> clearAuth() + /login
//   (viewport + fullscreen listeners attach BEFORE the await so a failed
//   /auth/me can never skip them — the classic shell has that bug)
// - logout(): best-effort POST /auth/logout, then clearAuth() + /login
// - provide('openMobileNav') for ChatPane's immersive hamburger
// - shell-level <Toast position="top-right"/> + <ConfirmDialog/>
// - .main-content-atmosphere wrapper class on atmosphere routes (global.css
//   frosted-glass rules key off it) + orbit backdrop at z-0, content at z-1
// - .main-view is THE scroll container; .route-page keeps the flex chain
// - immersive chat on route.name === 'jpilot' (chrome hidden, rail kept on
//   desktop/tablet, zero padding + overflow hidden + 100dvh on mobile)
// - sidebar collapse persisted via services/navSidebar.js (same boolean key)
// - theme changes only via services/theme.js toggleTheme()
import { computed, onMounted, onUnmounted, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ConfirmDialog from 'primevue/confirmdialog'
import Menu from 'primevue/menu'
import Toast from 'primevue/toast'
import BetaChatBackground from '../components/BetaChatBackground.vue'
import V2BottomNav from '../components/v2/V2BottomNav.vue'
import V2MobileDrawer from '../components/v2/V2MobileDrawer.vue'
import V2NavRail from '../components/v2/V2NavRail.vue'
import V2TopBar from '../components/v2/V2TopBar.vue'
import { LEGAL_LINKS } from '../components/v2/navModel'
import { NEXXUS_TECH } from '../config/nexxusTech'
import api from '../services/api'
import { clearAuth, getStoredUser } from '../services/auth'
import { getNavSidebarCollapsed, onNavSidebarChange, setNavSidebarCollapsed } from '../services/navSidebar'
import { currentAppliedTheme, toggleTheme } from '../services/theme'
import { setUiVersion, UI_CLASSIC } from '../services/uiVersion'
import { hasActiveChatRuns } from '../stores/copilotChatRuns'

const DESKTOP_BREAKPOINT = 992

const route = useRoute()
const router = useRouter()

const legalLinks = LEGAL_LINKS
const currentYear = new Date().getFullYear()

const currentUser = ref(getStoredUser())
const userMenu = ref(null)
const mobileNavOpen = ref(false)
const isDark = ref(currentAppliedTheme() === 'dark')
const isFullscreen = ref(false)
const navCollapsed = ref(getNavSidebarCollapsed())
const isDesktopLayout = ref(
  typeof window !== 'undefined' ? window.innerWidth >= DESKTOP_BREAKPOINT : true
)
let navSidebarCleanup = null

const isImmersiveChat = computed(() => route.name === 'jpilot')
const showAtmosphere = computed(() => route.meta.atmosphere === true)

const userInitials = computed(() => {
  const name = currentUser.value?.username || 'A'
  return name.slice(0, 2).toUpperCase()
})

const userMenuItems = computed(() => [
  {
    label: currentUser.value?.displayName || currentUser.value?.username || 'Account',
    items: [
      {
        label: 'Logout',
        icon: 'pi pi-sign-out',
        command: () => logout()
      }
    ]
  }
])

function toggleUserMenu(event) {
  userMenu.value?.toggle(event)
}

function openMobileNav() {
  mobileNavOpen.value = true
}

provide('openMobileNav', openMobileNav)

function closeMobileNav() {
  mobileNavOpen.value = false
}

function onToggleNavCollapsed() {
  const next = !navCollapsed.value
  setNavSidebarCollapsed(next)
  navCollapsed.value = next
}

function onToggleTheme() {
  isDark.value = toggleTheme() === 'dark'
}

function syncTheme() {
  isDark.value = currentAppliedTheme() === 'dark'
}

function switchToClassic() {
  // If the mobile drawer is open, let its leave transition finish first:
  // unmounting an open PrimeVue Drawer skips onAfterLeave and leaks its
  // document keydown listener (and the swap looks abrupt).
  if (mobileNavOpen.value) {
    closeMobileNav()
    window.setTimeout(() => setUiVersion(UI_CLASSIC), 450)
    return
  }
  setUiVersion(UI_CLASSIC)
}

function syncFullscreenState() {
  isFullscreen.value = Boolean(document.fullscreenElement)
}

async function onToggleFullscreen() {
  closeMobileNav()
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    } else {
      await document.documentElement.requestFullscreen()
    }
  } catch {
    // Unsupported or denied (common on iOS Safari).
  } finally {
    syncFullscreenState()
  }
}

function syncDesktopLayout() {
  isDesktopLayout.value = window.innerWidth >= DESKTOP_BREAKPOINT
}

function onViewportChange() {
  syncDesktopLayout()
  if (window.innerWidth >= DESKTOP_BREAKPOINT) {
    closeMobileNav()
  }
}

async function logout() {
  closeMobileNav()
  try {
    await api.post('/auth/logout')
  } catch {
    // Clear the local session even if the API call fails.
  } finally {
    clearAuth()
    router.push('/login')
  }
}

watch(
  () => route.path,
  () => {
    closeMobileNav()
  }
)

onMounted(async () => {
  // Attach environment listeners BEFORE awaiting /auth/me: a non-auth failure
  // must not leave the shell blind to rotations / fullscreen changes.
  window.addEventListener('resize', onViewportChange)
  document.addEventListener('fullscreenchange', syncFullscreenState)
  window.addEventListener('jpilot-theme-change', syncTheme)
  syncDesktopLayout()
  syncFullscreenState()
  navSidebarCleanup = onNavSidebarChange(() => {
    navCollapsed.value = getNavSidebarCollapsed()
  })

  try {
    const { data } = await api.get('/auth/me')
    currentUser.value = data
  } catch (error) {
    const status = error?.response?.status
    if (status === 401 || status === 403) {
      clearAuth()
      router.push('/login')
    }
  }
})

onUnmounted(() => {
  navSidebarCleanup?.()
  window.removeEventListener('resize', onViewportChange)
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  window.removeEventListener('jpilot-theme-change', syncTheme)
})
</script>

<style scoped>
/* ==========================================================================
   Shell frame: rail + column body, single fixed viewport, .main-view scrolls.
   Ambient brand glows sit on the shell so the glass rail has something to
   blur. All colors come from --v2-* tokens (they flip with html.app-dark).
   ========================================================================== */
.v2-shell,
.v2-shell-body,
.v2-main,
.v2-atmosphere,
.main-view,
.v2-legal {
  box-sizing: border-box;
}

.v2-shell {
  display: flex;
  height: 100dvh;
  overflow: hidden;
  padding-top: env(safe-area-inset-top, 0px);
  color: var(--v2-text);
  background:
    radial-gradient(60rem 40rem at -12% -20%, var(--v2-accent-soft), transparent 60%),
    radial-gradient(52rem 38rem at 112% 118%, var(--v2-accent-2-soft), transparent 62%),
    var(--v2-bg);
}

.v2-shell-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* --- Main area ---------------------------------------------------------- */
.v2-main {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  /* Right edge is exposed on notched landscape phones; the left edge is
     covered by the rail >=768px and mirrors the inset below that. */
  padding: 0 max(0.5rem, env(safe-area-inset-right, 0px)) 0
    max(0.5rem, env(safe-area-inset-left, 0px));
  overflow: hidden;
}

/* Orbit canvas (>=992px) or static gradient wash (below) behind the views. */
.v2-atmosphere {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

.v2-atmosphere-lite {
  background:
    radial-gradient(38rem 26rem at 10% -8%, var(--v2-accent-soft), transparent 62%),
    radial-gradient(34rem 26rem at 106% 12%, var(--v2-accent-2-soft), transparent 60%),
    radial-gradient(42rem 30rem at 50% 118%, color-mix(in srgb, var(--v2-accent) 7%, transparent), transparent 65%);
}

/* THE scroll container — views (chat especially) rely on this flex chain. */
.main-view {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: auto;
}

.main-view :deep(.route-page) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* --- Legal footer (desktop + tablet; lives in the drawer on phones) ------ */
.v2-legal {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  margin-top: auto;
  padding: 0.5rem 0.75rem max(0.5rem, env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--v2-border);
  font-size: 0.75rem;
  color: var(--v2-text-3);
}

.v2-legal-brand {
  color: var(--v2-text-2);
  font-weight: 600;
  text-decoration: none;
  transition: color var(--v2-dur-fast) var(--v2-ease);
}

.v2-legal-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
}

.v2-legal-links a {
  color: var(--v2-text-2);
  text-decoration: none;
  transition: color var(--v2-dur-fast) var(--v2-ease);
}

.v2-legal-links a:focus-visible,
.v2-legal-brand:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
  border-radius: var(--v2-radius-sm);
}

@media (hover: hover) {
  .v2-legal-links a:hover,
  .v2-legal-brand:hover {
    color: var(--p-primary-color);
  }
}

/* --- Page transition: fade + rise ---------------------------------------- */
.v2-page-enter-active,
.v2-page-leave-active {
  transition:
    opacity var(--v2-dur) var(--v2-ease),
    transform var(--v2-dur) var(--v2-ease);
}

.v2-page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.v2-page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* --- Immersive chat (route.name === 'jpilot') ----------------------------
   Chrome is hidden via v-if; ChatPane owns its own chrome and scroll. */
.v2-shell-immersive .v2-main {
  padding: 0;
  gap: 0;
}

/* --- Phones (<768px): topbar + drawer + floating dock --------------------- */
@media (max-width: 767.98px) {
  .v2-main {
    padding: 0.75rem 0.75rem calc(4.75rem + env(safe-area-inset-bottom, 0px));
  }

  .v2-legal {
    display: none;
  }
}

/* Mobile immersive chat: zero padding, hidden overflow, 100dvh containment. */
@media (max-width: 991.98px) {
  .v2-shell-immersive {
    height: 100dvh;
    max-height: 100dvh;
  }

  .v2-shell-immersive .v2-main {
    padding: 0;
    overflow: hidden;
  }
}

/* --- Reduced motion -------------------------------------------------------- */
@media (prefers-reduced-motion: reduce) {
  .v2-page-enter-active,
  .v2-page-leave-active {
    transition: none !important;
  }
}
</style>
