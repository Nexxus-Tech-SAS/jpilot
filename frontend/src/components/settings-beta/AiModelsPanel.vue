<template>
  <div class="flex flex-column gap-4">
    <AIProvidersPanel />
    <div class="content-panel content-panel-padded usage-panel-wrap">
      <ModelUsageDashboard />
    </div>
  </div>
</template>

<script setup>
import AIProvidersPanel from '../AIProvidersPanel.vue'
import ModelUsageDashboard from '../ModelUsageDashboard.vue'
</script>

<style scoped>
.usage-panel-wrap {
  width: 100%;
}
</style>
