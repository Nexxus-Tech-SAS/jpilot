<template>
  <div class="persona-panel">
    <div class="persona-heading">
      <h2 class="persona-title m-0">Personas</h2>
      <p class="persona-subtitle m-0">
        Personas define how JPilot behaves for each role. Base roles ship with the active
        Knowledge Pack; custom personas can be updated or removed individually.
      </p>
    </div>

    <!-- Base role personas: always present, updateable from here -->
    <section class="persona-section">
      <div class="persona-section-row">
        <h3 class="persona-section-title m-0">Base roles</h3>
        <Tag value="Updateable" severity="secondary" />
      </div>
      <div class="persona-grid">
        <div
          v-for="persona in baseRolePersonas"
          :key="persona.id"
          class="content-panel content-panel-padded persona-card"
        >
          <div class="persona-card-head">
            <span class="persona-icon" :style="{ '--persona-accent': persona.accent }">
              <i :class="persona.icon" />
            </span>
            <div class="persona-card-id">
              <div class="persona-name">{{ persona.label }}</div>
              <code class="persona-role">role: {{ persona.id }}</code>
            </div>
            <Tag :value="persona.version ? `v${persona.version}` : 'Active'" severity="success" />
          </div>
          <p class="persona-desc m-0">{{ persona.description }}</p>
          <div class="persona-card-actions">
            <Button
              v-if="persona.updateAvailable"
              label="Update"
              icon="pi pi-download"
              size="small"
              :loading="busyId === persona.id"
              @click="$emit('update', persona.row)"
            />
            <Button
              v-else
              label="Up to date"
              icon="pi pi-check"
              severity="secondary"
              outlined
              size="small"
              disabled
            />
          </div>
        </div>
      </div>
    </section>

    <!-- Custom personas: installed individually; can be updated or deleted -->
    <section class="persona-section">
      <div class="persona-section-row">
        <h3 class="persona-section-title m-0">Custom personas</h3>
        <Tag :value="`${customPersonas.length} installed`" severity="secondary" />
      </div>

      <div v-if="!customPersonas.length" class="persona-empty-card">
        <i class="pi pi-users persona-empty-icon" />
        <div>
          <p class="persona-empty-title m-0">No custom personas installed</p>
          <p class="persona-empty-copy m-0 mt-1">
            Install personas from the <strong>Blueprint Library</strong> to tailor JPilot for
            specialised roles. They will appear here so you can update or remove them.
          </p>
        </div>
      </div>

      <div v-else class="persona-grid">
        <div
          v-for="persona in customPersonas"
          :key="persona.id"
          class="content-panel content-panel-padded persona-card"
        >
          <div class="persona-card-head">
            <span class="persona-icon persona-icon-custom">
              <i class="pi pi-user" />
            </span>
            <div class="persona-card-id">
              <div class="persona-name">{{ persona.label }}</div>
              <code class="persona-role">role: {{ persona.baseRole || persona.id }}</code>
            </div>
            <Tag :value="persona.version ? `v${persona.version}` : 'Active'" severity="success" />
          </div>
          <p class="persona-desc m-0">{{ persona.description || 'Custom persona installed from the Blueprint Library.' }}</p>
          <div class="persona-card-actions">
            <Button
              v-if="persona.updateAvailable"
              label="Update"
              icon="pi pi-download"
              size="small"
              :loading="busyId === persona.id"
              @click="$emit('update', persona.row)"
            />
            <Button
              label="Delete"
              icon="pi pi-trash"
              severity="danger"
              outlined
              size="small"
              :loading="busyId === persona.id"
              @click="(event) => $emit('delete', event, persona.row)"
            />
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { JPILOT_ROLES } from '../config/jpilotRoles.js'

const props = defineProps({
  // Persona blueprint rows from the catalog (type === 'persona'), each carrying
  // install state + version (installedVersion / catalogVersion / updateAvailable).
  personas: { type: Array, default: () => [] },
  // skillId currently being installed/updated/removed (drives per-card loading state).
  busyId: { type: String, default: '' }
})

defineEmits(['update', 'delete'])

const BASE_ROLE_IDS = new Set(JPILOT_ROLES.map((r) => r.id))

const rowById = computed(() => {
  const map = new Map()
  for (const row of props.personas) {
    if (row?.skillId) map.set(row.skillId, row)
  }
  return map
})

// The three base roles are always shown; enrich each with version / update state
// from a matching catalog row when one exists.
const baseRolePersonas = computed(() =>
  JPILOT_ROLES.map((role) => {
    const row = rowById.value.get(role.id) || null
    return {
      id: role.id,
      label: role.label,
      description: role.description,
      icon: role.icon,
      accent: role.accent,
      version: row?.installedVersion || null,
      updateAvailable: Boolean(row?.updateAvailable && row?.installable),
      row
    }
  })
)

// Custom personas = installed persona rows that aren't one of the base roles,
// de-duplicated by display label so identical installs only appear once.
const customPersonas = computed(() => {
  const seenLabels = new Set()
  const result = []
  for (const row of props.personas) {
    const id = row?.skillId
    if (!id || BASE_ROLE_IDS.has(id) || !row.installed) continue
    const labelKey = (row.label || '').trim().toLowerCase()
    if (labelKey && seenLabels.has(labelKey)) continue
    if (labelKey) seenLabels.add(labelKey)
    result.push({
      id,
      label: row.label || id,
      description: row.description,
      baseRole: row.baseRole || null,
      version: row.installedVersion || null,
      updateAvailable: Boolean(row.updateAvailable && row.installable),
      row
    })
  }
  return result.sort((a, b) => a.label.localeCompare(b.label))
})
</script>

<style scoped>
.persona-panel {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.persona-heading {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.persona-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.persona-subtitle {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  max-width: 46rem;
}

.persona-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.persona-section-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.persona-section-title {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
  gap: 0.75rem;
}

.persona-card {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.persona-card-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.persona-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  color: var(--persona-accent, var(--p-primary-color));
  background: color-mix(in srgb, var(--persona-accent, var(--p-primary-color)) 14%, transparent);
  flex-shrink: 0;
}

.persona-icon-custom {
  --persona-accent: #f59e0b;
}

.persona-card-id {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  margin-right: auto;
  min-width: 0;
}

.persona-name {
  font-weight: 600;
  color: var(--p-text-color);
}

.persona-role {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.persona-desc {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  flex: 1;
}

.persona-card-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: auto;
}

.persona-empty-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--content-radius);
}

.persona-empty-icon {
  font-size: 1.75rem;
  color: var(--p-text-muted-color);
}

.persona-empty-title {
  font-weight: 600;
  color: var(--p-text-color);
}

.persona-empty-copy {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  max-width: 38rem;
}
</style>
