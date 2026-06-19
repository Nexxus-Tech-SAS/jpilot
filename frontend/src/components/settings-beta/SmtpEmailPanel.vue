<template>
  <div class="content-panel content-panel-padded">
    <div class="flex align-items-start justify-content-between gap-3 flex-wrap">
      <div>
        <h2 class="section-title">SMTP / Email</h2>
        <p v-if="showSmtpConfigFields" class="section-copy">
          Outbound email server used for password resets and notifications.
        </p>
      </div>
      <div class="flex align-items-center gap-2">
        <Tag
          :value="isSmtpConfigured ? 'Configured' : 'Not set up'"
          :severity="isSmtpConfigured ? 'success' : 'secondary'"
        />
        <Button
          v-if="isSmtpConfigured && !smtpEditing"
          icon="pi pi-pencil"
          text
          rounded
          severity="secondary"
          aria-label="Edit SMTP settings"
          v-tooltip.bottom="'Edit SMTP settings'"
          @click="startSmtpEdit"
        />
      </div>
    </div>

    <div v-if="smtpLoading" class="mt-4">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
    </div>

    <div v-else class="smtp-fields mt-4">
      <div v-if="isSmtpConfigured && !smtpEditing" class="smtp-compact flex flex-column gap-3">
        <div class="flex flex-column gap-2">
          <label for="betaSmtpTestRecipientCompact" class="setting-label">Send test email to</label>
          <InputText
            id="betaSmtpTestRecipientCompact"
            v-model="smtpTestRecipient"
            placeholder="you@example.com"
          />
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            label="Send test email"
            icon="pi pi-send"
            size="small"
            severity="secondary"
            outlined
            :loading="smtpTesting"
            @click="testSmtpSettings"
          />
        </div>
      </div>

      <div v-if="showSmtpConfigFields" class="smtp-fields-grid">
        <div class="smtp-field smtp-field-span flex flex-column gap-2 setting-row">
          <label for="betaSmtpProvider" class="setting-label">Provider</label>
          <Select
            id="betaSmtpProvider"
            v-model="smtpSettings.provider"
            :options="smtpProviders"
            option-label="label"
            option-value="value"
            @update:model-value="applySmtpProvider"
          />
          <small class="setting-hint">Pick a preset to fill the server details, or choose Custom to enter your own.</small>
        </div>

        <div class="smtp-field flex flex-column gap-2 setting-row">
          <label for="betaSmtpHost" class="setting-label">SMTP host</label>
          <InputText
            id="betaSmtpHost"
            v-model="smtpSettings.host"
            placeholder="smtp.example.com"
            :disabled="isSmtpPreset"
          />
        </div>

        <div class="smtp-field flex flex-column gap-2 setting-row">
          <label for="betaSmtpPort" class="setting-label">Port</label>
          <InputNumber
            id="betaSmtpPort"
            v-model="smtpSettings.port"
            :use-grouping="false"
            :min="1"
            :max="65535"
            class="max-select w-full"
            :disabled="isSmtpPreset"
          />
        </div>

        <div class="smtp-field flex flex-column gap-2 setting-row">
          <label for="betaSmtpUsername" class="setting-label">Username</label>
          <InputText
            id="betaSmtpUsername"
            v-model="smtpSettings.username"
            placeholder="you@example.com"
          />
        </div>

        <div class="smtp-field flex flex-column gap-2 setting-row">
          <label for="betaSmtpFrom" class="setting-label">From address</label>
          <InputText
            id="betaSmtpFrom"
            v-model="smtpSettings.fromAddress"
            placeholder="no-reply@example.com"
          />
        </div>

        <div class="smtp-field smtp-field-span flex flex-column gap-2 setting-row">
          <label for="betaSmtpPassword" class="setting-label">Password</label>
          <Password
            id="betaSmtpPassword"
            v-model="smtpSettings.password"
            class="w-full"
            :feedback="false"
            toggle-mask
            input-class="w-full"
            :placeholder="smtpSettings.hasPassword ? 'Saved — enter a new password to replace' : 'App password or SMTP password'"
          />
          <small class="setting-hint">
            For Gmail/Outlook with 2FA, generate an app password. Stored encrypted on the backend.
          </small>
        </div>

        <div class="smtp-field smtp-field-span flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Encryption</div>
            <div class="setting-hint">STARTTLS (587) or implicit SSL/TLS (465).</div>
          </div>
          <SelectButton
            v-model="smtpEncryption"
            :options="smtpEncryptionOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            :disabled="isSmtpPreset"
          />
        </div>

        <div class="smtp-field smtp-field-span flex flex-column gap-2 setting-row">
          <label for="betaSmtpTestRecipient" class="setting-label">Send test email to</label>
          <InputText
            id="betaSmtpTestRecipient"
            v-model="smtpTestRecipient"
            placeholder="you@example.com"
          />
          <small class="setting-hint">A test message is sent here to confirm the settings work.</small>
        </div>

        <div class="smtp-field smtp-field-span flex flex-wrap gap-2 pt-2">
          <Button
            label="Save SMTP settings"
            icon="pi pi-save"
            size="small"
            :loading="smtpSaving"
            @click="saveSmtpSettings"
          />
          <Button
            v-if="isSmtpConfigured && smtpEditing"
            label="Cancel"
            icon="pi pi-times"
            size="small"
            severity="secondary"
            text
            :disabled="smtpSaving"
            @click="cancelSmtpEdit"
          />
          <Button
            label="Send test email"
            icon="pi pi-send"
            size="small"
            severity="secondary"
            outlined
            :loading="smtpTesting"
            @click="testSmtpSettings"
          />
        </div>
      </div>

      <Message
        v-if="smtpMessage"
        class="mt-3"
        :severity="smtpMessageSeverity"
        :closable="false"
      >
        {{ smtpMessage }}
      </Message>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import ProgressSpinner from 'primevue/progressspinner'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import { getSmtpConfig, saveSmtpConfig, testSmtpConfig } from '../../services/smtp'

const smtpProviders = [
  { label: 'Gmail', value: 'gmail' },
  { label: 'Outlook / Office 365', value: 'outlook' },
  { label: 'Custom', value: 'custom' }
]

const smtpPresets = {
  gmail: { host: 'smtp.gmail.com', port: 587, useTls: true, useSsl: false },
  outlook: { host: 'smtp.office365.com', port: 587, useTls: true, useSsl: false }
}

const smtpEncryptionOptions = [
  { label: 'STARTTLS', value: 'starttls' },
  { label: 'SSL/TLS', value: 'ssl' },
  { label: 'None', value: 'none' }
]

const smtpLoading = ref(true)
const smtpSaving = ref(false)
const smtpTesting = ref(false)
const smtpMessage = ref('')
const smtpMessageSeverity = ref('info')
const smtpTestRecipient = ref('')
const smtpEditing = ref(false)

const smtpSettings = reactive({
  provider: 'custom',
  host: '',
  port: 587,
  username: '',
  password: '',
  fromAddress: '',
  hasPassword: false,
  useTls: true,
  useSsl: false
})

const isSmtpPreset = computed(() => smtpSettings.provider !== 'custom')

const isSmtpConfigured = computed(
  () => Boolean(smtpSettings.host?.trim() && smtpSettings.hasPassword)
)

const showSmtpConfigFields = computed(() => smtpEditing.value || !isSmtpConfigured.value)

function startSmtpEdit() {
  smtpEditing.value = true
}

async function cancelSmtpEdit() {
  smtpEditing.value = false
  smtpSettings.password = ''
  await loadSmtpSettings()
}

const smtpEncryption = computed({
  get() {
    if (smtpSettings.useSsl) return 'ssl'
    if (smtpSettings.useTls) return 'starttls'
    return 'none'
  },
  set(value) {
    smtpSettings.useSsl = value === 'ssl'
    smtpSettings.useTls = value === 'starttls'
  }
})

function applySmtpProvider(provider) {
  const preset = smtpPresets[provider]
  if (preset) {
    smtpSettings.host = preset.host
    smtpSettings.port = preset.port
    smtpSettings.useTls = preset.useTls
    smtpSettings.useSsl = preset.useSsl
  }
}

async function loadSmtpSettings() {
  smtpLoading.value = true
  try {
    const config = await getSmtpConfig()
    Object.assign(smtpSettings, {
      provider: config.provider || 'custom',
      host: config.host || '',
      port: config.port || 587,
      username: config.username || '',
      password: '',
      fromAddress: config.fromAddress || '',
      hasPassword: config.hasPassword || false,
      useTls: config.useTls,
      useSsl: config.useSsl
    })
    smtpEditing.value = !(Boolean(config.host?.trim()) && config.hasPassword)
  } catch (error) {
    smtpMessage.value = error.response?.data?.detail || 'Failed to load SMTP settings'
    smtpMessageSeverity.value = 'error'
  } finally {
    smtpLoading.value = false
  }
}

function smtpPayload() {
  return {
    provider: smtpSettings.provider,
    host: smtpSettings.host,
    port: smtpSettings.port,
    username: smtpSettings.username,
    password: smtpSettings.password || null,
    fromAddress: smtpSettings.fromAddress,
    useTls: smtpSettings.useTls,
    useSsl: smtpSettings.useSsl
  }
}

async function saveSmtpSettings() {
  smtpSaving.value = true
  smtpMessage.value = ''
  try {
    const saved = await saveSmtpConfig(smtpPayload())
    Object.assign(smtpSettings, {
      provider: saved.provider,
      host: saved.host,
      port: saved.port,
      username: saved.username,
      password: '',
      fromAddress: saved.fromAddress,
      hasPassword: saved.hasPassword,
      useTls: saved.useTls,
      useSsl: saved.useSsl
    })
    smtpMessage.value = 'SMTP settings saved.'
    smtpMessageSeverity.value = 'success'
    smtpEditing.value = false
  } catch (error) {
    smtpMessage.value = error.response?.data?.detail || 'Failed to save SMTP settings'
    smtpMessageSeverity.value = 'error'
  } finally {
    smtpSaving.value = false
  }
}

async function testSmtpSettings() {
  if (!smtpTestRecipient.value.trim()) {
    smtpMessage.value = 'Enter a recipient address to send the test email.'
    smtpMessageSeverity.value = 'warn'
    return
  }
  smtpTesting.value = true
  smtpMessage.value = ''
  try {
    const result = await testSmtpConfig({
      ...smtpPayload(),
      testRecipient: smtpTestRecipient.value.trim()
    })
    smtpMessage.value = result.message
    smtpMessageSeverity.value = result.success ? 'success' : 'error'
  } catch (error) {
    smtpMessage.value = error.response?.data?.detail || 'SMTP test failed'
    smtpMessageSeverity.value = 'error'
  } finally {
    smtpTesting.value = false
  }
}

onMounted(loadSmtpSettings)
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

.smtp-fields-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}

.smtp-field-span {
  grid-column: 1 / -1;
}

.max-select {
  max-width: 8rem;
}

@media (max-width: 991px) {
  .smtp-fields-grid {
    grid-template-columns: 1fr;
  }
}
</style>
