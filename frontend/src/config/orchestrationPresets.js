export const ORCHESTRATION_MODES = ['standard', 'extended', 'max', 'custom']

export const ORCHESTRATION_PRESETS = {
  standard: {
    maxToolIterations: 20,
    maxToolContinuationPhases: 3,
    longTaskToolThreshold: 8,
    promptBeforeLongTasks: true
  },
  extended: {
    maxToolIterations: 30,
    maxToolContinuationPhases: 4,
    longTaskToolThreshold: 10,
    promptBeforeLongTasks: true
  },
  max: {
    maxToolIterations: 40,
    maxToolContinuationPhases: 5,
    longTaskToolThreshold: 12,
    promptBeforeLongTasks: true
  }
}

export const ORCHESTRATION_MODE_OPTIONS = [
  {
    value: 'standard',
    label: 'Standard',
    description: 'Balanced for everyday operator tasks and short deployments.'
  },
  {
    value: 'extended',
    label: 'Extended',
    description: 'More tool rounds and continuations for multi-step configuration work.'
  },
  {
    value: 'max',
    label: 'Max',
    description: 'Highest limits for complex HA upgrades and long deployment chains.'
  },
  {
    value: 'custom',
    label: 'Custom',
    description: 'Set your own limits within the supported ranges.'
  }
]

export function inferOrchestrationMode(settings) {
  const stored = settings?.orchestrationMode
  if (stored && ORCHESTRATION_MODES.includes(stored)) {
    return stored
  }
  for (const mode of ['standard', 'extended', 'max']) {
    const preset = ORCHESTRATION_PRESETS[mode]
    const iterations = Number(settings?.maxToolIterations ?? preset.maxToolIterations)
    const phases = Number(settings?.maxToolContinuationPhases ?? preset.maxToolContinuationPhases)
    const threshold = Number(settings?.longTaskToolThreshold ?? preset.longTaskToolThreshold)
    const prompt = settings?.promptBeforeLongTasks ?? preset.promptBeforeLongTasks
    if (
      iterations === preset.maxToolIterations &&
      phases === preset.maxToolContinuationPhases &&
      threshold === preset.longTaskToolThreshold &&
      Boolean(prompt) === preset.promptBeforeLongTasks
    ) {
      return mode
    }
  }
  return 'custom'
}

export function orchestrationModeDescription(mode) {
  return ORCHESTRATION_MODE_OPTIONS.find((option) => option.value === mode)?.description || ''
}

export function applyOrchestrationPreset(mode) {
  if (!ORCHESTRATION_PRESETS[mode]) return null
  return { ...ORCHESTRATION_PRESETS[mode] }
}

/** Max model↔tool loops in one chat turn: (continuation phases + 1) × rounds per phase. */
export function effectiveMaxToolRounds(settings) {
  const roundsPerPhase = Number(settings?.maxToolIterations ?? 0)
  const continuationPhases = Number(settings?.maxToolContinuationPhases ?? 0)
  if (!roundsPerPhase || continuationPhases < 0) return 0
  return (continuationPhases + 1) * roundsPerPhase
}

export function effectiveMaxToolRoundsLabel(settings) {
  const total = effectiveMaxToolRounds(settings)
  const roundsPerPhase = Number(settings?.maxToolIterations ?? 0)
  const continuationPhases = Number(settings?.maxToolContinuationPhases ?? 0)
  const phaseCount = continuationPhases + 1
  return `${total} (${phaseCount} × ${roundsPerPhase})`
}
