<template>
  <div
    class="beta-sidebar flex flex-column h-full"
    :class="{
      'beta-sidebar-drawer': variant === 'drawer',
      'beta-sidebar-lab': showBetaLabel
    }"
  >
    <div v-if="variant !== 'drawer'" class="beta-sidebar-profile">
      <TriArcLoader class="beta-sidebar-logo" />
      <div class="ld-cursor beta-sidebar-brand">JPilot</div>
      <span class="beta-sidebar-tagline">AI assistant for your appliances</span>
    </div>

    <div class="beta-sidebar-body">
      <div class="beta-sidebar-toolbar">
        <Button
          label="New chat"
          icon="pi pi-plus"
          size="small"
          class="beta-new-chat-btn"
          :disabled="!canAdd"
          @click="$emit('new-chat')"
        />
        <span class="beta-chat-count">{{ conversationCount }} / {{ maxConversations }}</span>
      </div>

      <IconField class="beta-sidebar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="searchQuery"
          type="text"
          placeholder="Search chats"
          class="w-full"
        />
      </IconField>

      <div class="beta-sidebar-list">
        <BetaChatPaneCard
          v-for="pane in filteredPanes"
          :key="pane.sessionId"
          :pane="pane"
          :active="pane.sessionId === activeSessionId"
          :deletable="conversationCount > 1"
          :lab-variant="showBetaLabel"
          @select="$emit('select', pane.sessionId)"
          @delete="$emit('delete', pane.sessionId)"
        />
      </div>

      <p v-if="!canAdd" class="beta-sidebar-limit">
        Conversation limit reached. Delete an old chat to start a new one.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import TriArcLoader from './TriArcLoader.vue'
import BetaChatPaneCard from './BetaChatPaneCard.vue'

const props = defineProps({
  panes: { type: Array, default: () => [] },
  activeSessionId: { type: String, required: true },
  canAdd: { type: Boolean, default: true },
  conversationCount: { type: Number, default: 0 },
  maxConversations: { type: Number, default: 12 },
  /** `drawer` — compact list for mobile slide-over. */
  variant: { type: String, default: 'default' },
  /** Show experimental Chat Beta label under the sidebar title. */
  showBetaLabel: { type: Boolean, default: false }
})

defineEmits(['select', 'new-chat', 'delete'])

const searchQuery = ref('')

const filteredPanes = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return props.panes
  return props.panes.filter(
    (pane) =>
      pane.title.toLowerCase().includes(q) ||
      pane.preview.toLowerCase().includes(q) ||
      pane.role.label.toLowerCase().includes(q)
  )
})
</script>

<style scoped>
.beta-sidebar {
  min-height: 0;
}

.beta-sidebar-profile {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 1.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
  text-align: center;
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) .beta-sidebar-profile {
  padding: 1.1rem 1.25rem;
  background: transparent;
  border-bottom-color: color-mix(in srgb, var(--p-content-border-color) 22%, transparent);
}

.beta-sidebar-logo {
  color: var(--p-primary-color);
  flex-shrink: 0;
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) .beta-sidebar-logo {
  transform: scale(0.79);
  transform-origin: center top;
}

.beta-sidebar-brand {
  margin-top: 1.25rem;
  color: var(--p-primary-color);
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) .beta-sidebar-brand {
  margin-top: 0.5rem;
}

.beta-sidebar-tagline {
  margin-top: 0.35rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  line-height: 1.45;
  max-width: 14rem;
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) .beta-sidebar-tagline {
  display: none;
}

.beta-sidebar-beta-tag {
  display: inline-flex;
  margin-top: 0.55rem;
  padding: 0.18rem 0.6rem;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--p-orange-700);
  background: color-mix(in srgb, var(--p-orange-500) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-orange-500) 32%, transparent);
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) .beta-sidebar-beta-tag {
  margin-top: 0.35rem;
}

:global(.app-dark) .beta-sidebar-beta-tag {
  color: var(--p-orange-300);
}

.beta-sidebar-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  min-height: 0;
  flex: 1;
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) .beta-sidebar-body {
  gap: 0.75rem;
  padding: 1rem;
  background: transparent;
}

.beta-sidebar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.beta-new-chat-btn {
  flex: 1;
}

.beta-chat-count {
  flex-shrink: 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}

.beta-sidebar-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  min-height: 0;
  flex: 1;
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) .beta-sidebar-list {
  gap: 0.5rem;
}

.beta-sidebar:not(.beta-sidebar-drawer) :deep(.beta-pane-card) {
  background: color-mix(in srgb, var(--p-content-background) 50%, transparent);
  border-color: color-mix(in srgb, var(--p-content-border-color) 52%, transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.beta-sidebar:not(.beta-sidebar-drawer) :deep(.beta-pane-card:hover) {
  background: color-mix(in srgb, var(--p-surface-100) 55%, transparent);
}

:global(.app-dark) .beta-sidebar:not(.beta-sidebar-drawer) :deep(.beta-pane-card:hover) {
  background: color-mix(in srgb, var(--p-surface-800) 55%, transparent);
}

.beta-sidebar:not(.beta-sidebar-drawer) :deep(.beta-pane-card-active) {
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}

.beta-sidebar-lab:not(.beta-sidebar-drawer) :deep(.beta-pane-card-active) {
  background: color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 10%, transparent);
  border-color: color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 45%, transparent);
}

.beta-sidebar-limit {
  margin: 0;
  font-size: 0.75rem;
  color: var(--p-orange-500);
  line-height: 1.45;
}

@media (max-width: 991px) {
  .beta-sidebar:not(.beta-sidebar-drawer) .beta-sidebar-profile {
    padding: 1.25rem;
  }

  .beta-sidebar:not(.beta-sidebar-drawer) .beta-sidebar-logo {
    transform: scale(1.29);
    transform-origin: center top;
  }

  .beta-sidebar:not(.beta-sidebar-drawer) .beta-sidebar-list {
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 0.25rem;
  }

  .beta-sidebar:not(.beta-sidebar-drawer) .beta-sidebar-list :deep(.beta-pane-card) {
    min-width: 16rem;
  }
}

.beta-sidebar-drawer .beta-sidebar-body {
  padding: 0;
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.beta-sidebar-drawer .beta-sidebar-list {
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
}

.beta-sidebar-drawer .beta-sidebar-list :deep(.beta-pane-card) {
  min-width: 0;
}
</style>
