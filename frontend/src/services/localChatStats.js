import { readStorageJson } from '../utils/chatStorage'

/** Chat threads and messages saved in this browser (localStorage). */
export function getLocalChatStats() {
  const sessions = readStorageJson(localStorage, 'jpilot_sessions_v1') || {}
  let threads = 0
  let messages = 0
  for (const session of Object.values(sessions)) {
    const msgs = session?.messages || []
    if (msgs.length > 0) {
      threads += 1
      messages += msgs.length
    }
  }
  return { threads, messages }
}
