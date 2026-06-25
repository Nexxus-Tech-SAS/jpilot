// Remembers login terms checkbox per browser. Bump LOGIN_TERMS_REVISION when legal text changes.
import { allowsPreferenceStorage } from './cookieConsent'

export const LOGIN_TERMS_REVISION = '1'

const COOKIE_NAME = 'jpilot_login_terms'
const MAX_AGE_SECONDS = 60 * 60 * 24 * 365

function readCookie(name) {
  if (typeof document === 'undefined') return null
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function writeCookie(value, maxAgeSeconds) {
  if (typeof document === 'undefined') return
  const secure = window.location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(value)}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax${secure}`
}

export function hasStoredLoginTermsAgreement() {
  if (!allowsPreferenceStorage()) {
    return false
  }
  return readCookie(COOKIE_NAME) === LOGIN_TERMS_REVISION
}

export function saveLoginTermsAgreement() {
  if (!allowsPreferenceStorage()) {
    return
  }
  writeCookie(LOGIN_TERMS_REVISION, MAX_AGE_SECONDS)
}

export function clearLoginTermsAgreement() {
  writeCookie('', 0)
}
