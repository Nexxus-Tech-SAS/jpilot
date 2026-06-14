<template>
  <div class="usage-dashboard">
    <div class="usage-header">
      <div>
        <h3 class="info-title m-0">JPilot usage</h3>
        <p class="usage-period">{{ dashboard?.periodLabel || 'This month' }}</p>
        <p class="usage-lead">Activity tracked inside JPilot this calendar month — not provider billing or account balance.</p>
      </div>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        aria-label="Refresh usage"
        @click="load"
      />
    </div>

    <div v-if="loading && !dashboard" class="usage-loading">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
    </div>

    <template v-else-if="dashboard">
      <div v-if="!dashboard.providers.length" class="usage-empty-block">
        No AI providers configured. Add LLM providers under Settings → AI Providers.
      </div>

      <div
        v-for="provider in dashboard.providers"
        :key="provider.id"
        class="usage-card"
        :class="{ 'usage-card-muted': !provider.enabled }"
      >
        <div class="usage-card-top">
          <div class="usage-icon" :class="providerIconClass(provider.providerType)">
            <i :class="providerIcon(provider.providerType)" />
          </div>
          <div class="usage-meta">
            <span class="usage-name">{{ provider.providerName }}</span>
            <span class="usage-sub">{{ provider.providerType }} · {{ provider.model }}</span>
          </div>
          <div class="usage-tags">
            <Tag v-if="provider.isDefault" value="Default" severity="info" />
            <Tag v-if="!provider.enabled" value="Disabled" severity="secondary" />
          </div>
        </div>

        <div class="usage-stats">
          <div class="usage-stat">
            <span class="usage-stat-value">{{ formatCount(provider.requestsUsed) }}</span>
            <span class="usage-stat-label">Chat rounds</span>
            <span class="usage-stat-hint">LLM API calls in JPilot</span>
          </div>
          <div v-if="hasTokenSplit(provider)" class="usage-stat">
            <span class="usage-stat-value">{{ formatCount(provider.inputTokensUsed) }}</span>
            <span class="usage-stat-label">Input tokens</span>
          </div>
          <div v-if="hasTokenSplit(provider)" class="usage-stat">
            <span class="usage-stat-value">{{ formatCount(provider.outputTokensUsed) }}</span>
            <span class="usage-stat-label">Output tokens</span>
          </div>
          <div class="usage-stat">
            <span class="usage-stat-value">{{ formatCount(provider.tokensUsed) }}</span>
            <span class="usage-stat-label">{{ hasTokenSplit(provider) ? 'Total tokens' : 'Tokens' }}</span>
            <span v-if="!hasTokenSplit(provider)" class="usage-stat-hint">Reported by the provider API</span>
          </div>
          <div v-if="provider.avgTokensPerRequest != null" class="usage-stat">
            <span class="usage-stat-value">{{ formatCount(provider.avgTokensPerRequest) }}</span>
            <span class="usage-stat-label">Avg / chat round</span>
          </div>
        </div>

        <div v-if="provider.limitsConfigured" class="usage-budget">
          <span class="usage-budget-label">Local budget caps</span>
          <UsageMeter
            v-if="provider.monthlyRequestLimit != null"
            label="Chat rounds"
            :used="provider.requestsUsed"
            :limit="provider.monthlyRequestLimit"
            :percent="provider.requestPercent"
            :remaining="provider.remainingRequests"
            :unlimited="false"
            unit="rounds"
          />
          <UsageMeter
            v-if="provider.monthlyTokenLimit != null"
            label="Tokens"
            :used="provider.tokensUsed"
            :limit="provider.monthlyTokenLimit"
            :percent="provider.tokenPercent"
            :remaining="provider.remainingTokens"
            :unlimited="false"
            unit="tokens"
          />
        </div>
      </div>

      <p class="usage-footnote">
        Totals include tool-loop rounds during a chat. Usage outside JPilot or before tracking was enabled is not included. Check each provider’s console for billing and remaining credits.
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
import Tag from 'primevue/tag'
import UsageMeter from './UsageMeter.vue'
import { formatCount, getModelUsageDashboard } from '../services/modelUsage'

const loading = ref(false)
const error = ref('')
const dashboard = ref(null)

function hasTokenSplit(provider) {
  return (provider.inputTokensUsed ?? 0) > 0 || (provider.outputTokensUsed ?? 0) > 0
}

function providerIcon(type) {
  const map = {
    OpenAI: 'pi pi-sparkles',
    Anthropic: 'pi pi-comments',
    Gemini: 'pi pi-google',
    Grok: 'pi pi-bolt',
    DeepSeek: 'pi pi-code',
    OpenRouter: 'pi pi-share-alt',
    'Azure OpenAI': 'pi pi-microsoft',
    'AWS Bedrock': 'pi pi-cloud',
    'LM Studio': 'pi pi-desktop',
    'OpenAI-Compatible': 'pi pi-server'
  }
  return map[type] || 'pi pi-microchip-ai'
}

function providerIconClass(type) {
  return (type || 'default').replace(/\s+/g, '-').toLowerCase()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    dashboard.value = await getModelUsageDashboard()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load usage'
    dashboard.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>

<style scoped>
.usage-dashboard {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
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
  padding: 1.5rem 0;
}

.usage-card {
  padding: 0.85rem 0.9rem;
  border-radius: 12px;
  background: linear-gradient(145deg, var(--app-nested-surface), var(--app-nested-surface-strong));
  border: 1px solid var(--p-content-border-color);
  box-shadow: 0 1px 8px rgba(15, 23, 42, 0.04);
}

.usage-card-muted {
  opacity: 0.72;
}

.usage-card-top {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}

.usage-icon {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  background: var(--p-primary-100);
  color: var(--p-primary-700);
  flex-shrink: 0;
}

.usage-icon.openai {
  background: rgba(16, 163, 127, 0.12);
  color: #0d9488;
}

.usage-icon.anthropic {
  background: rgba(217, 119, 6, 0.12);
  color: #b45309;
}

.usage-icon.gemini {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.usage-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.usage-name {
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.2;
}

.usage-sub {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.usage-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.usage-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
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

.usage-stat-hint {
  font-size: 0.65rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}

.usage-budget {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed var(--p-content-border-color);
}

.usage-budget-label,
.usage-budget-meter {
  margin-top: 0.75rem;
}

.usage-budget-label {
  display: block;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.usage-empty,
.usage-empty-block,
.usage-footnote {
  margin: 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  line-height: 1.45;
}

.usage-empty-block {
  padding: 0.75rem;
  border-radius: 8px;
  background: var(--app-nested-surface-strong);
}

:global(html.app-dark) .usage-card {
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.22);
}

:global(html.app-dark) .usage-icon {
  background: color-mix(in srgb, var(--p-primary-400) 18%, var(--app-nested-surface-strong));
  color: var(--p-primary-200);
}
</style>
