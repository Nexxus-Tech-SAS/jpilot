<template>
  <aside class="architect-design-panel" :class="{ 'architect-design-panel-streaming': document?.streaming }">
    <div class="architect-design-panel-head">
      <div class="architect-design-panel-title-wrap">
        <h3 class="architect-design-panel-title">{{ panelTitle }}</h3>
        <Tag
          :value="document?.type === 'change_control' ? 'Change control' : 'Design'"
          :severity="document?.type === 'change_control' ? 'warn' : 'info'"
        />
        <Tag v-if="document?.revision" :value="`v${document.revision}`" severity="secondary" />
        <Tag v-if="document?.dirty" value="Edited" severity="warn" />
      </div>
      <div class="architect-design-panel-actions">
        <Button
          v-tooltip.bottom="'Hide design panel'"
          icon="pi pi-times"
          text
          rounded
          severity="secondary"
          aria-label="Hide design panel"
          @click="$emit('close')"
        />
      </div>
    </div>

    <div v-if="document?.streaming" class="architect-design-panel-status">
      <ProgressSpinner style="width: 1.25rem; height: 1.25rem" />
      <span>Writing document…</span>
    </div>

    <div v-if="!document?.markdown && !document?.streaming" class="architect-design-panel-empty">
      <i class="pi pi-file-edit" />
      <p>Your design document or change control record will appear here after discovery, when you attach a <code>.md</code> file, or when you ask JPilot to generate it.</p>
    </div>

    <template v-else>
      <div class="architect-design-panel-toolbar">
        <Button
          label="Send for revision"
          icon="pi pi-sync"
          size="small"
          :disabled="disabled || !document?.markdown?.trim()"
          @click="$emit('send-revision')"
        />
        <Button
          v-if="canSendToOperator"
          label="Send to Operator"
          icon="pi pi-arrow-right"
          size="small"
          severity="secondary"
          outlined
          :disabled="disabled"
          @click="$emit('send-to-operator')"
        />
        <Button
          :label="downloadLabel"
          icon="pi pi-download"
          size="small"
          text
          :disabled="!document?.markdown?.trim()"
          @click="$emit('download')"
        />
      </div>

      <Textarea
        :model-value="document?.markdown || ''"
        class="architect-design-editor"
        auto-resize
        rows="12"
        :disabled="disabled || document?.streaming"
        placeholder="Design document markdown…"
        @update:model-value="onEditorInput"
      />

      <div class="architect-design-preview-head">Preview</div>
      <div class="architect-design-preview">
        <ChatMarkdown :content="document?.markdown || ''" />
      </div>
    </template>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ChatMarkdown from './ChatMarkdown.vue'
import { canSendDeliverableToOperator } from '../utils/architectDeliverable'

const props = defineProps({
  document: { type: Object, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'update:markdown', 'send-revision', 'send-to-operator', 'download'])

const panelTitle = computed(() =>
  props.document?.type === 'change_control' ? 'Change control record' : 'Design document'
)

const downloadLabel = computed(() =>
  props.document?.type === 'change_control' ? 'Download record' : 'Download design'
)

const canSendToOperator = computed(() => {
  if (!props.document?.markdown) return false
  const marker =
    props.document.type === 'change_control'
      ? '<!-- jpilot-change-control-document -->'
      : '<!-- jpilot-design-document -->'
  return canSendDeliverableToOperator(`${marker}\n${props.document.markdown}`)
})

function onEditorInput(value) {
  emit('update:markdown', value)
}
</script>

<style scoped>
.architect-design-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  border-left: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}

.architect-design-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.85rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.architect-design-panel-title-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.architect-design-panel-title {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
}

.architect-design-panel-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  border-bottom: 1px solid var(--p-content-border-color);
}

.architect-design-panel-empty {
  padding: 1.25rem 0.85rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  line-height: 1.55;
}

.architect-design-panel-empty i {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  color: var(--p-primary-color);
}

.architect-design-panel-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.architect-design-editor {
  width: calc(100% - 1.7rem);
  margin: 0.75rem 0.85rem 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  max-height: 28vh;
  overflow: auto;
}

.architect-design-preview-head {
  padding: 0.75rem 0.85rem 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
}

.architect-design-preview {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 0.85rem 0.85rem;
}

@media (max-width: 991px) {
  .architect-design-panel {
    border-left: none;
    border-top: 1px solid var(--p-content-border-color);
  }

  .architect-design-editor {
    max-height: 22vh;
  }
}
</style>
