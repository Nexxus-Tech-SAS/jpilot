<template>
  <div class="usage-chart-block">
    <div class="usage-chart-head flex align-items-center justify-content-between gap-2 flex-wrap">
      <h4 class="breakdown-title m-0">Daily activity</h4>
      <span class="chart-legend-hint">Left: rounds &amp; searches · Right: tokens</span>
    </div>

    <Message v-if="showNoDailyDataHint" severity="info" :closable="false" class="mb-2">
      Per-day totals are not stored for past usage. JPilot only has
      <strong>month-to-date</strong> numbers ({{ formatCount(monthlyRequests) }} chat rounds so far).
      Daily points appear here after new chats once daily tracking is active on this server.
    </Message>

    <div class="usage-chart-wrap">
      <Chart
        v-if="ready"
        type="line"
        :data="chartData"
        :options="chartOptions"
        class="usage-chart"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import Chart from 'primevue/chart'
import Message from 'primevue/message'
import { formatCount } from '../services/modelUsage'

const props = defineProps({
  series: {
    type: Array,
    default: () => []
  },
  showSearches: {
    type: Boolean,
    default: false
  },
  monthlyRequests: {
    type: Number,
    default: 0
  }
})

const chartData = ref(null)
const chartOptions = ref(null)
const ready = ref(false)

const hasDailyUsage = computed(() =>
  props.series.some((day) => (day.requests || 0) + (day.tokens || 0) + (day.queries || 0) > 0)
)

const showNoDailyDataHint = computed(
  () => props.series.length > 0 && !hasDailyUsage.value && props.monthlyRequests > 0
)

function themeColors() {
  const root = getComputedStyle(document.documentElement)
  return {
    text: root.getPropertyValue('--p-text-color').trim() || '#334155',
    muted: root.getPropertyValue('--p-text-muted-color').trim() || '#64748b',
    border: root.getPropertyValue('--p-content-border-color').trim() || '#e2e8f0',
    emerald: root.getPropertyValue('--p-emerald-500').trim() || '#10b981',
    blue: root.getPropertyValue('--p-blue-500').trim() || '#3b82f6',
    amber: root.getPropertyValue('--p-amber-500').trim() || '#f59e0b'
  }
}

function applyChart() {
  if (!props.series.length) {
    ready.value = false
    return
  }

  const colors = themeColors()
  const labels = props.series.map((day) => day.label)
  const datasets = [
    {
      label: 'Chat rounds',
      fill: true,
      borderColor: colors.emerald,
      backgroundColor: 'rgba(16, 185, 129, 0.15)',
      yAxisID: 'y',
      tension: 0.4,
      data: props.series.map((day) => day.requests || 0),
      pointRadius: hasDailyUsage.value ? 2 : 0
    }
  ]

  if (props.showSearches) {
    datasets.push({
      label: 'Web searches',
      fill: false,
      borderColor: colors.blue,
      borderDash: [6, 4],
      yAxisID: 'y',
      tension: 0.4,
      data: props.series.map((day) => day.queries || 0),
      pointRadius: hasDailyUsage.value ? 2 : 0
    })
  }

  datasets.push({
    label: 'Tokens',
    fill: false,
    borderColor: colors.amber,
    yAxisID: 'y1',
    tension: 0.4,
    data: props.series.map((day) => day.tokens || 0),
    pointRadius: hasDailyUsage.value ? 2 : 0
  })

  chartData.value = { labels, datasets }
  chartOptions.value = {
    stacked: false,
    maintainAspectRatio: false,
    aspectRatio: 0.6,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: colors.text, boxWidth: 10, usePointStyle: true }
      }
    },
    scales: {
      x: {
        ticks: { color: colors.muted, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
        grid: { color: colors.border }
      },
      y: {
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        title: { display: true, text: 'Rounds / searches', color: colors.muted },
        ticks: { color: colors.muted, precision: 0 },
        grid: { color: colors.border }
      },
      y1: {
        type: 'linear',
        position: 'right',
        beginAtZero: true,
        title: { display: true, text: 'Tokens', color: colors.muted },
        ticks: {
          color: colors.muted,
          callback(value) {
            const n = Number(value)
            if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
            if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`
            return n
          }
        },
        grid: { drawOnChartArea: false, color: colors.border }
      }
    }
  }
  ready.value = true
}

onMounted(applyChart)
watch(() => [props.series, props.showSearches, props.monthlyRequests], applyChart, { deep: true })
</script>

<style scoped>
.usage-chart-block {
  margin-top: 1rem;
}

.usage-chart-head {
  margin-bottom: 0.65rem;
}

.breakdown-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.chart-legend-hint {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.usage-chart-wrap {
  position: relative;
  min-height: 16rem;
}

.usage-chart {
  width: 100%;
  height: 16rem;
}
</style>
