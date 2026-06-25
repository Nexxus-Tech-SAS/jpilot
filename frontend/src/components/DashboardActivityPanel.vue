<template>
  <section class="activity-panel content-panel content-panel-padded">
    <div class="activity-header flex align-items-start justify-content-between gap-2 flex-wrap">
      <div>
        <h3 class="panel-heading m-0">Activity</h3>
        <p class="activity-sub m-0 mt-1">
          Last {{ activityDays }} days · tracked on this server
          <span v-if="dashboard?.periodLabel"> · {{ dashboard.periodLabel }} totals below</span>
        </p>
      </div>
      <RouterLink v-if="isAdmin" to="/settings?section=ai-models" class="activity-detail-link">
        Full usage →
      </RouterLink>
    </div>

    <div v-if="loading" class="activity-loading">
      <ProgressSpinner style="width: 1.75rem; height: 1.75rem" />
    </div>

    <template v-else>
      <UsageProvidersChart
        v-if="dashboard?.providers?.length"
        :providers="dashboard.providers"
      />

      <UsageActivityChart
        v-if="activitySeries.length"
        :series="activitySeries"
        :show-searches="braveConfigured"
        :monthly-requests="totals.requests"
      />

      <Message
        v-else-if="!error && hasMonthlyUsage"
        severity="info"
        :closable="false"
        class="mt-2"
      >
        Monthly usage is recorded (see totals below). Daily breakdown could not be loaded.
      </Message>

      <div class="activity-grid mt-3">
        <div class="stat-card activity-stat">
          <div class="stat-label">Chat rounds</div>
          <div class="stat-value">{{ formatCount(totals.requests) }}</div>
          <p class="stat-detail">This month</p>
        </div>
        <div class="stat-card activity-stat">
          <div class="stat-label">Tokens</div>
          <div class="stat-value">{{ formatCount(totals.tokens) }}</div>
          <p class="stat-detail">This month</p>
        </div>
        <div class="stat-card activity-stat">
          <div class="stat-label">Saved chats</div>
          <div class="stat-value">{{ formatCount(localChats.threads) }}</div>
          <p class="stat-detail">{{ formatCount(localChats.messages) }} messages on this device</p>
        </div>
        <div v-if="braveConfigured" class="stat-card activity-stat">
          <div class="stat-label">Web searches</div>
          <div class="stat-value">{{ formatCount(braveUsed) }}</div>
          <p class="stat-detail">This month</p>
        </div>
      </div>

      <p v-if="!hasMonthlyUsage && !hasDailyUsage" class="activity-empty m-0 mt-3">
        No AI usage recorded yet. Start a conversation in
        <RouterLink to="/jpilot">JPilot Chat</RouterLink>
        after configuring a provider.
      </p>

      <p class="activity-footnote m-0 mt-3">
        Monthly totals come from Settings → AI Models. Daily charts only include usage after per-day
        tracking was enabled on this server (not retroactive). Saved chat counts are local to this browser.
      </p>
    </template>

    <Message v-if="error" severity="warn" :closable="false" class="mt-3">{{ error }}</Message>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import UsageActivityChart from './UsageActivityChart.vue'
import UsageProvidersChart from './UsageProvidersChart.vue'
import { formatCount, getModelUsageDashboard, getUsageActivity } from '../services/modelUsage'
import { getLocalChatStats } from '../services/localChatStats'

defineProps({
  isAdmin: {
    type: Boolean,
    default: false
  }
})

const activityDays = 30
const loading = ref(true)
const error = ref('')
const dashboard = ref(null)
const activity = ref(null)
const localChats = ref({ threads: 0, messages: 0 })

const activitySeries = computed(() => activity.value?.series || [])

const totals = computed(() => {
  const providers = dashboard.value?.providers || []
  return providers.reduce(
    (acc, p) => ({
      requests: acc.requests + (p.requestsUsed || 0),
      tokens: acc.tokens + (p.tokensUsed || 0)
    }),
    { requests: 0, tokens: 0 }
  )
})

const braveConfigured = computed(() => Boolean(dashboard.value?.braveSearch?.configured))
const braveUsed = computed(() => dashboard.value?.braveSearch?.queriesUsed || 0)

const hasMonthlyUsage = computed(() => totals.value.requests > 0 || totals.value.tokens > 0)

const hasDailyUsage = computed(() =>
  activitySeries.value.some(
    (day) => (day.requests || 0) + (day.tokens || 0) + (day.queries || 0) > 0
  )
)

async function load() {
  loading.value = true
  error.value = ''
  localChats.value = getLocalChatStats()
  try {
    const [usageDashboard, usageActivity] = await Promise.allSettled([
      getModelUsageDashboard(),
      getUsageActivity(activityDays)
    ])
    if (usageDashboard.status === 'fulfilled') {
      dashboard.value = usageDashboard.value
    }
    if (usageActivity.status === 'fulfilled') {
      activity.value = usageActivity.value
    } else if (usageActivity.status === 'rejected') {
      if (!error.value) {
        error.value = 'Daily activity chart could not be loaded.'
      }
    }
    if (usageDashboard.status === 'rejected' && usageActivity.status === 'rejected') {
      throw usageDashboard.reason
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Could not load usage stats.'
    dashboard.value = null
    activity.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.activity-panel {
  margin-top: 0.25rem;
}

.activity-header {
  margin-bottom: 1rem;
}

.activity-sub {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.activity-detail-link {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--p-primary-color);
  text-decoration: none;
  white-space: nowrap;
}

.activity-detail-link:hover {
  text-decoration: underline;
}

.activity-loading {
  display: flex;
  justify-content: center;
  padding: 1.25rem 0;
}

.activity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr));
  gap: 0.75rem;
}

.activity-stat {
  margin: 0;
}

.panel-heading {
  font-size: 0.9375rem;
  font-weight: 600;
}

.activity-empty,
.activity-footnote {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  line-height: 1.45;
}

.activity-empty a {
  color: var(--p-primary-color);
  font-weight: 600;
}
</style>
