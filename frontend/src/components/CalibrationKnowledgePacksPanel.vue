<template>
  <div class="kp-panel">
    <div class="kp-header">
      <div class="kp-heading">
        <h2 class="kp-title m-0">Knowledge Packs</h2>
        <p class="kp-subtitle m-0">
          Reusable reference and knowledge assets assigned to personas, vendors, products, and domains.
          A Knowledge Pack bundles the blueprint index and persona behaviour used by JPilot at runtime.
        </p>
      </div>
      <div class="kp-header-actions">
        <Button
          label="Refresh"
          icon="pi pi-refresh"
          severity="secondary"
          outlined
          size="small"
          :loading="loading"
          @click="loadStatus"
        />
        <Button
          label="Import / Update"
          icon="pi pi-upload"
          size="small"
          :loading="importing"
          v-tooltip="'Install or update the knowledge pack from a downloaded bundle'"
          @click="openImportPicker"
        />
        <input
          ref="importInputRef"
          type="file"
          accept=".zip,.tar,.tgz,.gz,application/zip,application/gzip,application/x-tar"
          class="kp-file-input"
          @change="onImport"
        />
      </div>
    </div>

    <Message v-if="errorMessage" severity="warn" :closable="true" @close="errorMessage = ''">
      {{ errorMessage }}
    </Message>

    <div v-if="loading" class="kp-empty text-color-secondary">Loading knowledge pack status…</div>

    <!-- Empty state: no pack installed yet -->
    <div v-else-if="!status.packId" class="kp-empty-card">
      <i class="pi pi-box kp-empty-icon" />
      <div>
        <p class="kp-empty-title m-0">No knowledge pack installed</p>
        <p class="kp-empty-copy m-0 mt-1">
          Knowledge packs are delivered automatically on the next sync, or import one manually with
          <strong>Import / Update</strong> above.
        </p>
      </div>
    </div>

    <!-- Installed knowledge pack(s).
         TODO(backend): /copilot/knowledge-pack exposes only the single active pack plus its
         previousVersion (rollback target). When the API can list multiple installed packs
         (per vendor/product/domain scope), map them here instead of the single-pack card. -->
    <template v-else>
      <div class="content-panel content-panel-padded kp-card">
        <div class="kp-card-head">
          <div class="kp-card-id">
            <i class="pi pi-box kp-card-icon" />
            <div>
              <div class="kp-card-name">{{ status.packId }}</div>
              <code class="kp-card-version">v{{ status.version || '—' }}</code>
            </div>
          </div>
          <Tag :value="statusLabel" :severity="statusSeverity" />
        </div>

        <div class="kp-meta-grid">
          <div class="kp-meta">
            <span class="kp-meta-label">Scope</span>
            <span class="kp-meta-value">{{ status.blueprintCount }} blueprint{{ status.blueprintCount === 1 ? '' : 's' }}</span>
          </div>
          <div class="kp-meta">
            <span class="kp-meta-label">Source</span>
            <span class="kp-meta-value" :title="status.path">{{ sourceLabel }}</span>
          </div>
          <div class="kp-meta">
            <span class="kp-meta-label">Published</span>
            <span class="kp-meta-value">{{ formatDate(status.publishedAt) }}</span>
          </div>
          <div class="kp-meta">
            <span class="kp-meta-label">Last sync</span>
            <span class="kp-meta-value">{{ formatDate(status.lastSyncAt) }}</span>
          </div>
          <div v-if="status.pinnedVersion" class="kp-meta">
            <span class="kp-meta-label">Pinned</span>
            <span class="kp-meta-value">v{{ status.pinnedVersion }}</span>
          </div>
          <div v-if="status.legacySkillCount" class="kp-meta">
            <span class="kp-meta-label">Legacy skills</span>
            <span class="kp-meta-value">{{ status.legacySkillCount }}</span>
          </div>
        </div>

        <div class="kp-actions">
          <Button
            :label="status.pinnedVersion ? 'Unpin version' : 'Pin version'"
            :icon="status.pinnedVersion ? 'pi pi-lock-open' : 'pi pi-lock'"
            severity="secondary"
            outlined
            size="small"
            :loading="pinning"
            v-tooltip="status.pinnedVersion
              ? 'Allow automatic updates to newer pack versions again'
              : 'Pin to the current version and block automatic updates'"
            @click="togglePin"
          />
          <Button
            :label="status.syncScheduleEnabled ? 'Disable auto-sync' : 'Enable auto-sync'"
            :icon="status.syncScheduleEnabled ? 'pi pi-pause' : 'pi pi-play'"
            severity="secondary"
            outlined
            size="small"
            :loading="scheduling"
            v-tooltip="`Scheduled sync every ${status.syncScheduleHours}h`"
            @click="toggleSchedule"
          />
          <Button
            v-if="status.previousVersion"
            label="Rollback / Remove"
            icon="pi pi-undo"
            severity="danger"
            text
            size="small"
            class="kp-action-danger"
            :loading="rollingBack"
            v-tooltip="`Roll back to the previously installed version (v${status.previousVersion})`"
            @click="confirmRollback($event)"
          />
        </div>
      </div>

      <!-- Previous version surfaced as the rollback target -->
      <div v-if="status.previousVersion" class="kp-previous text-color-secondary">
        <i class="pi pi-history" />
        Previous version <code>v{{ status.previousVersion }}</code> is retained as the rollback target.
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import {
  fetchKnowledgePackStatus,
  importKnowledgePack,
  rollbackKnowledgePack,
  pinKnowledgePackVersion,
  updateKnowledgePackSchedule,
} from '../services/calibrationSync.js'

const confirm = useConfirm()
const toast = useToast()

const status = ref({})
const importInputRef = ref(null)
const loading = ref(false)
const importing = ref(false)
const rollingBack = ref(false)
const pinning = ref(false)
const scheduling = ref(false)
const errorMessage = ref('')

const statusLabel = computed(() => {
  if (!status.value.active) return 'Disabled'
  if (status.value.pinnedVersion) return 'Installed · pinned'
  return 'Installed'
})

const statusSeverity = computed(() => {
  if (!status.value.active) return 'secondary'
  if (status.value.pinnedVersion) return 'info'
  return 'success'
})

const sourceLabel = computed(() => {
  const path = status.value.path || ''
  if (!path) return '—'
  const parts = path.split('/')
  return parts[parts.length - 1] || path
})

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

async function loadStatus() {
  loading.value = true
  errorMessage.value = ''
  try {
    status.value = await fetchKnowledgePackStatus()
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || error.message || 'Could not load knowledge pack status.'
    status.value = {}
  } finally {
    loading.value = false
  }
}

function openImportPicker() {
  importInputRef.value?.click()
}

async function onImport(event) {
  const file = event.target?.files?.[0]
  if (!file) return
  importing.value = true
  errorMessage.value = ''
  try {
    const result = await importKnowledgePack(file)
    toast.add({
      severity: 'success',
      summary: 'Knowledge pack imported',
      detail: result.message || `Installed ${result.packId} v${result.version}.`,
      life: 4000,
    })
    await loadStatus()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Import failed',
      detail: error.response?.data?.detail || error.message || 'Import failed.',
      life: 5000,
    })
  } finally {
    importing.value = false
    if (event.target) event.target.value = ''
  }
}

async function togglePin() {
  pinning.value = true
  try {
    const target = status.value.pinnedVersion ? null : status.value.version
    const result = await pinKnowledgePackVersion(target)
    toast.add({
      severity: 'success',
      summary: target ? 'Version pinned' : 'Version unpinned',
      detail: result.message || (target ? `Pinned to v${target}.` : 'Automatic updates re-enabled.'),
      life: 3500,
    })
    await loadStatus()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Could not update pin',
      detail: error.response?.data?.detail || error.message || 'Pin update failed.',
      life: 5000,
    })
  } finally {
    pinning.value = false
  }
}

async function toggleSchedule() {
  scheduling.value = true
  try {
    const enabled = !status.value.syncScheduleEnabled
    const result = await updateKnowledgePackSchedule({ enabled, hours: status.value.syncScheduleHours })
    toast.add({
      severity: 'success',
      summary: enabled ? 'Auto-sync enabled' : 'Auto-sync disabled',
      detail: result.message || `Scheduled sync ${enabled ? 'enabled' : 'disabled'}.`,
      life: 3500,
    })
    await loadStatus()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Could not update schedule',
      detail: error.response?.data?.detail || error.message || 'Schedule update failed.',
      life: 5000,
    })
  } finally {
    scheduling.value = false
  }
}

function confirmRollback(event) {
  confirm.require({
    target: event.currentTarget,
    message: `Roll back to v${status.value.previousVersion}? The current pack (v${status.value.version}) will be replaced.`,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Roll back',
    rejectLabel: 'Cancel',
    acceptClass: 'p-button-danger p-button-sm',
    rejectClass: 'p-button-secondary p-button-text p-button-sm',
    accept: rollback,
  })
}

async function rollback() {
  rollingBack.value = true
  try {
    const result = await rollbackKnowledgePack()
    toast.add({
      severity: 'success',
      summary: 'Rolled back',
      detail: result.message || `Restored ${result.packId} v${result.version}.`,
      life: 4000,
    })
    await loadStatus()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Rollback failed',
      detail: error.response?.data?.detail || error.message || 'Rollback failed.',
      life: 5000,
    })
  } finally {
    rollingBack.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.kp-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.kp-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.kp-heading {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.kp-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.kp-subtitle {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  max-width: 46rem;
}

.kp-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.kp-file-input {
  display: none;
}

.kp-empty {
  font-size: 0.875rem;
  padding: 1rem 0;
}

.kp-empty-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--content-radius);
}

.kp-empty-icon {
  font-size: 1.75rem;
  color: var(--p-text-muted-color);
}

.kp-empty-title {
  font-weight: 600;
  color: var(--p-text-color);
}

.kp-empty-copy {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.kp-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.kp-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.kp-card-id {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.kp-card-icon {
  font-size: 1.5rem;
  color: var(--p-primary-color);
}

.kp-card-name {
  font-weight: 600;
  font-size: 1rem;
  color: var(--p-text-color);
}

.kp-card-version {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.kp-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 0.75rem 1.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--p-content-border-color);
}

.kp-meta {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.kp-meta-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.kp-meta-value {
  font-size: 0.875rem;
  color: var(--p-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kp-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--p-content-border-color);
}

.kp-action-danger {
  margin-left: auto;
}

.kp-previous {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  padding-left: 0.25rem;
}
</style>
