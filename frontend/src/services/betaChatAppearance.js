/** Device-local glass transparency for JPilot beta chat panels. */

const STORAGE_KEYS = {
  main: {
    panel: 'jpilot_beta_chat_panel_transparency_v1',
    sidebar: 'jpilot_beta_chat_sidebar_transparency_v1'
  },
  lab: {
    panel: 'jpilot_beta_lab_chat_panel_transparency_v1',
    sidebar: 'jpilot_beta_lab_chat_sidebar_transparency_v1'
  }
}

/** @typedef {'main'|'lab'} BetaChatNamespace */

/** Transparency 0 (opaque) – 100 (fully see-through). */
export const BETA_CHAT_TRANSPARENCY_DEFAULTS = {
  main: { panel: 58, sidebar: 58 },
  lab: { panel: 96, sidebar: 99 }
}

const APPEARANCE_EVENT = 'jpilot-beta-chat-appearance-change'

function storageKeys(namespace = 'main') {
  return STORAGE_KEYS[namespace] || STORAGE_KEYS.main
}

function defaults(namespace = 'main') {
  return BETA_CHAT_TRANSPARENCY_DEFAULTS[namespace] || BETA_CHAT_TRANSPARENCY_DEFAULTS.main
}

function clampTransparency(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 0
  return Math.min(100, Math.max(0, Math.round(n)))
}

function readStored(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null || raw === '') return fallback
    return clampTransparency(raw)
  } catch {
    return fallback
  }
}

function writeStored(key, value) {
  try {
    localStorage.setItem(key, String(clampTransparency(value)))
    window.dispatchEvent(new CustomEvent(APPEARANCE_EVENT))
  } catch {
    /* ignore */
  }
}

/** @param {BetaChatNamespace} [namespace] */
export function getBetaChatPanelTransparency(namespace = 'main') {
  const keys = storageKeys(namespace)
  return readStored(keys.panel, defaults(namespace).panel)
}

/** @param {BetaChatNamespace} [namespace] */
export function getBetaChatSidebarTransparency(namespace = 'main') {
  const keys = storageKeys(namespace)
  return readStored(keys.sidebar, defaults(namespace).sidebar)
}

/** @param {number} value @param {BetaChatNamespace} [namespace] */
export function setBetaChatPanelTransparency(value, namespace = 'main') {
  writeStored(storageKeys(namespace).panel, value)
}

/** @param {number} value @param {BetaChatNamespace} [namespace] */
export function setBetaChatSidebarTransparency(value, namespace = 'main') {
  writeStored(storageKeys(namespace).sidebar, value)
}

/** Background mix percentage for CSS color-mix (inverse of transparency). */
export function transparencyToBackgroundMix(transparency) {
  return Math.max(0, Math.min(100, 100 - clampTransparency(transparency)))
}

/** @param {BetaChatNamespace} [namespace] */
export function getBetaChatGlassStyle(namespace = 'main') {
  const panelMix = transparencyToBackgroundMix(getBetaChatPanelTransparency(namespace))
  const sidebarMix = transparencyToBackgroundMix(getBetaChatSidebarTransparency(namespace))
  return {
    '--beta-chat-panel-mix': `${panelMix}%`,
    '--beta-chat-sidebar-mix': `${sidebarMix}%`
  }
}

/** @param {(event: Event) => void} listener */
export function onBetaChatAppearanceChange(listener) {
  window.addEventListener(APPEARANCE_EVENT, listener)
  return () => window.removeEventListener(APPEARANCE_EVENT, listener)
}
