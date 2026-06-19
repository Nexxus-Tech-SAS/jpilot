<template>
  <div class="flex flex-column gap-4">
    <div v-if="isAdmin" class="content-panel content-panel-padded">
      <h2 class="section-title">Public portal</h2>
      <p class="section-copy">
        Control what unauthenticated visitors see when they open your JPilot URL.
      </p>

      <div class="flex flex-column gap-4 mt-4">
        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Display home page</div>
            <div class="setting-hint">
              When enabled, visitors are sent to <code>/home</code>. When disabled, only the login page is shown.
            </div>
          </div>
          <ToggleSwitch
            v-model="jpilotPortalSettings.displayHomePage"
            :disabled="jpilotPortalSaving"
            @update:model-value="saveJpilotPortalSettingsAction"
          />
        </div>
      </div>

      <Message
        v-if="jpilotPortalMessage"
        class="mt-3"
        :severity="jpilotPortalMessageSeverity"
        :closable="false"
      >
        {{ jpilotPortalMessage }}
      </Message>
    </div>

    <div class="content-panel content-panel-padded">
      <h2 class="section-title">Attachments</h2>
      <p class="section-copy">Control what can be attached to JPilot chat messages.</p>

      <div class="flex flex-column gap-4 mt-4">
        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Allow image attachments</div>
            <div class="setting-hint">PNG, JPEG, WebP, GIF — up to 5 MB each</div>
          </div>
          <ToggleSwitch v-model="copilotSettings.allowImages" @update:model-value="saveCopilotPrefs" />
        </div>

        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Allow configuration and document files</div>
            <div class="setting-hint">.conf, .cfg, .txt, .json, .yaml, .xml, .md, .ns, .cs — up to 1 MB each</div>
          </div>
          <ToggleSwitch v-model="copilotSettings.allowConfigFiles" @update:model-value="saveCopilotPrefs" />
        </div>

        <div class="flex flex-column gap-2 setting-row">
          <label for="betaMaxAttachments" class="setting-label">Max attachments per message</label>
          <Select
            id="betaMaxAttachments"
            v-model="copilotSettings.maxAttachments"
            :options="maxAttachmentOptions"
            class="max-select"
            @update:model-value="saveCopilotPrefs"
          />
        </div>
      </div>
    </div>

    <div class="content-panel content-panel-padded">
      <h2 class="section-title">Reply notifications</h2>
      <p class="section-copy">
        When JPilot finishes while you are on another page, another chat pane, or another browser tab,
        show a toast and play a short sound (like Cursor).
      </p>

      <div class="flex flex-column gap-4 mt-4">
        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Notify when reply completes</div>
            <div class="setting-hint">Toast when you are not viewing that chat pane</div>
          </div>
          <ToggleSwitch
            v-model="copilotSettings.notifyWhenReplyComplete"
            @update:model-value="saveCopilotPrefs"
          />
        </div>

        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Play completion sound</div>
            <div class="setting-hint">Short tone with the toast (browser may require a prior click)</div>
          </div>
          <ToggleSwitch v-model="copilotSettings.playReplySound" @update:model-value="saveCopilotPrefs" />
        </div>
      </div>
    </div>

    <OrchestrationSettingsPanel />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import Message from 'primevue/message'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import OrchestrationSettingsPanel from '../OrchestrationSettingsPanel.vue'
import { getCopilotSettings, saveCopilotSettings } from '../../services/copilot'
import { getJpilotSettings, saveJpilotSettings } from '../../services/portal'
import { getStoredUser } from '../../services/auth'

const props = defineProps({
  isAdmin: {
    type: Boolean,
    default: false
  }
})

const maxAttachmentOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
const copilotSettings = reactive(getCopilotSettings())

const jpilotPortalSettings = reactive({
  displayHomePage: true
})
const jpilotPortalSaving = ref(false)
const jpilotPortalMessage = ref('')
const jpilotPortalMessageSeverity = ref('info')

function isAdminUser() {
  return props.isAdmin || getStoredUser()?.role === 'admin'
}

async function loadJpilotPortalSettings() {
  if (!isAdminUser()) return
  try {
    const data = await getJpilotSettings()
    jpilotPortalSettings.displayHomePage = Boolean(data.displayHomePage)
  } catch {
    jpilotPortalSettings.displayHomePage = true
  }
}

async function saveJpilotPortalSettingsAction() {
  jpilotPortalSaving.value = true
  jpilotPortalMessage.value = ''
  try {
    const data = await saveJpilotSettings({
      displayHomePage: jpilotPortalSettings.displayHomePage
    })
    jpilotPortalSettings.displayHomePage = Boolean(data.displayHomePage)
    jpilotPortalMessage.value = 'Public portal settings saved.'
    jpilotPortalMessageSeverity.value = 'success'
  } catch (error) {
    jpilotPortalMessage.value =
      error.response?.data?.detail || error.message || 'Failed to save public portal settings.'
    jpilotPortalMessageSeverity.value = 'error'
    await loadJpilotPortalSettings()
  } finally {
    jpilotPortalSaving.value = false
  }
}

function saveCopilotPrefs() {
  saveCopilotSettings({ ...copilotSettings })
}

onMounted(loadJpilotPortalSettings)
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

.max-select {
  max-width: 8rem;
}
</style>
