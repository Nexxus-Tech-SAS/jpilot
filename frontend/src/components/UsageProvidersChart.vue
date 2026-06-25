<template>
  <div class="providers-chart-block">
    <div class="usage-chart-head flex align-items-center justify-content-between gap-2 flex-wrap">
      <h4 class="breakdown-title m-0">This month by provider</h4>
      <span class="chart-legend-hint">Left: chat rounds · Right: tokens</span>
    </div>
    <div class="usage-chart-wrap">
      <Chart
        v-if="chartData && chartOptions"
        type="bar"
        :data="chartData"
        :options="chartOptions"
        class="usage-chart"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import Chart from 'primevue/chart'

const props = defineProps({
  providers: {
    type: Array,
    default: () => []
  }
})

const chartData = ref(null)
const chartOptions = ref(null)

function themeColors() {
  const root = getComputedStyle(document.documentElement)
  return {
    text: root.getPropertyValue('--p-text-color').trim() || '#334155',
    muted: root.getPropertyValue('--p-text-muted-color').trim() || '#64748b',
    border: root.getPropertyValue('--p-content-border-color').trim() || '#e2e8f0',
    emerald: root.getPropertyValue('--p-emerald-500').trim() || '#10b981',
    amber: root.getPropertyValue('--p-amber-500').trim() || '#f59e0b'
  }
}

function refreshChart() {
  const active = props.providers.filter((p) => (p.requestsUsed || 0) > 0 || (p.tokensUsed || 0) > 0)
  if (!active.length) {
    chartData.value = null
    chartOptions.value = null
    return
  }

  const colors = themeColors()
  const labels = active.map((p) => p.providerName || p.providerType || 'Provider')

  chartData.value = {
    labels,
    datasets: [
      {
        label: 'Chat rounds',
        data: active.map((p) => p.requestsUsed || 0),
        backgroundColor: colors.emerald,
        yAxisID: 'y',
        borderRadius: 4
      },
      {
        label: 'Tokens',
        data: active.map((p) => p.tokensUsed || 0),
        backgroundColor: colors.amber,
        yAxisID: 'y1',
        borderRadius: 4
      }
    ]
  }

  chartOptions.value = {
    stacked: false,
    maintainAspectRatio: false,
    aspectRatio: 0.8,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: colors.text, boxWidth: 10, usePointStyle: true }
      },
      tooltip: {
        callbacks: {
          label(context) {
            return `${context.dataset.label}: ${(context.parsed.y ?? 0).toLocaleString()}`
          }
        }
      }
    },
    scales: {
      x: {
        ticks: { color: colors.muted, maxRotation: 45, minRotation: 0 },
        grid: { color: colors.border }
      },
      y: {
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        ticks: { color: colors.muted, precision: 0 },
        grid: { color: colors.border }
      },
      y1: {
        type: 'linear',
        position: 'right',
        beginAtZero: true,
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
}

watch(() => props.providers, refreshChart, { deep: true, immediate: true })
</script>

<style scoped>
.providers-chart-block {
  margin-top: 0.5rem;
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
  min-height: 14rem;
}

.usage-chart {
  width: 100%;
  height: 14rem;
}
</style>
