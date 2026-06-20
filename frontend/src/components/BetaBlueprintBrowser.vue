<template>
  <div class="bp-browser" :style="{ '--persona-accent': accent }">
    <div class="bp-search-wrap">
      <IconField icon-position="left" class="bp-search-field">
        <InputIcon class="pi pi-search" />
        <InputText
          ref="searchInputRef"
          v-model="searchQuery"
          type="text"
          :placeholder="BETA_BLUEPRINTS_COPY.searchPlaceholder"
          class="bp-search-input"
          :disabled="disabled || loading"
          @keydown.enter.prevent="pickFirstResult"
        />
      </IconField>
    </div>

    <div v-if="domainTabs.length > 1" class="bp-domain-tabs" role="tablist" aria-label="Filter by domain">
      <button
        v-for="tab in domainTabs"
        :key="tab.id || 'all'"
        type="button"
        role="tab"
        class="bp-domain-tab"
        :class="{ 'bp-domain-tab-active': selectedDomain === tab.id }"
        :aria-selected="selectedDomain === tab.id"
        :disabled="disabled || loading"
        @click="selectedDomain = tab.id"
      >
        {{ tab.label }}
        <span class="bp-domain-tab-count">{{ tab.count }}</span>
      </button>
    </div>

    <div class="bp-results-meta">
      <span class="bp-results-label">Results by domain</span>
      <span class="bp-results-count">{{ filteredBlueprints.length }} blueprint{{ filteredBlueprints.length === 1 ? '' : 's' }}</span>
    </div>

    <div class="bp-scroll">
      <p v-if="loading" class="bp-empty">{{ BETA_BLUEPRINTS_COPY.loading }}</p>

      <div v-else-if="!blueprints.length" class="bp-empty-panel">
        <p class="bp-empty-title">{{ BETA_BLUEPRINTS_COPY.empty(roleLabel) }}</p>
        <p class="bp-empty-hint">{{ BETA_BLUEPRINTS_COPY.emptyHint }}</p>
        <RouterLink to="/calibration-studio" class="bp-empty-link">Open Calibration Studio</RouterLink>
      </div>

      <template v-else-if="groupedBlueprints.length">
        <template v-for="group in groupedBlueprints" :key="group.id">
          <div class="bp-section-head">
            {{ group.title }}
            <span class="bp-section-count">{{ group.items.length }}</span>
          </div>
          <button
            v-for="blueprint in group.items"
            :key="blueprint.skillId"
            type="button"
            class="bp-result"
            :disabled="disabled"
            @click="$emit('select', blueprint)"
          >
            <span class="bp-result-icon"><i class="pi pi-sliders-h" aria-hidden="true" /></span>
            <span class="bp-result-body">
              <span class="bp-result-title">{{ blueprint.label || blueprint.skillId }}</span>
              <span class="bp-result-sub">{{ resultSubtitle(blueprint) }}</span>
            </span>
            <span v-if="blueprint.version" class="bp-result-version">v{{ blueprint.version }}</span>
            <i class="pi pi-arrow-right bp-result-arrow" aria-hidden="true" />
          </button>
        </template>
      </template>

      <p v-else class="bp-empty">{{ BETA_BLUEPRINTS_COPY.emptySearch }}</p>
    </div>

    <button type="button" class="bp-back" :disabled="disabled" @click="$emit('back')">
      <i class="pi pi-arrow-left" aria-hidden="true" />
      Back to actions
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import {
  BETA_BLUEPRINTS_COPY,
  blueprintDisplayDescription,
  blueprintDomainTabs,
  filterBrowseBlueprints,
  groupBrowseBlueprintsByDomain
} from '../utils/betaInstalledBlueprints'

const props = defineProps({
  blueprints: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  accent: { type: String, default: '#6366f1' },
  roleLabel: { type: String, default: '' },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['select', 'back'])

const searchQuery = ref('')
const selectedDomain = ref('')
const searchInputRef = ref(null)

const domainTabs = computed(() => blueprintDomainTabs(props.blueprints))

const filteredBlueprints = computed(() =>
  filterBrowseBlueprints(props.blueprints, {
    search: searchQuery.value,
    domain: selectedDomain.value
  })
)

const groupedBlueprints = computed(() => groupBrowseBlueprintsByDomain(filteredBlueprints.value))

function resultSubtitle(blueprint) {
  const parts = [blueprintDisplayDescription(blueprint)]
  if (blueprint.vendorLabel && !String(blueprintDisplayDescription(blueprint)).includes(blueprint.vendorLabel)) {
    parts.push(blueprint.vendorLabel)
  }
  return parts.filter(Boolean).join(' · ')
}

function pickFirstResult() {
  const first = groupedBlueprints.value[0]?.items[0]
  if (first && !props.disabled) {
    emit('select', first)
  }
}

async function focusSearch() {
  await nextTick()
  const el = searchInputRef.value?.$el
  if (el?.focus) el.focus()
  else el?.querySelector?.('input')?.focus()
}

watch(
  () => props.loading,
  (loading) => {
    if (!loading) focusSearch()
  }
)

watch(
  () => props.blueprints,
  () => {
    selectedDomain.value = ''
  }
)

focusSearch()
</script>

<style scoped>
.bp-browser {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
  text-align: left;
  animation: bp-rise 320ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

.bp-search-wrap {
  width: 100%;
}

.bp-search-field {
  width: 100%;
}

.bp-search-input {
  width: 100%;
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--p-content-background) 62%, transparent);
  border-color: color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.bp-domain-tabs {
  display: flex;
  gap: 0;
  overflow-x: auto;
  scrollbar-width: none;
  border-bottom: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
}

.bp-domain-tabs::-webkit-scrollbar {
  display: none;
}

.bp-domain-tab {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.65rem 0.85rem;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.8125rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.bp-domain-tab:hover {
  color: var(--p-text-color);
}

.bp-domain-tab-active {
  color: var(--p-text-color);
  border-bottom-color: var(--persona-accent);
}

.bp-domain-tab-count {
  font-size: 0.6875rem;
  font-weight: 650;
  color: var(--p-text-muted-color);
}

.bp-results-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.15rem 0.35rem 0;
}

.bp-results-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.bp-results-count {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.bp-scroll {
  max-height: min(28rem, 52vh);
  overflow-y: auto;
  padding-right: 0.15rem;
}

.bp-section-head {
  padding: 0.75rem 0.35rem 0.3rem;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--persona-accent);
  letter-spacing: 0.02em;
}

.bp-section-count {
  margin-left: 0.35rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.bp-result {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.65rem 0.45rem;
  border: 0;
  border-radius: 0.65rem;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: inherit;
  font: inherit;
  transition: background 0.12s ease;
}

.bp-result:hover:not(:disabled),
.bp-result:focus-visible {
  background: color-mix(in srgb, var(--persona-accent) 10%, transparent);
  outline: none;
}

.bp-result:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.bp-result-icon {
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.55rem;
  border: 1px solid color-mix(in srgb, var(--persona-accent) 28%, transparent);
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 12%, transparent);
}

.bp-result-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.bp-result-title {
  font-size: 0.875rem;
  font-weight: 650;
  color: var(--p-text-color);
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.bp-result-sub {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.bp-result-version {
  flex-shrink: 0;
  font-size: 0.6875rem;
  font-weight: 650;
  color: var(--p-text-muted-color);
}

.bp-result-arrow {
  flex-shrink: 0;
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}

.bp-empty {
  margin: 0.75rem 0.35rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.bp-empty-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
  padding: 1.25rem 1rem;
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--p-content-background) 50%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 52%, transparent);
  text-align: center;
}

.bp-empty-title {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 650;
  color: var(--p-text-color);
}

.bp-empty-hint {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.bp-empty-link {
  margin-top: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 650;
  color: var(--p-primary-color);
  text-decoration: none;
}

.bp-empty-link:hover {
  text-decoration: underline;
}

.bp-back {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.15rem;
  padding: 0.35rem 0.65rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease;
}

.bp-back:hover,
.bp-back:focus-visible {
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-surface-100) 70%, transparent);
  outline: none;
}

:global(.app-dark) .bp-back:hover,
:global(.app-dark) .bp-back:focus-visible {
  background: color-mix(in srgb, var(--p-surface-800) 70%, transparent);
}

@keyframes bp-rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

@media (min-width: 992px) {
  .bp-scroll {
    max-height: min(34rem, 58vh);
  }

  .bp-result {
    padding: 0.7rem 0.55rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .bp-browser {
    animation: none;
  }
}
</style>
