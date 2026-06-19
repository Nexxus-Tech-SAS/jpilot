<template>
  <div class="flex flex-column gap-4">
    <JpilotTlsPanel v-if="isAdmin" />

    <div v-if="isAdmin" class="content-panel content-panel-padded">
      <h2 class="section-title">Passkey policy</h2>
      <p class="section-copy">
        Control passkey sign-in for the whole platform. We recommend <strong>Enable</strong> so users can
        register passkeys voluntarily while keeping password recovery available until they do.
      </p>

      <div class="flex flex-column gap-3 mt-4">
        <div class="flex align-items-center justify-content-between gap-3 flex-wrap setting-row">
          <div>
            <div class="setting-label">Platform policy</div>
            <div class="setting-hint">{{ passkeyPolicyDescription(securitySettings.passkeyPolicy) }}</div>
          </div>
          <SelectButton
            v-model="securitySettings.passkeyPolicy"
            :options="passkeyPolicyOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            :disabled="securitySaving"
          />
        </div>

        <Message
          v-if="securitySettings.passkeyPolicy === 'enabled'"
          severity="info"
          :closable="false"
        >
          Recommended — passkeys are optional, but once a user registers one, password sign-in is disabled
          for that account.
        </Message>
        <Message
          v-else-if="securitySettings.passkeyPolicy === 'enforced'"
          severity="warn"
          :closable="false"
        >
          Enforced — users without a passkey can sign in with a password once, then must register a passkey
          under Settings → Security.
        </Message>
        <Message
          v-else
          severity="secondary"
          :closable="false"
        >
          Disabled — passkey registration and passkey sign-in are turned off for everyone.
        </Message>

        <div class="flex gap-2">
          <Button
            label="Save passkey policy"
            icon="pi pi-save"
            size="small"
            :loading="securitySaving"
            @click="saveSecuritySettingsAction"
          />
        </div>

        <Message v-if="securityMessage" :severity="securityMessageSeverity" :closable="false">
          {{ securityMessage }}
        </Message>
      </div>
    </div>

    <div class="content-panel content-panel-padded">
      <h2 class="section-title">{{ isAdmin ? 'Your passkey' : 'Security' }}</h2>
      <p v-if="passkeyStatus.passkeyPolicy === 'disabled'" class="section-copy">
        Passkeys are disabled by your administrator. Sign in with your password only.
      </p>
      <p v-else-if="passkeyStatus.passkeyEnforced && !passkeyStatus.hasPasskey" class="section-copy">
        Passkeys are required on this platform. Register one below, then future sign-ins will use your
        passkey instead of your password.
      </p>
      <p v-else class="section-copy">
        Register a passkey for passwordless sign-in. Once a passkey is active, password sign-in is
        disabled for your account. Use account recovery (email code) if you lose your device.
      </p>

      <div v-if="passkeyStatus.passkeyPolicy !== 'disabled'" class="flex flex-column gap-3 mt-4">
        <div class="flex align-items-center justify-content-between gap-3 flex-wrap">
          <div>
            <div class="setting-label">Passkeys</div>
            <div class="setting-hint">
              {{ passkeyStatus.hasPasskey
                ? `${passkeyStatus.passkeyCount} passkey(s) registered for ${passkeyStatus.username}`
                : 'No passkey registered yet for your account.' }}
            </div>
          </div>
          <Tag
            :value="passkeyStatus.hasPasskey ? 'Enabled' : (passkeyStatus.passkeyRecommended ? 'Recommended' : 'Not set up')"
            :severity="passkeyStatus.hasPasskey ? 'success' : (passkeyStatus.passkeyRecommended ? 'info' : 'secondary')"
          />
        </div>

        <Message
          v-if="passkeyStatus.passkeyRecommended && !passkeyStatus.hasPasskey"
          severity="info"
          :closable="false"
        >
          Passkeys are recommended for faster, phishing-resistant sign-in.
        </Message>

        <Button
          label="Register passkey"
          icon="pi pi-key"
          size="small"
          :loading="passkeyRegistering"
          @click="registerMyPasskey"
        />

        <Message v-if="passkeyMessage" :severity="passkeyMessageSeverity" :closable="false">
          {{ passkeyMessage }}
        </Message>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import JpilotTlsPanel from '../JpilotTlsPanel.vue'
import {
  PASSKEY_POLICY_OPTIONS,
  getSecuritySettings,
  passkeyPolicyDescription,
  saveSecuritySettings
} from '../../services/security'
import api from '../../services/api'
import { getStoredUser } from '../../services/auth'
import { fetchPasskeyStatus, passkeyErrorMessage, registerPasskey } from '../../services/webauthn'

const currentUser = ref(getStoredUser())
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const passkeyPolicyOptions = PASSKEY_POLICY_OPTIONS
const securitySettings = reactive({
  passkeyPolicy: 'enabled'
})
const securitySaving = ref(false)
const securityMessage = ref('')
const securityMessageSeverity = ref('info')

const passkeyRegistering = ref(false)
const passkeyMessage = ref('')
const passkeyMessageSeverity = ref('info')

const passkeyStatus = reactive({
  username: '',
  hasPasskey: false,
  passkeyCount: 0,
  passkeyPolicy: 'enabled',
  passkeyRecommended: false,
  passkeyEnforced: false
})

async function loadSecuritySettings() {
  if (!isAdmin.value) return
  try {
    const data = await getSecuritySettings()
    securitySettings.passkeyPolicy = data.passkeyPolicy || 'enabled'
  } catch {
    securitySettings.passkeyPolicy = 'enabled'
  }
}

async function saveSecuritySettingsAction() {
  securitySaving.value = true
  securityMessage.value = ''
  try {
    const data = await saveSecuritySettings({
      passkeyPolicy: securitySettings.passkeyPolicy
    })
    securitySettings.passkeyPolicy = data.passkeyPolicy || securitySettings.passkeyPolicy
    securityMessage.value = 'Passkey policy saved.'
    securityMessageSeverity.value = 'success'
    await loadPasskeyStatus()
  } catch (error) {
    securityMessage.value = error.response?.data?.detail || error.message || 'Failed to save passkey policy.'
    securityMessageSeverity.value = 'error'
  } finally {
    securitySaving.value = false
  }
}

async function loadPasskeyStatus() {
  const user = getStoredUser()
  if (!user?.username) return
  passkeyStatus.username = user.username
  try {
    const status = await fetchPasskeyStatus(user.username)
    passkeyStatus.hasPasskey = status.hasPasskey
    passkeyStatus.passkeyPolicy = status.passkeyPolicy || 'enabled'
    passkeyStatus.passkeyRecommended = Boolean(status.passkeyRecommended)
    passkeyStatus.passkeyEnforced = Boolean(status.passkeyEnforced)
    passkeyStatus.passkeyCount = status.hasPasskey ? 1 : 0
    const { data } = await api.get(`/users/${user.id}`)
    passkeyStatus.passkeyCount = data.passkeyCount || 0
    passkeyStatus.hasPasskey = passkeyStatus.passkeyCount > 0
  } catch {
    passkeyStatus.hasPasskey = false
    passkeyStatus.passkeyCount = 0
  }
}

async function registerMyPasskey() {
  const user = getStoredUser()
  if (!user?.username) return
  if (passkeyStatus.passkeyPolicy === 'disabled') {
    passkeyMessage.value = 'Passkeys are disabled by your administrator.'
    passkeyMessageSeverity.value = 'warn'
    return
  }
  passkeyRegistering.value = true
  passkeyMessage.value = ''
  try {
    await registerPasskey(user.username)
    passkeyMessage.value = 'Passkey registered. You can use it on the login screen next time.'
    passkeyMessageSeverity.value = 'success'
    await loadPasskeyStatus()
  } catch (error) {
    passkeyMessage.value = passkeyErrorMessage(error)
    passkeyMessageSeverity.value = 'error'
  } finally {
    passkeyRegistering.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me')
    currentUser.value = data
  } catch {
    // Fall back to stored user from login.
  }
  const tasks = [loadPasskeyStatus()]
  if (isAdmin.value) {
    tasks.push(loadSecuritySettings())
  }
  await Promise.all(tasks)
})
</script>

<style scoped>
.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.section-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
}

.setting-row {
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.setting-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.setting-label {
  font-size: 0.9375rem;
  font-weight: 500;
}

.setting-hint {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  margin-top: 0.2rem;
}
</style>
