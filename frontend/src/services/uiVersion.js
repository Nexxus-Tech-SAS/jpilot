// Switch between the classic UI and the redesigned V2 experience.
// Mirrors theme.js: toggles a 'ui-v2' class on <html> so scoped v2 stylesheets
// (and PrimeVue overlays teleported to <body>) all react, and persists the choice
// in localStorage only when the user chose Accept all (see cookieConsent.js).
import { ref, readonly } from 'vue'
import {
  allowsPreferenceStorage,
  CONSENT_ACCEPTED,
  CONSENT_ESSENTIAL
} from './cookieConsent'

const KEY = 'jpilot_ui_version'
const V2_CLASS = 'ui-v2'

export const UI_CLASSIC = 'classic'
export const UI_V2 = 'v2'

/** Session-only choice when preference storage is not allowed. */
let sessionVersion = null

const uiVersionRef = ref(UI_CLASSIC)

function isValidVersion(value) {
  return value === UI_CLASSIC || value === UI_V2
}

function readPersistedVersion() {
  if (!allowsPreferenceStorage()) return null
  try {
    const value = localStorage.getItem(KEY)
    return isValidVersion(value) ? value : null
  } catch {
    return null
  }
}

function writePersistedVersion(version) {
  if (!allowsPreferenceStorage()) return
  try {
    localStorage.setItem(KEY, version)
  } catch {
    // Ignore quota / private-mode failures.
  }
}

function removePersistedVersion() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Ignore.
  }
}

export function currentAppliedUiVersion() {
  if (typeof document === 'undefined') return UI_CLASSIC
  return document.documentElement.classList.contains(V2_CLASS) ? UI_V2 : UI_CLASSIC
}

export function getUiVersion() {
  const persisted = readPersistedVersion()
  if (persisted) return persisted
  if (isValidVersion(sessionVersion)) return sessionVersion
  return UI_CLASSIC
}

export function applyUiVersion(version) {
  const next = version === UI_V2 ? UI_V2 : UI_CLASSIC
  document.documentElement.classList.toggle(V2_CLASS, next === UI_V2)
  uiVersionRef.value = next
}

export function setUiVersion(version) {
  if (!isValidVersion(version)) return
  if (allowsPreferenceStorage()) {
    writePersistedVersion(version)
    sessionVersion = null
  } else {
    sessionVersion = version
  }
  applyUiVersion(version)
  window.dispatchEvent(new CustomEvent('jpilot-ui-version-change', { detail: version }))
}

export function toggleUiVersion() {
  const next = getUiVersion() === UI_V2 ? UI_CLASSIC : UI_V2
  setUiVersion(next)
  return next
}

export function applyStoredUiVersion() {
  applyUiVersion(getUiVersion())
}

/** Reactive read-only ref for components (LayoutGate, settings toggle). */
export function useUiVersion() {
  return readonly(uiVersionRef)
}

/** Drop persisted choice; keep the current UI for this browser session. */
export function clearUiVersionPreference() {
  removePersistedVersion()
  sessionVersion = currentAppliedUiVersion()
}

/** Save the UI version currently on screen (after Accept all). */
export function persistUiVersionPreference() {
  const version = currentAppliedUiVersion()
  sessionVersion = null
  writePersistedVersion(version)
}

export function handleCookieConsentChange(detail) {
  if (detail === CONSENT_ACCEPTED) {
    persistUiVersionPreference()
    window.dispatchEvent(new CustomEvent('jpilot-ui-version-change', { detail: getUiVersion() }))
    return
  }
  if (detail === CONSENT_ESSENTIAL) {
    clearUiVersionPreference()
    applyUiVersion(getUiVersion())
    window.dispatchEvent(new CustomEvent('jpilot-ui-version-change', { detail: getUiVersion() }))
  }
}

export function initUiVersionConsentListener() {
  if (typeof window === 'undefined') return
  window.addEventListener('jpilot-cookie-consent-change', (event) => {
    handleCookieConsentChange(event.detail)
  })
}
