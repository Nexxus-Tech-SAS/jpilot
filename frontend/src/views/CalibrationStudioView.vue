<template>
  <div class="page">
    <PageHeader
      title="Calibration Studio"
      subtitle="Browse the full Nexxus blueprint library by vendor, product, and domain. Download is enabled only for skills your license entitles."
    />

    <div class="content-panel content-panel-padded studio-panel">
      <div class="studio-actions flex align-items-center justify-content-between gap-3 flex-wrap mb-3">
        <div>
          <h2 class="m-0 text-lg font-semibold">Blueprint library</h2>
          <p class="m-0 mt-1 text-sm text-color-secondary">
            Catalog from
            <a :href="catalogUrl || studioBaseUrl" target="_blank" rel="noopener noreferrer">{{ catalogUrl || studioBaseUrl }}</a>
          </p>
        </div>
        <div class="studio-action-buttons flex flex-wrap gap-2">
          <Button
            label="Refresh entitlements"
            icon="pi pi-refresh"
            severity="secondary"
            outlined
            :loading="refreshingEntitlements"
            v-tooltip="'Sync license with Nexxus, then reload the blueprint catalog (use after a license change in Nexxus Admin)'"
            @click="refreshEntitlements"
          />
          <Button
            label="Check for updates"
            icon="pi pi-check-circle"
            severity="secondary"
            outlined
            :loading="checking"
            v-tooltip="'Compare installed skills against the latest official catalog versions'"
            @click="checkForUpdates"
          />
          <Button
            label="Sync all entitled"
            icon="pi pi-sync"
            :loading="syncing"
            :disabled="!installableCount"
            v-tooltip="syncAllTooltip"
            @click="runSyncAll"
          />
        </div>
      </div>

      <Message
        v-if="tierOkBlockedMessage"
        severity="info"
        :closable="false"
        class="mb-3"
      >
        {{ tierOkBlockedMessage }}
      </Message>

      <Message
        v-if="licenseMismatchMessage"
        severity="warn"
        :closable="false"
        class="mb-3"
      >
        {{ licenseMismatchMessage }}
      </Message>

      <div v-if="licenseType" class="license-row flex flex-wrap align-items-center gap-2 mb-3">
        <Tag :value="studioLicenseLabel" severity="secondary" />
        <Tag
          v-if="localLicenseType && localLicenseType !== licenseType"
          :value="`JPilot: ${localLicenseLabel}`"
          severity="warn"
        />
        <span class="license-hint text-sm text-color-secondary">
          {{ installableCount }} entitled · {{ filteredCount }} shown · {{ blueprints.length }} total
          <template v-if="licenseType === 'free' || licenseType === 'early_access'">
            — Ent and Ent+ blueprints are listed but require a matching license to download.
          </template>
        </span>
      </div>

      <div class="library-toolbar flex flex-column lg:flex-row gap-3 mb-3">
        <span class="library-search p-input-icon-left flex-1">
          <i class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Search blueprints by name, skill id, vendor, product, or domain…"
            class="w-full"
          />
        </span>
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

      <Message v-if="checkMessage" :severity="checkSeverity" class="mb-3" :closable="true" @close="clearCheckMessage">
        <div>{{ checkMessage }}</div>
        <ul v-if="checkDetails.length" class="check-details m-0 mt-2 pl-3">
          <li v-for="line in checkDetails" :key="line">{{ line }}</li>
        </ul>
        <div v-if="showUpdatesOnly" class="mt-2">
          <Button label="Show all blueprints" size="small" text @click="showUpdatesOnly = false" />
        </div>
      </Message>

      <Message v-if="syncMessage" severity="success" class="mb-3" :closable="false">{{ syncMessage }}</Message>
      <Message v-if="syncError" severity="warn" class="mb-3" :closable="false">{{ syncError }}</Message>

      <div v-if="loading" class="loading-copy text-color-secondary">Loading blueprint library…</div>

      <template v-else-if="groupedLibrary.length">
        <section
          v-for="vendorGroup in groupedLibrary"
          :key="vendorGroup.vendorKey"
          class="vendor-group"
        >
          <div class="group-header vendor-header">
            <h3 class="group-title m-0">{{ vendorGroup.vendorLabel }}</h3>
            <Tag :value="`${vendorGroup.count} blueprint${vendorGroup.count === 1 ? '' : 's'}`" severity="secondary" />
          </div>

          <section
            v-for="productGroup in vendorGroup.products"
            :key="`${vendorGroup.vendorKey}-${productGroup.product}`"
            class="product-group"
          >
            <div class="group-header product-header">
              <h4 class="group-subtitle m-0">{{ productGroup.product }}</h4>
              <span class="group-count text-sm text-color-secondary">{{ productGroup.count }} blueprint{{ productGroup.count === 1 ? '' : 's' }}</span>
            </div>

            <section
              v-for="domainGroup in productGroup.domains"
              :key="`${vendorGroup.vendorKey}-${productGroup.product}-${domainGroup.domain}`"
              class="domain-group"
            >
              <div class="group-header domain-header">
                <span class="domain-label">{{ domainGroup.domainLabel }}</span>
                <span class="group-count text-sm text-color-secondary">{{ domainGroup.items.length }} skill{{ domainGroup.items.length === 1 ? '' : 's' }}</span>
              </div>

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
                    <Tag
                      :value="data.globalFreeSkill ? 'Yes' : 'No'"
                      :severity="data.globalFreeSkill ? 'success' : 'secondary'"
                    />
                  </template>
                </Column>
                <Column header="Version" style="width: 9rem">
                  <template #body="{ data }">
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
                    <Tag
                      v-tooltip="data.ineligibleReason || undefined"
                      :value="statusLabel(data)"
                      :severity="statusSeverity(data)"
                    />
                  </template>
                </Column>
                <Column header="Actions" style="width: 9rem">
                  <template #body="{ data }">
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
                        @click="uninstallSkill(data)"
                      />
                    </div>
                  </template>
                </Column>
              </DataTable>
            </section>
          </section>
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
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import PageHeader from '../components/PageHeader.vue'
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
  syncMessage.value = ''
  syncError.value = ''
  try {
    const result = await installCalibrationSkill(row.skillId)
    syncMessage.value = result.message || `Downloaded ${row.label}.`
    applyCatalog(await fetchCalibrationCatalog())
  } catch (error) {
    syncError.value = error.response?.data?.detail || error.message || 'Download failed.'
  } finally {
    installingSkillId.value = ''
  }
}

async function uninstallSkill(row) {
  if (!row.installed) return
  const versionHint = row.installedVersion ? ` (${row.installedVersion})` : ''
  const confirmed = window.confirm(
    `Uninstall "${row.label}"${versionHint} from this JPilot installation?\n\n` +
      'The local skill files will be removed. You can download again when entitled.'
  )
  if (!confirmed) return

  uninstallingSkillId.value = row.skillId
  syncMessage.value = ''
  syncError.value = ''
  clearCheckMessage()
  try {
    const result = await uninstallCalibrationSkill(row.skillId, row.installedVersion || undefined)
    syncMessage.value = result.message || `Uninstalled ${row.label}.`
    applyCatalog(await fetchCalibrationCatalog())
  } catch (error) {
    syncError.value = error.response?.data?.detail || error.message || 'Uninstall failed.'
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
  max-width: 80rem;
}

.studio-panel {
  margin-top: 0.5rem;
}

.license-hint {
  max-width: 48rem;
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

.vendor-group + .vendor-group {
  margin-top: 2rem;
}

.product-group {
  margin-top: 1.25rem;
  margin-left: 0.5rem;
  padding-left: 0.75rem;
  border-left: 2px solid var(--p-content-border-color);
}

.domain-group {
  margin-top: 1rem;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.group-title {
  font-size: 1.125rem;
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
</style>
