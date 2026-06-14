<template>
  <div class="architect-deliverable-card">
    <div class="architect-deliverable-card-icon">
      <i :class="type === 'change_control' ? 'pi pi-calendar' : 'pi pi-file-edit'" />
    </div>
    <div class="architect-deliverable-card-copy">
      <div class="architect-deliverable-card-title">{{ title }}</div>
      <div class="architect-deliverable-card-meta">Revision {{ revision }} · open the panel to preview or edit</div>
    </div>
    <Button label="Open panel" size="small" text @click="$emit('open-panel')" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'

const props = defineProps({
  revision: { type: Number, required: true },
  type: { type: String, default: 'design' }
})

defineEmits(['open-panel'])

const title = computed(() =>
  props.type === 'change_control' ? 'Change control record' : 'Design document'
)
</script>

<style scoped>
.architect-deliverable-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--p-primary-color) 6%, var(--p-content-background));
}

.architect-deliverable-card-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
}

.architect-deliverable-card-copy {
  flex: 1;
  min-width: 0;
}

.architect-deliverable-card-title {
  font-weight: 600;
  font-size: 0.9375rem;
}

.architect-deliverable-card-meta {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  margin-top: 0.15rem;
}
</style>
