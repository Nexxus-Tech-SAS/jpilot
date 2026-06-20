import { reactive, watch } from 'vue'
import { getRoleById } from '../config/jpilotRoles'
import { migrateStorageJson, readStorageJson, writeStorageJson } from '../utils/chatStorage'
import { deleteSession, getSession } from './copilotSessions'
import { isSessionLoading } from './copilotChatRuns'

/** Bounded list size — user must delete a thread to add beyond this cap. */
export const MAX_BETA_CONVERSATIONS = 12

const NAMESPACE_CONFIG = {
  main: {
    storageKey: 'jpilot_beta_conversations_v1',
    sessionPrefix: 'beta',
    defaultSessionId: 'beta-pane-1',
    defaultLabel: 'Architect'
  },
  lab: {
    storageKey: 'jpilot_beta_lab_conversations_v1',
    sessionPrefix: 'beta-lab',
    defaultSessionId: 'beta-lab-pane-1',
    defaultLabel: 'Architect'
  }
}

/** @typedef {'main' | 'lab'} BetaChatNamespace */

const stores = /** @type {Record<string, ReturnType<typeof createBetaChatStore>>} */ ({})

function defaultConversation(sessionId, initialRole, label) {
  return {
    id: sessionId.replace(/^beta(?:-lab)?-(?:chat-|pane-)/, '') || 'default',
    sessionId,
    label,
    initialRole,
    createdAt: Date.now()
  }
}

function createBetaChatStore(namespace) {
  const config = NAMESPACE_CONFIG[namespace] || NAMESPACE_CONFIG.main
  const { storageKey, sessionPrefix, defaultSessionId, defaultLabel } = config

  function loadState() {
    const migrated = migrateStorageJson(storageKey, sessionStorage, localStorage)
    if (migrated?.conversations?.length) {
      return {
        activeId: migrated.activeId || migrated.conversations[0].sessionId,
        conversations: migrated.conversations
      }
    }

    const stored = readStorageJson(localStorage, storageKey)
    if (stored?.conversations?.length) {
      return {
        activeId: stored.activeId || stored.conversations[0].sessionId,
        conversations: stored.conversations
      }
    }

    const legacy = readStorageJson(sessionStorage, storageKey)
    if (legacy?.conversations?.length) {
      return {
        activeId: legacy.activeId || legacy.conversations[0].sessionId,
        conversations: legacy.conversations
      }
    }

    return {
      activeId: defaultSessionId,
      conversations: [defaultConversation(defaultSessionId, 'architect', defaultLabel)]
    }
  }

  const state = reactive(loadState())

  function persist() {
    writeStorageJson(localStorage, storageKey, {
      activeId: state.activeId,
      conversations: state.conversations
    })
  }

  watch(() => state, persist, { deep: true })

  function newSessionId() {
    const id =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID().slice(0, 8)
        : String(Date.now()).slice(-8)
    return `${sessionPrefix}-chat-${id}`
  }

  function createBetaConversation(initialRole = 'operator', label = '') {
    if (state.conversations.length >= MAX_BETA_CONVERSATIONS) {
      return null
    }
    const role = getRoleById(initialRole)
    const sessionId = newSessionId()
    const conversation = {
      id: sessionId.replace(`${sessionPrefix}-chat-`, ''),
      sessionId,
      label: label || role.label,
      initialRole: role.id,
      createdAt: Date.now()
    }
    state.conversations.unshift(conversation)
    state.activeId = sessionId
    getSession(sessionId, role.id)
    return conversation
  }

  function setActiveBetaConversation(sessionId) {
    if (state.conversations.some((c) => c.sessionId === sessionId)) {
      state.activeId = sessionId
    }
  }

  function removeBetaConversation(sessionId) {
    if (state.conversations.length <= 1) {
      return { ok: false, reason: 'Keep at least one conversation.' }
    }
    if (isSessionLoading(sessionId)) {
      return { ok: false, reason: 'Stop the in-flight reply before deleting this chat.' }
    }

    const index = state.conversations.findIndex((c) => c.sessionId === sessionId)
    if (index < 0) {
      return { ok: false, reason: 'Conversation not found.' }
    }

    state.conversations.splice(index, 1)
    deleteSession(sessionId)

    if (state.activeId === sessionId) {
      state.activeId = state.conversations[0]?.sessionId || ''
    }

    return { ok: true }
  }

  function resolveBetaHandoffTargetSessionId() {
    const existing = state.conversations.find((conversation) => {
      const session = getSession(conversation.sessionId, conversation.initialRole)
      return session.role === 'operator'
    })
    if (existing) {
      return existing.sessionId
    }
    const created = createBetaConversation('operator', 'Operator handoff')
    return created?.sessionId || state.activeId
  }

  function conversationDisplayTitle(conversation) {
    const session = getSession(conversation.sessionId, conversation.initialRole)
    const role = getRoleById(session.role)
    const firstUser = (session.messages || []).find(
      (msg) => msg.role === 'user' && msg.content && String(msg.content).trim()
    )
    if (firstUser?.content) {
      const text = String(firstUser.content).replace(/\s+/g, ' ').trim()
      return text.length > 48 ? `${text.slice(0, 48)}…` : text
    }
    if (conversation.label && conversation.label !== role.label) {
      return conversation.label
    }
    return `${role.label} chat`
  }

  function canAddBetaConversation() {
    return state.conversations.length < MAX_BETA_CONVERSATIONS
  }

  return {
    namespace,
    state,
    createBetaConversation,
    setActiveBetaConversation,
    removeBetaConversation,
    resolveBetaHandoffTargetSessionId,
    conversationDisplayTitle,
    canAddBetaConversation
  }
}

/** @param {BetaChatNamespace} [namespace] */
export function getBetaChatStore(namespace = 'main') {
  const key = NAMESPACE_CONFIG[namespace] ? namespace : 'main'
  if (!stores[key]) {
    stores[key] = createBetaChatStore(key)
  }
  return stores[key]
}

const mainStore = getBetaChatStore('main')

export const betaChatState = mainStore.state
export const createBetaConversation = mainStore.createBetaConversation
export const setActiveBetaConversation = mainStore.setActiveBetaConversation
export const removeBetaConversation = mainStore.removeBetaConversation
export const resolveBetaHandoffTargetSessionId = mainStore.resolveBetaHandoffTargetSessionId
export const conversationDisplayTitle = mainStore.conversationDisplayTitle
export const canAddBetaConversation = mainStore.canAddBetaConversation
