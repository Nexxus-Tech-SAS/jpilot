<template>
  <div v-if="visible" class="cookie-consent" role="dialog" aria-labelledby="cookie-consent-title" aria-live="polite">
    <div class="cookie-consent-inner">
      <p id="cookie-consent-title" class="cookie-consent-copy">
        JPilot uses essential storage to keep you signed in and run the app. With your consent, we also store
        preferences on this device (for example theme and remembering that you accepted the login terms).
        See our
        <RouterLink to="/legal/privacy" class="cookie-consent-link">Privacy Policy</RouterLink>
        for details.
      </p>
      <div class="cookie-consent-actions">
        <button type="button" class="cookie-consent-btn cookie-consent-btn-muted" @click="chooseEssential">
          Essential only
        </button>
        <button type="button" class="cookie-consent-btn cookie-consent-btn-primary" @click="chooseAcceptAll">
          Accept all
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import {
  acceptAllCookies,
  acceptEssentialCookiesOnly,
  hasCookieConsentChoice
} from '../services/cookieConsent'
import { clearLoginTermsAgreement } from '../services/loginTermsCookie'

const visible = ref(false)

function syncVisibility() {
  visible.value = !hasCookieConsentChoice()
}

function chooseAcceptAll() {
  acceptAllCookies()
  syncVisibility()
}

function chooseEssential() {
  acceptEssentialCookiesOnly()
  clearLoginTermsAgreement()
  syncVisibility()
}

function onConsentChange() {
  syncVisibility()
}

onMounted(() => {
  syncVisibility()
  window.addEventListener('jpilot-cookie-consent-change', onConsentChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('jpilot-cookie-consent-change', onConsentChange)
})
</script>

<style scoped>
.cookie-consent {
  position: fixed;
  z-index: 9999;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 1rem;
  padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
  pointer-events: none;
}

.cookie-consent-inner {
  pointer-events: auto;
  max-width: 42rem;
  margin: 0 auto;
  padding: 1rem 1.125rem;
  border-radius: 0.875rem;
  border: 1px solid var(--p-content-border-color);
  background: color-mix(in srgb, var(--p-content-background) 92%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow:
    0 10px 30px rgba(2, 6, 23, 0.12),
    0 0 0 1px color-mix(in srgb, var(--p-primary-color) 8%, transparent);
}

:global(.app-dark) .cookie-consent-inner {
  box-shadow:
    0 14px 36px rgba(0, 0, 0, 0.45),
    0 0 0 1px color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}

.cookie-consent-copy {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--p-text-color);
}

.cookie-consent-link {
  color: var(--p-primary-color);
  text-decoration: none;
}

.cookie-consent-link:hover {
  text-decoration: underline;
}

.cookie-consent-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.875rem;
}

.cookie-consent-btn {
  border-radius: 0.5rem;
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.cookie-consent-btn-muted {
  background: transparent;
  border-color: var(--p-content-border-color);
  color: var(--p-text-muted-color);
}

.cookie-consent-btn-muted:hover {
  background: var(--p-surface-100);
  color: var(--p-text-color);
}

:global(.app-dark) .cookie-consent-btn-muted:hover {
  background: var(--p-surface-800);
}

.cookie-consent-btn-primary {
  background: var(--p-primary-color);
  border-color: var(--p-primary-color);
  color: var(--p-primary-contrast-color, #fff);
}

.cookie-consent-btn-primary:hover {
  filter: brightness(1.05);
}
</style>
