<template>
  <div class="content-panel content-panel-padded web-search-usage-panel">
    <div class="usage-header">
      <div>
        <h3 class="info-title m-0">JPilot usage</h3>
        <p class="usage-period">{{ usage?.periodLabel || 'This month' }}</p>
        <p class="usage-lead">
          Search queries initiated during JPilot chats. This is local JPilot tracking — not your search provider billing.
        </p>
      </div>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        aria-label="Refresh web search usage"
        @click="load"
      />
    </div>

    <div v-if="loading && !usage" class="usage-loading">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
    </div>

    <template v-else-if="usage">
      <div class="usage-stats">
        <div class="usage-stat">
          <span class="usage-stat-value">{{ formatCount(usage.queriesUsed) }}</span>
          <span class="usage-stat-label">Search queries</span>
        </div>
        <div v-if="usage.enabled" class="usage-stat usage-stat-muted">
          <span class="usage-stat-value"><i class="pi pi-check-circle" /></span>
          <span class="usage-stat-label">Enabled in chat</span>
        </div>
      </div>

      <UsageMeter
        v-if="usage.configured && usage.limitConfigured"
        class="usage-budget-meter"
        label="Budget cap"
        :used="usage.queriesUsed"
        :limit="usage.monthlyQueryLimit"
        :percent="usage.percent"
        :remaining="usage.remainingQueries"
        :unlimited="usage.unlimited"
        unit="queries"
      />

      <p v-if="!usage.configured" class="usage-empty">
        Save a search provider API key above to start tracking query usage.
      </p>
    </template>

    <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import UsageMeter from './UsageMeter.vue'
import { formatCount, getModelUsageDashboard } from '../services/modelUsage'

const loading = ref(false)
const error = ref('')
const usage = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const dashboard = await getModelUsageDashboard()
    usage.value = {
      periodLabel: dashboard.periodLabel,
      ...dashboard.braveSearch
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load web search usage'
    usage.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>

<style scoped>
.web-search-usage-panel {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  height: 100%;
  background: var(--app-nested-surface);
}

.usage-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.usage-period {
  margin: 0.2rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.usage-lead {
  margin: 0.35rem 0 0;
  max-width: 36rem;
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}

.usage-loading {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
}

.usage-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(6.5rem, 1fr));
  gap: 0.55rem;
}

.usage-stat {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding: 0.55rem 0.65rem;
  border-radius: 10px;
  background: var(--app-nested-surface-strong);
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 70%, transparent);
}

.usage-stat-muted .usage-stat-value {
  color: var(--p-primary-color);
  font-size: 1rem;
}

.usage-stat-value {
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.usage-stat-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.usage-budget-meter {
  margin-top: 0.25rem;
}

.usage-empty {
  margin: 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  line-height: 1.45;
}
</style>
