import { reactive, watch } from 'vue'
import { getRoleById, normalizeRoleId, readLastUsedPersona } from '../config/jpilotRoles'
import { trimDesignDocumentForStorage } from '../utils/architectDesignDocument'
import { migrateStorageJson, readStorageJson, writeStorageJson } from '../utils/chatStorage'

// JPilot chat sessions keyed by pane / conversation id (e.g. pane-1, beta-chat-abc).
// Mirrored to localStorage on this device until the user clears a chat or deletes a thread.
const STORAGE_KEY = 'jpilot_sessions_v1'

function blankSession() {
  // Persona-first: a new chat defaults to the last persona the user selected (falling
  // back to the built-in Operator). `role` is the persona's base role — for built-ins it
  // equals the id; for a custom last-used persona it falls back to operator until ChatPane
  // reconciles it to the persona's real baseRole once the installed list loads.
  const personaId = readLastUsedPersona()
  return {
    messages: [],
    input: '',
    role: getRoleById(personaId).id,
    personaId,
    connectedAppliance: '',
    applianceChoice: null,
    providerId: '',
    webSearch: true,
    pendingMessage: null,
    pendingAttachmentsSnapshot: [],
    pendingRoleSwitch: null,
    designDocument: null
  }
}

function loadPersisted() {
  const migrated = migrateStorageJson(STORAGE_KEY, sessionStorage, localStorage)
  if (migrated && typeof migrated === 'object') return migrated

  const stored = readStorageJson(localStorage, STORAGE_KEY)
  if (stored && typeof stored === 'object') return stored

  const legacy = readStorageJson(sessionStorage, STORAGE_KEY)
  if (legacy && typeof legacy === 'object') return legacy

  return {}
}

function trimSessionsForStorage(sessions) {
  const trimmed = {}
  for (const [id, session] of Object.entries(sessions)) {
    trimmed[id] = {
      input: session.input || '',
      role: session.role || 'operator',
      personaId: session.personaId || null,
      connectedAppliance: session.connectedAppliance || '',
      applianceChoice: session.applianceChoice || null,
      providerId: session.providerId || '',
      webSearch: session.webSearch !== false,
      pendingMessage: null,
      pendingAttachmentsSnapshot: [],
      designDocument: trimDesignDocumentForStorage(session.designDocument),
      messages: (session.messages || []).map((m) => ({
        role: m.role,
        content: m.content,
        createdAt: m.createdAt || undefined,
        toolCalls: m.toolCalls || undefined,
        webSources: m.webSources || undefined,
        appliancePicker: m.appliancePicker || undefined,
        inputForm: m.inputForm || undefined,
        formSubmitted: m.formSubmitted || undefined,
        designDocRevision: m.designDocRevision || undefined,
        attachments: (m.attachments || []).map((a) => ({
          name: a.name,
          kind: a.kind,
          mimeType: a.mimeType
        }))
      }))
    }
  }
  return trimmed
}

const state = reactive({ sessions: loadPersisted() })

export function getSession(id, defaultPersonaId = null) {
  if (!state.sessions[id]) {
    const session = blankSession()
    // An explicit caller choice (e.g. "new Architect chat") selects that persona;
    // otherwise the blank session keeps the last-used persona.
    if (defaultPersonaId) {
      session.personaId = defaultPersonaId
      session.role = getRoleById(defaultPersonaId).id
    }
    state.sessions[id] = session
  } else {
    const existing = state.sessions[id]
    existing.role = normalizeRoleId(existing.role)
    // Migrate pre-persona-first sessions (personaId absent) to a built-in persona id.
    if (!existing.personaId) {
      existing.personaId = existing.role
    }
  }
  return state.sessions[id]
}

export function clearSession(id) {
  const session = getSession(id)
  session.messages = []
  session.input = ''
  session.pendingMessage = null
  session.pendingAttachmentsSnapshot = []
  session.pendingRoleSwitch = null
  session.designDocument = null
  // Intentionally keep connectedAppliance, applianceChoice, and providerId.
}

export function deleteSession(id) {
  if (id && state.sessions[id]) {
    delete state.sessions[id]
  }
}

// Persist a trimmed copy: drop heavy base64 attachment data to stay under localStorage quota.
watch(
  () => state.sessions,
  (sessions) => {
    writeStorageJson(localStorage, STORAGE_KEY, trimSessionsForStorage(sessions))
  },
  { deep: true }
)
