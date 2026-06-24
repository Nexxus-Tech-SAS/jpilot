<template>
  <div class="content-panel content-panel-padded">
    <h2 class="section-title">Agent orchestration</h2>
    <p class="section-copy">
      Choose how much room JPilot has for multi-step deployments: tool rounds per phase, automatic
      continuations, and when to pause for user approval on long operator tasks.
    </p>

    <div class="flex flex-column gap-4 mt-4">
      <div class="setting-row">
        <div class="setting-label">Orchestration mode</div>
        <SelectButton
          v-model="orchestrationMode"
          :options="modeOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          :disabled="saving"
          class="orchestration-mode-select mt-2"
          @update:model-value="onModeChange"
        />
        <p class="mode-description mt-2 mb-0">{{ modeDescription }}</p>
      </div>

      <div class="effective-max-rounds">
        <span class="effective-max-label">Effective max tool rounds per chat turn</span>
        <span class="effective-max-value">{{ effectiveMaxRoundsText }}</span>
        <span class="effective-max-hint">
          Initial run plus {{ settings.maxToolContinuationPhases }} automatic continuation
          {{ settings.maxToolContinuationPhases === 1 ? 'phase' : 'phases' }} when Operator deployments need more steps.
        </span>
      </div>

      <div class="orchestration-summary">
        <div class="summary-item">
          <span class="summary-label">Tool rounds / phase</span>
          <span class="summary-value">{{ settings.maxToolIterations }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Continuation phases</span>
          <span class="summary-value">{{ settings.maxToolContinuationPhases }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Long-task threshold</span>
          <span class="summary-value">{{ settings.longTaskToolThreshold }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Prompt before long tasks</span>
          <span class="summary-value">{{ settings.promptBeforeLongTasks ? 'Yes' : 'No' }}</span>
        </div>
      </div>

      <div v-if="orchestrationMode === 'custom'" class="custom-orchestration flex flex-column gap-4">
        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Prompt before long deployments</div>
            <div class="setting-hint">
              After several tool rounds, pause and ask the user to continue with a deployment checklist.
            </div>
          </div>
          <ToggleSwitch
            v-model="settings.promptBeforeLongTasks"
            :disabled="saving"
            @update:model-value="saveSettings"
          />
        </div>

        <div class="flex flex-column gap-2 setting-row">
          <label for="longTaskToolThreshold" class="setting-label">Long-task threshold (tool rounds)</label>
          <InputNumber
            id="longTaskToolThreshold"
            v-model="settings.longTaskToolThreshold"
            :min="3"
            :max="40"
            :disabled="saving"
            class="max-select"
            @blur="saveSettings"
          />
        </div>

        <div class="flex flex-column gap-2 setting-row">
          <label for="maxToolIterations" class="setting-label">Max tool rounds per phase</label>
          <InputNumber
            id="maxToolIterations"
            v-model="settings.maxToolIterations"
            :min="5"
            :max="60"
            :disabled="saving"
            class="max-select"
            @blur="saveSettings"
          />
        </div>

        <div class="flex flex-column gap-2 setting-row">
          <label for="maxToolContinuationPhases" class="setting-label">Continuation phases</label>
          <InputNumber
            id="maxToolContinuationPhases"
            v-model="settings.maxToolContinuationPhases"
            :min="0"
            :max="8"
            :disabled="saving"
            class="max-select"
            @blur="saveSettings"
          />
        </div>
      </div>

      <div class="flex flex-column gap-4 stuck-detection">
        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label">Stuck detection (loop-breakers)</div>
            <div class="setting-hint">
              When a chat turn keeps failing the same call, fails one tool repeatedly, or makes
              no new progress, JPilot pauses and asks you how to proceed instead of grinding to
              the tool-call limit. Applies to every orchestration mode.
            </div>
          </div>
          <ToggleSwitch
            v-model="settings.loopBreakersEnabled"
            :disabled="saving"
            @update:model-value="saveSettings"
          />
        </div>

        <div v-if="settings.loopBreakersEnabled" class="flex flex-column gap-4">
          <div class="flex flex-column gap-2 setting-row">
            <label for="repeatedFailedCallLimit" class="setting-label">Identical failed calls before pausing</label>
            <InputNumber
              id="repeatedFailedCallLimit"
              v-model="settings.repeatedFailedCallLimit"
              :min="1"
              :max="10"
              :disabled="saving"
              class="max-select"
              @blur="saveSettings"
            />
          </div>

          <div class="flex flex-column gap-2 setting-row">
            <label for="perToolFailureLimit" class="setting-label">Failures of one tool before pausing</label>
            <InputNumber
              id="perToolFailureLimit"
              v-model="settings.perToolFailureLimit"
              :min="1"
              :max="15"
              :disabled="saving"
              class="max-select"
              @blur="saveSettings"
            />
          </div>

          <div class="flex flex-column gap-2 setting-row">
            <label for="noProgressWindow" class="setting-label">No-progress steps before pausing</label>
            <InputNumber
              id="noProgressWindow"
              v-model="settings.noProgressWindow"
              :min="2"
              :max="30"
              :disabled="saving"
              class="max-select"
              @blur="saveSettings"
            />
          </div>

          <div class="flex flex-column gap-2 setting-row">
            <label for="noProgressFloor" class="setting-label">Minimum tool rounds before the no-progress check</label>
            <InputNumber
              id="noProgressFloor"
              v-model="settings.noProgressFloor"
              :min="2"
              :max="60"
              :disabled="saving"
              class="max-select"
              @blur="saveSettings"
            />
          </div>
        </div>
      </div>
    </div>

    <Message v-if="message" class="mt-3" :severity="messageSeverity" :closable="false">
      {{ message }}
    </Message>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import {
  ORCHESTRATION_MODE_OPTIONS,
  ORCHESTRATION_PRESETS,
  applyOrchestrationPreset,
  effectiveMaxToolRoundsLabel as formatEffectiveMaxToolRounds,
  inferOrchestrationMode,
  orchestrationModeDescription
} from '../config/orchestrationPresets'
import { getCopilotPlatformSettings, saveCopilotPlatformSettings } from '../services/copilotPlatform'

const modeOptions = ORCHESTRATION_MODE_OPTIONS
const saving = ref(false)
const message = ref('')
const messageSeverity = ref('info')
const orchestrationMode = ref('standard')
const settings = reactive({
  maxToolIterations: 20,
  maxToolContinuationPhases: 3,
  longTaskToolThreshold: 8,
  promptBeforeLongTasks: true,
  loopBreakersEnabled: true,
  repeatedFailedCallLimit: 2,
  perToolFailureLimit: 3,
  noProgressWindow: 5,
  noProgressFloor: 8
})

const modeDescription = computed(() => orchestrationModeDescription(orchestrationMode.value))

const effectiveMaxRoundsText = computed(() => formatEffectiveMaxToolRounds(settings))

function applySettings(data) {
  settings.maxToolIterations = Number(data.maxToolIterations ?? 20)
  settings.maxToolContinuationPhases = Number(data.maxToolContinuationPhases ?? 3)
  settings.longTaskToolThreshold = Number(data.longTaskToolThreshold ?? 8)
  settings.promptBeforeLongTasks = Boolean(data.promptBeforeLongTasks ?? true)
  settings.loopBreakersEnabled = Boolean(data.loopBreakersEnabled ?? true)
  settings.repeatedFailedCallLimit = Number(data.repeatedFailedCallLimit ?? 2)
  settings.perToolFailureLimit = Number(data.perToolFailureLimit ?? 3)
  settings.noProgressWindow = Number(data.noProgressWindow ?? 5)
  settings.noProgressFloor = Number(data.noProgressFloor ?? 8)
  orchestrationMode.value = inferOrchestrationMode(data)
}

async function loadSettings() {
  try {
    const data = await getCopilotPlatformSettings()
    applySettings(data)
  } catch {
    Object.assign(settings, applyOrchestrationPreset('standard'))
    orchestrationMode.value = 'standard'
  }
}

function buildPayload() {
  const payload = {
    orchestrationMode: orchestrationMode.value
  }
  if (orchestrationMode.value === 'custom') {
    payload.maxToolIterations = settings.maxToolIterations
    payload.maxToolContinuationPhases = settings.maxToolContinuationPhases
    payload.longTaskToolThreshold = settings.longTaskToolThreshold
    payload.promptBeforeLongTasks = settings.promptBeforeLongTasks
  }
  // Loop-breakers apply to every mode, so always include them.
  payload.loopBreakersEnabled = settings.loopBreakersEnabled
  payload.repeatedFailedCallLimit = settings.repeatedFailedCallLimit
  payload.perToolFailureLimit = settings.perToolFailureLimit
  payload.noProgressWindow = settings.noProgressWindow
  payload.noProgressFloor = settings.noProgressFloor
  return payload
}

async function saveSettings() {
  saving.value = true
  message.value = ''
  try {
    const data = await saveCopilotPlatformSettings(buildPayload())
    applySettings(data)
    message.value = 'Agent orchestration settings saved.'
    messageSeverity.value = 'success'
  } catch (error) {
    message.value =
      error.response?.data?.detail || error.message || 'Failed to save agent orchestration settings.'
    messageSeverity.value = 'error'
    await loadSettings()
  } finally {
    saving.value = false
  }
}

function onModeChange(mode) {
  if (mode !== 'custom') {
    Object.assign(settings, applyOrchestrationPreset(mode) || ORCHESTRATION_PRESETS.standard)
  }
  saveSettings()
}

onMounted(loadSettings)
</script>

<style scoped>
.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.section-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  max-width: 42rem;
}

.setting-row {
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.setting-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.setting-label {
  font-size: 0.9375rem;
  font-weight: 500;
}

.setting-hint {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  margin-top: 0.2rem;
}

.mode-description {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  max-width: 42rem;
}

.orchestration-mode-select {
  flex-wrap: wrap;
}

.effective-max-rounds {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.75rem 0.875rem;
  border-radius: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 35%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--app-nested-surface-strong));
}

.effective-max-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.effective-max-value {
  font-size: 1.125rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.effective-max-hint {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  line-height: 1.45;
  max-width: 42rem;
}

.orchestration-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.65rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--app-nested-surface-strong);
}

.summary-label {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.summary-value {
  font-size: 0.9375rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.custom-orchestration {
  padding-top: 0.25rem;
}

.stuck-detection {
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color);
}

.max-select {
  max-width: 8rem;
}
</style>
