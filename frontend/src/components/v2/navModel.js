/**
 * JPilot UI V2 — shared navigation model for the shell components
 * (rail, mobile drawer, bottom nav). Mirrors the classic MainLayout nav
 * data exactly: same labels, routes, icons, `replace` navigation and
 * isActive() semantics. Do not add/remove items without updating classic.
 */

export const NAV_PRIMARY = [
  { label: 'Dashboard', shortLabel: 'Dashboard', path: '/', icon: 'pi pi-home' },
  { label: 'Chat', shortLabel: 'Chat', path: '/jpilot', icon: 'pi pi-sparkles' }
]

export const NAV_SECONDARY = [
  { label: 'Plans', shortLabel: 'Plans', path: '/plans', icon: 'pi pi-tags' },
  { label: 'Calibration Studio', shortLabel: 'Studio', path: '/calibration-studio', icon: 'pi pi-sliders-h' },
  { label: 'Settings', shortLabel: 'Settings', path: '/settings', icon: 'pi pi-cog' }
]

export const NAV_ITEMS = [...NAV_PRIMARY, ...NAV_SECONDARY]

export const LEGAL_LINKS = [
  { label: 'Privacy Policy', short: 'Privacy', path: '/legal/privacy' },
  { label: 'Terms of Service', short: 'Terms', path: '/legal/terms' },
  { label: 'EULA', short: 'EULA', path: '/legal/eula' },
  { label: 'Acceptable Use', short: 'Acceptable Use', path: '/legal/acceptable-use' }
]

/** Exact classic MainLayout.isActive() semantics. */
export function isNavItemActive(itemPath, routePath) {
  if (itemPath === '/') return routePath === '/'
  if (itemPath === '/jpilot') return routePath === '/jpilot'
  if (itemPath === '/jpilot/beta') return routePath === '/jpilot/beta'
  return routePath.startsWith(itemPath)
}

/** The Chat item shows a busy pulse while chat runs are in flight. */
export function isCopilotNavItem(item) {
  return item.path === '/jpilot' || item.path === '/jpilot/beta'
}
