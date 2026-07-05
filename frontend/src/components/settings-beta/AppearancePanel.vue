<template>
  <div class="flex flex-column gap-4">
    <div class="content-panel content-panel-padded">
      <h2 class="section-title">Interface</h2>
      <p class="section-copy">
        Choose how JPilot looks. The new interface is a full redesign — animated, faster to
        navigate, and built for tablets and phones.
      </p>

      <div class="flex flex-column gap-4 mt-4">
        <div class="flex align-items-center justify-content-between gap-3 setting-row">
          <div>
            <div class="setting-label label-with-tag">
              New JPilot interface
              <Tag value="Beta" class="beta-tag" />
            </div>
            <div class="setting-hint">
              Redesigned, animated, mobile-friendly UI (beta preview). Your data, conversations
              and settings are unaffected — switch back anytime.
            </div>
          </div>
          <ToggleSwitch v-model="uiV2" aria-label="New JPilot interface" />
        </div>

        <Transition name="pill-hint">
          <div v-if="uiV2" class="setting-row">
            <div class="setting-hint pill-note">
              <i class="pi pi-sparkles" aria-hidden="true"></i>
              <span>
                You can also leave the new interface anytime from the
                <strong>New UI · Beta</strong> pill inside it.
              </span>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <div class="content-panel content-panel-padded">
      <h2 class="section-title">Theme</h2>
      <p class="section-copy">Light or dark — applies instantly to both interfaces.</p>

      <div class="flex flex-column gap-4 mt-4">
        <div class="flex align-items-center justify-content-between gap-3 flex-wrap setting-row">
          <div>
            <div class="setting-label">Color scheme</div>
            <div class="setting-hint">Stays in sync with the theme toggle in the top bar</div>
          </div>
          <SelectButton
            v-model="theme"
            :options="themeOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            aria-label="Color scheme"
            @update:model-value="onThemeSelect"
          >
            <template #option="{ option }">
              <i :class="option.icon" aria-hidden="true"></i>
              <span>{{ option.label }}</span>
            </template>
          </SelectButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { useUiVersion, setUiVersion, UI_V2, UI_CLASSIC } from '../../services/uiVersion'
import { getTheme, setTheme } from '../../services/theme'

// Reactive service ref: stays correct even while this panel sits in KeepAlive,
// including when the shell is swapped from the "New UI · Beta" pill.
const uiVersion = useUiVersion()

const uiV2 = computed({
  get: () => uiVersion.value === UI_V2,
  set: (checked) => setUiVersion(checked ? UI_V2 : UI_CLASSIC)
})

const themeOptions = [
  { label: 'Light', value: 'light', icon: 'pi pi-sun' },
  { label: 'Dark', value: 'dark', icon: 'pi pi-moon' }
]

const theme = ref(getTheme())

function onThemeSelect(value) {
  if (value === 'light' || value === 'dark') setTheme(value)
}

// Keep the SelectButton in sync when the theme changes elsewhere (top-bar toggle).
function onThemeChanged(event) {
  theme.value = event.detail === 'dark' ? 'dark' : 'light'
}

onMounted(() => {
  theme.value = getTheme()
  window.addEventListener('jpilot-theme-change', onThemeChanged)
})

onBeforeUnmount(() => {
  window.removeEventListener('jpilot-theme-change', onThemeChanged)
})
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

.label-with-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.beta-tag {
  background: linear-gradient(135deg, #22d3ee 0%, #6366f1 100%);
  color: #ffffff;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.pill-note {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-top: 0;
}

.pill-note .pi {
  color: var(--p-primary-color);
  font-size: 0.8125rem;
}

.pill-hint-enter-active,
.pill-hint-leave-active {
  transition:
    opacity var(--v2-dur, 250ms) var(--v2-ease, ease),
    transform var(--v2-dur, 250ms) var(--v2-ease, ease);
}

.pill-hint-enter-from,
.pill-hint-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (prefers-reduced-motion: reduce) {
  .pill-hint-enter-active,
  .pill-hint-leave-active {
    transition: none;
  }
}
</style>
