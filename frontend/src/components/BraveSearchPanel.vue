<template>
  <div class="web-search-settings flex flex-column gap-4">
    <div class="content-panel content-panel-padded web-search-intro">
      <div class="panel-eyebrow">
        <Tag value="Optional" severity="secondary" icon="pi pi-globe" />
        <span>Separate from AI providers</span>
      </div>
      <h2 class="section-title mt-2">Documentation web search</h2>
      <p class="section-copy">
        JPilot uses built-in vendor memory first. Enable web search when you want live official documentation
        alongside that memory during chat. Results are restricted to approved domains per appliance vendor.
      </p>
      <Message severity="info" :closable="false" class="mt-3 mb-0">
        Web search retrieves pages for JPilot to read — it does not generate chat replies on its own.
      </Message>
    </div>

    <div class="web-search-top-row">
      <div class="content-panel content-panel-padded web-search-card web-search-config">
        <h3 class="card-title">Configuration</h3>
        <p class="card-copy">
          Turn search on for chat and provide a search provider API key. Keys are stored encrypted on the backend.
        </p>

        <div class="flex flex-column gap-4 mt-4">
          <div class="flex align-items-center justify-content-between gap-3 setting-row">
            <div>
              <div class="setting-label">Enable documentation web search</div>
              <div class="setting-hint">Adds live official doc results when built-in memory is not enough.</div>
            </div>
            <ToggleSwitch v-model="platformSettings.allowWebSearch" />
          </div>

          <div class="flex flex-column gap-2 setting-row">
            <label for="searchApiKey" class="setting-label">Search provider API key</label>
            <Password
              id="searchApiKey"
              v-model="platformSettings.braveSearchApiKey"
              class="w-full"
              :feedback="false"
              toggle-mask
              input-class="w-full"
              :placeholder="platformSettings.hasBraveSearchApiKey ? 'Saved — enter a new key to replace' : 'Paste API key…'"
            />
            <small class="setting-hint">
              JPilot currently uses the Brave Search API as the provider. This key is not used for chat completions.
            </small>
          </div>

          <div class="flex gap-2 pt-1">
            <Button
              label="Save settings"
              icon="pi pi-save"
              size="small"
              :loading="saving"
              @click="saveSettings"
            />
            <Button
              label="Test search"
              icon="pi pi-bolt"
              size="small"
              severity="secondary"
              outlined
              :loading="testing"
              @click="testSearch"
            />
          </div>

          <Message v-if="message" :severity="messageSeverity" :closable="false">
            {{ message }}
          </Message>
        </div>
      </div>

      <BraveSearchUsagePanel ref="usagePanelRef" class="web-search-usage-col" />
    </div>

    <div class="content-panel content-panel-padded web-search-card">
      <h3 class="card-title">Official documentation domains</h3>
      <p class="card-copy">
        Each enabled appliance vendor searches only its own approved domains. Disable a vendor under
        Settings → Appliances → Vendors to hide it here.
      </p>

      <div v-if="catalogLoading" class="domains-loading">
        <ProgressSpinner style="width: 1.75rem; height: 1.75rem" />
      </div>

      <div v-else-if="enabledVendorDomainSections.length" class="vendor-domain-sections">
        <div
          v-for="section in enabledVendorDomainSections"
          :key="section.id"
          class="vendor-domain-block"
        >
          <div class="vendor-domain-head">
            <span class="vendor-domain-title">{{ section.title }}</span>
            <Tag value="Locked" severity="secondary" />
          </div>
          <p class="vendor-domain-hint">{{ section.description }}</p>
          <div class="domain-chips">
            <span v-for="d in section.domains" :key="`${section.id}-${d}`" class="domain-chip domain-chip-locked">
              <i class="pi pi-lock" /> {{ d }}
            </span>
          </div>
        </div>
      </div>

      <p v-else class="domains-empty">
        No platform-enabled vendors with web search domains yet. Enable a supported vendor under Appliances → Vendors.
      </p>
    </div>

    <div v-if="showCustomDomainsCard" class="content-panel content-panel-padded web-search-card">
      <h3 class="card-title">Custom domains</h3>
      <p class="card-copy">
        Extend NetScaler / Citrix documentation search with internal or partner sites. These domains are added on top
        of the locked official list above — only for NetScaler and SDX chat sessions.
      </p>

      <div class="domain-chips mt-3">
        <span v-if="!platformSettings.extraDomains.length" class="domains-empty-inline">No custom domains yet.</span>
        <span v-for="d in platformSettings.extraDomains" :key="d" class="domain-chip">
          {{ d }}
          <button type="button" class="domain-remove" aria-label="Remove domain" @click="removeDomain(d)">
            <i class="pi pi-times" />
          </button>
        </span>
      </div>

      <div class="flex gap-2 mt-3">
        <InputText
          v-model="newDomain"
          class="flex-1"
          placeholder="e.g. docs.internal.example.com"
          @keydown.enter.prevent="addDomain"
        />
        <Button label="Add" icon="pi pi-plus" size="small" severity="secondary" outlined @click="addDomain" />
      </div>
      <small class="setting-hint mt-2 block">Save configuration after editing custom domains.</small>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import BraveSearchUsagePanel from './BraveSearchUsagePanel.vue'
import {
  getCopilotPlatformSettings,
  saveCopilotPlatformSettings,
  testCopilotPlatformSearch
} from '../services/copilotPlatform'
import { getVendorCatalog } from '../services/vendorCatalog'

const usagePanelRef = ref(null)

const VENDOR_DOMAIN_SECTIONS = [
  {
    id: 'citrix',
    catalogGroupId: 'citrix',
    title: 'NetScaler / Citrix',
    description: 'Used when chatting with NetScaler MPX, VPX, or SDX appliances.',
    domainKeys: ['netscaler']
  },
  {
    id: 'cisco',
    catalogGroupId: 'cisco',
    title: 'Cisco',
    description: 'Used when chatting with Cisco appliances.',
    domainKeys: ['cisco']
  },
  {
    id: 'f5',
    catalogGroupId: 'f5',
    title: 'F5 BIG-IP',
    description: 'Used when chatting with F5 appliances.',
    domainKeys: ['f5']
  }
]

const saving = ref(false)
const testing = ref(false)
const catalogLoading = ref(false)
const message = ref('')
const messageSeverity = ref('info')
const platformSettings = reactive({
  allowWebSearch: false,
  hasBraveSearchApiKey: false,
  braveSearchApiKey: '',
  extraDomains: []
})
const lockedDomains = ref([])
const vendorLockedDomains = ref({})
const vendorCatalog = ref(null)
const newDomain = ref('')

const enabledCatalogGroupIds = computed(() => {
  const enabled = new Set()
  if (!vendorCatalog.value?.groups) return enabled
  for (const group of vendorCatalog.value.groups) {
    const hasEnabledProduct = (group.products || []).some(
      (product) => product.toggleable && product.platformEnabled
    )
    if (hasEnabledProduct) {
      enabled.add(group.id)
    }
  }
  return enabled
})

const enabledVendorDomainSections = computed(() =>
  VENDOR_DOMAIN_SECTIONS.filter((section) => enabledCatalogGroupIds.value.has(section.catalogGroupId))
    .map((section) => {
      const domains = []
      for (const key of section.domainKeys) {
        const fromVendor = vendorLockedDomains.value[key] || []
        const fromLocked = key === 'netscaler' ? lockedDomains.value : []
        for (const domain of [...fromLocked, ...fromVendor]) {
          if (domain && !domains.includes(domain)) {
            domains.push(domain)
          }
        }
      }
      return { ...section, domains }
    })
    .filter((section) => section.domains.length)
)

const showCustomDomainsCard = computed(() => enabledCatalogGroupIds.value.has('citrix'))

async function loadVendorCatalog() {
  catalogLoading.value = true
  try {
    vendorCatalog.value = await getVendorCatalog()
  } catch {
    vendorCatalog.value = null
  } finally {
    catalogLoading.value = false
  }
}

async function loadSettings() {
  try {
    const settings = await getCopilotPlatformSettings()
    Object.assign(platformSettings, {
      allowWebSearch: settings.allowWebSearch,
      hasBraveSearchApiKey: settings.hasBraveSearchApiKey,
      braveSearchApiKey: '',
      extraDomains: [...(settings.extraDomains || [])]
    })
    lockedDomains.value = settings.lockedDomains || []
    vendorLockedDomains.value = settings.vendorLockedDomains || {}
  } catch (error) {
    message.value = error.response?.data?.detail || 'Failed to load web search settings'
    messageSeverity.value = 'error'
  }
}

async function saveSettings() {
  saving.value = true
  message.value = ''
  try {
    const payload = {
      allowWebSearch: platformSettings.allowWebSearch,
      braveSearchApiKey: platformSettings.braveSearchApiKey || null,
      extraDomains: platformSettings.extraDomains
    }
    const saved = await saveCopilotPlatformSettings(payload)
    Object.assign(platformSettings, {
      allowWebSearch: saved.allowWebSearch,
      hasBraveSearchApiKey: saved.hasBraveSearchApiKey,
      braveSearchApiKey: '',
      extraDomains: [...(saved.extraDomains || [])]
    })
    lockedDomains.value = saved.lockedDomains || []
    vendorLockedDomains.value = saved.vendorLockedDomains || {}
    message.value = 'Web search settings saved.'
    messageSeverity.value = 'success'
    refreshUsage()
  } catch (error) {
    message.value = error.response?.data?.detail || 'Failed to save web search settings'
    messageSeverity.value = 'error'
  } finally {
    saving.value = false
  }
}

function addDomain() {
  let d = (newDomain.value || '').trim().toLowerCase()
  d = d.replace(/^https?:\/\//, '').split('/')[0].replace(/^\.+|\.+$/g, '')
  if (!d) return
  const allLocked = [
    ...lockedDomains.value,
    ...Object.values(vendorLockedDomains.value).flat()
  ]
  if (allLocked.includes(d) || platformSettings.extraDomains.includes(d)) {
    newDomain.value = ''
    return
  }
  platformSettings.extraDomains.push(d)
  newDomain.value = ''
}

function removeDomain(domain) {
  platformSettings.extraDomains = platformSettings.extraDomains.filter((d) => d !== domain)
}

async function testSearch() {
  testing.value = true
  message.value = ''
  try {
    const result = await testCopilotPlatformSearch({
      allowWebSearch: platformSettings.allowWebSearch,
      braveSearchApiKey: platformSettings.braveSearchApiKey || null
    })
    message.value = result.message
    messageSeverity.value = result.success ? 'success' : 'error'
    if (result.success) {
      refreshUsage()
    }
  } catch (error) {
    message.value = error.response?.data?.detail || 'Web search test failed'
    messageSeverity.value = 'error'
  } finally {
    testing.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadSettings(), loadVendorCatalog()])
})

function refreshUsage() {
  usagePanelRef.value?.refresh?.()
}
</script>

<style scoped>
.web-search-intro {
  border-left: 3px solid var(--p-surface-400);
  background: var(--app-nested-surface);
}

.web-search-card {
  background: var(--app-nested-surface);
}

.web-search-top-row {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr);
  gap: 1rem;
  align-items: stretch;
}

.web-search-config {
  min-width: 0;
}

.web-search-usage-col {
  min-width: 0;
  height: 100%;
}

@media (max-width: 992px) {
  .web-search-top-row {
    grid-template-columns: 1fr;
  }
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.card-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  max-width: 42rem;
}

.section-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  max-width: 42rem;
}

.panel-eyebrow {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
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

.domains-loading {
  display: flex;
  justify-content: center;
  padding: 1.25rem 0 0.5rem;
}

.vendor-domain-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.vendor-domain-block {
  padding: 0.875rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  background: var(--app-nested-surface-strong);
}

.vendor-domain-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.vendor-domain-title {
  font-size: 0.9375rem;
  font-weight: 600;
}

.vendor-domain-hint {
  margin: 0.35rem 0 0.65rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.domains-empty,
.domains-empty-inline {
  margin: 1rem 0 0;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.domain-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.domain-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  font-size: 0.8125rem;
  background: var(--app-nested-surface);
  border: 1px solid var(--p-content-border-color);
}

.domain-chip-locked {
  color: var(--p-text-muted-color);
}

.domain-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
  line-height: 1;
}

.domain-remove:hover {
  color: var(--p-text-color);
}
</style>
