<template>
  <div class="nextgen-panel">
    <div v-if="loading" class="content-panel content-panel-padded py-4">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
    </div>

    <div v-else class="flex flex-column gap-4">
      <nav class="nextgen-nav">
        <ul class="nextgen-nav-list">
          <li
            v-for="tab in tabs"
            :key="tab.key"
            class="nextgen-nav-item"
            :class="{ 'is-active': activeTab === tab.key }"
          >
            <a class="nextgen-nav-link" @click="selectTab(tab.key)">
              <i :class="[tab.icon, 'nextgen-nav-icon']" />
              <span>{{ tab.label }}</span>
            </a>
          </li>
        </ul>
      </nav>

      <div v-show="activeTab === 'tools'" class="grid">
        <div class="col-12 lg:col-8">
          <div class="content-panel content-panel-padded">
            <div class="flex align-items-start justify-content-between gap-3 flex-wrap mb-4">
              <div>
                <h2 class="section-title">Available options</h2>
                <p class="section-copy">Enable or disable individual MCP tools exposed to JPilot.</p>
              </div>
              <Button
                label="Save tool settings"
                icon="pi pi-save"
                size="small"
                :loading="saving"
                @click="saveSettings"
              />
            </div>

            <Message v-if="message" class="mb-3" :severity="messageSeverity" :closable="false">
              {{ message }}
            </Message>

            <DataTable :value="nextGenOptions" size="small" striped-rows class="options-table">
              <Column field="label" header="Option">
                <template #body="{ data }">
                  <div class="option-label">{{ data.label }}</div>
                  <div class="setting-hint">{{ data.description }}</div>
                  <code class="tool-code">{{ data.name }}</code>
                </template>
              </Column>
              <Column header="Next-Gen endpoints">
                <template #body="{ data }">
                  <ul v-if="data.nextGenEndpoints?.length" class="endpoint-list m-0 pl-3">
                    <li v-for="endpoint in data.nextGenEndpoints" :key="endpoint">
                      <code>{{ endpoint }}</code>
                    </li>
                  </ul>
                  <span v-else class="setting-hint">Platform / docs</span>
                </template>
              </Column>
              <Column header="Available in">
                <template #body="{ data }">
                  <div class="surface-tags">
                    <Tag v-for="surface in data.surfaces" :key="surface" :value="surface" severity="secondary" />
                  </div>
                </template>
              </Column>
              <Column header="Enabled" style="width: 6rem">
                <template #body="{ data }">
                  <ToggleSwitch
                    v-if="data.configurable"
                    :model-value="isToolEnabled(data.name)"
                    @update:model-value="toggleTool(data.name, $event)"
                  />
                  <Tag v-else value="Always on" severity="info" />
                </template>
              </Column>
            </DataTable>
          </div>
        </div>

        <div class="col-12 lg:col-4 flex flex-column gap-4">
          <div class="sidebar-top-row">
            <div class="content-panel content-panel-padded info-panel sidebar-card">
              <h3 class="info-title">Summary</h3>
              <ul class="info-list m-0 pl-0 list-none">
                <li><strong>Options:</strong> {{ nextGenOptions.length }}</li>
                <li><strong>API operations:</strong> {{ apiOperations.length }}</li>
                <li><strong>Enabled:</strong> {{ enabledToolCount }} / {{ configurableOptionCount }}</li>
                <li><strong>MCP status:</strong> {{ mcpStatus.online ? 'Online' : 'Offline' }}</li>
              </ul>
            </div>

            <div class="content-panel content-panel-padded sidebar-card api-base-panel">
              <span class="meta-label">API base</span>
              <code class="api-base-code">{{ nextGenApi.apiBase || '—' }}</code>
            </div>
          </div>

          <div class="content-panel content-panel-padded">
            <h3 class="info-title">Connection details</h3>
            <p class="setting-hint mb-3">
              Timeouts, SSL, and SSH fallback are configured under Settings → MCP Server.
            </p>
            <div class="meta-details">
              <div class="meta-item">
                <span class="meta-label">Transport</span>
                <span>{{ nextGenApi.transport || '—' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Authentication</span>
                <span>{{ nextGenApi.auth || '—' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Documentation</span>
                <a
                  v-if="nextGenApi.guideUrl"
                  :href="nextGenApi.guideUrl"
                  target="_blank"
                  rel="noopener"
                >
                  Getting started guide
                </a>
                <span v-else>—</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">CLI reference</span>
                <a
                  v-if="nextGenApi.cliReferenceUrl"
                  :href="nextGenApi.cliReferenceUrl"
                  target="_blank"
                  rel="noopener"
                >
                  ADC command reference
                </a>
                <span v-else>—</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">OpenAPI catalog</span>
                <a
                  v-if="nextGenApi.apiDocsUrl"
                  :href="nextGenApi.apiDocsUrl"
                  target="_blank"
                  rel="noopener"
                >
                  External API docs
                </a>
                <span v-else>—</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'reference'" class="content-panel content-panel-padded">
        <div class="flex align-items-start justify-content-between gap-3 flex-wrap mb-4">
          <div>
            <h2 class="section-title">NetScaler API reference</h2>
            <p class="section-copy">
              Full endpoint catalog indexed for JPilot RAG ({{ apiOperations.length }} operations).
            </p>
          </div>
          <div v-if="nextGenApi.apiBase" class="reference-meta">
            <span class="meta-label">API base</span>
            <code class="api-base-code">{{ nextGenApi.apiBase }}</code>
          </div>
        </div>

        <DataTable
          :value="apiOperations"
          size="small"
          striped-rows
          paginator
          :rows="12"
          class="options-table"
        >
          <Column field="category" header="Category" sortable />
          <Column field="name" header="Operation" sortable />
          <Column field="method" header="Method" style="width: 5rem">
            <template #body="{ data }">
              <Tag :value="data.method" :severity="data.method === 'GET' ? 'info' : 'secondary'" />
            </template>
          </Column>
          <Column field="path" header="Path">
            <template #body="{ data }">
              <code>{{ data.path }}</code>
            </template>
          </Column>
        </DataTable>
      </div>

      <BetaFeaturesPanel v-if="activeTab === 'beta'" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import BetaFeaturesPanel from './BetaFeaturesPanel.vue'
import { getMcpConfig, getMcpStatus, saveMcpConfig } from '../services/mcp'

const route = useRoute()
const router = useRouter()
const VALID_TABS = new Set(['tools', 'reference', 'beta'])

const loading = ref(true)
const saving = ref(false)
const activeTab = ref('tools')
const message = ref('')
const messageSeverity = ref('info')
const nextGenOptions = ref([])
const apiCategories = ref([])
const nextGenApi = reactive({
  apiBase: '',
  guideUrl: '',
  apiDocsUrl: '',
  cliReferenceUrl: '',
  transport: '',
  auth: ''
})

const tabs = [
  { key: 'tools', label: 'NetScaler', icon: 'pi pi-cog' },
  { key: 'reference', label: 'NetScaler API reference', icon: 'pi pi-book' },
  { key: 'beta', label: 'Beta features', icon: 'pi pi-flag' }
]

function selectTab(key) {
  if (!VALID_TABS.has(key)) return
  activeTab.value = key
  router.replace({ query: { ...route.query, section: 'nextgen', tab: key } })
}

function syncTabFromQuery() {
  const tab = route.query.tab
  if (typeof tab === 'string' && VALID_TABS.has(tab)) {
    activeTab.value = tab
  }
}

const apiOperations = computed(() =>
  apiCategories.value.flatMap((group) =>
    (group.operations || []).map((operation) => ({
      category: group.category,
      name: operation.name,
      method: operation.method,
      path: operation.path
    }))
  )
)

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
  enabledToolCount: 0
})

const configurableOptionCount = computed(
  () => nextGenOptions.value.filter((item) => item.configurable).length
)

const enabledToolCount = computed(
  () => mcpSettings.enabledTools.filter((name) =>
    nextGenOptions.value.some((item) => item.configurable && item.name === name)
  ).length
)

function isToolEnabled(name) {
  return mcpSettings.enabledTools.includes(name)
}

function toggleTool(name, enabled) {
  if (enabled && !mcpSettings.enabledTools.includes(name)) {
    mcpSettings.enabledTools.push(name)
  }
  if (!enabled) {
    mcpSettings.enabledTools = mcpSettings.enabledTools.filter((item) => item !== name)
  }
}

async function refreshMcpStatus() {
  try {
    const status = await getMcpStatus()
    mcpStatus.online = status.online
    mcpStatus.enabledToolCount = status.enabledToolCount
  } catch {
    mcpStatus.online = false
  }
}

async function loadConfig() {
  loading.value = true
  try {
    const config = await getMcpConfig()
    nextGenOptions.value = config.nextGenOptions || config.availableTools || []
    apiCategories.value = config.nextGenApiCategories || []
    Object.assign(nextGenApi, config.nextGenApi || {})
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
    message.value = error.response?.data?.detail || 'Failed to load MCP tool settings'
    messageSeverity.value = 'error'
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  message.value = ''
  try {
    await saveMcpConfig({ ...mcpSettings })
    message.value = 'MCP tool settings saved and synced to the MCP server.'
    messageSeverity.value = 'success'
    await refreshMcpStatus()
  } catch (error) {
    message.value = error.response?.data?.detail || 'Failed to save settings'
    messageSeverity.value = 'error'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  syncTabFromQuery()
  loadConfig()
})

watch(() => route.query.tab, syncTabFromQuery)
</script>

<style scoped>
.nextgen-nav {
  border-bottom: 1px solid var(--p-content-border-color);
  overflow-x: auto;
}

.nextgen-nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: row;
  white-space: nowrap;
}

.nextgen-nav-item {
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.nextgen-nav-item.is-active {
  border-bottom-color: var(--p-primary-color);
}

.nextgen-nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  font-weight: 500;
  color: var(--p-text-muted-color);
  transition: color 0.15s ease;
}

.nextgen-nav-item.is-active .nextgen-nav-link {
  color: var(--p-primary-color);
}

.nextgen-nav-link:hover {
  color: var(--p-text-color);
}

.nextgen-nav-icon {
  font-size: 1rem;
}

.reference-meta {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
  max-width: 20rem;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.section-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.setting-hint {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  margin-top: 0.2rem;
}

.tool-code {
  display: inline-block;
  margin-top: 0.35rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.sidebar-top-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.sidebar-card {
  min-width: 0;
}

.api-base-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.api-base-code {
  font-size: 0.75rem;
  word-break: break-all;
  line-height: 1.45;
}

.meta-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.875rem;
}

.meta-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
}

.option-label {
  font-size: 0.9375rem;
  font-weight: 500;
}

.endpoint-list {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.endpoint-list li + li {
  margin-top: 0.25rem;
}

.surface-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.options-table :deep(.p-datatable-tbody > tr > td) {
  vertical-align: top;
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

.info-list li + li {
  margin-top: 0.35rem;
}

@media (max-width: 991px) {
  .sidebar-top-row {
    grid-template-columns: 1fr;
  }
}
</style>
