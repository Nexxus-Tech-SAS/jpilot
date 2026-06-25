export const CONSENT_COOKIE_NAME = 'jpilot_cookie_consent'
export const CONSENT_ACCEPTED = 'accepted'
export const CONSENT_ESSENTIAL = 'essential'

const MAX_AGE_SECONDS = 60 * 60 * 24 * 365

function readCookie(name) {
  if (typeof document === 'undefined') return null
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function writeCookie(name, value, maxAgeSeconds) {
  if (typeof document === 'undefined') return
  const secure = window.location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax${secure}`
}

export function getCookieConsent() {
  const value = readCookie(CONSENT_COOKIE_NAME)
  if (value === CONSENT_ACCEPTED || value === CONSENT_ESSENTIAL) {
    return value
  }
  return null
}

export function hasCookieConsentChoice() {
  return getCookieConsent() !== null
}

export function allowsPreferenceStorage() {
  return getCookieConsent() === CONSENT_ACCEPTED
}

export function acceptAllCookies() {
  writeCookie(CONSENT_COOKIE_NAME, CONSENT_ACCEPTED, MAX_AGE_SECONDS)
  window.dispatchEvent(new CustomEvent('jpilot-cookie-consent-change', { detail: CONSENT_ACCEPTED }))
}

export function acceptEssentialCookiesOnly() {
  writeCookie(CONSENT_COOKIE_NAME, CONSENT_ESSENTIAL, MAX_AGE_SECONDS)
  window.dispatchEvent(new CustomEvent('jpilot-cookie-consent-change', { detail: CONSENT_ESSENTIAL }))
}
