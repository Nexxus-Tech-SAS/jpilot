/** Phones and phone-landscape only — iPad portrait keeps the desktop chat chrome. */
export const MOBILE_CHAT_LAYOUT_MQL =
  '(max-width: 767px), (max-width: 991px) and (max-height: 500px)'

export function isMobileChatLayout(viewport = typeof window !== 'undefined' ? window : null) {
  if (!viewport?.matchMedia) return false
  return viewport.matchMedia(MOBILE_CHAT_LAYOUT_MQL).matches
}
