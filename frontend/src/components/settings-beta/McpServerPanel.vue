<template>
  <div class="content-panel content-panel-padded">
    <div class="flex align-items-start justify-content-between gap-3 flex-wrap">
      <div>
        <h2 class="section-title">MCP server</h2>
        <p class="section-copy">Configure the Model Context Protocol server connection.</p>
      </div>
      <Tag
        :value="mcpStatus.online ? 'Online' : 'Offline'"
        :severity="mcpStatus.online ? 'success' : 'danger'"
        :icon="mcpStatus.online ? 'pi pi-check-circle' : 'pi pi-times-circle'"
      />
    </div>

    <div v-if="mcpLoading" class="mt-4">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
    </div>

    <div v-else class="flex flex-column gap-4 mt-4">
      <div class="flex flex-column gap-2 setting-row">
        <label for="betaServerUrl" class="setting-label">Server URL</label>
        <InputText
          id="betaServerUrl"
          v-model="mcpSettings.serverUrl"
          placeholder="http://mcp-server:8001"
        />
        <small class="setting-hint">Backend uses this URL to reach the MCP server. Use host.docker.internal for host-side services.</small>
      </div>

      <div class="flex flex-column gap-2 setting-row">
        <label for="betaServerName" class="setting-label">Server name</label>
        <InputText id="betaServerName" v-model="mcpSettings.serverName" />
      </div>

      <div class="flex align-items-center justify-content-between gap-3 setting-row">
        <div>
          <div class="setting-label">SSE transport</div>
          <div class="setting-hint">Server-Sent Events endpoint for MCP clients.</div>
        </div>
        <ToggleSwitch v-model="mcpSettings.sseEnabled" />
      </div>

      <div class="mcp-subsection">
        <h3 class="subsection-title">Appliance connection</h3>
        <p class="subsection-copy">Timeouts, SSL verification, and SSH fallback for MCP appliance tools.</p>

        <div class="flex flex-column gap-4 mt-3">
          <div class="flex align-items-center justify-content-between gap-3 setting-row">
            <label for="betaNitroTimeout" class="setting-label m-0">Next-Gen API timeout (s)</label>
            <InputNumber
              id="betaNitroTimeout"
              v-model="mcpSettings.nitroTimeoutSeconds"
              :min="5"
              :max="120"
              show-buttons
              button-layout="horizontal"
              class="compact-input-number"
            />
          </div>

          <div class="flex align-items-center justify-content-between gap-3 setting-row">
            <label for="betaSshPort" class="setting-label m-0">SSH port</label>
            <InputNumber
              id="betaSshPort"
              v-model="mcpSettings.sshPort"
              :min="1"
              :max="65535"
              :use-grouping="false"
              show-buttons
              button-layout="horizontal"
              class="compact-input-number compact-input-number--port"
            />
          </div>

          <div class="flex align-items-center justify-content-between gap-3 setting-row">
            <label for="betaSshTimeout" class="setting-label m-0">SSH timeout (s)</label>
            <InputNumber
              id="betaSshTimeout"
              v-model="mcpSettings.sshTimeoutSeconds"
              :min="5"
              :max="120"
              show-buttons
              button-layout="horizontal"
              class="compact-input-number"
            />
          </div>

          <div class="flex align-items-center justify-content-between gap-3 setting-row">
            <div>
              <div class="setting-label">Verify SSL certificates</div>
              <div class="setting-hint">Disable for appliances with self-signed certificates (default off).</div>
            </div>
            <ToggleSwitch v-model="mcpSettings.verifySsl" />
          </div>

          <div class="flex align-items-center justify-content-between gap-3 setting-row">
            <div>
              <div class="setting-label">SSH fallback</div>
              <div class="setting-hint">
                When Next-Gen API cannot answer, JPilot may run read-only show/stat/get commands via SSH.
              </div>
            </div>
            <ToggleSwitch v-model="mcpSettings.sshFallbackEnabled" />
          </div>
        </div>
      </div>

      <div class="flex gap-2 pt-2">
        <Button
          label="Save MCP settings"
          icon="pi pi-save"
          size="small"
          :loading="mcpSaving"
          @click="saveMcpSettings"
        />
        <Button
          label="Test connection"
          icon="pi pi-bolt"
          size="small"
          severity="secondary"
          outlined
          :loading="mcpTesting"
          @click="testMcpConnection"
        />
      </div>

      <Message v-if="mcpMessage" :severity="mcpMessageSeverity" :closable="false">
        {{ mcpMessage }}
      </Message>

      <div class="mcp-status-inline">
        <h3 class="info-title">MCP status</h3>
        <ul class="info-list mcp-status-list m-0 pl-0 list-none">
          <li><strong>URL:</strong> {{ mcpStatus.serverUrl || '—' }}</li>
          <li><strong>Enabled tools:</strong> {{ mcpStatus.enabledToolCount }} / {{ mcpStatus.toolCount }}</li>
          <li><strong>Status:</strong> {{ mcpStatus.message }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { getMcpConfig, getMcpStatus, saveMcpConfig } from '../../services/mcp'

const mcpLoading = ref(true)
const mcpSaving = ref(false)
const mcpTesting = ref(false)
const mcpMessage = ref('')
const mcpMessageSeverity = ref('info')

const mcpSettings = reactive({
  serverUrl: '',
  serverName: 'jpilot-mcp',
  nitroTimeoutSeconds: 30,
  verifySsl: false,
  enabledTools: [],
  sseEnabled: true,
  sshFallbackEnabled: true,
  sshPort: 22,
  sshTimeoutSeconds: 30
})

const mcpStatus = reactive({
  online: false,
  serverUrl: '',
  message: 'Checking…',
  toolCount: 0,
  enabledToolCount: 0
})

async function refreshMcpStatus() {
  try {
    const status = await getMcpStatus()
    Object.assign(mcpStatus, status)
  } catch (error) {
    mcpStatus.online = false
    mcpStatus.message = error.response?.data?.detail || error.message
  }
}

async function loadMcpConfig() {
  mcpLoading.value = true
  try {
    const config = await getMcpConfig()
    Object.assign(mcpSettings, {
      serverUrl: config.serverUrl,
      serverName: config.serverName,
      nitroTimeoutSeconds: config.nitroTimeoutSeconds,
      verifySsl: config.verifySsl,
      enabledTools: [...(config.enabledTools || [])],
      sseEnabled: config.sseEnabled,
      sshFallbackEnabled: config.sshFallbackEnabled ?? true,
      sshPort: config.sshPort ?? 22,
      sshTimeoutSeconds: config.sshTimeoutSeconds ?? 30
    })
    await refreshMcpStatus()
  } catch (error) {
    mcpMessage.value = error.response?.data?.detail || 'Failed to load MCP settings'
    mcpMessageSeverity.value = 'error'
  } finally {
    mcpLoading.value = false
  }
}

async function saveMcpSettings() {
  mcpSaving.value = true
  mcpMessage.value = ''
  try {
    await saveMcpConfig({ ...mcpSettings })
    mcpMessage.value = 'Settings saved and synced to the MCP server.'
    mcpMessageSeverity.value = 'success'
    await refreshMcpStatus()
  } catch (error) {
    mcpMessage.value = error.response?.data?.detail || 'Failed to save MCP settings'
    mcpMessageSeverity.value = 'error'
  } finally {
    mcpSaving.value = false
  }
}

async function testMcpConnection() {
  mcpTesting.value = true
  mcpMessage.value = ''
  try {
    await refreshMcpStatus()
    if (mcpStatus.online) {
      mcpMessage.value = `Connected — ${mcpStatus.enabledToolCount} tool(s) enabled.`
      mcpMessageSeverity.value = 'success'
    } else {
      mcpMessage.value = mcpStatus.message
      mcpMessageSeverity.value = 'error'
    }
  } finally {
    mcpTesting.value = false
  }
}

onMounted(loadMcpConfig)
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

.mcp-status-inline {
  margin-top: 0.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color);
}

.mcp-subsection {
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color);
}

.subsection-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.subsection-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.8125rem;
}

.compact-input-number {
  flex-shrink: 0;
  width: fit-content;
}

.compact-input-number :deep(.p-inputnumber) {
  display: inline-flex;
  width: auto;
}

.compact-input-number :deep(.p-inputnumber-input) {
  width: 3.25rem;
  min-width: 3.25rem;
  text-align: center;
  flex: 0 0 auto;
}

.compact-input-number--port :deep(.p-inputnumber-input) {
  width: 4.25rem;
  min-width: 4.25rem;
}

.mcp-status-inline .info-title {
  margin-bottom: 0.5rem;
}

.info-title {
  font-size: 0.9375rem;
  font-weight: 600;
  margin: 0 0 0.75rem;
}

.info-list {
  color: var(--p-text-muted-color);
  line-height: 1.6;
  font-size: 0.875rem;
}

.mcp-status-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.mcp-status-list strong {
  color: var(--p-text-color);
  font-weight: 600;
}
</style>
