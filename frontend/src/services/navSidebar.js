/** Device-local collapsed state for the main JPilot navigation sidebar. */

const STORAGE_KEY = 'jpilot_nav_sidebar_collapsed_v1'
const CHANGE_EVENT = 'jpilot-nav-sidebar-change'

function readCollapsed() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function getNavSidebarCollapsed() {
  return readCollapsed()
}

export function setNavSidebarCollapsed(collapsed) {
  try {
    localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT))
  } catch {
    /* ignore */
  }
}

/** @param {(event: Event) => void} listener */
export function onNavSidebarChange(listener) {
  window.addEventListener(CHANGE_EVENT, listener)
  return () => window.removeEventListener(CHANGE_EVENT, listener)
}
