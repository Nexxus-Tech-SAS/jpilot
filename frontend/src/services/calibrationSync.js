import api from './api'
import {
  enrichBlueprintRow,
  filterBlueprintRows,
  blueprintFilterOptions,
  groupBlueprintRows,
} from '../utils/calibrationBlueprintCatalog.js'

export async function listInstalledCalibrations() {
  const { data } = await api.get('/copilot/calibrations')
  return data
}

export async function fetchCalibrationCatalog(vendor) {
  const params = vendor ? { vendor } : undefined
  const { data } = await api.get('/copilot/calibrations/catalog', { params })
  return data
}

export async function syncCalibrationsFromStudio() {
  const { data } = await api.post('/copilot/calibrations/sync')
  return data
}

export async function fetchKnowledgePackStatus() {
  const { data } = await api.get('/copilot/knowledge-pack')
  return data
}

export async function importKnowledgePack(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/copilot/knowledge-pack/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
}

export async function rollbackKnowledgePack() {
  const { data } = await api.post('/copilot/knowledge-pack/rollback')
  return data
}

export async function pinKnowledgePackVersion(version) {
  const { data } = await api.put('/copilot/knowledge-pack/pin', { version: version || null })
  return data
}

export async function updateKnowledgePackSchedule({ enabled, hours }) {
  const { data } = await api.put('/copilot/knowledge-pack/schedule', { enabled, hours })
  return data
}

export async function installCalibrationSkill(skillId) {
  const { data } = await api.post(`/copilot/calibrations/${encodeURIComponent(skillId)}/install`)
  return data
}

export async function installCalibrationPersona(personaId) {
  const { data } = await api.post(
    `/copilot/calibrations/personas/${encodeURIComponent(personaId)}/install`
  )
  return data
}

export async function installCalibrationKnowledgePack(packId) {
  const { data } = await api.post(
    `/copilot/calibrations/knowledge-packs/${encodeURIComponent(packId)}/install`
  )
  return data
}

/** Artifact types served by the unified Blueprint Library. */
export const ARTIFACT_TYPES = {
  skill: 'skill',
  persona: 'persona',
  knowledge_pack: 'knowledge_pack',
}

export function normalizeArtifactType(type) {
  const cleaned = String(type || 'skill')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
  return cleaned || 'skill'
}

export function artifactTypeLabel(type) {
  const map = { skill: 'Skill', persona: 'Persona', knowledge_pack: 'Knowledge Pack' }
  return map[normalizeArtifactType(type)] || 'Skill'
}

/** Install dispatch by artifact type — routes to the matching backend endpoint. */
export function installCalibrationItem(row) {
  const type = normalizeArtifactType(row?.type)
  if (type === 'persona') return installCalibrationPersona(row.skillId)
  if (type === 'knowledge_pack') return installCalibrationKnowledgePack(row.skillId)
  return installCalibrationSkill(row.skillId)
}

export async function uninstallCalibrationSkill(skillId, version) {
  const params = version ? { version } : undefined
  const { data } = await api.delete(`/copilot/calibrations/${encodeURIComponent(skillId)}`, { params })
  return data
}

export async function uninstallCalibrationPersona(personaId, version) {
  const params = version ? { version } : undefined
  const { data } = await api.delete(
    `/copilot/calibrations/personas/${encodeURIComponent(personaId)}`,
    { params }
  )
  return data
}

export async function uninstallCalibrationKnowledgePack(packId) {
  const { data } = await api.delete(
    `/copilot/calibrations/knowledge-packs/${encodeURIComponent(packId)}`
  )
  return data
}

/** Uninstall dispatch by artifact type — mirrors installCalibrationItem. */
export function uninstallCalibrationItem(row) {
  const type = normalizeArtifactType(row?.type)
  if (type === 'persona') return uninstallCalibrationPersona(row.skillId, row.installedVersion || undefined)
  if (type === 'knowledge_pack') return uninstallCalibrationKnowledgePack(row.skillId)
  return uninstallCalibrationSkill(row.skillId, row.installedVersion || undefined)
}

/** Normalize minTier values from scstudio (`enterprise-pro` → `enterprise_pro`). */
export function normalizeMinTier(minTier) {
  return String(minTier || 'free')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

export function licenseTypeLabel(licenseType) {
  const tier = normalizeMinTier(licenseType)
  const map = {
    free: 'Early Access / Free',
    early_access: 'Early Access / Free',
    enterprise: 'Enterprise',
    enterprise_pro: 'Enterprise Pro',
  }
  return map[tier] || licenseType || 'Unknown license'
}

/** Match scstudio Blueprint Library tier tags. */
export function blueprintTierLabel({ minTier, globalFreeSkill }) {
  if (globalFreeSkill) return 'Free'
  const tier = normalizeMinTier(minTier)
  if (tier === 'enterprise_pro') return 'Ent+'
  if (tier === 'enterprise') return 'Ent'
  return 'Free'
}

/** Compact tier tag for the active install license (matches Min tier labels). */
export function currentBlueprintTierLabel(licenseType) {
  const tier = normalizeMinTier(licenseType)
  if (tier === 'enterprise_pro') return 'Ent+'
  if (tier === 'enterprise') return 'Ent'
  if (tier === 'early_access') return 'Free'
  return 'Free'
}

export function licenseTierRank(licenseType) {
  const tier = normalizeMinTier(licenseType)
  if (tier === 'enterprise_pro') return 3
  if (tier === 'enterprise') return 2
  return 1
}

export function blueprintRequiredTierRank({ minTier, globalFreeSkill }) {
  if (globalFreeSkill) return 1
  return licenseTierRank(minTier)
}

export function tierMeetsBlueprintRequirement(currentLicenseType, row) {
  return licenseTierRank(currentLicenseType) >= blueprintRequiredTierRank(row)
}

export function blueprintDownloadTargetVersion(row) {
  return row.entitledVersion || row.catalogVersion || ''
}

export function blueprintHasDownloadableUpdate(row) {
  if (!row.installable || !row.inCatalog) return false
  if (!row.installed) return true
  const target = blueprintDownloadTargetVersion(row)
  return Boolean(target && row.installedVersion !== target)
}

export function blueprintIsLatestEntitled(row) {
  if (!row.installed || !row.installable) return false
  const target = blueprintDownloadTargetVersion(row)
  return Boolean(target && row.installedVersion === target)
}

export function blueprintCatalogAheadOfEntitlement(row) {
  return Boolean(
    row.installed
    && row.catalogVersion
    && row.entitledVersion
    && row.catalogVersion !== row.entitledVersion
    && row.installedVersion === row.entitledVersion
  )
}

export function blueprintCanDownload(row) {
  return blueprintHasDownloadableUpdate(row)
}

export function blueprintStatusLabel(row, currentLicenseType) {
  const tierOk = tierMeetsBlueprintRequirement(currentLicenseType, row)
  if (row.installable) {
    if (row.installed && blueprintIsLatestEntitled(row)) {
      if (blueprintCatalogAheadOfEntitlement(row)) {
        return 'Latest entitled'
      }
      return 'Installed'
    }
    if (row.installed && blueprintHasDownloadableUpdate(row)) {
      const target = blueprintDownloadTargetVersion(row)
      if (row.entitledVersion && row.entitledVersion !== row.catalogVersion) {
        return `Sync ${target} available`
      }
      return 'Update available'
    }
    if (row.installed) return 'Installed'
    if (row.entitledViaSync && row.entitledVersion && row.entitledVersion !== row.catalogVersion) {
      return `Entitled · sync ${row.entitledVersion}`
    }
    return 'Entitled'
  }
  if (row.installed && row.updateAvailable) {
    return tierOk ? 'Update blocked' : blueprintRequirementLabel(row)
  }
  if (row.installed) return 'Installed'
  if (tierOk && row.inCatalog) return 'Not assigned'
  return blueprintRequirementLabel(row)
}

export function blueprintDownloadBlockedLabel(row, currentLicenseType) {
  if (blueprintIsLatestEntitled(row)) {
    if (blueprintCatalogAheadOfEntitlement(row)) {
      return `You have the latest entitled sync version (${row.entitledVersion}). Catalog ${row.catalogVersion} is not assigned to this installation yet.`
    }
    return 'Already installed at the latest entitled version'
  }
  if (row.installed && !row.updateAvailable) {
    return 'Already installed at the latest catalog version'
  }
  if (row.ineligibleReason) return row.ineligibleReason
  if (row.installed && row.updateAvailable && tierMeetsBlueprintRequirement(currentLicenseType, row)) {
    return 'Your license tier qualifies, but this blueprint is not enabled for your installation.'
  }
  return blueprintRequirementLabel(row)
}

export function blueprintDownloadBlockedButtonLabel(row, currentLicenseType) {
  if (row.installed && row.updateAvailable && !row.installable) {
    return tierMeetsBlueprintRequirement(currentLicenseType, row) ? 'Update blocked' : 'Not entitled'
  }
  if (tierMeetsBlueprintRequirement(currentLicenseType, row) && row.inCatalog && !row.installable) {
    return 'Not assigned'
  }
  return 'Not entitled'
}

export function blueprintTierRowNote(row, currentLicenseType) {
  if (row.installable) return ''
  if (!tierMeetsBlueprintRequirement(currentLicenseType, row)) return ''
  return 'Tier OK'
}

export function collectTierOkBlockedRows(rows, currentLicenseType) {
  return rows.filter(
    (row) => row.inCatalog && !row.installable && tierMeetsBlueprintRequirement(currentLicenseType, row)
  )
}

export function blueprintTierRowTooltip(row, currentLicenseType, studioLicenseLabel) {
  const parts = [`Your license tier: ${studioLicenseLabel}`]
  if (row.ineligibleReason) {
    parts.push(row.ineligibleReason)
  } else if (!row.installable && tierMeetsBlueprintRequirement(currentLicenseType, row)) {
    parts.push('Your tier meets the minimum, but this blueprint is not enabled for your installation.')
  }
  return parts.join(' ')
}

export function blueprintTierSeverity({ minTier, globalFreeSkill }) {
  const tier = normalizeMinTier(minTier)
  if (globalFreeSkill || tier === 'free') return 'success'
  if (tier === 'enterprise_pro') return 'danger'
  return 'info'
}

export function blueprintRequirementLabel({ minTier, globalFreeSkill, installable, inCatalog }) {
  if (installable) return 'Entitled'
  if (!inCatalog) return 'Local only'
  const tier = normalizeMinTier(minTier)
  if (globalFreeSkill) return 'Not entitled'
  if (tier === 'enterprise_pro') return 'Requires Ent+'
  if (tier === 'enterprise') return 'Requires Ent'
  return 'Not entitled'
}

/** Compare installed skills against the official catalog versions. */
export function collectBlueprintUpdates(rows) {
  const installed = rows.filter((row) => row.installed)
  const catalogUpdates = installed.filter((row) => row.updateAvailable)
  const downloadableUpdates = installed.filter((row) => blueprintHasDownloadableUpdate(row))

  return {
    installedCount: installed.length,
    upToDateCount: installed.filter((row) => !row.updateAvailable).length,
    updateCount: catalogUpdates.length,
    entitledUpdateCount: downloadableUpdates.length,
    blockedUpdateCount: catalogUpdates.filter((row) => !blueprintHasDownloadableUpdate(row)).length,
    updates: catalogUpdates.map((row) => ({
      skillId: row.skillId,
      label: row.label,
      installedVersion: row.installedVersion,
      catalogVersion: row.catalogVersion,
      entitledVersion: row.entitledVersion,
      installable: blueprintHasDownloadableUpdate(row),
      ineligibleReason: row.ineligibleReason,
    })),
  }
}

export function formatBlueprintUpdateSummary(summary) {
  if (!summary.installedCount) {
    return {
      severity: 'info',
      message: 'No skills installed locally. Download entitled blueprints from the library below.',
      detail: [],
    }
  }
  if (!summary.updateCount) {
    return {
      severity: 'success',
      message: `All ${summary.installedCount} installed skill(s) match the latest official catalog versions.`,
      detail: [],
    }
  }

  const detail = summary.updates.map((row) => {
    const versionLine = `${row.label}: ${row.installedVersion} → ${row.catalogVersion}`
    if (row.installable) return versionLine
    if (row.entitledVersion && row.entitledVersion !== row.catalogVersion) {
      return `${versionLine} (catalog ahead; sync offers ${row.entitledVersion} only)`
    }
    return `${versionLine} (newer version not entitled under your license)`
  })

  let message = `${summary.updateCount} installed skill(s) have a newer version in the official catalog.`
  if (summary.entitledUpdateCount) {
    message += ` ${summary.entitledUpdateCount} can be updated now.`
  }
  if (summary.blockedUpdateCount) {
    message += ` ${summary.blockedUpdateCount} require a higher license.`
  }

  return { severity: 'warn', message, detail }
}

/**
 * Merge the official catalog with local install state for the Studio UI.
 *
 * Prefers the unified `items[]` (skills + personas + knowledge packs, frozen contract);
 * falls back to the legacy skills-only `skills[]` when an older backend/scstudio omits
 * `items[]`. Each row carries its `type` so the UI can badge/filter by artifact type.
 */
export function buildBlueprintLibraryRows(catalog) {
  const rawItems =
    Array.isArray(catalog?.items) && catalog.items.length ? catalog.items : catalog?.skills || []
  const installedBlueprints = catalog?.installedBlueprints || []
  // Key catalog entries by (type, id); install state is skill-keyed (legacy by id).
  const itemByKey = new Map()
  for (const item of rawItems) {
    const type = normalizeArtifactType(item.type)
    itemByKey.set(`${type}::${item.id}`, item)
  }
  const installById = Object.fromEntries(installedBlueprints.map((row) => [row.skillId, row]))

  const keys = new Set(itemByKey.keys())
  // Installed-only rows (no longer in catalog) are treated as skills.
  for (const b of installedBlueprints) {
    if (b.skillId) keys.add(`skill::${b.skillId}`)
  }

  return [...keys]
    .map((key) => {
      const item = itemByKey.get(key) || {}
      const type = normalizeArtifactType(item.type || key.split('::')[0])
      const id = item.id || key.split('::').slice(1).join('::')
      // Skills carry install state via installedBlueprints; personas/packs carry it
      // on the catalog item itself (marked server-side from on-disk install state).
      const install =
        type === 'skill'
          ? installById[id] || {}
          : {
              installed: Boolean(item.installed),
              installedVersion: item.installedVersion || null,
              updateAvailable: Boolean(item.updateAvailable),
            }
      const minTier = normalizeMinTier(item.minTier)
      const globalFreeSkill = Boolean(item.globalFree || item.globalFreeSkill)
      const installable = Boolean(item.installable)
      const inCatalog = itemByKey.has(key)
      const entitledVersion = item.entitledVersion || null
      return enrichBlueprintRow({
        type,
        skillId: id,
        label: item.label || install.label || id,
        vendor: item.vendor || install.vendor || '',
        domains: item.domains || [],
        description: item.description || '',
        catalogVersion: item.version || install.catalogVersion || '',
        entitledVersion,
        entitledViaSync: Boolean(item.entitledViaSync),
        installedVersion: install.installedVersion || null,
        minTier,
        globalFreeSkill,
        installable,
        ineligibleReason: item.ineligibleReason || null,
        installed: Boolean(install.installed),
        updateAvailable: Boolean(install.updateAvailable),
        inCatalog,
        meta: item.meta || {},
      })
    })
    .sort((a, b) => a.label.localeCompare(b.label))
}

export { filterBlueprintRows, blueprintFilterOptions, groupBlueprintRows }
