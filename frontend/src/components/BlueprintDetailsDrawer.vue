<template>
  <Drawer
    :visible="visible"
    position="right"
    class="bp-drawer"
    :style="{ width: '32rem', maxWidth: '100vw' }"
    :pt="{ header: { class: 'bp-drawer-header' } }"
    @update:visible="$emit('update:visible', $event)"
  >
    <template #header>
      <div v-if="row" class="bp-head">
        <span class="bp-vendor-mark" aria-hidden="true">{{ vendorInitials }}</span>
        <div class="bp-head-id">
          <h2 class="bp-name m-0">{{ row.label }}</h2>
          <code class="bp-skill-id">{{ row.skillId }}</code>
        </div>
      </div>
    </template>

    <div v-if="row" class="bp-body">
      <!-- Badges -->
      <div class="bp-badges">
        <Tag :value="tierLabel" :severity="tierSeverity" rounded />
        <Tag
          v-tooltip.bottom="row.ineligibleReason || undefined"
          :value="statusLabel"
          :severity="statusSeverity"
        />
        <Tag v-if="row.globalFreeSkill" value="Free for all" severity="success" />
      </div>

      <p class="bp-desc">{{ row.description || 'No description provided for this blueprint.' }}</p>

      <!-- Primary actions -->
      <div class="bp-actions">
        <Button
          v-if="canDownload"
          :label="row.installed && row.updateAvailable ? 'Update now' : 'Install blueprint'"
          :icon="row.installed && row.updateAvailable ? 'pi pi-arrow-up' : 'pi pi-download'"
          :loading="installing"
          @click="$emit('install', row)"
        />
        <Button
          v-else-if="upToDate"
          label="Installed — up to date"
          icon="pi pi-check"
          severity="success"
          outlined
          disabled
        />
        <Button
          v-else
          :label="blockedLabel"
          icon="pi pi-lock"
          severity="secondary"
          outlined
          disabled
          v-tooltip.bottom="blockedTooltip"
        />
        <Button
          v-if="row.installed"
          label="Uninstall"
          icon="pi pi-trash"
          severity="danger"
          text
          :loading="uninstalling"
          @click="$emit('uninstall', $event, row)"
        />
      </div>

      <!-- Meta grid -->
      <section class="bp-section">
        <h3 class="bp-section-title">Overview</h3>
        <dl class="bp-meta-grid">
          <div class="bp-meta">
            <dt>Vendor</dt>
            <dd>{{ row.vendorLabel || '—' }}</dd>
          </div>
          <div class="bp-meta">
            <dt>Product</dt>
            <dd>{{ row.product || '—' }}</dd>
          </div>
          <div class="bp-meta">
            <dt>Domains</dt>
            <dd>
              <div v-if="row.domainLabels?.length" class="bp-domain-tags">
                <Tag v-for="t in row.domainLabels" :key="t" :value="t" severity="secondary" />
              </div>
              <span v-else>—</span>
            </dd>
          </div>
          <div class="bp-meta">
            <dt>Minimum tier</dt>
            <dd>{{ tierLabel }}</dd>
          </div>
        </dl>
      </section>

      <!-- Versions -->
      <section class="bp-section">
        <h3 class="bp-section-title">Versions</h3>
        <ul class="bp-version-list">
          <li>
            <span class="bp-version-label">Catalog</span>
            <span class="bp-version-value">{{ row.catalogVersion ? `v${row.catalogVersion}` : '—' }}</span>
          </li>
          <li v-if="row.entitledVersion && row.entitledVersion !== row.catalogVersion">
            <span class="bp-version-label">Entitled (sync)</span>
            <span class="bp-version-value">v{{ row.entitledVersion }}</span>
          </li>
          <li>
            <span class="bp-version-label">Installed</span>
            <span class="bp-version-value">
              {{ row.installedVersion ? `v${row.installedVersion}` : 'Not installed' }}
            </span>
          </li>
        </ul>
      </section>

      <!-- Release notes / dependencies / permissions: honest empty states until the
           catalog API exposes this metadata. -->
      <section class="bp-section">
        <h3 class="bp-section-title">Release notes</h3>
        <p class="bp-muted">Release notes are not published in the catalog feed yet.</p>
      </section>

      <section class="bp-section">
        <h3 class="bp-section-title">Dependencies</h3>
        <p class="bp-muted">This blueprint declares no dependencies in the current catalog.</p>
      </section>

      <section class="bp-section">
        <h3 class="bp-section-title">Permissions</h3>
        <p class="bp-muted">
          Blueprints run inside JPilot's sandbox and request no extra permissions.
        </p>
      </section>
    </div>
  </Drawer>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import {
  blueprintTierLabel,
  blueprintTierSeverity,
  blueprintCanDownload,
  blueprintIsLatestEntitled,
  blueprintStatusLabel,
  blueprintDownloadBlockedButtonLabel,
  blueprintDownloadBlockedLabel,
} from '../services/calibrationSync.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  row: { type: Object, default: null },
  licenseType: { type: String, default: '' },
  installing: { type: Boolean, default: false },
  uninstalling: { type: Boolean, default: false },
})

defineEmits(['update:visible', 'install', 'uninstall'])

const vendorInitials = computed(() => {
  const label = props.row?.vendorLabel || props.row?.vendor || '?'
  return label
    .split(/[\s-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
})

const tierLabel = computed(() => (props.row ? blueprintTierLabel(props.row) : ''))
const tierSeverity = computed(() => (props.row ? blueprintTierSeverity(props.row) : 'secondary'))
const canDownload = computed(() => (props.row ? blueprintCanDownload(props.row) : false))
const upToDate = computed(
  () => props.row && (blueprintIsLatestEntitled(props.row) || (props.row.installed && !props.row.updateAvailable))
)
const statusLabel = computed(() => (props.row ? blueprintStatusLabel(props.row, props.licenseType) : ''))
const statusSeverity = computed(() => {
  if (!props.row) return 'secondary'
  if (blueprintIsLatestEntitled(props.row)) return 'success'
  if (props.row.installed && props.row.updateAvailable) return 'warn'
  if (props.row.installed) return 'success'
  if (props.row.installable) return 'info'
  return 'secondary'
})
const blockedLabel = computed(() =>
  props.row ? blueprintDownloadBlockedButtonLabel(props.row, props.licenseType) : ''
)
const blockedTooltip = computed(() =>
  props.row ? blueprintDownloadBlockedLabel(props.row, props.licenseType) : ''
)
</script>

<style scoped>
.bp-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.bp-vendor-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  border-radius: 0.65rem;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}

.bp-head-id {
  min-width: 0;
}

.bp-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--p-text-color);
  line-height: 1.25;
}

.bp-skill-id {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}

.bp-body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.bp-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.bp-desc {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--p-text-color);
}

.bp-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.bp-section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color);
}

.bp-section-title {
  margin: 0;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.bp-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.9rem 1.25rem;
  margin: 0;
}

.bp-meta {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.bp-meta dt {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.bp-meta dd {
  margin: 0;
  font-size: 0.875rem;
  color: var(--p-text-color);
}

.bp-domain-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.bp-version-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.bp-version-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8125rem;
}

.bp-version-label {
  color: var(--p-text-muted-color);
}

.bp-version-value {
  font-weight: 600;
  color: var(--p-text-color);
}

.bp-muted {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}
</style>
