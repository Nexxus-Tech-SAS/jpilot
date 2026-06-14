<template>
  <div class="vendors-panel">
    <div class="vendors-header">
      <div>
        <h2 class="section-title m-0">Vendor platforms</h2>
        <p class="section-copy">
          Enable or disable vendor integrations for JPilot chat and the add-appliance flow. Inventory records
          stay in the database; disabled vendors turn off matching appliances until re-enabled.
        </p>
      </div>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        aria-label="Refresh vendors"
        @click="load"
      />
    </div>

    <Message v-if="!isAdmin" severity="info" :closable="false" class="mb-0">
      Only administrators can change vendor availability.
    </Message>

    <div v-if="loading && !catalog" class="vendors-loading">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
    </div>

    <template v-else-if="catalog">
      <div v-for="group in catalog.groups" :key="group.id" class="vendor-group content-panel content-panel-padded">
        <div class="vendor-group-head">
          <div>
            <h3 class="vendor-group-title">{{ group.label }}</h3>
            <p v-if="group.toggleable" class="vendor-group-meta">
              {{ group.enabledCount }} / {{ group.supportedCount }} enabled
            </p>
            <p v-else class="vendor-group-meta">Coming soon</p>
          </div>
          <ToggleSwitch
            v-if="group.toggleable"
            :model-value="group.platformEnabled"
            :disabled="!isAdmin || savingKey === `group:${group.id}`"
            v-tooltip.left="isAdmin ? 'Enable or disable all supported products in this vendor family' : 'Admin only'"
            @update:model-value="(value) => onGroupToggle(group, value)"
          />
        </div>

        <div class="vendor-product-list">
          <div v-for="product in group.products" :key="product.id" class="vendor-product-row">
            <div class="vendor-product-main">
              <span class="vendor-product-name">{{ product.label }}</span>
              <Tag :value="product.statusLabel" :severity="statusSeverity(product.status)" />
              <span v-if="product.applianceCount" class="vendor-product-count">
                {{ product.applianceCount }} in inventory
              </span>
            </div>
            <p class="vendor-product-desc">{{ product.description }}</p>
            <div class="vendor-product-actions">
              <ToggleSwitch
                v-if="product.toggleable"
                :model-value="product.platformEnabled"
                :disabled="!isAdmin || savingKey === `product:${product.id}`"
                v-tooltip.left="isAdmin ? 'Platform integration' : 'Admin only'"
                @update:model-value="(value) => onProductToggle(product, value)"
              />
              <span v-else class="vendor-product-soon">Roadmap only</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { getVendorCatalog, saveVendorCatalog } from '../services/vendorCatalog'
import { getStoredUser } from '../services/auth'

const emit = defineEmits(['changed'])

const loading = ref(false)
const savingKey = ref('')
const error = ref('')
const catalog = ref(null)

const currentUser = ref(getStoredUser())
const isAdmin = computed(() => currentUser.value?.role === 'admin')

function statusSeverity(status) {
  if (status === 'supported') return 'success'
  if (status === 'beta') return 'warn'
  return 'secondary'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    catalog.value = await getVendorCatalog()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load vendor catalog'
    catalog.value = null
  } finally {
    loading.value = false
  }
}

async function persist(payload) {
  catalog.value = await saveVendorCatalog(payload)
  emit('changed')
}

async function onProductToggle(product, enabled) {
  if (!isAdmin.value) return
  savingKey.value = `product:${product.id}`
  try {
    await persist({
      products: [{ productId: product.id, enabled }],
      groups: []
    })
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to update vendor'
    await load()
  } finally {
    savingKey.value = ''
  }
}

async function onGroupToggle(group, enabled) {
  if (!isAdmin.value) return
  savingKey.value = `group:${group.id}`
  try {
    await persist({
      products: [],
      groups: [{ vendorGroupId: group.id, enabled }]
    })
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to update vendor group'
    await load()
  } finally {
    savingKey.value = ''
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>

<style scoped>
.vendors-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.vendors-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.vendors-loading {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}

.vendor-group {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.vendor-group-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.vendor-group-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.vendor-group-meta {
  margin: 0.2rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.vendor-product-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.vendor-product-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.35rem 1rem;
  padding: 0.75rem 0.85rem;
  border-radius: 10px;
  background: var(--app-nested-surface-strong);
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 75%, transparent);
}

.vendor-product-main {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}

.vendor-product-name {
  font-size: 0.875rem;
  font-weight: 600;
}

.vendor-product-count {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}

.vendor-product-desc {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}

.vendor-product-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.vendor-product-soon {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
</style>
