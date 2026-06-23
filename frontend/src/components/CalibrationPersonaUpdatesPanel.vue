<template>
  <div class="persona-panel">
    <div class="persona-heading">
      <h2 class="persona-title m-0">Personas</h2>
      <p class="persona-subtitle m-0">
        Personas define how JPilot behaves for each role. They are delivered as part of the active
        Knowledge Pack and applied automatically per chat role.
      </p>
    </div>

    <!-- Installed personas (sourced from the active knowledge pack / role config) -->
    <section class="persona-section">
      <h3 class="persona-section-title">Installed personas</h3>
      <div class="persona-grid">
        <div
          v-for="persona in installedPersonas"
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
            <Tag value="Active" severity="success" />
          </div>
          <p class="persona-desc m-0">{{ persona.description }}</p>
          <div class="persona-card-actions">
            <Button
              label="Disable"
              icon="pi pi-pause"
              severity="secondary"
              outlined
              size="small"
              disabled
              v-tooltip="'Personas are bundled with the active Knowledge Pack and cannot be toggled individually yet.'"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- Downloaded persona updates.
         TODO(backend): there is currently no API that lists individually downloaded persona
         updates — persona content ships inside the Knowledge Pack (personas/<role>/). When a
         dedicated persona-update feed exists, populate `personaUpdates` and wire the actions
         (Apply/Enable, Update, Remove) to it. Until then this stays as an honest empty state. -->
    <section class="persona-section">
      <div class="persona-section-row">
        <h3 class="persona-section-title m-0">Persona updates</h3>
        <Tag value="Managed via Knowledge Pack" severity="secondary" />
      </div>

      <div v-if="!personaUpdates.length" class="persona-empty-card">
        <i class="pi pi-users persona-empty-icon" />
        <div>
          <p class="persona-empty-title m-0">No standalone persona updates</p>
          <p class="persona-empty-copy m-0 mt-1">
            Persona behaviour is updated together with the Knowledge Pack. Check the
            <strong>Knowledge Packs</strong> tab to update or roll back persona content.
          </p>
        </div>
      </div>

      <DataTable v-else :value="personaUpdates" striped-rows data-key="id" class="persona-table">
        <Column field="name" header="Persona" />
        <Column field="role" header="Target role" />
        <Column field="scope" header="Scope" />
        <Column field="version" header="Version" />
        <Column header="Status">
          <template #body="{ data }">
            <Tag :value="data.status" :severity="data.statusSeverity || 'secondary'" />
          </template>
        </Column>
        <Column header="Actions">
          <template #body="{ data }">
            <div class="persona-row-actions">
              <Button label="Apply" icon="pi pi-check" size="small" @click="$emit('apply', data)" />
              <Button label="Update" icon="pi pi-download" size="small" severity="secondary" outlined @click="$emit('update', data)" />
              <Button label="Remove" icon="pi pi-trash" size="small" severity="danger" text @click="$emit('remove', data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </section>
  </div>
</template>

<script setup>
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { JPILOT_ROLES } from '../config/jpilotRoles.js'

defineEmits(['apply', 'update', 'remove'])

const installedPersonas = JPILOT_ROLES

// Placeholder until a persona-update feed exists (see TODO in template).
const personaUpdates = []
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
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
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

.persona-row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
</style>
