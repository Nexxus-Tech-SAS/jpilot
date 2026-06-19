<template>
  <div class="page">
    <ConfirmPopup />

    <!-- Header card: title, license tier, entitlement counts, and actions -->
    <div class="content-panel content-panel-padded summary-bar">
      <div class="summary-heading">
        <h1 class="summary-title m-0">Calibration Studio</h1>
        <p class="summary-subtitle m-0">
          Browse the full Nexxus blueprint library by vendor, product, and domain. Download is enabled
          only for skills your license entitles.
        </p>
      </div>

      <div class="summary-row">
        <div class="summary-metrics">
          <div class="summary-metric">
            <span class="summary-metric-label">License tier</span>
            <div class="summary-metric-tags">
              <Tag :value="licenseType ? studioLicenseLabel : '—'" severity="secondary" />
              <Tag
                v-if="localLicenseType && localLicenseType !== licenseType"
                :value="`JPilot: ${localLicenseLabel}`"
                severity="warn"
              />
            </div>
          </div>
          <span class="summary-divider" aria-hidden="true" />
          <div class="summary-metric">
            <span class="summary-metric-label">Entitled</span>
            <span class="summary-metric-number">{{ installableCount }}</span>
          </div>
          <div class="summary-metric">
            <span class="summary-metric-label">Shown</span>
            <span class="summary-metric-number">{{ filteredCount }}</span>
          </div>
          <div class="summary-metric">
            <span class="summary-metric-label">Total</span>
            <span class="summary-metric-number">{{ blueprints.length }}</span>
          </div>
        </div>

        <div class="summary-actions">
          <Button
            :label="isMobile ? 'Refresh' : 'Refresh entitlements'"
            icon="pi pi-refresh"
            severity="secondary"
            outlined
            size="small"
            :loading="refreshingEntitlements"
            v-tooltip="'Sync license with Nexxus, then reload the blueprint catalog (use after a license change in Nexxus Admin)'"
            @click="refreshEntitlements"
          />
          <Button
            :label="isMobile ? 'Updates' : 'Check for updates'"
            icon="pi pi-check-circle"
            severity="secondary"
            outlined
            size="small"
            :loading="checking"
            v-tooltip="'Compare installed skills against the latest official catalog versions'"
            @click="checkForUpdates"
          />
          <Button
            :label="isMobile ? 'Sync' : 'Sync all entitled'"
            icon="pi pi-sync"
            size="small"
            :loading="syncing"
            :disabled="!installableCount"
            v-tooltip="syncAllTooltip"
            @click="runSyncAll"
          />
        </div>
      </div>
    </div>

    <p
      v-if="licenseType === 'free' || licenseType === 'early_access'"
      class="summary-note m-0 mb-3"
    >
      Ent and Ent+ blueprints are listed but require a matching license to download.
    </p>

    <!-- Notifications: entitlement state, license mismatch, and sync/check results -->
    <div class="studio-messages">
      <Message v-if="tierOkBlockedMessage" severity="info" :closable="false">
        {{ tierOkBlockedMessage }}
      </Message>

      <Message v-if="licenseMismatchMessage" severity="warn" :closable="false">
        {{ licenseMismatchMessage }}
      </Message>

      <Message v-if="checkMessage" :severity="checkSeverity" :closable="true" @close="clearCheckMessage">
        <div>{{ checkMessage }}</div>
        <ul v-if="checkDetails.length" class="check-details m-0 mt-2 pl-3">
          <li v-for="line in checkDetails" :key="line">{{ line }}</li>
        </ul>
        <div v-if="showUpdatesOnly" class="mt-2">
          <Button label="Show all blueprints" size="small" text @click="showUpdatesOnly = false" />
        </div>
      </Message>

      <Message v-if="syncMessage" severity="success" :closable="false">{{ syncMessage }}</Message>
      <Message v-if="syncError" severity="warn" :closable="false">{{ syncError }}</Message>
    </div>

    <!-- Library: search, filters, and grouped blueprint tables -->
    <div class="content-panel content-panel-padded library-panel">
      <div class="library-toolbar flex flex-column lg:flex-row gap-3 mb-4">
        <IconField class="library-search flex-1">
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Search blueprints by name, skill id, vendor, product, or domain…"
            class="w-full"
          />
        </IconField>
        <div class="library-filters flex flex-wrap gap-2">
          <Select
            v-model="vendorFilter"
            :options="vendorOptions"
            option-label="label"
            option-value="value"
            placeholder="All vendors"
            show-clear
            class="filter-select"
          />
          <Select
            v-model="productFilter"
            :options="productOptions"
            option-label="label"
            option-value="value"
            placeholder="All products"
            show-clear
            class="filter-select"
          />
          <Select
            v-model="domainFilter"
            :options="domainOptions"
            option-label="label"
            option-value="value"
            placeholder="All domains"
            show-clear
            class="filter-select"
          />
          <Button
            v-if="hasActiveFilters"
            label="Clear filters"
            icon="pi pi-filter-slash"
            severity="secondary"
            text
            @click="clearFilters"
          />
        </div>
      </div>

      <div class="library-scroll">
      <div v-if="loading" class="loading-copy text-color-secondary">Loading blueprint library…</div>

      <template v-else-if="groupedLibrary.length">
        <section
          v-for="vendorGroup in groupedLibrary"
          :key="vendorGroup.vendorKey"
          class="vendor-group"
          :class="{ 'vendor-group-open': isVendorOpen(vendorGroup.vendorKey) }"
        >
          <button
            type="button"
            class="group-header vendor-header"
            :aria-expanded="isVendorOpen(vendorGroup.vendorKey)"
            @click="toggleVendor(vendorGroup.vendorKey)"
          >
            <span class="vendor-header-title">
              <i
                class="pi pi-chevron-right vendor-chevron"
                :class="{ 'vendor-chevron-open': isVendorOpen(vendorGroup.vendorKey) }"
              />
              <h3 class="group-title m-0">{{ vendorGroup.vendorLabel }}</h3>
            </span>
            <Tag :value="`${vendorGroup.count} blueprint${vendorGroup.count === 1 ? '' : 's'}`" severity="secondary" />
          </button>

          <Transition name="expand" @enter="onExpandEnter" @after-enter="onExpandAfterEnter" @leave="onExpandLeave">
          <div v-show="isVendorOpen(vendorGroup.vendorKey)" class="vendor-body">
          <section
            v-for="productGroup in vendorGroup.products"
            :key="`${vendorGroup.vendorKey}-${productGroup.product}`"
            class="product-group"
            :class="{ 'product-group-open': isProductOpen(vendorGroup.vendorKey, productGroup.product) }"
          >
            <button
              type="button"
              class="group-header product-header"
              :aria-expanded="isProductOpen(vendorGroup.vendorKey, productGroup.product)"
              @click="toggleProduct(vendorGroup.vendorKey, productGroup.product)"
            >
              <span class="vendor-header-title">
                <i
                  class="pi pi-chevron-right product-chevron"
                  :class="{ 'vendor-chevron-open': isProductOpen(vendorGroup.vendorKey, productGroup.product) }"
                />
                <h4 class="group-subtitle m-0">{{ productGroup.product }}</h4>
              </span>
              <span class="group-count text-sm text-color-secondary">{{ productGroup.count }} blueprint{{ productGroup.count === 1 ? '' : 's' }}</span>
            </button>

            <Transition name="expand" @enter="onExpandEnter" @after-enter="onExpandAfterEnter" @leave="onExpandLeave">
            <div v-show="isProductOpen(vendorGroup.vendorKey, productGroup.product)" class="product-body">
            <section
              v-for="domainGroup in productGroup.domains"
              :key="`${vendorGroup.vendorKey}-${productGroup.product}-${domainGroup.domain}`"
              class="domain-group"
              :class="{ 'domain-group-open': isDomainOpen(vendorGroup.vendorKey, productGroup.product, domainGroup.domain) }"
            >
              <button
                type="button"
                class="group-header domain-header"
                :aria-expanded="isDomainOpen(vendorGroup.vendorKey, productGroup.product, domainGroup.domain)"
                @click="toggleDomain(vendorGroup.vendorKey, productGroup.product, domainGroup.domain)"
              >
                <span class="vendor-header-title">
                  <i
                    class="pi pi-chevron-right domain-chevron"
                    :class="{ 'vendor-chevron-open': isDomainOpen(vendorGroup.vendorKey, productGroup.product, domainGroup.domain) }"
                  />
                  <span class="domain-label">{{ domainGroup.domainLabel }}</span>
                </span>
                <span class="group-count text-sm text-color-secondary">{{ domainGroup.items.length }} skill{{ domainGroup.items.length === 1 ? '' : 's' }}</span>
              </button>

              <Transition name="expand" @enter="onExpandEnter" @after-enter="onExpandAfterEnter" @leave="onExpandLeave">
              <div v-show="isDomainOpen(vendorGroup.vendorKey, productGroup.product, domainGroup.domain)" class="domain-pane">
              <DataTable
                :value="domainGroup.items"
                striped-rows
                data-key="skillId"
                class="blueprint-table"
              >
                <Column field="label" header="Skill">
                  <template #body="{ data }">
                    <div class="font-medium">{{ data.label }}</div>
                    <code class="skill-id">{{ data.skillId }}</code>
                    <p v-if="data.description" class="skill-desc m-0 mt-1">{{ data.description }}</p>
                    <div v-if="data.domainLabels.length > 1" class="domain-tags mt-1">
                      <Tag
                        v-for="tag in data.domainLabels"
                        :key="tag"
                        :value="tag"
                        severity="secondary"
                        class="domain-tag"
                      />
                    </div>
                  </template>
                </Column>
                <Column header="Min tier" style="width: 7.5rem">
                  <template #body="{ data }">
                    <span class="cell-label">Min tier</span>
                    <div class="tier-cell">
                      <Tag :value="blueprintTierLabel(data)" :severity="blueprintTierSeverity(data)" />
                      <span
                        class="current-tier-note"
                        :class="{ 'current-tier-note-ok': blueprintTierRowNote(data, licenseType) === 'Tier OK' }"
                        :title="blueprintTierRowTooltip(data, licenseType, studioLicenseLabel)"
                      >
                        You: {{ currentTierShortLabel }}
                      </span>
                      <span
                        v-if="blueprintTierRowNote(data, licenseType)"
                        class="current-tier-match"
                        :title="data.ineligibleReason || blueprintTierRowTooltip(data, licenseType, studioLicenseLabel)"
                      >
                        {{ blueprintTierRowNote(data, licenseType) }}
                      </span>
                    </div>
                  </template>
                </Column>
                <Column header="Free global" style="width: 6rem">
                  <template #body="{ data }">
                    <span class="cell-label">Free global</span>
                    <Tag
                      :value="data.globalFreeSkill ? 'Yes' : 'No'"
                      :severity="data.globalFreeSkill ? 'success' : 'secondary'"
                    />
                  </template>
                </Column>
                <Column header="Version" style="width: 9rem">
                  <template #body="{ data }">
                    <span class="cell-label">Version</span>
                    <div class="version-cell">
                      <span v-if="data.catalogVersion">catalog {{ data.catalogVersion }}</span>
                      <span v-else class="text-color-secondary">—</span>
                      <span
                        v-if="data.entitledVersion && data.entitledVersion !== data.catalogVersion"
                        class="installed-version"
                      >
                        download {{ data.entitledVersion }}
                      </span>
                      <span v-if="data.installedVersion" class="installed-version">
                        installed {{ data.installedVersion }}
                      </span>
                    </div>
                  </template>
                </Column>
                <Column header="Status" style="width: 9rem">
                  <template #body="{ data }">
                    <span class="cell-label">Status</span>
                    <Tag
                      v-tooltip="data.ineligibleReason || undefined"
                      :value="statusLabel(data)"
                      :severity="statusSeverity(data)"
                    />
                  </template>
                </Column>
                <Column header="Actions" style="width: 9rem">
                  <template #body="{ data }">
                    <span class="cell-label">Actions</span>
                    <div class="action-cell">
                      <Button
                        v-if="canDownload(data)"
                        :label="downloadLabel(data)"
                        icon="pi pi-download"
                        size="small"
                        :loading="installingSkillId === data.skillId"
                        @click="downloadSkill(data)"
                      />
                      <Tag
                        v-else-if="blueprintIsLatestEntitled(data)"
                        value="Up to date"
                        severity="success"
                        v-tooltip="blueprintCatalogAheadOfEntitlement(data)
                          ? `Catalog ${data.catalogVersion} is not assigned via sync yet; ${data.entitledVersion} is the latest entitled version.`
                          : undefined"
                      />
                      <Tag
                        v-else-if="data.installed && !data.updateAvailable"
                        value="Up to date"
                        severity="success"
                      />
                      <Button
                        v-else
                        :label="blueprintDownloadBlockedButtonLabel(data, licenseType)"
                        icon="pi pi-lock"
                        size="small"
                        severity="secondary"
                        outlined
                        disabled
                        v-tooltip="blueprintDownloadBlockedLabel(data, licenseType)"
                      />
                      <Button
                        v-if="data.installed"
                        label="Uninstall"
                        icon="pi pi-trash"
                        size="small"
                        severity="danger"
                        text
                        class="action-uninstall"
                        :loading="uninstallingSkillId === data.skillId"
                        v-tooltip="'Remove the local copy of this skill from JPilot'"
                        @click="confirmUninstall(data, $event)"
                      />
                    </div>
                  </template>
                </Column>
              </DataTable>
              </div>
              </Transition>
            </section>
            </div>
            </Transition>
          </section>
          </div>
          </Transition>
        </section>
      </template>

      <p v-else-if="!loading && blueprints.length && !filteredCount" class="empty-copy m-0 mt-3">
        No blueprints match your search or filters. Try clearing filters or broadening your search.
      </p>

      <p v-else-if="!loading && !blueprints.length" class="empty-copy m-0 mt-3">
        No blueprints returned from the official catalog. Check connectivity to
        <strong>{{ studioBaseUrl }}</strong>, then refresh the page.
      </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import ConfirmPopup from 'primevue/confirmpopup'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { CALIBRATION_STUDIO_BASE_URL } from '../config/calibrationStudio.js'
import { getLicense } from '../services/system.js'
import {
  blueprintFilterOptions,
  blueprintDownloadBlockedButtonLabel,
  blueprintDownloadBlockedLabel,
  blueprintCatalogAheadOfEntitlement,
  blueprintCanDownload,
  blueprintHasDownloadableUpdate,
  blueprintIsLatestEntitled,
  blueprintStatusLabel,
  blueprintTierLabel,
  blueprintTierSeverity,
  blueprintTierRowNote,
  blueprintTierRowTooltip,
  buildBlueprintLibraryRows,
  collectBlueprintUpdates,
  collectTierOkBlockedRows,
  currentBlueprintTierLabel,
  fetchCalibrationCatalog,
  filterBlueprintRows,
  formatBlueprintUpdateSummary,
  groupBlueprintRows,
  installCalibrationSkill,
  licenseTypeLabel,
  syncCalibrationsFromStudio,
  uninstallCalibrationSkill,
} from '../services/calibrationSync.js'

const confirm = useConfirm()
const toast = useToast()

const studioBaseUrl = CALIBRATION_STUDIO_BASE_URL
const blueprints = ref([])
const loading = ref(false)
const refreshingEntitlements = ref(false)
const syncing = ref(false)
const checking = ref(false)
const installingSkillId = ref('')
const uninstallingSkillId = ref('')
const syncMessage = ref('')
const syncError = ref('')
const checkMessage = ref('')
const checkSeverity = ref('info')
const checkDetails = ref([])
const showUpdatesOnly = ref(false)
const catalogUrl = ref('')
const clientId = ref('')
const licenseType = ref('')
const localLicenseType = ref('')
const licenseEntitlementMismatch = ref(false)
const studioAuthMissing = ref(false)
const searchQuery = ref('')
const vendorFilter = ref('')
const productFilter = ref('')
const domainFilter = ref('')
const openVendors = ref(new Set())
const openProducts = ref(new Set())
const openDomains = ref(new Set())

// Track narrow viewports so we can shorten labels and tighten layout on mobile.
const isMobile = ref(false)
let mobileMq = null
function syncIsMobile(event) {
  isMobile.value = event.matches
}
onMounted(() => {
  mobileMq = window.matchMedia('(max-width: 640px)')
  isMobile.value = mobileMq.matches
  mobileMq.addEventListener('change', syncIsMobile)
})
onUnmounted(() => {
  mobileMq?.removeEventListener('change', syncIsMobile)
})

function toggleInSet(setRef, key) {
  const next = new Set(setRef.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  setRef.value = next
}

const productKey = (vendorKey, product) => `${vendorKey}::${product}`
const domainKey = (vendorKey, product, domain) => `${vendorKey}::${product}::${domain}`

// Animate height for expand/collapse (works for unknown content heights).
function onExpandEnter(el) {
  el.style.height = '0'
  el.style.overflow = 'hidden'
  void el.offsetHeight
  el.style.transition = 'height 0.26s ease'
  el.style.height = `${el.scrollHeight}px`
}

function onExpandAfterEnter(el) {
  el.style.height = ''
  el.style.overflow = ''
  el.style.transition = ''
}

function onExpandLeave(el) {
  el.style.height = `${el.scrollHeight}px`
  el.style.overflow = 'hidden'
  void el.offsetHeight
  el.style.transition = 'height 0.26s ease'
  el.style.height = '0'
}

function isVendorOpen(vendorKey) {
  return openVendors.value.has(vendorKey)
}
function toggleVendor(vendorKey) {
  toggleInSet(openVendors, vendorKey)
}

function isProductOpen(vendorKey, product) {
  return openProducts.value.has(productKey(vendorKey, product))
}
function toggleProduct(vendorKey, product) {
  toggleInSet(openProducts, productKey(vendorKey, product))
}

function isDomainOpen(vendorKey, product, domain) {
  return openDomains.value.has(domainKey(vendorKey, product, domain))
}
function toggleDomain(vendorKey, product, domain) {
  toggleInSet(openDomains, domainKey(vendorKey, product, domain))
}

const studioLicenseLabel = computed(() => licenseTypeLabel(licenseType.value))
const localLicenseLabel = computed(() => licenseTypeLabel(localLicenseType.value))
const currentTierShortLabel = computed(() => currentBlueprintTierLabel(licenseType.value))

const licenseMismatchMessage = computed(() => {
  if (!licenseEntitlementMismatch.value) return ''
  if (studioAuthMissing.value) {
    return (
      `JPilot shows ${localLicenseLabel.value}, but Calibration Studio still reports ${studioLicenseLabel.value}. ` +
      'Add your license code under Settings → License and sync, then refresh this library.'
    )
  }
  return (
    `JPilot shows ${localLicenseLabel.value}, but Calibration Studio reports ${studioLicenseLabel.value} for blueprint downloads. ` +
    'Try Settings → License → Sync. If entitlements stay blocked, contact Nexxus to assign blueprints to this installation.'
  )
})

const tierOkBlockedMessage = computed(() => {
  const blocked = collectTierOkBlockedRows(blueprints.value, licenseType.value)
  if (!blocked.length) return ''
  const names = blocked.slice(0, 3).map((row) => row.label).join(', ')
  const suffix = blocked.length > 3 ? ` and ${blocked.length - 3} more` : ''
  const clientHint = clientId.value
    ? ' Nexxus must enable each blueprint for your organization in Calibration Studio.'
    : ' This install has no Nexxus client id yet — assign the license to this fingerprint in Nexxus Admin, then click Refresh entitlements.'
  return (
    `Your ${studioLicenseLabel.value} license tier qualifies for ${blocked.length} blueprint(s) ` +
    `(${names}${suffix}), but they are not enabled for download yet.${clientHint} ` +
    'After a license change in Nexxus Admin, use Refresh entitlements above.'
  )
})

const installableCount = computed(() => blueprints.value.filter((row) => row.installable).length)

const filteredRows = computed(() => {
  let rows = filterBlueprintRows(blueprints.value, {
    search: searchQuery.value,
    vendor: vendorFilter.value,
    product: productFilter.value,
    domain: domainFilter.value,
  })
  if (showUpdatesOnly.value) {
    rows = rows.filter((row) => row.updateAvailable)
  }
  return rows
})

const filteredCount = computed(() => filteredRows.value.length)

const groupedLibrary = computed(() => groupBlueprintRows(filteredRows.value))

const allFilterOptions = computed(() => blueprintFilterOptions(blueprints.value))

const vendorOptions = computed(() => allFilterOptions.value.vendors)

const productOptions = computed(() => {
  const scope = vendorFilter.value
    ? blueprints.value.filter((row) => row.vendorKey === vendorFilter.value)
    : blueprints.value
  return blueprintFilterOptions(scope).products
})

const domainOptions = computed(() => {
  let scope = blueprints.value
  if (vendorFilter.value) {
    scope = scope.filter((row) => row.vendorKey === vendorFilter.value)
  }
  if (productFilter.value) {
    scope = scope.filter((row) => row.product === productFilter.value)
  }
  return blueprintFilterOptions(scope).domains
})

const hasActiveFilters = computed(
  () => Boolean(searchQuery.value.trim() || vendorFilter.value || productFilter.value || domainFilter.value)
)

const syncAllTooltip = computed(() => {
  if (!installableCount.value) return 'No entitled blueprints to sync'
  return `Download all ${installableCount.value} entitled blueprint(s) from the official catalog`
})

function clearCheckMessage() {
  checkMessage.value = ''
  checkDetails.value = []
  showUpdatesOnly.value = false
}

function clearFilters() {
  searchQuery.value = ''
  vendorFilter.value = ''
  productFilter.value = ''
  domainFilter.value = ''
  showUpdatesOnly.value = false
}

watch(vendorFilter, () => {
  if (productFilter.value && !productOptions.value.some((option) => option.value === productFilter.value)) {
    productFilter.value = ''
  }
  if (domainFilter.value && !domainOptions.value.some((option) => option.value === domainFilter.value)) {
    domainFilter.value = ''
  }
})

watch(productFilter, () => {
  if (domainFilter.value && !domainOptions.value.some((option) => option.value === domainFilter.value)) {
    domainFilter.value = ''
  }
})

// While searching or filtering, expand every matching group so results are visible.
watch([hasActiveFilters, groupedLibrary], ([active, groups]) => {
  if (!active) return
  const vendors = new Set()
  const products = new Set()
  const domains = new Set()
  for (const group of groups) {
    vendors.add(group.vendorKey)
    for (const product of group.products) {
      products.add(productKey(group.vendorKey, product.product))
      for (const domain of product.domains) {
        domains.add(domainKey(group.vendorKey, product.product, domain.domain))
      }
    }
  }
  openVendors.value = vendors
  openProducts.value = products
  openDomains.value = domains
})

function statusLabel(row) {
  return blueprintStatusLabel(row, licenseType.value)
}

function statusSeverity(row) {
  if (blueprintIsLatestEntitled(row)) return 'success'
  if (row.installable && row.installed && blueprintHasDownloadableUpdate(row)) return 'warn'
  if (row.installable && row.installed) return 'success'
  if (row.installable) return 'info'
  if (row.installed && row.updateAvailable) return 'warn'
  if (row.installed) return 'success'
  if (row.inCatalog && !row.installable) return 'warn'
  return 'secondary'
}

function canDownload(row) {
  return blueprintCanDownload(row)
}

function downloadLabel(row) {
  if (row.installed && row.updateAvailable) return 'Update'
  return 'Download'
}

function applyCatalog(catalog) {
  catalogUrl.value = catalog.catalogUrl || studioBaseUrl
  clientId.value = catalog.clientId || ''
  licenseType.value = catalog.licenseType || 'free'
  localLicenseType.value = catalog.localLicenseType || ''
  licenseEntitlementMismatch.value = Boolean(catalog.licenseEntitlementMismatch)
  studioAuthMissing.value = Boolean(catalog.studioAuthMissing)
  blueprints.value = buildBlueprintLibraryRows(catalog)
}

async function refreshEntitlements() {
  refreshingEntitlements.value = true
  syncError.value = ''
  try {
    await getLicense()
    await loadCatalog()
  } catch (error) {
    syncError.value =
      error.response?.data?.detail || error.message || 'Could not refresh entitlements from Nexxus.'
  } finally {
    refreshingEntitlements.value = false
  }
}

async function loadCatalog() {
  loading.value = true
  syncError.value = ''
  try {
    applyCatalog(await fetchCalibrationCatalog())
  } catch (error) {
    syncError.value = error.response?.data?.detail || error.message || 'Could not load blueprint library.'
    blueprints.value = []
  } finally {
    loading.value = false
  }
}

async function checkForUpdates() {
  checking.value = true
  syncError.value = ''
  syncMessage.value = ''
  clearCheckMessage()
  try {
    applyCatalog(await fetchCalibrationCatalog())
    const summary = collectBlueprintUpdates(blueprints.value)
    const result = formatBlueprintUpdateSummary(summary)
    checkMessage.value = result.message
    checkSeverity.value = result.severity
    checkDetails.value = result.detail
    if (summary.updateCount) {
      showUpdatesOnly.value = true
    }
  } catch (error) {
    syncError.value = error.response?.data?.detail || error.message || 'Could not check for blueprint updates.'
  } finally {
    checking.value = false
  }
}

async function downloadSkill(row) {
  if (!canDownload(row)) return
  installingSkillId.value = row.skillId
  syncError.value = ''
  try {
    const result = await installCalibrationSkill(row.skillId)
    toast.add({
      severity: 'success',
      summary: row.installed && row.updateAvailable ? 'Update complete' : 'Download complete',
      detail: result.message || `Downloaded ${row.label}.`,
      life: 4000,
    })
    applyCatalog(await fetchCalibrationCatalog())
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Download failed',
      detail: error.response?.data?.detail || error.message || 'Download failed.',
      life: 5000,
    })
  } finally {
    installingSkillId.value = ''
  }
}

function confirmUninstall(row, event) {
  if (!row.installed) return
  const versionHint = row.installedVersion ? ` (${row.installedVersion})` : ''
  confirm.require({
    target: event.currentTarget,
    message: `Uninstall "${row.label}"${versionHint}? The local skill files will be removed.`,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Uninstall',
    rejectLabel: 'Cancel',
    acceptClass: 'p-button-danger p-button-sm',
    rejectClass: 'p-button-secondary p-button-text p-button-sm',
    accept: () => uninstallSkill(row),
  })
}

async function uninstallSkill(row) {
  if (!row.installed) return
  uninstallingSkillId.value = row.skillId
  syncError.value = ''
  clearCheckMessage()
  try {
    const result = await uninstallCalibrationSkill(row.skillId, row.installedVersion || undefined)
    toast.add({
      severity: 'success',
      summary: 'Uninstalled',
      detail: result.message || `Uninstalled ${row.label}.`,
      life: 4000,
    })
    applyCatalog(await fetchCalibrationCatalog())
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Uninstall failed',
      detail: error.response?.data?.detail || error.message || 'Uninstall failed.',
      life: 5000,
    })
  } finally {
    uninstallingSkillId.value = ''
  }
}

async function runSyncAll() {
  syncing.value = true
  syncMessage.value = ''
  syncError.value = ''
  try {
    try {
      applyCatalog(await fetchCalibrationCatalog())
    } catch (error) {
      syncError.value = error.response?.data?.detail || error.message || 'Could not refresh blueprint library.'
    }

    const result = await syncCalibrationsFromStudio()
    syncMessage.value = result.message || 'Entitled blueprints synced.'

    try {
      applyCatalog(await fetchCalibrationCatalog())
    } catch {
      // Keep the pre-sync catalog visible if refresh fails after a successful sync.
    }
  } catch (error) {
    syncError.value = error.response?.data?.detail || error.message || 'Sync failed.'
  } finally {
    syncing.value = false
  }
}

onMounted(refreshEntitlements)
</script>

<style scoped>
.page {
  padding: 0 0.5rem 1rem;
  width: 100%;
  max-width: 100%;
  /* MainLayout makes .route-page a full-height flex column (flex:1; min-height:0).
     Keep the header + filters fixed and let only .library-scroll scroll. */
  min-height: 0;
}

/* Fixed (non-scrolling) regions */
.summary-bar,
.summary-note,
.studio-messages {
  flex: 0 0 auto;
}

/* Blueprint panel fills remaining height; its list scrolls internally */
.library-panel {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.library-toolbar {
  flex: 0 0 auto;
}

.library-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  /* room so the scrollbar doesn't sit on top of the cards */
  margin-right: -0.5rem;
  padding-right: 0.5rem;
}

/* Header card: title, license tier, entitlement counts, and actions */
.summary-bar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 0.5rem 0 0.75rem;
}

.summary-heading {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-title {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--p-text-color);
}

.summary-subtitle {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  max-width: 60rem;
}

.summary-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem 2rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--p-content-border-color);
}

.summary-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.summary-metrics {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.25rem 1.75rem;
}

.summary-metric {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.summary-metric-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.summary-metric-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.summary-metric-number {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--p-text-color);
}

.summary-divider {
  align-self: stretch;
  width: 1px;
  min-height: 2.25rem;
  background: var(--p-content-border-color);
}

.summary-note {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  padding-left: 0.25rem;
}

/* Notifications block */
.studio-messages {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.studio-messages:not(:empty) {
  margin-bottom: 1rem;
}

.library-search {
  min-width: 14rem;
}

.library-search :deep(.p-inputtext) {
  width: 100%;
}

.filter-select {
  min-width: 10rem;
}

.loading-copy {
  font-size: 0.875rem;
  padding: 1rem 0;
}

/* Collapsible vendor group */
.vendor-group {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
}

.vendor-group + .vendor-group {
  margin-top: 0.75rem;
}

.vendor-header {
  width: 100%;
  margin: 0;
  padding: 0.875rem 1.25rem;
  background: var(--p-content-background);
  border: 0;
  border-radius: var(--content-radius) var(--content-radius) 0 0;
  cursor: pointer;
  transition: background 0.15s ease;
}

.vendor-header:hover {
  background: var(--p-content-hover-background, var(--p-highlight-background));
}

.vendor-group-open .vendor-header {
  border-bottom: 1px solid var(--p-content-border-color);
}

.vendor-header-title {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.vendor-chevron {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  transition: transform 0.2s ease;
}

.vendor-chevron-open {
  transform: rotate(90deg);
}

/* Animated collapse panes: border-box keeps padding from leaving a gap at height 0 */
.vendor-body,
.product-body,
.domain-pane {
  box-sizing: border-box;
}

.vendor-body {
  padding: 0.75rem 1.25rem 1.25rem;
}

.product-group {
  margin-top: 0.75rem;
  margin-left: 0.5rem;
  padding-left: 0.75rem;
  border-left: 2px solid var(--p-content-border-color);
}

.product-group:first-child {
  margin-top: 0;
}

.product-body {
  padding: 0.25rem 0 0.5rem;
}

.domain-group {
  margin-top: 0.5rem;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

/* Product & domain headers act as collapse toggles */
.product-header,
.domain-header {
  width: 100%;
  background: none;
  border: 0;
  padding: 0.35rem 0;
  cursor: pointer;
  text-align: left;
}

.product-header:hover .group-subtitle,
.domain-header:hover .domain-label {
  color: var(--p-primary-color);
}

.product-chevron,
.domain-chevron {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  transition: transform 0.2s ease;
}

.group-title {
  font-size: 1.0625rem;
  font-weight: 600;
}

.group-subtitle {
  font-size: 1rem;
  font-weight: 600;
}

.domain-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.blueprint-table {
  margin-bottom: 0.5rem;
}

.skill-id {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

/* Per-cell labels: only shown in the mobile stacked-card layout */
.cell-label {
  display: none;
}

.skill-desc {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.domain-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.domain-tag {
  font-size: 0.6875rem;
}

.version-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.8125rem;
}

.tier-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.current-tier-note {
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  line-height: 1.2;
  white-space: nowrap;
}

.current-tier-note-ok {
  color: var(--p-text-color);
}

.current-tier-match {
  color: var(--p-orange-500);
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.2;
  text-transform: uppercase;
}

.action-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.action-uninstall {
  padding-left: 0;
}

.installed-version {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.empty-copy {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.check-details {
  font-size: 0.8125rem;
  color: var(--p-text-color);
}

.check-details li + li {
  margin-top: 0.25rem;
}

/* ---------- Mobile ---------- */
@media (max-width: 640px) {
  .page {
    padding: 0 0.25rem 0.75rem;
  }

  /* Tighter cards, hide low-value chrome */
  .summary-bar,
  .library-panel {
    padding: 0.85rem 0.9rem;
  }

  .summary-bar {
    gap: 0.75rem;
  }

  .summary-subtitle {
    display: none;
  }

  .summary-row {
    gap: 0.75rem;
  }

  .summary-divider {
    display: none;
  }

  .summary-metrics {
    gap: 0.6rem 1.25rem;
  }

  .summary-metric-number {
    font-size: 1.25rem;
  }

  /* Action buttons: all three in one row, shortened labels, evenly split */
  .summary-actions {
    width: 100%;
    flex-wrap: nowrap;
    gap: 0.4rem;
  }

  .summary-actions :deep(.p-button) {
    flex: 1 1 0;
    min-width: 0;
    justify-content: center;
  }

  .summary-actions :deep(.p-button-label) {
    white-space: nowrap;
  }

  /* Filters share a single row; search stays on its own full-width line above */
  .library-toolbar {
    margin-bottom: 1rem !important;
  }

  .library-filters {
    flex-wrap: nowrap;
  }

  .filter-select {
    flex: 1 1 0;
    min-width: 0;
  }

  .library-search {
    min-width: 0;
    width: 100%;
  }

  /* Group headers: a little tighter */
  .vendor-header {
    padding: 0.75rem 0.9rem;
  }

  .vendor-body {
    padding: 0.6rem 0.9rem 0.9rem;
  }

  /* Blueprint rows become stacked, labeled cards instead of a squished table */
  .blueprint-table :deep(.p-datatable-thead) {
    display: none;
  }

  .blueprint-table :deep(.p-datatable-tbody) > tr {
    display: block;
    background: var(--p-content-background) !important;
    border: 1px solid var(--p-content-border-color);
    border-radius: 10px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.6rem;
  }

  .blueprint-table :deep(.p-datatable-tbody) > tr > td {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    width: auto !important;
    border: 0 !important;
    padding: 0.3rem 0 !important;
    text-align: right;
  }

  .cell-label {
    display: inline-block;
    flex-shrink: 0;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--p-text-muted-color);
    text-align: left;
    padding-top: 0.15rem;
  }

  /* Skill cell (first column) spans the full card width with no inline label */
  .blueprint-table :deep(.p-datatable-tbody) > tr > td:first-child {
    display: block;
    text-align: left;
    padding-bottom: 0.5rem !important;
    margin-bottom: 0.35rem;
    border-bottom: 1px solid var(--p-content-border-color) !important;
  }

  /* Tier / action sub-layouts read better right-aligned in card rows */
  .tier-cell,
  .action-cell {
    align-items: flex-end;
  }

  .action-cell {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .version-cell {
    align-items: flex-end;
    text-align: right;
  }
}
</style>
