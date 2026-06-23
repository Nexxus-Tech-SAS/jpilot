<template>
  <article
    class="mk-card"
    :class="{ 'mk-card-installed': row.installed, 'mk-card-update': showUpdateBadge }"
    role="button"
    tabindex="0"
    @click="$emit('open', row)"
    @keydown.enter.prevent="$emit('open', row)"
    @keydown.space.prevent="$emit('open', row)"
  >
    <!-- Top row: vendor mark + identity, tier badge -->
    <header class="mk-card-head">
      <span class="mk-vendor-mark" aria-hidden="true">{{ vendorInitials }}</span>
      <div class="mk-identity">
        <h3 class="mk-name" :title="row.label">{{ row.label }}</h3>
        <span class="mk-scope">{{ row.vendorLabel }}<template v-if="row.product"> · {{ row.product }}</template></span>
      </div>
      <div class="mk-badges">
        <Tag
          :value="typeLabel"
          :icon="typeIcon"
          :severity="typeSeverity"
          class="mk-type"
          rounded
        />
        <Tag :value="tierLabel" :severity="tierSeverity" class="mk-tier" rounded />
      </div>
    </header>

    <p class="mk-desc" :title="row.description || ''">
      {{ row.description || 'No description provided for this blueprint.' }}
    </p>

    <!-- Domain tags -->
    <div v-if="row.domainLabels?.length" class="mk-tags">
      <Tag
        v-for="tag in row.domainLabels.slice(0, 3)"
        :key="tag"
        :value="tag"
        severity="secondary"
        class="mk-domain-tag"
      />
      <span v-if="row.domainLabels.length > 3" class="mk-more-tags">+{{ row.domainLabels.length - 3 }}</span>
    </div>

    <!-- Footer: status + version on the left, primary action on the right -->
    <footer class="mk-card-foot" @click.stop>
      <div class="mk-status-col">
        <Tag
          v-tooltip.top="row.ineligibleReason || undefined"
          :value="statusLabel"
          :severity="statusSeverity"
          class="mk-status"
        />
        <span class="mk-version">{{ versionLine }}</span>
      </div>

      <div class="mk-actions">
        <Button
          v-if="canDownload"
          :label="primaryLabel"
          :icon="row.installed && row.updateAvailable ? 'pi pi-arrow-up' : 'pi pi-download'"
          size="small"
          :loading="installing"
          @click="$emit('install', row)"
        />
        <Tag
          v-else-if="upToDate"
          value="Up to date"
          icon="pi pi-check"
          severity="success"
          class="mk-uptodate"
        />
        <Button
          v-else
          :label="blockedLabel"
          icon="pi pi-lock"
          size="small"
          severity="secondary"
          outlined
          disabled
          v-tooltip.top="blockedTooltip"
        />
        <Button
          v-if="row.installed"
          icon="pi pi-trash"
          size="small"
          severity="danger"
          text
          rounded
          :loading="uninstalling"
          aria-label="Uninstall"
          v-tooltip.top="'Uninstall'"
          @click="$emit('uninstall', $event, row)"
        />
      </div>
    </footer>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import {
  artifactTypeLabel,
  blueprintTierLabel,
  blueprintTierSeverity,
  blueprintCanDownload,
  blueprintHasDownloadableUpdate,
  blueprintIsLatestEntitled,
  blueprintStatusLabel,
  blueprintDownloadBlockedButtonLabel,
  blueprintDownloadBlockedLabel,
  normalizeArtifactType,
} from '../services/calibrationSync.js'

const props = defineProps({
  row: { type: Object, required: true },
  licenseType: { type: String, default: '' },
  installing: { type: Boolean, default: false },
  uninstalling: { type: Boolean, default: false },
})

defineEmits(['open', 'install', 'uninstall'])

const vendorInitials = computed(() => {
  const label = props.row.vendorLabel || props.row.vendor || '?'
  return label
    .split(/[\s-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
})

const artifactType = computed(() => normalizeArtifactType(props.row.type))
const typeLabel = computed(() => artifactTypeLabel(props.row.type))
const typeIcon = computed(() => {
  if (artifactType.value === 'persona') return 'pi pi-users'
  if (artifactType.value === 'knowledge_pack') return 'pi pi-box'
  return 'pi pi-bolt'
})
const typeSeverity = computed(() => {
  if (artifactType.value === 'persona') return 'contrast'
  if (artifactType.value === 'knowledge_pack') return 'info'
  return 'secondary'
})

const tierLabel = computed(() => blueprintTierLabel(props.row))
const tierSeverity = computed(() => blueprintTierSeverity(props.row))

const canDownload = computed(() => blueprintCanDownload(props.row))
const upToDate = computed(
  () => blueprintIsLatestEntitled(props.row) || (props.row.installed && !props.row.updateAvailable)
)
const showUpdateBadge = computed(() => props.row.installed && blueprintHasDownloadableUpdate(props.row))

const statusLabel = computed(() => blueprintStatusLabel(props.row, props.licenseType))
const statusSeverity = computed(() => {
  if (blueprintIsLatestEntitled(props.row)) return 'success'
  if (props.row.installed && blueprintHasDownloadableUpdate(props.row)) return 'warn'
  if (props.row.installed) return 'success'
  if (props.row.installable) return 'info'
  if (props.row.inCatalog && !props.row.installable) return 'secondary'
  return 'secondary'
})

const primaryLabel = computed(() => (props.row.installed && props.row.updateAvailable ? 'Update' : 'Install'))
const blockedLabel = computed(() => blueprintDownloadBlockedButtonLabel(props.row, props.licenseType))
const blockedTooltip = computed(() => blueprintDownloadBlockedLabel(props.row, props.licenseType))

const versionLine = computed(() => {
  if (props.row.installed) {
    return `v${props.row.installedVersion || '—'}${
      showUpdateBadge.value && props.row.catalogVersion ? ` → v${props.row.catalogVersion}` : ''
    }`
  }
  return props.row.catalogVersion ? `v${props.row.catalogVersion}` : 'Catalog'
})
</script>

<style scoped>
.mk-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.1rem 1.15rem;
  text-align: left;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.mk-card:hover {
  border-color: var(--p-primary-300);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.mk-card:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}

html.app-dark .mk-card:hover {
  border-color: var(--p-primary-600);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.32);
}

.mk-card-update {
  border-color: color-mix(in srgb, var(--p-orange-400) 50%, var(--p-content-border-color));
}

.mk-card-head {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
}

.mk-vendor-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  border-radius: 0.6rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}

.mk-identity {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.mk-name {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 650;
  line-height: 1.25;
  color: var(--p-text-color);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mk-scope {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mk-badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.3rem;
  flex-shrink: 0;
}

.mk-type {
  font-size: 0.625rem;
}

.mk-tier {
  flex-shrink: 0;
  font-size: 0.6875rem;
}

.mk-desc {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.35rem;
}

.mk-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem;
}

.mk-domain-tag {
  font-size: 0.625rem;
}

.mk-more-tags {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.mk-card-foot {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: auto;
  padding-top: 0.65rem;
  border-top: 1px solid var(--p-content-border-color);
}

.mk-status-col {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
  min-width: 0;
}

.mk-status {
  font-size: 0.6875rem;
}

.mk-version {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.mk-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.mk-uptodate {
  font-size: 0.6875rem;
}
</style>
