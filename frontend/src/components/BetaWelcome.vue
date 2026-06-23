<template>
  <div class="bw-root">
    <div class="bw-stage" :class="{ 'bw-stage-blueprints': panelView === 'blueprints' }">
      <!-- Hero: compact greeting only -->
      <h1 class="bw-greeting">{{ panelGreeting }}</h1>
      <p class="bw-subtitle">{{ panelSubtitle }}</p>

      <div class="bw-panel-stage">
        <Transition name="bw-swap" mode="out-in">
          <!-- UNIFIED ROLE + SKILLS VIEW (replaces the old two-stage personas→skills) -->
          <div v-if="panelView === 'personas' || panelView === 'skills'" key="unified" class="bw-unified">

            <!-- Horizontal segmented role selector -->
            <div class="bw-role-tabs" role="group" aria-label="Select role">
              <button
                v-for="(persona, index) in personas"
                :key="persona.id"
                type="button"
                class="bw-role-tab"
                :class="{ 'bw-role-tab-active': selectedRole === persona.id }"
                :style="{ '--persona-accent': persona.accent, '--stagger': `${index * 50}ms` }"
                :disabled="disabled"
                :aria-pressed="selectedRole === persona.id"
                :aria-label="persona.label"
                @click="onRoleTabClick(persona.id)"
              >
                <span class="bw-role-tab-icon">
                  <i :class="persona.icon" aria-hidden="true" />
                </span>
                <span class="bw-role-tab-label">{{ persona.label }}</span>
              </button>
            </div>

            <!-- Contextual role description -->
            <p
              v-if="selectedRole && activePersona"
              class="bw-role-desc"
              :style="{ '--persona-accent': activePersona.accent }"
            >
              {{ activePersona.description }}
            </p>

            <!-- Quick actions (starter skills for the selected role) -->
            <ul
              v-if="activeSkills.length"
              class="bw-skills-list"
              role="list"
              aria-label="Quick actions"
            >
              <li
                v-for="(skill, index) in activeSkills"
                :key="skill.id"
                :style="{ '--stagger': `${index * 60}ms` }"
              >
                <button
                  type="button"
                  class="bw-skill"
                  :style="{ '--persona-accent': activePersona?.accent }"
                  :disabled="disabled"
                  @click="onSkillClick(skill)"
                >
                  <span class="bw-skill-icon"><i :class="skill.icon" aria-hidden="true" /></span>
                  <span class="bw-skill-copy">
                    <span class="bw-skill-name">{{ skill.label }}</span>
                    <span class="bw-skill-desc">{{ skill.description }}</span>
                  </span>
                  <i class="pi pi-arrow-right bw-skill-arrow" aria-hidden="true" />
                </button>
              </li>
            </ul>

            <!-- Empty state: no skills for this role -->
            <p v-else-if="selectedRole" class="bw-no-skills-hint">
              Type your request below, or browse blueprints for pre-built workflows.
            </p>

            <!-- Browse blueprints button -->
            <button
              v-if="selectedRole"
              type="button"
              class="bw-browse-blueprints"
              :style="{ '--persona-accent': activePersona?.accent }"
              :disabled="disabled || blueprintsLoading"
              @click="openBlueprints"
            >
              <i class="pi pi-book" aria-hidden="true" />
              Browse blueprints
            </button>
          </div>

          <!-- Blueprints panel (unchanged) -->
          <BetaBlueprintBrowser
            v-else
            key="blueprints"
            :blueprints="roleBlueprints"
            :loading="blueprintsLoading"
            :accent="activePersona?.accent"
            :role-label="activePersona?.label || ''"
            :disabled="disabled"
            @select="onBlueprintClick"
            @back="backToSkills"
          />
        </Transition>
      </div>

      <!-- Provider note -->
      <p v-if="!ready" class="bw-note bw-note-warn">
        <i class="pi pi-exclamation-triangle" aria-hidden="true" />
        No LLM assigned — configure one in Settings → AI Providers.
      </p>
      <p v-else-if="providerName" class="bw-note">
        <i class="pi pi-sparkles" aria-hidden="true" />
        Using <strong>{{ providerName }}</strong>
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import BetaBlueprintBrowser from './BetaBlueprintBrowser.vue'
import { JPILOT_ROLES, getRoleById } from '../config/jpilotRoles'
import { getBetaPersonaSkills } from '../config/betaPersonaSkills'
import { listInstalledCalibrations } from '../services/calibrationSync'
import {
  BETA_BLUEPRINTS_COPY,
  blueprintStarterPrompt,
  filterInstalledBlueprintsForRole
} from '../utils/betaInstalledBlueprints'

const props = defineProps({
  activeRole: { type: String, required: true },
  providerName: { type: String, default: '' },
  ready: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['select-persona', 'select-skill'])

const personas = JPILOT_ROLES

// Single selected role drives the unified view
const selectedRole = ref(props.activeRole || null)
const panelView = ref('personas')
const installedBlueprints = ref([])
const blueprintsLoading = ref(false)

const activePersona = computed(() => (selectedRole.value ? getRoleById(selectedRole.value) : null))
const activeSkills = computed(() => (selectedRole.value ? getBetaPersonaSkills(selectedRole.value) : []))
const roleBlueprints = computed(() =>
  selectedRole.value ? filterInstalledBlueprintsForRole(installedBlueprints.value, selectedRole.value) : []
)

function buildGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning — how can I help?'
  if (hour < 17) return 'Good afternoon — how can I help?'
  if (hour < 22) return 'Good evening — how can I help?'
  return 'How can I help you today?'
}

const baseGreeting = buildGreeting()

const PERSONA_SKILL_COPY = {
  architect: {
    greeting: 'What are you planning?',
    subtitle: 'Pick a starting point — Architect will guide discovery and deliverables.'
  },
  operator: {
    greeting: 'What do you want to build?',
    subtitle: 'Pick a starting point — connect an appliance first if you need live changes.'
  },
  analyst: {
    greeting: 'What should we investigate?',
    subtitle: 'Pick a starting point — Analyst runs read-first checks before any writes.'
  }
}

const panelGreeting = computed(() => {
  if (panelView.value === 'blueprints') return BETA_BLUEPRINTS_COPY.greeting
  if (selectedRole.value && PERSONA_SKILL_COPY[selectedRole.value]) {
    return PERSONA_SKILL_COPY[selectedRole.value].greeting
  }
  if (selectedRole.value) return `How can ${activePersona.value?.label} help?`
  return baseGreeting
})

const panelSubtitle = computed(() => {
  if (panelView.value === 'blueprints') {
    return BETA_BLUEPRINTS_COPY.subtitle(activePersona.value?.label || 'this role')
  }
  if (selectedRole.value && PERSONA_SKILL_COPY[selectedRole.value]) {
    return PERSONA_SKILL_COPY[selectedRole.value].subtitle
  }
  if (selectedRole.value) {
    return 'Pick an action below, or type your own request.'
  }
  return 'Pick where you want to start — or just type below.'
})

function onRoleTabClick(roleId) {
  selectedRole.value = roleId
  if (panelView.value !== 'personas' && panelView.value !== 'skills') {
    panelView.value = 'personas'
  }
  emit('select-persona', { roleId, deferFocus: getBetaPersonaSkills(roleId).length > 0 })
}

function onSkillClick(skill) {
  if (!selectedRole.value) return
  emit('select-skill', {
    roleId: selectedRole.value,
    skillId: skill.id,
    prompt: skill.prompt,
    source: 'starter'
  })
}

function onBlueprintClick(blueprint) {
  if (!selectedRole.value) return
  emit('select-skill', {
    roleId: selectedRole.value,
    skillId: blueprint.skillId,
    prompt: blueprintStarterPrompt(blueprint),
    source: 'blueprint'
  })
}

async function openBlueprints() {
  if (!selectedRole.value) return
  panelView.value = 'blueprints'
  blueprintsLoading.value = true
  try {
    installedBlueprints.value = await listInstalledCalibrations()
  } catch {
    installedBlueprints.value = []
  } finally {
    blueprintsLoading.value = false
  }
}

function backToSkills() {
  panelView.value = 'personas'
}

watch(
  () => props.activeRole,
  (roleId) => {
    if (!roleId || roleId === selectedRole.value) return
    selectedRole.value = roleId
    if (panelView.value === 'blueprints') {
      panelView.value = 'personas'
    }
  }
)
</script>

<style scoped>
.bw-root {
  height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1rem 1rem 1.5rem;
}

.bw-stage {
  max-width: 48rem;
  width: 100%;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  animation: bw-rise 300ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

.bw-stage-blueprints {
  max-width: min(60rem, 100%);
  text-align: left;
  align-items: stretch;
}

.bw-panel-stage {
  width: 100%;
}

/* Hero */
.bw-greeting {
  margin: 0;
  font-size: clamp(1.35rem, 0.9rem + 2vw, 2rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--p-text-color);
  transition: opacity 0.24s ease;
}

.bw-subtitle {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  transition: opacity 0.24s ease;
}

/* Unified view */
.bw-unified {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.85rem;
  width: 100%;
  animation: bw-rise 280ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

/* ---- Horizontal segmented role tabs ---- */
.bw-role-tabs {
  display: flex;
  gap: 0.35rem;
  width: 100%;
  padding: 0.3rem;
  border-radius: 0.85rem;
  background: color-mix(in srgb, var(--p-content-background) 70%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  box-shadow: 0 2px 8px rgba(2, 6, 23, 0.05);
}

.bw-role-tab {
  flex: 1 1 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.5rem 0.5rem;
  border: 0;
  border-radius: 0.6rem;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
  font: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  transition:
    background 0.2s cubic-bezier(0.4, 0, 0.2, 1),
    color 0.2s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  min-width: 0;
  animation: bw-rise 260ms cubic-bezier(0.4, 0, 0.2, 1) both;
  animation-delay: var(--stagger, 0ms);
}

.bw-role-tab:hover:not(:disabled):not(.bw-role-tab-active) {
  background: color-mix(in srgb, var(--persona-accent) 10%, transparent);
  color: var(--persona-accent);
}

.bw-role-tab:focus-visible {
  outline: 2px solid var(--persona-accent);
  outline-offset: 2px;
}

.bw-role-tab-active {
  background: color-mix(in srgb, var(--persona-accent) 16%, var(--p-content-background));
  color: var(--persona-accent);
  box-shadow: 0 2px 10px color-mix(in srgb, var(--persona-accent) 22%, transparent);
}

.bw-role-tab:disabled {
  opacity: 0.6;
  pointer-events: none;
}

.bw-role-tab-icon {
  display: grid;
  place-items: center;
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 0.45rem;
  font-size: 0.9rem;
  flex-shrink: 0;
  background: color-mix(in srgb, var(--persona-accent) 12%, transparent);
  color: var(--persona-accent);
  transition: transform 0.2s ease;
}

.bw-role-tab-active .bw-role-tab-icon {
  transform: scale(1.08);
}

.bw-role-tab-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  letter-spacing: -0.01em;
}

/* ---- Role description ---- */
.bw-role-desc {
  margin: 0;
  padding: 0.5rem 0.75rem;
  border-radius: 0.65rem;
  background: color-mix(in srgb, var(--persona-accent) 7%, transparent);
  border: 1px solid color-mix(in srgb, var(--persona-accent) 18%, transparent);
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  text-align: left;
  line-height: 1.45;
  animation: bw-rise 220ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

/* ---- Skills list ---- */
.bw-skills-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.55rem;
  width: 100%;
}

.bw-skills-list > li {
  animation: bw-rise 280ms cubic-bezier(0.4, 0, 0.2, 1) both;
  animation-delay: var(--stagger, 0ms);
}

.bw-skill {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  text-align: left;
  padding: 0.75rem 0.85rem;
  border-radius: 0.75rem;
  cursor: pointer;
  color: inherit;
  font: inherit;
  background: color-mix(in srgb, var(--p-content-background) 72%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  box-shadow: 0 2px 8px rgba(2, 6, 23, 0.05);
  transition:
    transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

.bw-skill:hover,
.bw-skill:focus-visible {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--persona-accent) 48%, transparent);
  box-shadow: 0 8px 20px rgba(2, 6, 23, 0.09);
  outline: none;
}

.bw-skill:disabled {
  opacity: 0.6;
  pointer-events: none;
}

.bw-skill-icon {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 0.55rem;
  display: grid;
  place-items: center;
  font-size: 0.9rem;
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 14%, transparent);
}

.bw-skill-copy {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
  flex: 1;
}

.bw-skill-name {
  font-weight: 650;
  font-size: 0.9rem;
  color: var(--p-text-color);
}

.bw-skill-desc {
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
}

.bw-skill-arrow {
  flex-shrink: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  transition: transform 0.18s ease, color 0.18s ease;
}

.bw-skill:hover .bw-skill-arrow,
.bw-skill:focus-visible .bw-skill-arrow {
  transform: translateX(3px);
  color: var(--persona-accent);
}

/* No skills hint */
.bw-no-skills-hint {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  text-align: center;
}

/* ---- Browse blueprints ---- */
.bw-browse-blueprints {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  width: 100%;
  padding: 0.65rem 0.85rem;
  border-radius: 0.75rem;
  cursor: pointer;
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 650;
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 8%, transparent);
  border: 1px dashed color-mix(in srgb, var(--persona-accent) 35%, transparent);
  transition:
    transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    background 0.18s ease,
    border-color 0.18s ease;
}

.bw-browse-blueprints:hover,
.bw-browse-blueprints:focus-visible {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--persona-accent) 14%, transparent);
  border-color: color-mix(in srgb, var(--persona-accent) 52%, transparent);
  outline: none;
}

.bw-browse-blueprints:disabled {
  opacity: 0.6;
  pointer-events: none;
}

/* ---- Provider note ---- */
.bw-note {
  margin: 0.15rem 0 0;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}

.bw-note-warn {
  color: var(--p-orange-600);
}

:global(.app-dark) .bw-note-warn {
  color: var(--p-orange-300);
}

/* ---- Dark-mode elevations ---- */
:global(html.app-dark) .bw-skill {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.22);
}

:global(html.app-dark) .bw-skill:hover,
:global(html.app-dark) .bw-skill:focus-visible {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

:global(html.app-dark) .bw-role-tabs {
  background: color-mix(in srgb, var(--p-surface-800) 80%, transparent);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}

/* ---- Transitions ---- */
.bw-swap-enter-active,
.bw-swap-leave-active {
  transition:
    opacity 0.24s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.24s cubic-bezier(0.4, 0, 0.2, 1);
}

.bw-swap-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.bw-swap-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ---- Keyframes ---- */
@keyframes bw-rise {
  from {
    opacity: 0;
    transform: translateY(6px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

/* ---- Mobile overrides ---- */
@media (max-width: 991px) {
  .bw-root {
    padding: 0.75rem 0.75rem 1rem;
    align-items: flex-start;
  }

  .bw-stage {
    gap: 0.5rem;
  }

  .bw-greeting {
    font-size: clamp(1.2rem, 0.85rem + 2.5vw, 1.6rem);
  }

  .bw-role-tab {
    font-size: 0.8125rem;
    padding: 0.45rem 0.35rem;
    gap: 0.35rem;
  }

  .bw-role-tab-icon {
    width: 1.45rem;
    height: 1.45rem;
    font-size: 0.8rem;
  }

  .bw-skill {
    padding: 0.7rem 0.75rem;
  }
}

/* ---- Reduced motion ---- */
@media (prefers-reduced-motion: reduce) {
  .bw-stage,
  .bw-unified,
  .bw-role-tab,
  .bw-skills-list > li,
  .bw-role-desc,
  .bw-swap-enter-active,
  .bw-swap-leave-active {
    animation: none;
    transition: none;
  }

  .bw-skill:hover,
  .bw-skill:focus-visible,
  .bw-browse-blueprints:hover,
  .bw-browse-blueprints:focus-visible {
    transform: none;
  }

  .bw-skill:hover .bw-skill-arrow,
  .bw-skill:focus-visible .bw-skill-arrow {
    transform: none;
  }

  .bw-role-tab-active .bw-role-tab-icon {
    transform: none;
  }
}
</style>
