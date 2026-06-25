<template>
  <div class="login-page flex align-items-center justify-content-center min-h-screen">
    <div class="login-bg" aria-hidden="true">
      <SoftAuroraBackground
        :speed="0.4"
        :scale="0.1"
        :brightness="1.1"
        color1="#7184df"
        color2="#10B981"
        :noise-frequency="2.5"
        :noise-amplitude="3.5"
        :band-height="0.5"
        :band-spread="0.8"
        :octave-decay="0.41"
        :layer-offset="1"
        :color-speed="1.0"
        :enable-mouse-interaction="true"
        :mouse-influence="0.1"
      />
      <div class="login-bg-overlay"></div>
    </div>

    <div
      class="login-panel"
      v-animateonscroll="{ enterClass: 'anim-panel-in' }"
    >
      <div class="login-panel-header">
        <span class="login-meta-tag login-meta-edition">Early Access</span>
        <span v-if="serverVersion" class="login-meta-tag login-meta-version">{{ serverVersion }}</span>
      </div>

      <div
        class="login-brand flex flex-column align-items-center mb-5"
        v-animateonscroll="{ enterClass: 'anim-rise anim-delay-1' }"
      >
        <TriArcLoader class="login-logo" />
        <h1 class="ld-cursor login-cursor-title m-0 mt-3">JPilot</h1>
        <p class="login-subtitle m-0 mt-2">{{ loginSubtitle }}</p>
      </div>

      <form
        class="flex flex-column gap-4"
        v-animateonscroll="{ enterClass: 'anim-rise anim-delay-2' }"
        @submit.prevent="onFormSubmit"
      >
        <template v-if="step === 'username'">
          <div class="flex flex-column gap-2">
            <label for="username" class="field-label">Username</label>
            <InputText
              id="username"
              v-model="username"
              autocomplete="username"
              class="w-full"
              :disabled="loadingContinue"
              @keydown.enter.prevent="submitUsernameStep"
            />
          </div>

          <Message v-if="errorMessage" severity="error" :closable="false">
            {{ errorMessage }}
          </Message>

          <div class="flex align-items-start gap-2">
            <Checkbox v-model="agreed" :binary="true" input-id="agree" />
            <label for="agree" class="agree-label">
              I have read and agree to the
              <RouterLink to="/legal/terms" target="_blank">Terms of Service</RouterLink>,
              <RouterLink to="/legal/privacy" target="_blank">Privacy Policy</RouterLink>,
              <RouterLink to="/legal/acceptable-use" target="_blank">Acceptable Use Policy</RouterLink>, and
              <RouterLink to="/legal/eula" target="_blank">EULA</RouterLink>.
            </label>
          </div>

          <button
            type="submit"
            class="btn fx-95 fx-71 login-action-btn"
            :disabled="loadingContinue || !username.trim() || !agreed"
          >
            <span class="btn-label">{{ loadingContinue ? 'Checking…' : 'Continue' }}</span>
          </button>
        </template>

        <template v-else>
          <div class="login-step-user flex align-items-center justify-content-between gap-2">
            <span class="login-step-user-label">
              Signing in as <strong>{{ username.trim() }}</strong>
            </span>
            <button type="button" class="login-step-change" @click="backToUsername">
              Change
            </button>
          </div>

          <Message v-if="errorMessage" severity="error" :closable="false">
            {{ errorMessage }}
          </Message>

          <Message
            v-if="status?.passkeyPolicy === 'disabled'"
            severity="secondary"
            :closable="false"
          >
            Passkeys are disabled on this platform. Sign in with your password.
          </Message>

          <Message
            v-else-if="status?.passkeyEnforced && !status?.hasPasskey"
            severity="warn"
            :closable="false"
          >
            Passkeys are required. Sign in with your password once, then register a passkey under Settings → Security.
          </Message>

          <Message
            v-else-if="status?.passkeyRecommended && !status?.hasPasskey"
            severity="info"
            :closable="false"
          >
            Passkeys are recommended for faster, phishing-resistant sign-in. Register one in Settings → Security after you sign in.
          </Message>

          <template v-if="status?.passkeyRequired">
            <button
              type="button"
              class="btn fx-95 fx-71 login-action-btn"
              :disabled="!agreed || loadingPasskey"
              @click="handlePasskeyLogin(false)"
            >
              <span class="btn-label">
                {{ loadingPasskey && passkeyMode === 'local' ? 'Signing in…' : 'Sign in with passkey' }}
              </span>
            </button>

            <div
              class="cross-device-panel"
              v-animateonscroll="{ enterClass: 'anim-rise anim-delay-3' }"
            >
              <div class="cross-device-panel-header">
                <i class="pi pi-mobile" aria-hidden="true"></i>
                <span>Sign in from your phone</span>
              </div>
              <p class="cross-device-copy">
                Passkey saved on another device? We will open a QR code so you can scan it with a phone
                that has this passkey (for example via iCloud Keychain or Google Password Manager).
              </p>
              <div class="cross-device-qr-area" :class="{ active: crossDeviceActive }">
                <div class="qr-placeholder" aria-hidden="true">
                  <span v-for="cell in qrPattern" :key="cell" :class="{ filled: cell }"></span>
                </div>
                <p v-if="crossDeviceActive" class="cross-device-status">
                  Scan the QR code in your browser&rsquo;s passkey dialog with your phone camera.
                </p>
                <p v-else class="cross-device-status muted">
                  The scannable QR code opens when you start phone sign-in below.
                </p>
              </div>
              <button
                type="button"
                class="btn fx-95 fx-71 login-action-btn"
                :disabled="!agreed || loadingPasskey"
                @click="handlePasskeyLogin(true)"
              >
                <span class="btn-label">
                  {{ loadingPasskey && passkeyMode === 'cross-device' ? 'Opening…' : 'Show QR code' }}
                </span>
              </button>
            </div>

            <small class="field-hint text-center">
              On this computer, use Touch ID, Face ID, or Windows Hello if your passkey is synced here.
            </small>

            <div class="text-center">
              <RouterLink
                :to="{ path: '/account-recovery', query: { username: username.trim().toLowerCase() } }"
                class="reset-link"
              >
                Lost passkey or device? Account recovery
              </RouterLink>
            </div>
          </template>

          <template v-else>
            <div class="flex flex-column gap-2">
              <label for="password" class="field-label">Password</label>
              <Password
                id="password"
                v-model="password"
                autocomplete="current-password"
                class="w-full"
                :feedback="false"
                toggle-mask
                input-class="w-full"
                :disabled="loading"
                @keydown.enter.prevent="onFormSubmit"
              />
            </div>

            <button
              type="submit"
              class="btn fx-95 fx-71 login-action-btn"
              :disabled="!agreed || loading || !password"
            >
              <span class="btn-label">{{ loading ? 'Signing in…' : 'Sign in' }}</span>
            </button>

            <div class="text-center">
              <RouterLink
                :to="{ path: '/account-recovery', query: username.trim() ? { username: username.trim() } : {} }"
                class="reset-link"
              >
                Lost access? Recover with email code
              </RouterLink>
            </div>

            <template v-if="status?.exists && !status?.hasPasskey && status?.passkeyPolicy !== 'disabled'">
              <div class="login-divider">
                <span>optional</span>
              </div>
              <button
                type="button"
                class="btn fx-95 fx-71 login-action-btn"
                :disabled="!agreed || loadingPasskey"
                @click="handlePasskeyLogin(false)"
              >
                <span class="btn-label">
                  {{ loadingPasskey ? 'Signing in…' : 'Sign in with passkey' }}
                </span>
              </button>
              <small class="field-hint text-center">
                Available after you register a passkey in Settings.
              </small>
            </template>

            <template v-else-if="status?.hasPasskey && status?.passkeyPolicy !== 'disabled'">
              <div class="login-divider">
                <span>or</span>
              </div>
              <button
                type="button"
                class="btn fx-95 fx-71 login-action-btn"
                :disabled="!agreed || loadingPasskey"
                @click="handlePasskeyLogin(false)"
              >
                <span class="btn-label">
                  {{ loadingPasskey ? 'Signing in…' : 'Sign in with passkey' }}
                </span>
              </button>
            </template>
          </template>
        </template>
      </form>
    </div>

    <footer class="login-legal">
      <RouterLink to="/legal/privacy">Privacy Policy</RouterLink>
      <span aria-hidden="true">·</span>
      <RouterLink to="/legal/terms">Terms of Service</RouterLink>
      <span aria-hidden="true">·</span>
      <RouterLink to="/legal/eula">EULA</RouterLink>
      <span aria-hidden="true">·</span>
      <RouterLink to="/legal/acceptable-use">Acceptable Use</RouterLink>
    </footer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import TriArcLoader from '../components/TriArcLoader.vue'
import SoftAuroraBackground from '../components/SoftAuroraBackground.vue'
import api from '../services/api'
import { setAuth } from '../services/auth'
import { getSystemVersion } from '../services/system'
import {
  fetchPasskeyStatus,
  loginWithPasskey,
  passkeyErrorMessage
} from '../services/webauthn'
import { WebAuthnAbortService } from '@simplewebauthn/browser'
import { resolvePostLoginPath } from '../services/postLoginRedirect'
import {
  clearLoginTermsAgreement,
  hasStoredLoginTermsAgreement,
  saveLoginTermsAgreement
} from '../services/loginTermsCookie'
import { allowsPreferenceStorage } from '../services/cookieConsent'

const router = useRouter()
const route = useRoute()

const username = ref(route.query.username?.toString() || '')
const password = ref('')
const step = ref('username')
const agreed = ref(false)
const loading = ref(false)
const loadingContinue = ref(false)
const loadingPasskey = ref(false)
const passkeyMode = ref('local')
const crossDeviceActive = ref(false)
const crossDeviceAutoStarted = ref(false)
const errorMessage = ref('')
const status = ref(null)
const serverVersion = ref('')

const loginSubtitle = computed(() => {
  if (step.value === 'username') {
    return 'Sign in to manage your platform'
  }
  if (status.value?.passkeyRequired) {
    return 'Sign in with your passkey'
  }
  return 'Enter your password'
})

const qrPattern = [
  true, true, true, false, true, true, true,
  true, false, true, false, true, false, true,
  true, true, true, false, false, true, true,
  false, true, false, true, true, false, true,
  true, false, true, true, true, false, true,
  true, true, true, false, true, false, true,
  false, false, true, false, true, true, true
]

async function continueWithUsername() {
  errorMessage.value = ''
  loadingContinue.value = true
  try {
    status.value = await fetchPasskeyStatus(username.value.trim())
    if (!status.value?.exists) {
      errorMessage.value = 'No account found for that username.'
      return
    }
    step.value = 'authenticate'
    if (!status.value.passkeyRequired) {
      await nextTick()
      focusPasswordInput()
    }
  } catch {
    errorMessage.value = 'Could not look up username. Try again in a moment.'
  } finally {
    loadingContinue.value = false
  }
}

function submitUsernameStep() {
  if (step.value !== 'username' || loadingContinue.value || !username.value.trim() || !agreed.value) {
    return
  }
  continueWithUsername()
}

function focusPasswordInput() {
  const input =
    document.getElementById('password') ||
    document.querySelector('#password input') ||
    document.querySelector('input[autocomplete="current-password"]')
  input?.focus()
}

function onFormSubmit() {
  if (step.value === 'username') {
    continueWithUsername()
    return
  }
  if (!status.value?.passkeyRequired) {
    if (!password.value || loading.value) {
      return
    }
    handlePasswordLogin()
  }
}

function backToUsername() {
  step.value = 'username'
  password.value = ''
  status.value = null
  errorMessage.value = ''
  crossDeviceActive.value = false
  crossDeviceAutoStarted.value = false
  WebAuthnAbortService.cancelCeremony()
}

watch(agreed, (isAgreed) => {
  if (isAgreed) {
    saveLoginTermsAgreement()
    return
  }
  clearLoginTermsAgreement()
})

function applyStoredTermsAgreement() {
  if (hasStoredLoginTermsAgreement()) {
    agreed.value = true
  }
}

function onCookieConsentChange() {
  if (!allowsPreferenceStorage()) {
    clearLoginTermsAgreement()
    return
  }
  applyStoredTermsAgreement()
  if (agreed.value) {
    saveLoginTermsAgreement()
  }
}

watch([agreed, () => status.value?.passkeyRequired, step], ([isAgreed, passkeyRequired, currentStep]) => {
  if (currentStep !== 'authenticate' || !isAgreed || !passkeyRequired || crossDeviceAutoStarted.value) {
    return
  }
  crossDeviceAutoStarted.value = true
  handlePasskeyLogin(true)
})

onMounted(async () => {
  applyStoredTermsAgreement()
  window.addEventListener('jpilot-cookie-consent-change', onCookieConsentChange)
  try {
    const info = await getSystemVersion()
    serverVersion.value = info.display_version
  } catch {
    serverVersion.value = ''
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('jpilot-cookie-consent-change', onCookieConsentChange)
  WebAuthnAbortService.cancelCeremony()
})

async function handlePasswordLogin() {
  errorMessage.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/login', {
      username: username.value.trim().toLowerCase(),
      password: password.value
    })
    setAuth(data.accessToken, data.user)
    const destination = await resolvePostLoginPath(route.query.redirect)
    router.push(destination)
  } catch (error) {
    const detail = error.response?.data?.detail
    errorMessage.value = typeof detail === 'string' ? detail : 'Invalid username or password'
  } finally {
    loading.value = false
  }
}

async function handlePasskeyLogin(preferCrossDevice = false) {
  errorMessage.value = ''
  passkeyMode.value = preferCrossDevice ? 'cross-device' : 'local'
  crossDeviceActive.value = preferCrossDevice
  loadingPasskey.value = true
  try {
    if (!status.value?.hasPasskey) {
      errorMessage.value = 'No passkey registered for this account yet.'
      crossDeviceActive.value = false
      return
    }
    await loginWithPasskey(username.value, { preferCrossDevice })
    const destination = await resolvePostLoginPath(route.query.redirect)
    router.push(destination)
  } catch (error) {
    errorMessage.value = passkeyErrorMessage(error)
    crossDeviceActive.value = false
    if (preferCrossDevice) {
      crossDeviceAutoStarted.value = false
    }
  } finally {
    loadingPasskey.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  padding: 1.5rem;
  background: #000000;
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.login-bg-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 50% 35%, rgba(113, 132, 223, 0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 40% 55%, rgba(16, 185, 129, 0.05) 0%, transparent 45%),
    linear-gradient(180deg, transparent 65%, rgba(0, 0, 0, 0.88) 100%);
  pointer-events: none;
}

:global(.app-dark) .login-bg-overlay {
  background:
    radial-gradient(ellipse at 50% 35%, rgba(113, 132, 223, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 40% 55%, rgba(16, 185, 129, 0.07) 0%, transparent 45%),
    linear-gradient(180deg, transparent 65%, rgba(0, 0, 0, 0.92) 100%);
}

.anim-panel-in {
  animation: panel-in 700ms cubic-bezier(0.22, 1, 0.36, 1) backwards;
}

.anim-rise {
  animation: rise-in 600ms cubic-bezier(0.22, 1, 0.36, 1) backwards;
}

.anim-delay-1 { animation-delay: 120ms; }
.anim-delay-2 { animation-delay: 240ms; }
.anim-delay-3 { animation-delay: 360ms; }

@keyframes panel-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes rise-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .anim-panel-in,
  .anim-rise {
    animation: none;
  }
}

.agree-label {
  font-size: 0.8125rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
}

.agree-label a {
  color: var(--p-primary-color);
  text-decoration: none;
}

.login-legal {
  position: absolute;
  z-index: 1;
  bottom: 1.25rem;
  left: 0;
  right: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0 1rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.login-legal a {
  color: var(--p-text-muted-color);
  text-decoration: none;
}

.login-legal a:hover {
  color: var(--p-primary-color);
}

.login-panel {
  position: relative;
  z-index: 1;
  width: min(100%, 24rem);
  padding: 2.5rem 2rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  box-shadow:
    0 12px 40px rgba(0, 0, 0, 0.08),
    0 0 0 1px color-mix(in srgb, var(--p-primary-color) 12%, transparent),
    0 0 32px color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}

:global(.app-dark) .login-panel {
  box-shadow:
    0 18px 50px rgba(0, 0, 0, 0.5),
    0 0 0 1px color-mix(in srgb, var(--p-primary-color) 22%, transparent),
    0 0 48px color-mix(in srgb, var(--p-primary-color) 28%, transparent);
}

.login-cursor-title {
  color: var(--p-primary-color);
}

.login-logo {
  color: var(--p-primary-color);
}

.login-action-btn {
  width: 100%;
  --bink: var(--p-primary-color);
  --secondary: var(--p-text-color);
  --surface: var(--p-content-background);
  --bsurf: var(--p-content-background);
}

.login-panel-header {
  position: absolute;
  top: 0.875rem;
  left: 0.875rem;
  right: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.login-meta-tag {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 100px;
  letter-spacing: 0.04em;
  background: transparent;
}

.login-meta-edition {
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 45%, transparent);
  color: var(--p-primary-color);
}

.login-meta-version {
  border: 1px solid color-mix(in srgb, var(--p-text-muted-color) 40%, transparent);
  color: var(--p-text-muted-color);
  font-weight: 600;
}

.login-subtitle {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.login-step-user-label {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  min-width: 0;
}

.login-step-change {
  border: 0;
  background: transparent;
  padding: 0;
  font-size: 0.8125rem;
  color: var(--p-primary-color);
  cursor: pointer;
  flex-shrink: 0;
}

.login-step-change:hover {
  text-decoration: underline;
}

.field-label {
  font-size: 0.8125rem;
  font-weight: 500;
}

.field-hint {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.login-divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.login-divider::before,
.login-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--p-content-border-color);
}

.reset-link {
  color: var(--p-primary-color);
  font-size: 0.8125rem;
  text-decoration: none;
}

.reset-link:hover {
  text-decoration: underline;
}

.cross-device-panel {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  padding: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-content-background));
}

.cross-device-panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.cross-device-panel-header .pi {
  color: var(--p-primary-color);
}

.cross-device-copy {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}

.cross-device-qr-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem;
  border-radius: 0.625rem;
  border: 1px dashed var(--p-content-border-color);
  background: var(--p-content-background);
}

.cross-device-qr-area.active {
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, var(--p-content-border-color));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}

.qr-placeholder {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.18rem;
  width: 5.5rem;
  aspect-ratio: 1;
  padding: 0.35rem;
  border-radius: 0.35rem;
  background: #fff;
}

.qr-placeholder span {
  border-radius: 0.1rem;
  background: color-mix(in srgb, var(--p-text-color) 8%, #fff);
}

.qr-placeholder span.filled {
  background: var(--p-text-color);
}

.cross-device-qr-area.active .qr-placeholder {
  animation: qr-pulse 1.6s ease-in-out infinite;
}

.cross-device-status {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  text-align: center;
  color: var(--p-text-color);
}

.cross-device-status.muted {
  color: var(--p-text-muted-color);
}

@keyframes qr-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.82; transform: scale(0.98); }
}
</style>
