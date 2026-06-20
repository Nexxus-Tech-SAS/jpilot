<template>
  <div class="bw-root">
    <div class="bw-stage" :class="{ 'bw-stage-blueprints': panelView === 'blueprints' }">
      <p class="bw-eyebrow">JPilot · Beta</p>
      <h1 class="bw-greeting">{{ panelGreeting }}</h1>
      <p class="bw-subtitle">{{ panelSubtitle }}</p>

      <div class="bw-panel-stage">
        <Transition name="bw-swap" mode="out-in">
          <ul v-if="panelView === 'personas'" key="personas" class="bw-personas" role="list">
            <li v-for="(persona, index) in personas" :key="persona.id" :style="{ '--stagger': `${index * 60}ms` }">
              <button
                type="button"
                class="bw-persona"
                :class="{ 'bw-persona-active': persona.id === activeRole }"
                :style="{ '--persona-accent': persona.accent }"
                :disabled="disabled"
                @click="onPersonaClick(persona.id)"
              >
                <span class="bw-persona-icon"><i :class="persona.icon" aria-hidden="true" /></span>
                <span class="bw-persona-name">{{ persona.label }}</span>
                <span class="bw-persona-desc">{{ persona.description }}</span>
              </button>
            </li>
          </ul>

          <div v-else-if="panelView === 'skills'" key="skills" class="bw-skills">
            <div class="bw-skills-role" :style="{ '--persona-accent': activePersona?.accent }">
              <span class="bw-skills-role-icon"><i :class="activePersona?.icon" aria-hidden="true" /></span>
              <span class="bw-skills-role-label">{{ activePersona?.label }}</span>
            </div>

            <ul class="bw-skills-list" role="list">
              <li
                v-for="(skill, index) in activeSkills"
                :key="skill.id"
                :style="{ '--stagger': `${index * 70}ms` }"
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

            <button
              type="button"
              class="bw-browse-blueprints"
              :style="{ '--persona-accent': activePersona?.accent }"
              :disabled="disabled || blueprintsLoading"
              @click="openBlueprints"
            >
              <i class="pi pi-book" aria-hidden="true" />
              Browse blueprints
            </button>

            <button type="button" class="bw-back" :disabled="disabled" @click="backToPersonas">
              <i class="pi pi-arrow-left" aria-hidden="true" />
              Choose a different role
            </button>
          </div>

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

      <p v-if="!ready" class="bw-note bw-note-warn">
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
const panelView = ref('personas')
const skillsRole = ref(null)
const installedBlueprints = ref([])
const blueprintsLoading = ref(false)

const activePersona = computed(() => (skillsRole.value ? getRoleById(skillsRole.value) : null))
const activeSkills = computed(() => (skillsRole.value ? getBetaPersonaSkills(skillsRole.value) : []))
const roleBlueprints = computed(() =>
  skillsRole.value ? filterInstalledBlueprintsForRole(installedBlueprints.value, skillsRole.value) : []
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
  if (skillsRole.value && PERSONA_SKILL_COPY[skillsRole.value]) {
    return PERSONA_SKILL_COPY[skillsRole.value].greeting
  }
  if (skillsRole.value) return `How can ${activePersona.value?.label} help?`
  return baseGreeting
})

const panelSubtitle = computed(() => {
  if (panelView.value === 'blueprints') {
    return BETA_BLUEPRINTS_COPY.subtitle(activePersona.value?.label || 'this role')
  }
  if (skillsRole.value && PERSONA_SKILL_COPY[skillsRole.value]) {
    return PERSONA_SKILL_COPY[skillsRole.value].subtitle
  }
  if (skillsRole.value) {
    return 'Pick an action below, or type your own request.'
  }
  return 'Pick where you want to start — or just type below.'
})

function onPersonaClick(roleId) {
  emit('select-persona', { roleId, deferFocus: getBetaPersonaSkills(roleId).length > 0 })
  if (getBetaPersonaSkills(roleId).length > 0) {
    skillsRole.value = roleId
    panelView.value = 'skills'
  }
}

function onSkillClick(skill) {
  if (!skillsRole.value) return
  emit('select-skill', {
    roleId: skillsRole.value,
    skillId: skill.id,
    prompt: skill.prompt,
    source: 'starter'
  })
}

function onBlueprintClick(blueprint) {
  if (!skillsRole.value) return
  emit('select-skill', {
    roleId: skillsRole.value,
    skillId: blueprint.skillId,
    prompt: blueprintStarterPrompt(blueprint),
    source: 'blueprint'
  })
}

async function openBlueprints() {
  if (!skillsRole.value) return
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
  panelView.value = 'skills'
}

function backToPersonas() {
  panelView.value = 'personas'
  skillsRole.value = null
}

watch(
  () => props.activeRole,
  (roleId) => {
    if (!skillsRole.value || roleId === skillsRole.value) return
    if (getBetaPersonaSkills(roleId).length > 0) {
      skillsRole.value = roleId
      if (panelView.value === 'personas') {
        panelView.value = 'skills'
      }
      return
    }
    panelView.value = 'personas'
    skillsRole.value = null
  }
)
</script>

<style scoped>
.bw-root {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.bw-stage {
  max-width: 52rem;
  width: 100%;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  animation: bw-rise 300ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

.bw-stage-blueprints {
  max-width: min(60rem, 100%);
  text-align: left;
  align-items: stretch;
}

.bw-panel-stage {
  width: 100%;
  min-height: 12rem;
}

.bw-eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.bw-greeting {
  margin: 0;
  font-size: clamp(1.6rem, 1.1rem + 2.2vw, 2.6rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--p-text-color);
  transition: opacity 0.24s ease;
}

.bw-subtitle {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
  transition: opacity 0.24s ease;
}

.bw-personas {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
}

.bw-personas > li {
  animation: bw-rise 300ms cubic-bezier(0.4, 0, 0.2, 1) both;
  animation-delay: var(--stagger, 0ms);
}

.bw-persona {
  background: color-mix(in srgb, var(--p-content-background) 60%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  border-radius: 1rem;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  text-align: left;
  padding: 1.1rem 1.15rem;
  cursor: pointer;
  width: 100%;
  box-shadow: 0 8px 28px rgba(2, 6, 23, 0.06);
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  color: inherit;
  font: inherit;
}

.bw-persona:hover,
.bw-persona:focus-visible {
  transform: translateY(-3px);
  box-shadow: 0 14px 34px rgba(2, 6, 23, 0.1);
  border-color: color-mix(in srgb, var(--persona-accent) 55%, transparent);
  outline: none;
}

.bw-persona:hover .bw-persona-icon,
.bw-persona:focus-visible .bw-persona-icon {
  transform: scale(1.08);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--persona-accent) 12%, transparent);
}

.bw-persona-active {
  border-color: var(--persona-accent);
  box-shadow:
    0 0 0 1px var(--persona-accent) inset,
    0 14px 34px rgba(2, 6, 23, 0.1);
}

.bw-persona:disabled {
  opacity: 0.6;
  pointer-events: none;
}

.bw-persona-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 14%, transparent);
  animation: bw-float 3.2s ease-in-out infinite;
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.bw-personas > li:nth-child(2) .bw-persona-icon {
  animation-delay: 0.4s;
}

.bw-personas > li:nth-child(3) .bw-persona-icon {
  animation-delay: 0.8s;
}

.bw-persona-name {
  font-weight: 650;
  font-size: 1rem;
  color: var(--p-text-color);
}

.bw-persona-desc {
  color: var(--p-text-muted-color);
  font-size: 0.82rem;
  line-height: 1.4;
}

.bw-skills {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 1rem;
  width: 100%;
  margin-top: 0.25rem;
  animation: bw-rise 320ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

.bw-skills-role {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  align-self: center;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--persona-accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--persona-accent) 28%, transparent);
  color: var(--persona-accent);
  font-size: 0.8125rem;
  font-weight: 650;
}

.bw-skills-role-icon {
  display: grid;
  place-items: center;
  font-size: 0.95rem;
}

.bw-skills-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
  width: 100%;
}

.bw-skills-list > li {
  animation: bw-rise 300ms cubic-bezier(0.4, 0, 0.2, 1) both;
  animation-delay: var(--stagger, 0ms);
}

.bw-skill {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  width: 100%;
  text-align: left;
  padding: 0.95rem 1rem;
  border-radius: 0.75rem;
  cursor: pointer;
  color: inherit;
  font: inherit;
  background: color-mix(in srgb, var(--p-content-background) 60%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  box-shadow: 0 8px 28px rgba(2, 6, 23, 0.06);
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.bw-skill:hover,
.bw-skill:focus-visible {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--persona-accent) 50%, transparent);
  box-shadow: 0 12px 32px rgba(2, 6, 23, 0.1);
  outline: none;
}

.bw-skill:disabled {
  opacity: 0.6;
  pointer-events: none;
}

.bw-skill-icon {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.65rem;
  display: grid;
  place-items: center;
  font-size: 1rem;
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 14%, transparent);
}

.bw-skill-copy {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
}

.bw-skill-name {
  font-weight: 650;
  font-size: 0.95rem;
  color: var(--p-text-color);
}

.bw-skill-desc {
  font-size: 0.8rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
}

.bw-skill-arrow {
  flex-shrink: 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  transition: transform 0.2s ease, color 0.2s ease;
}

.bw-skill:hover .bw-skill-arrow,
.bw-skill:focus-visible .bw-skill-arrow {
  transform: translateX(3px);
  color: var(--persona-accent);
}

.bw-browse-blueprints {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  cursor: pointer;
  font: inherit;
  font-size: 0.875rem;
  font-weight: 650;
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 10%, transparent);
  border: 1px dashed color-mix(in srgb, var(--persona-accent) 38%, transparent);
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    background 0.22s ease,
    border-color 0.22s ease;
}

.bw-browse-blueprints:hover,
.bw-browse-blueprints:focus-visible {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--persona-accent) 16%, transparent);
  border-color: color-mix(in srgb, var(--persona-accent) 55%, transparent);
  outline: none;
}

.bw-browse-blueprints:disabled {
  opacity: 0.6;
  pointer-events: none;
}

.bw-back {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.25rem;
  padding: 0.35rem 0.65rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease;
}

.bw-back:hover,
.bw-back:focus-visible {
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-surface-100) 70%, transparent);
  outline: none;
}

:global(.app-dark) .bw-back:hover,
:global(.app-dark) .bw-back:focus-visible {
  background: color-mix(in srgb, var(--p-surface-800) 70%, transparent);
}

.bw-note {
  margin: 0.25rem 0 0;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.bw-note-warn {
  color: var(--p-orange-600);
}

:global(.app-dark) .bw-note-warn {
  color: var(--p-orange-300);
}

:global(html.app-dark) .bw-persona,
:global(html.app-dark) .bw-skill {
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
}

:global(html.app-dark) .bw-persona:hover,
:global(html.app-dark) .bw-persona:focus-visible,
:global(html.app-dark) .bw-persona-active,
:global(html.app-dark) .bw-skill:hover,
:global(html.app-dark) .bw-skill:focus-visible {
  box-shadow:
    0 0 0 1px var(--persona-accent) inset,
    0 14px 34px rgba(0, 0, 0, 0.32);
}

.bw-swap-enter-active,
.bw-swap-leave-active {
  transition:
    opacity 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.bw-swap-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.bw-swap-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes bw-float {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-4px);
  }
}

@keyframes bw-rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 720px) {
  .bw-personas {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .bw-persona-icon,
  .bw-stage,
  .bw-personas > li,
  .bw-skills,
  .bw-skills-list > li,
  .bw-swap-enter-active,
  .bw-swap-leave-active {
    animation: none;
    transition: none;
  }

  .bw-persona:hover,
  .bw-persona:focus-visible,
  .bw-skill:hover,
  .bw-skill:focus-visible,
  .bw-browse-blueprints:hover,
  .bw-browse-blueprints:focus-visible {
    transform: none;
  }

  .bw-persona:hover .bw-persona-icon,
  .bw-persona:focus-visible .bw-persona-icon {
    transform: none;
  }

  .bw-skill:hover .bw-skill-arrow,
  .bw-skill:focus-visible .bw-skill-arrow {
    transform: none;
  }
}
</style>
