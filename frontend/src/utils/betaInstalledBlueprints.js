/**
 * Installed calibration blueprints for Chat Beta welcome browse flow.
 */

import {
  blueprintFilterOptions,
  enrichBlueprintRow,
  formatDomainLabel
} from './calibrationBlueprintCatalog.js'

/** @typedef {{ skillId: string, label?: string, version?: string, vendor?: string, roles?: string[], description?: string, domains?: string[] }} InstalledBlueprint */

export function blueprintMatchesRole(blueprint, roleId) {
  const roles = blueprint?.roles || []
  if (!roles.length) return true
  return roles.includes(roleId)
}

export function enrichInstalledBlueprint(blueprint) {
  return enrichBlueprintRow({
    ...blueprint,
    skillId: blueprint.skillId,
    label: blueprint.label || blueprint.skillId,
    vendor: blueprint.vendor,
    description: blueprint.description || '',
    domains: blueprint.domains || []
  })
}

export function filterInstalledBlueprintsForRole(blueprints, roleId) {
  return (blueprints || [])
    .filter((row) => blueprintMatchesRole(row, roleId))
    .map(enrichInstalledBlueprint)
    .sort((a, b) => String(a.label || a.skillId).localeCompare(String(b.label || b.skillId)))
}

export function filterBrowseBlueprints(rows, { search = '', domain = '' } = {}) {
  const query = search.trim().toLowerCase()
  return (rows || []).filter((row) => {
    if (domain && row.primaryDomain !== domain) return false
    if (query && !row.searchText?.includes(query)) return false
    return true
  })
}

export function groupBrowseBlueprintsByDomain(rows) {
  const map = new Map()

  for (const row of rows) {
    const key = row.primaryDomain || 'general'
    if (!map.has(key)) {
      map.set(key, {
        id: key,
        title: row.primaryDomainLabel || formatDomainLabel(key),
        items: []
      })
    }
    map.get(key).items.push(row)
  }

  return [...map.values()]
    .sort((a, b) => a.title.localeCompare(b.title))
    .map((group) => ({
      ...group,
      items: [...group.items].sort((a, b) => String(a.label || a.skillId).localeCompare(String(b.label || b.skillId)))
    }))
}

export function blueprintDomainTabs(rows) {
  const { domains } = blueprintFilterOptions(rows || [])
  return [
    { id: '', label: 'All domains', count: rows.length },
    ...domains.map(({ value, label }) => ({
      id: value,
      label,
      count: rows.filter((row) => row.primaryDomain === value).length
    }))
  ]
}

export function blueprintDisplayDescription(blueprint) {
  const description = String(blueprint?.description || '').trim()
  if (description) return description
  if (blueprint?.product) return blueprint.product
  if (blueprint?.vendorLabel) return blueprint.vendorLabel
  return 'Installed calibration blueprint'
}

export function blueprintStarterPrompt(blueprint) {
  const label = blueprint?.label || blueprint?.skillId || 'calibration blueprint'
  return `Help me using the installed "${label}" calibration blueprint. Match this workflow to my request and follow its guidance.`
}

export const BETA_BLUEPRINTS_COPY = {
  greeting: 'Browse blueprints',
  subtitle: (roleLabel) => `Search installed ${roleLabel} skills by name or domain.`,
  empty: (roleLabel) => `No blueprints installed for ${roleLabel} yet.`,
  emptyHint: 'Download skills in Calibration Studio, then return here.',
  emptySearch: 'No blueprints match your search or domain filter.',
  loading: 'Loading installed blueprints…',
  searchPlaceholder: 'Search blueprints by name, domain, vendor, or skill id…'
}
