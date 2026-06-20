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

export async function uninstallCalibrationSkill(skillId, version) {
  const params = version ? { version } : undefined
  const { data } = await api.delete(`/copilot/calibrations/${encodeURIComponent(skillId)}`, { params })
  return data
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

/** Merge official catalog skills with local install state for the Studio UI. */
export function buildBlueprintLibraryRows(catalog) {
  const skills = catalog?.skills || []
  const installedBlueprints = catalog?.installedBlueprints || []
  const skillById = Object.fromEntries(skills.map((skill) => [skill.id, skill]))
  const installById = Object.fromEntries(installedBlueprints.map((row) => [row.skillId, row]))
  const ids = [...new Set([...skills.map((s) => s.id), ...installedBlueprints.map((b) => b.skillId)])].filter(Boolean)

  return ids
    .map((id) => {
      const skill = skillById[id] || {}
      const install = installById[id] || {}
      const minTier = normalizeMinTier(skill.minTier)
      const globalFreeSkill = Boolean(skill.globalFreeSkill)
      const installable = Boolean(skill.installable)
      const inCatalog = Boolean(skillById[id])
      const entitledVersion = skill.entitledVersion || null
      return enrichBlueprintRow({
        skillId: id,
        label: skill.label || install.label || id,
        vendor: skill.vendor || install.vendor || '',
        domains: skill.domains || [],
        description: skill.description || '',
        catalogVersion: skill.version || install.catalogVersion || '',
        entitledVersion,
        entitledViaSync: Boolean(skill.entitledViaSync),
        installedVersion: install.installedVersion || null,
        minTier,
        globalFreeSkill,
        installable,
        ineligibleReason: skill.ineligibleReason || null,
        installed: Boolean(install.installed),
        updateAvailable: Boolean(install.updateAvailable),
        inCatalog,
      })
    })
    .sort((a, b) => a.label.localeCompare(b.label))
}

export { filterBlueprintRows, blueprintFilterOptions, groupBlueprintRows }
