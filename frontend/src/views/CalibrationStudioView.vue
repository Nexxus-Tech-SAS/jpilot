<template>
  <div class="studio">
    <ConfirmPopup />

    <!-- Header: title + secondary license popover + catalog actions -->
    <header class="studio-header">
      <div class="studio-heading">
        <h1 class="studio-title m-0">Calibration Studio</h1>
        <p class="studio-subtitle m-0">
          Discover, install, and manage Skills, Personas, and Knowledge Packs for JPilot.
        </p>
      </div>

      <div class="studio-header-actions">
        <Button
          class="license-chip"
          severity="secondary"
          text
          size="small"
          icon="pi pi-verified"
          :label="`${headlineLicenseLabel}`"
          v-tooltip.bottom="'License & entitlements'"
          @click="toggleLicense"
        />
        <Popover ref="licensePopover">
          <div class="license-panel">
            <div class="license-panel-row">
              <span>License tier</span>
              <Tag :value="headlineLicenseLabel" :severity="headlineLicenseSeverity" />
            </div>
            <div class="license-panel-row">
              <span>Entitled blueprints</span>
              <strong>{{ installableCount }}</strong>
            </div>
            <div class="license-panel-row">
              <span>Catalog total</span>
              <strong>{{ blueprints.length }}</strong>
            </div>
            <p class="license-panel-note m-0">
              Ent and Ent+ blueprints are listed but require a matching license to install.
            </p>
            <Button
              label="Refresh entitlements"
              icon="pi pi-refresh"
              size="small"
              outlined
              class="w-full"
              :loading="refreshingEntitlements"
              @click="refreshEntitlements"
            />
          </div>
        </Popover>

        <Button
          :label="isMobile ? 'Updates' : 'Check updates'"
          icon="pi pi-check-circle"
          severity="secondary"
          outlined
          size="small"
          :loading="checking"
          v-tooltip.bottom="'Compare installed skills against the latest catalog versions'"
          @click="checkForUpdates"
        />
        <Button
          :label="isMobile ? 'Sync' : 'Sync all entitled'"
          icon="pi pi-sync"
          size="small"
          :loading="syncing"
          :disabled="!installableCount"
          v-tooltip.bottom="syncAllTooltip"
          @click="runSyncAll"
        />
      </div>
    </header>

    <!-- Dashboard: compact summary cards -->
    <section class="studio-stats">
      <button type="button" class="stat-tile" @click="goTo('skills', 'installed')">
        <span class="stat-tile-icon stat-skill"><i class="pi pi-bolt" /></span>
        <span class="stat-tile-body">
          <span class="stat-tile-value">{{ loading ? '—' : installedBlueprints.length }}</span>
          <span class="stat-tile-label">Installed Skills</span>
        </span>
      </button>
      <button type="button" class="stat-tile" @click="browseType('persona')">
        <span class="stat-tile-icon stat-persona"><i class="pi pi-users" /></span>
        <span class="stat-tile-body">
          <span class="stat-tile-value">{{ loading ? '—' : (catalogPersonaCount || installedPersonaCount) }}</span>
          <span class="stat-tile-label">Personas</span>
        </span>
      </button>
      <button type="button" class="stat-tile" @click="browseType('knowledge_pack')">
        <span class="stat-tile-icon stat-pack"><i class="pi pi-box" /></span>
        <span class="stat-tile-body">
          <span class="stat-tile-value">{{ loading ? '—' : (typeCounts.knowledge_pack || knowledgePackCount) }}</span>
          <span class="stat-tile-label">Knowledge Packs</span>
        </span>
      </button>
      <button
        type="button"
        class="stat-tile"
        :class="{ 'stat-tile-alert': updatesAvailable > 0 }"
        @click="goTo('skills', 'updates')"
      >
        <span class="stat-tile-icon stat-update"><i class="pi pi-arrow-up" /></span>
        <span class="stat-tile-body">
          <span class="stat-tile-value">{{ loading ? '—' : updatesAvailable }}</span>
          <span class="stat-tile-label">Updates Available</span>
        </span>
      </button>
    </section>

    <!-- Notifications -->
    <div class="studio-messages">
      <Message v-if="syncError" severity="warn" :closable="false">{{ syncError }}</Message>
    </div>

    <!-- Asset type switch -->
    <SelectButton
      v-model="activeView"
      :options="viewOptions"
      option-label="label"
      option-value="value"
      :allow-empty="false"
      class="view-switch"
      aria-label="Content type"
    >
      <template #option="{ option }">
        <i :class="option.icon" />
        <span>{{ option.label }}</span>
      </template>
    </SelectButton>

    <!-- BLUEPRINT LIBRARY (skills + personas + knowledge packs) -->
    <template v-if="activeView === 'skills'">
      <div class="catalog-toolbar">
        <IconField class="catalog-search">
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Search by name, vendor, product, or domain…"
            class="w-full"
          />
        </IconField>

        <SelectButton
          v-model="quickFilter"
          :options="quickFilterOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          class="quick-filter"
          aria-label="Quick filter"
        />
      </div>

      <SelectButton
        v-model="typeFilter"
        :options="typeFilterOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        class="type-filter"
        aria-label="Artifact type"
      />

      <div class="catalog-filters">
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
          label="Clear"
          icon="pi pi-filter-slash"
          severity="secondary"
          text
          size="small"
          @click="clearFilters"
        />
        <span class="catalog-count">{{ filteredCount }} result{{ filteredCount === 1 ? '' : 's' }}</span>
      </div>

      <!-- Loading skeletons -->
      <div v-if="loading" class="catalog-grid">
        <div v-for="n in 8" :key="n" class="skeleton-card">
          <div class="skeleton-card-head">
            <Skeleton shape="circle" size="2.25rem" />
            <div class="flex-1">
              <Skeleton width="70%" height="0.9rem" class="mb-2" />
              <Skeleton width="45%" height="0.7rem" />
            </div>
          </div>
          <Skeleton width="100%" height="0.7rem" class="mt-2" />
          <Skeleton width="85%" height="0.7rem" class="mt-2" />
          <div class="skeleton-card-foot">
            <Skeleton width="5rem" height="1.4rem" borderRadius="1rem" />
            <Skeleton width="5rem" height="2rem" borderRadius="0.5rem" />
          </div>
        </div>
      </div>

      <!-- Card grid -->
      <div v-else-if="filteredCount" class="catalog-grid">
        <MarketplaceSkillCard
          v-for="row in filteredRows"
          :key="`${row.type || 'skill'}::${row.skillId}`"
          :row="row"
          :license-type="effectiveLicenseType"
          :installing="installingSkillId === row.skillId"
          :uninstalling="uninstallingSkillId === row.skillId"
          @open="openDetails"
          @install="downloadSkill"
          @uninstall="confirmUninstall"
        />
      </div>

      <!-- Empty states -->
      <div v-else-if="blueprints.length" class="catalog-empty">
        <i class="pi pi-search catalog-empty-icon" />
        <p class="catalog-empty-title m-0">No blueprints match your filters</p>
        <p class="catalog-empty-copy m-0">Try a different search or clear the active filters.</p>
        <Button label="Clear filters" icon="pi pi-filter-slash" size="small" outlined @click="clearFilters" />
      </div>

      <div v-else class="catalog-empty">
        <i class="pi pi-inbox catalog-empty-icon" />
        <p class="catalog-empty-title m-0">No blueprints in the catalog</p>
        <p class="catalog-empty-copy m-0">
          Check connectivity to <strong>{{ studioBaseUrl }}</strong>, then refresh entitlements.
        </p>
      </div>
    </template>

    <CalibrationPersonaUpdatesPanel
      v-else-if="activeView === 'personas'"
      :personas="personaRows"
      :busy-id="installingSkillId || uninstallingSkillId"
      @update="downloadSkill"
      @delete="confirmUninstall"
    />
    <CalibrationKnowledgePacksPanel v-else />

    <BlueprintDetailsDrawer
      v-model:visible="drawerVisible"
      :row="selectedRow"
      :license-type="effectiveLicenseType"
      :installing="!!selectedRow && installingSkillId === selectedRow.skillId"
      :uninstalling="!!selectedRow && uninstallingSkillId === selectedRow.skillId"
      @install="downloadSkill"
      @uninstall="confirmUninstall"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import ConfirmPopup from 'primevue/confirmpopup'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Popover from 'primevue/popover'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import MarketplaceSkillCard from '../components/MarketplaceSkillCard.vue'
import BlueprintDetailsDrawer from '../components/BlueprintDetailsDrawer.vue'
import CalibrationKnowledgePacksPanel from '../components/CalibrationKnowledgePacksPanel.vue'
import CalibrationPersonaUpdatesPanel from '../components/CalibrationPersonaUpdatesPanel.vue'
import { CALIBRATION_STUDIO_BASE_URL } from '../config/calibrationStudio.js'
import { JPILOT_ROLES } from '../config/jpilotRoles.js'
import { getLicense } from '../services/system.js'
import {
  blueprintFilterOptions,
  blueprintHasDownloadableUpdate,
  blueprintTierLabel,
  buildBlueprintLibraryRows,
  collectBlueprintUpdates,
  fetchCalibrationCatalog,
  fetchKnowledgePackStatus,
  filterBlueprintRows,
  formatBlueprintUpdateSummary,
  installCalibrationItem,
  licenseTypeLabel,
  licenseTierRank,
  normalizeArtifactType,
  syncCalibrationsFromStudio,
  uninstallCalibrationItem,
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
const syncError = ref('')
const licenseType = ref('')
const localLicenseType = ref('')
const knowledgePackCount = ref(0)

const activeView = ref('skills')
const typeFilter = ref('all')
const quickFilter = ref('all')
const searchQuery = ref('')
const vendorFilter = ref('')
const productFilter = ref('')
const domainFilter = ref('')

const drawerVisible = ref(false)
const selectedRow = ref(null)
const licensePopover = ref(null)

const viewOptions = [
  { label: 'Skills', value: 'skills', icon: 'pi pi-bolt' },
  { label: 'Personas', value: 'personas', icon: 'pi pi-users' },
  { label: 'Knowledge Packs', value: 'packs', icon: 'pi pi-box' },
]

const quickFilterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Installed', value: 'installed' },
  { label: 'Updates', value: 'updates' },
  { label: 'Free', value: 'free' },
  { label: 'Premium', value: 'premium' },
]

// Track narrow viewports to shorten labels.
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

const effectiveLicenseType = computed(() => {
  const studio = licenseType.value
  const local = localLicenseType.value
  if (!local) return studio
  return licenseTierRank(local) > licenseTierRank(studio) ? local : studio
})

const headlineLicenseType = computed(() => localLicenseType.value || licenseType.value)
const headlineLicenseLabel = computed(() => licenseTypeLabel(headlineLicenseType.value))
const headlineLicenseSeverity = computed(() => {
  const rank = licenseTierRank(headlineLicenseType.value)
  if (rank >= 3) return 'success'
  if (rank === 2) return 'info'
  return 'secondary'
})

const installableCount = computed(() => blueprints.value.filter((row) => row.installable).length)
const installedBlueprints = computed(() =>
  blueprints.value
    .filter((row) => row.installed && normalizeArtifactType(row.type) === 'skill')
    .sort((a, b) => a.label.localeCompare(b.label))
)
const personaRows = computed(() =>
  blueprints.value.filter((row) => normalizeArtifactType(row.type) === 'persona')
)
const catalogPersonaCount = computed(() => personaRows.value.length)
const installedPersonaCount = computed(() => catalogPersonaCount.value || JPILOT_ROLES.length)
const updatesAvailable = computed(() => collectBlueprintUpdates(blueprints.value).updateCount)

function rowsOfType(rows, type) {
  if (!type || type === 'all') return rows
  return rows.filter((row) => normalizeArtifactType(row.type) === type)
}

const typeCounts = computed(() => {
  const counts = { all: blueprints.value.length, skill: 0, persona: 0, knowledge_pack: 0 }
  for (const row of blueprints.value) {
    const t = normalizeArtifactType(row.type)
    if (counts[t] !== undefined) counts[t] += 1
  }
  return counts
})

const typeFilterOptions = computed(() => [
  { label: `All (${typeCounts.value.all})`, value: 'all' },
  { label: `Skills (${typeCounts.value.skill})`, value: 'skill' },
  { label: `Personas (${typeCounts.value.persona})`, value: 'persona' },
  { label: `Packs (${typeCounts.value.knowledge_pack})`, value: 'knowledge_pack' },
])

const filteredRows = computed(() => {
  let rows = filterBlueprintRows(blueprints.value, {
    search: searchQuery.value,
    vendor: vendorFilter.value,
    product: productFilter.value,
    domain: domainFilter.value,
  })
  rows = rowsOfType(rows, typeFilter.value)
  switch (quickFilter.value) {
    case 'installed':
      rows = rows.filter((row) => row.installed)
      break
    case 'updates':
      rows = rows.filter((row) => row.installed && blueprintHasDownloadableUpdate(row))
      break
    case 'free':
      rows = rows.filter((row) => blueprintTierLabel(row) === 'Free')
      break
    case 'premium':
      rows = rows.filter((row) => blueprintTierLabel(row) !== 'Free')
      break
  }
  return rows
})

const filteredCount = computed(() => filteredRows.value.length)

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
  if (vendorFilter.value) scope = scope.filter((row) => row.vendorKey === vendorFilter.value)
  if (productFilter.value) scope = scope.filter((row) => row.product === productFilter.value)
  return blueprintFilterOptions(scope).domains
})

const hasActiveFilters = computed(
  () =>
    Boolean(searchQuery.value.trim() || vendorFilter.value || productFilter.value || domainFilter.value) ||
    quickFilter.value !== 'all' ||
    typeFilter.value !== 'all'
)

const syncAllTooltip = computed(() => {
  if (!installableCount.value) return 'No entitled blueprints to sync'
  return `Download all ${installableCount.value} entitled blueprint(s) from the official catalog`
})

function toggleLicense(event) {
  licensePopover.value?.toggle(event)
}

function goTo(view, filter) {
  activeView.value = view
  if (view === 'skills') {
    quickFilter.value = filter || 'all'
  }
}

// Browse a single artifact type in the unified library grid.
function browseType(type, filter) {
  activeView.value = 'skills'
  typeFilter.value = type || 'all'
  quickFilter.value = filter || 'all'
}

function openDetails(row) {
  selectedRow.value = row
  drawerVisible.value = true
}

function clearFilters() {
  searchQuery.value = ''
  vendorFilter.value = ''
  productFilter.value = ''
  domainFilter.value = ''
  quickFilter.value = 'all'
  typeFilter.value = 'all'
}

watch(vendorFilter, () => {
  if (productFilter.value && !productOptions.value.some((o) => o.value === productFilter.value)) {
    productFilter.value = ''
  }
  if (domainFilter.value && !domainOptions.value.some((o) => o.value === domainFilter.value)) {
    domainFilter.value = ''
  }
})
watch(productFilter, () => {
  if (domainFilter.value && !domainOptions.value.some((o) => o.value === domainFilter.value)) {
    domainFilter.value = ''
  }
})

// Keep the open drawer in sync with refreshed catalog data after install/uninstall.
function refreshSelectedRow() {
  if (!selectedRow.value) return
  const next = blueprints.value.find((row) => row.skillId === selectedRow.value.skillId)
  if (next) selectedRow.value = next
}

function applyCatalog(catalog) {
  licenseType.value = catalog.licenseType || 'free'
  localLicenseType.value = catalog.localLicenseType || ''
  blueprints.value = buildBlueprintLibraryRows(catalog)
  refreshSelectedRow()
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

async function loadKnowledgePackCount() {
  try {
    const status = await fetchKnowledgePackStatus()
    knowledgePackCount.value = status?.packId ? 1 : 0
  } catch {
    knowledgePackCount.value = 0
  }
}

async function refreshEntitlements() {
  refreshingEntitlements.value = true
  syncError.value = ''
  licensePopover.value?.hide()
  try {
    const license = await getLicense()
    if (license.syncError) syncError.value = `License sync: ${license.syncError}`
    await loadCatalog()
    if (!syncError.value && license.licenseType && license.licenseType !== 'free') {
      toast.add({
        severity: 'success',
        summary: 'License refreshed',
        detail: `(${licenseTypeLabel(license.licenseType)}). Catalog updated.`,
        life: 4000,
      })
    }
  } catch (error) {
    syncError.value =
      error.response?.data?.detail || error.message || 'Could not refresh entitlements from Nexxus.'
  } finally {
    refreshingEntitlements.value = false
  }
}

async function checkForUpdates() {
  checking.value = true
  syncError.value = ''
  try {
    applyCatalog(await fetchCalibrationCatalog())
    const summary = collectBlueprintUpdates(blueprints.value)
    const result = formatBlueprintUpdateSummary(summary)
    // Discreet, transient feedback — the persistent indicator is the "Updates
    // Available" tile, and switching to the Updates filter shows the affected cards.
    toast.add({
      severity: result.severity || 'info',
      summary: summary.updateCount ? 'Updates available' : 'Up to date',
      detail: result.message,
      life: 6000,
    })
    if (summary.updateCount) {
      activeView.value = 'skills'
      quickFilter.value = 'updates'
    }
  } catch (error) {
    syncError.value = error.response?.data?.detail || error.message || 'Could not check for blueprint updates.'
  } finally {
    checking.value = false
  }
}

async function downloadSkill(row) {
  installingSkillId.value = row.skillId
  syncError.value = ''
  try {
    const result = await installCalibrationItem(row)
    toast.add({
      severity: 'success',
      summary: row.installed && row.updateAvailable ? 'Update complete' : 'Install complete',
      detail: result.message || `Installed ${row.label}.`,
      life: 4000,
    })
    applyCatalog(await fetchCalibrationCatalog())
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Install failed',
      detail: error.response?.data?.detail || error.message || 'Install failed.',
      life: 5000,
    })
  } finally {
    installingSkillId.value = ''
  }
}

function confirmUninstall(event, row) {
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
  try {
    const result = await uninstallCalibrationItem(row)
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
  syncError.value = ''
  try {
    try {
      applyCatalog(await fetchCalibrationCatalog())
    } catch (error) {
      syncError.value = error.response?.data?.detail || error.message || 'Could not refresh blueprint library.'
    }
    const result = await syncCalibrationsFromStudio()
    toast.add({
      severity: 'success',
      summary: 'Sync complete',
      detail: result.message || 'Entitled blueprints synced.',
      life: 4000,
    })
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

onMounted(() => {
  refreshEntitlements()
  loadKnowledgePackCount()
})
</script>

<style scoped>
.studio {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.5rem 0.5rem 1.5rem;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 0;
}

/* Header */
.studio-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.studio-heading {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.studio-title {
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--p-text-color);
}

.studio-subtitle {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  max-width: 42rem;
}

.studio-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.license-chip {
  font-weight: 600;
}

.license-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 17rem;
}

.license-panel-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.license-panel-row strong {
  color: var(--p-text-color);
}

.license-panel-note {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}

/* Dashboard tiles */
.studio-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.stat-tile {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 1rem 1.15rem;
  text-align: left;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.stat-tile:hover {
  border-color: var(--p-primary-300);
  box-shadow: 0 4px 22px rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

.stat-tile-alert {
  border-color: color-mix(in srgb, var(--p-orange-400) 55%, var(--p-content-border-color));
}

.stat-tile-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  border-radius: 0.7rem;
  font-size: 1.1rem;
}

.stat-skill {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 13%, transparent);
}
.stat-persona {
  color: var(--p-purple-500, #8b5cf6);
  background: color-mix(in srgb, var(--p-purple-500, #8b5cf6) 13%, transparent);
}
.stat-pack {
  color: var(--p-teal-500, #14b8a6);
  background: color-mix(in srgb, var(--p-teal-500, #14b8a6) 13%, transparent);
}
.stat-update {
  color: var(--p-orange-500, #f97316);
  background: color-mix(in srgb, var(--p-orange-500, #f97316) 13%, transparent);
}

.stat-tile-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-tile-value {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--p-text-color);
}

.stat-tile-label {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

/* Notifications */
.studio-messages {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.studio-messages:empty {
  display: none;
}

.check-details {
  font-size: 0.8125rem;
}
.check-details li + li {
  margin-top: 0.25rem;
}

/* View switch */
.view-switch :deep(.p-togglebutton) {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

/* Catalog toolbar */
.catalog-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.catalog-search {
  flex: 1 1 18rem;
  min-width: 14rem;
}
.catalog-search :deep(.p-inputtext) {
  width: 100%;
}

.quick-filter :deep(.p-togglebutton) {
  font-size: 0.8125rem;
}

.type-filter {
  align-self: flex-start;
}

.type-filter :deep(.p-togglebutton) {
  font-size: 0.8125rem;
}

.catalog-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.filter-select {
  min-width: 9.5rem;
}

.catalog-count {
  margin-left: auto;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

/* Card grid */
.catalog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));
  gap: 0.85rem;
}

/* Skeletons */
.skeleton-card {
  display: flex;
  flex-direction: column;
  padding: 1.1rem 1.15rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
}

.skeleton-card-head {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.skeleton-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 1.1rem;
}

/* Empty state */
.catalog-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  text-align: center;
  padding: 3rem 1.5rem;
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--content-radius);
}

.catalog-empty-icon {
  font-size: 2.25rem;
  color: var(--p-text-muted-color);
  margin-bottom: 0.25rem;
}

.catalog-empty-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--p-text-color);
}

.catalog-empty-copy {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  max-width: 28rem;
}

/* ---------- Mobile ---------- */
@media (max-width: 900px) {
  .studio-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .studio {
    padding: 0.25rem 0.25rem 1rem;
    gap: 1rem;
  }

  .studio-header-actions {
    width: 100%;
  }

  .stat-tile {
    padding: 0.8rem 0.9rem;
    gap: 0.6rem;
  }

  .stat-tile-icon {
    width: 2.1rem;
    height: 2.1rem;
    font-size: 0.95rem;
  }

  .stat-tile-value {
    font-size: 1.25rem;
  }

  .view-switch {
    width: 100%;
    overflow-x: auto;
  }

  .catalog-search {
    flex-basis: 100%;
  }

  .quick-filter {
    width: 100%;
    overflow-x: auto;
  }

  .catalog-count {
    width: 100%;
    margin-left: 0;
  }

  .catalog-grid {
    grid-template-columns: 1fr;
  }
}
</style>
