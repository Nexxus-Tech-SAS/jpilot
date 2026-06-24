/** JPilot chat roles — keep ids in sync with backend ChatRole / copilot_roles.py */

export const JPILOT_ROLES = [
  {
    id: 'architect',
    label: 'Architect',
    description: 'Plan deployments, designs, and change control windows without a connected appliance.',
    requiresAppliance: false,
    suggestedPaneLabel: 'Plan',
    handoffTarget: 'operator',
    icon: 'pi pi-compass',
    accent: '#9333ea',
    kind: 'builtin',
    capability: 'Plan-only'
  },
  {
    id: 'operator',
    label: 'Operator',
    description: 'Build and change configuration on a connected NetScaler.',
    requiresAppliance: true,
    suggestedPaneLabel: 'Operate',
    handoffTarget: null,
    icon: 'pi pi-cog',
    accent: '#2563eb',
    kind: 'builtin',
    capability: 'Full control'
  },
  {
    id: 'analyst',
    label: 'Analyst',
    description: 'Troubleshoot incidents with read-first checks on a connected appliance.',
    requiresAppliance: true,
    suggestedPaneLabel: 'Analyze',
    handoffTarget: 'operator',
    icon: 'pi pi-search',
    accent: '#10b981',
    kind: 'builtin',
    capability: 'Read-only'
  }
]

/** User-facing capability label per base role (mirrors backend PERSONA_CAPABILITY). */
export const PERSONA_CAPABILITY = {
  architect: 'Plan-only',
  operator: 'Full control',
  analyst: 'Read-only'
}

export function capabilityForRole(roleId) {
  return PERSONA_CAPABILITY[normalizeRoleId(roleId)] || ''
}

/** Accent for installed custom personas in the role picker (distinct from base roles). */
export const CUSTOM_PERSONA_ACCENT = '#f59e0b'

export const DEFAULT_JPILOT_ROLE = 'operator'

/** Persona-first: the default persona for a brand-new chat (before any last-used value). */
export const DEFAULT_PERSONA_ID = 'operator'

/** localStorage key holding the last persona the user selected (global, not per-pane). */
export const LAST_USED_PERSONA_KEY = 'jpilot_last_persona_v1'

export function readLastUsedPersona() {
  try {
    return localStorage.getItem(LAST_USED_PERSONA_KEY) || DEFAULT_PERSONA_ID
  } catch {
    return DEFAULT_PERSONA_ID
  }
}

export function writeLastUsedPersona(personaId) {
  if (!personaId) return
  try {
    localStorage.setItem(LAST_USED_PERSONA_KEY, personaId)
  } catch {
    /* ignore quota / unavailable storage */
  }
}

/** @deprecated Renamed to analyst; kept for persisted sessions. */
const LEGACY_ROLE_ALIASES = { investigator: 'analyst' }

export function normalizeRoleId(roleId) {
  if (!roleId) return DEFAULT_JPILOT_ROLE
  return LEGACY_ROLE_ALIASES[roleId] || roleId
}

export function getRoleById(roleId) {
  const id = normalizeRoleId(roleId)
  return JPILOT_ROLES.find((r) => r.id === id) || JPILOT_ROLES.find((r) => r.id === DEFAULT_JPILOT_ROLE)
}

export function roleRequiresAppliance(roleId) {
  return getRoleById(roleId)?.requiresAppliance !== false
}
