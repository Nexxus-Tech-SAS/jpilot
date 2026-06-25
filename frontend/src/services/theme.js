// App-wide light/dark theme. PrimeVue is configured with darkModeSelector '.app-dark',
// so toggling that class on <html> flips every PrimeVue component.
// Persisted in localStorage only when the user chose Accept all (see cookieConsent.js).
import {
  allowsPreferenceStorage,
  CONSENT_ACCEPTED,
  CONSENT_ESSENTIAL
} from './cookieConsent'

const KEY = 'jpilot_theme'
const DARK_CLASS = 'app-dark'

/** Session-only theme when preference storage is not allowed. */
let sessionTheme = null

function systemTheme() {
  if (typeof window === 'undefined' || !window.matchMedia) return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function readPersistedTheme() {
  if (!allowsPreferenceStorage()) return null
  try {
    const value = localStorage.getItem(KEY)
    return value === 'dark' || value === 'light' ? value : null
  } catch {
    return null
  }
}

function writePersistedTheme(theme) {
  if (!allowsPreferenceStorage()) return
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // Ignore quota / private-mode failures.
  }
}

function removePersistedTheme() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Ignore.
  }
}

export function currentAppliedTheme() {
  if (typeof document === 'undefined') return systemTheme()
  return document.documentElement.classList.contains(DARK_CLASS) ? 'dark' : 'light'
}

export function getTheme() {
  const persisted = readPersistedTheme()
  if (persisted) return persisted
  if (sessionTheme === 'dark' || sessionTheme === 'light') return sessionTheme
  return systemTheme()
}

export function applyTheme(theme) {
  document.documentElement.classList.toggle(DARK_CLASS, theme === 'dark')
}

export function setTheme(theme) {
  if (theme !== 'dark' && theme !== 'light') return
  if (allowsPreferenceStorage()) {
    writePersistedTheme(theme)
    sessionTheme = null
  } else {
    sessionTheme = theme
  }
  applyTheme(theme)
  window.dispatchEvent(new CustomEvent('jpilot-theme-change', { detail: theme }))
}

export function applyStoredTheme() {
  applyTheme(getTheme())
}

export function toggleTheme() {
  const next = getTheme() === 'dark' ? 'light' : 'dark'
  setTheme(next)
  return next
}

/** Drop persisted theme; keep the current look for this browser session. */
export function clearThemePreference() {
  removePersistedTheme()
  sessionTheme = currentAppliedTheme()
}

/** Save the theme currently on screen (after Accept all). */
export function persistThemePreference() {
  const theme = currentAppliedTheme()
  sessionTheme = null
  writePersistedTheme(theme)
}

export function handleCookieConsentChange(detail) {
  if (detail === CONSENT_ACCEPTED) {
    persistThemePreference()
    window.dispatchEvent(new CustomEvent('jpilot-theme-change', { detail: getTheme() }))
    return
  }
  if (detail === CONSENT_ESSENTIAL) {
    clearThemePreference()
    applyTheme(getTheme())
    window.dispatchEvent(new CustomEvent('jpilot-theme-change', { detail: getTheme() }))
  }
}

export function initThemeConsentListener() {
  if (typeof window === 'undefined') return
  window.addEventListener('jpilot-cookie-consent-change', (event) => {
    handleCookieConsentChange(event.detail)
  })
}
