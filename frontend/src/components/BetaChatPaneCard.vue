<template>
  <div
    class="beta-pane-card"
    :class="{
      'beta-pane-card-active': active,
      'beta-pane-card-lab': labVariant,
      'beta-pane-card-deletable': labVariant && deletable
    }"
    :style="roleAccentStyle"
    role="button"
    tabindex="0"
    @click="$emit('select')"
    @keydown.enter="$emit('select')"
  >
    <div class="beta-pane-card-main">
      <div class="beta-pane-card-avatar-wrap">
        <span class="beta-pane-card-avatar">
          <i :class="pane.role.icon" />
        </span>
        <span class="beta-pane-card-status" :class="`beta-pane-card-status-${pane.status}`" />
      </div>
      <div class="beta-pane-card-copy">
        <span class="beta-pane-card-title">{{ pane.title }}</span>
        <span class="beta-pane-card-preview">{{ pane.preview }}</span>
      </div>
    </div>
    <Button
      v-if="deletable"
      v-tooltip.top="'Delete conversation'"
      icon="pi pi-trash"
      text
      rounded
      size="small"
      severity="secondary"
      class="beta-pane-card-delete"
      :disabled="pane.busy"
      @click.stop="$emit('delete')"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'

const props = defineProps({
  pane: { type: Object, required: true },
  active: { type: Boolean, default: false },
  deletable: { type: Boolean, default: true },
  labVariant: { type: Boolean, default: false }
})

defineEmits(['select', 'delete'])

const roleAccentStyle = computed(() => {
  const accent = props.pane.role?.accent
  return accent ? { '--role-accent': accent } : undefined
})
</script>

<style scoped>
.beta-pane-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  padding: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
  background: var(--p-content-background);
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.beta-pane-card-lab {
  position: relative;
  padding: 0.6rem 0.75rem;
  gap: 0.6rem;
  background: var(--p-content-background);
  border-color: var(--p-content-border-color);
  box-shadow: 0 2px 10px rgba(2, 6, 23, 0.05);
}

:global(.app-dark) .beta-pane-card-lab {
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.22);
}

.beta-pane-card:hover {
  background: var(--p-surface-100);
}

:global(.app-dark) .beta-pane-card:hover {
  background: var(--p-surface-800);
}

.beta-pane-card-active {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--p-content-background));
}

.beta-pane-card-lab.beta-pane-card-active {
  border-color: color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 45%, transparent);
  background: color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 8%, var(--p-content-background));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 45%, transparent);
}

.beta-pane-card-main {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
  flex: 1;
}

.beta-pane-card-lab .beta-pane-card-main {
  gap: 0.6rem;
}

.beta-pane-card-lab.beta-pane-card-deletable .beta-pane-card-main {
  padding-right: 2rem;
}

.beta-pane-card-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}

.beta-pane-card-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 999px;
  background: var(--p-surface-100);
  color: var(--p-primary-color);
  box-shadow: 0 6px 18px rgba(2, 6, 23, 0.1);
}

.beta-pane-card-lab .beta-pane-card-avatar {
  width: 2.25rem;
  height: 2.25rem;
  background: color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 16%, transparent);
  color: var(--role-accent, var(--p-primary-color));
  box-shadow: 0 3px 8px rgba(2, 6, 23, 0.08);
}

.beta-pane-card-avatar i {
  font-size: 1.125rem;
}

.beta-pane-card-lab .beta-pane-card-avatar i {
  font-size: 1rem;
}

.beta-pane-card-status {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 999px;
  border: 2px solid var(--p-content-background);
  background: var(--p-surface-400);
}

.beta-pane-card-status-active {
  background: var(--p-green-400);
}

.beta-pane-card-status-busy {
  background: var(--p-yellow-400);
}

.beta-pane-card-status-away {
  background: var(--p-orange-400);
}

.beta-pane-card-copy {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.beta-pane-card-title {
  font-weight: 600;
  color: var(--p-text-color);
}

.beta-pane-card-lab .beta-pane-card-title {
  font-size: 0.9rem;
}

.beta-pane-card-preview {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 11rem;
}

.beta-pane-card-lab .beta-pane-card-preview {
  font-size: 0.78rem;
  max-width: 13rem;
}

.beta-pane-card-delete {
  flex-shrink: 0;
}

.beta-pane-card-lab .beta-pane-card-delete {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.15s ease;
}

.beta-pane-card-lab:hover .beta-pane-card-delete,
.beta-pane-card-lab:focus-within .beta-pane-card-delete {
  opacity: 1;
}

@media (max-width: 991px) {
  .beta-pane-card-lab .beta-pane-card-delete {
    position: static;
    transform: none;
    opacity: 1;
  }

  .beta-pane-card-lab.beta-pane-card-deletable .beta-pane-card-main {
    padding-right: 0;
  }
}
</style>
