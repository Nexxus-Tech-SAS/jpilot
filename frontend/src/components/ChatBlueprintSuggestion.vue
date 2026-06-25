<template>
  <div
    class="blueprint-suggestion"
    :class="suggestion.state === 'applied' ? 'blueprint-suggestion-applied' : 'blueprint-suggestion-candidate'"
    role="region"
    aria-label="Blueprint suggestion"
  >
    <div class="blueprint-suggestion-header">
      <span class="blueprint-suggestion-icon" aria-hidden="true">
        <i :class="suggestion.state === 'applied' ? 'pi pi-check-circle' : 'pi pi-bolt'" />
      </span>
      <span class="blueprint-suggestion-title">
        <template v-if="suggestion.state === 'applied'">
          Using the <strong>{{ suggestion.label }}</strong> blueprint for this answer
        </template>
        <template v-else>
          This looks like the <strong>{{ suggestion.label }}</strong> blueprint
        </template>
      </span>
      <span
        v-if="suggestion.state === 'suggested' && suggestion.confidence > 0"
        class="blueprint-suggestion-confidence"
        :title="`Match confidence: ${suggestion.confidence}%`"
      >
        {{ suggestion.confidence }}%
      </span>
    </div>
    <p v-if="suggestion.summary && suggestion.state === 'suggested'" class="blueprint-suggestion-summary">
      {{ suggestion.summary }}
    </p>
    <div class="blueprint-suggestion-actions">
      <!-- applied state: primary action is "use standard model instead" (i.e. skip) -->
      <template v-if="suggestion.state === 'applied'">
        <Button
          label="Use standard model instead"
          icon="pi pi-refresh"
          size="small"
          severity="secondary"
          :disabled="disabled"
          @click="onSkip"
        />
      </template>
      <!-- suggested state: primary is Apply, secondary is Skip -->
      <template v-else>
        <Button
          label="Apply blueprint"
          icon="pi pi-check"
          size="small"
          :disabled="disabled"
          @click="onApply"
        />
        <Button
          label="Skip"
          icon="pi pi-times"
          size="small"
          severity="secondary"
          text
          :disabled="disabled"
          @click="onSkip"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
defineProps({
  suggestion: {
    type: Object,
    required: true
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['apply', 'skip'])

function onApply() {
  emit('apply')
}

function onSkip() {
  emit('skip')
}
</script>

<style scoped>
.blueprint-suggestion {
  margin-top: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
}

.blueprint-suggestion-candidate {
  background: color-mix(in srgb, var(--p-primary-color, #6366f1) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-primary-color, #6366f1) 22%, transparent);
}

.blueprint-suggestion-applied {
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-green-500, #22c55e) 20%, transparent);
}

.blueprint-suggestion-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.35rem;
}

.blueprint-suggestion-applied .blueprint-suggestion-icon {
  color: var(--p-green-500, #22c55e);
  font-size: 0.9rem;
  flex-shrink: 0;
}

.blueprint-suggestion-candidate .blueprint-suggestion-icon {
  color: var(--p-primary-color, #6366f1);
  font-size: 0.9rem;
  flex-shrink: 0;
}

.blueprint-suggestion-title {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--p-text-color);
  flex: 1;
  min-width: 0;
}

.blueprint-suggestion-title strong {
  font-weight: 600;
}

.blueprint-suggestion-confidence {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-primary-color, #6366f1) 15%, transparent);
  color: var(--p-primary-color, #6366f1);
  flex-shrink: 0;
}

.blueprint-suggestion-summary {
  margin: 0 0 0.6rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}

.blueprint-suggestion-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
