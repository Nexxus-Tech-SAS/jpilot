import api from './api'
import { listChatProviders } from './copilot'

export const JPILOT_BETA_PATH = '/jpilot'

/** True when at least one enabled appliance and one enabled AI provider exist. */
export async function isJpilotBetaReady() {
  try {
    const [appliancesRes, providers] = await Promise.all([
      api.get('/appliances'),
      listChatProviders()
    ])
    const appliances = appliancesRes.data || []
    const hasAppliance = appliances.some((item) => item.enabled !== false)
    return hasAppliance && providers.length > 0
  } catch {
    return false
  }
}

/**
 * Default landing path after login. Honors explicit redirect query unless it is `/` or `/login`.
 * Sends ready installs straight to JPilot Chat Beta.
 */
export async function resolvePostLoginPath(requestedPath) {
  const explicit = typeof requestedPath === 'string' ? requestedPath.trim() : ''
  if (explicit && explicit !== '/' && explicit !== '/login') {
    return explicit
  }
  if (await isJpilotBetaReady()) {
    return JPILOT_BETA_PATH
  }
  return '/'
}
