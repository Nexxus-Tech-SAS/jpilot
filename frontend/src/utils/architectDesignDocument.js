import {
  architectDeliverableFilename,
  architectDeliverableType,
  stripArchitectDeliverableMarker
} from './architectDeliverable'
import { JPILOT_CHANGE_CONTROL_MARKER } from './architectDeliverable'
import { JPILOT_DESIGN_MARKER } from './designDocument'

export const DESIGN_PANEL_STORAGE_KEY = 'jpilot_architect_design_panel_v1'
export const MAX_PERSISTED_DESIGN_DOC_CHARS = 512_000

const MARKERS = [JPILOT_DESIGN_MARKER, JPILOT_CHANGE_CONTROL_MARKER]

export function isMarkdownAttachmentName(name) {
  const lowered = (name || '').toLowerCase()
  return lowered.endsWith('.md') || lowered.endsWith('.markdown')
}

/**
 * @returns {import('./architectDesignDocument').DesignDocument | null}
 */
export function blankDesignDocumentState() {
  return null
}

/**
 * @param {object} params
 * @returns {import('./architectDesignDocument').DesignDocument}
 */
export function createDesignDocument({ markdown, type = 'design', source = 'assistant', filename, revision = 1 }) {
  const body = markdown || ''
  return {
    markdown: body,
    filename: filename || architectDeliverableFilename(body || `${type}-document`),
    type: type === 'change_control' ? 'change_control' : 'design',
    revision,
    updatedAt: new Date().toISOString(),
    streaming: false,
    dirty: false,
    source
  }
}

export function trimDesignDocumentForStorage(doc) {
  if (!doc) return null
  let markdown = doc.markdown || ''
  if (markdown.length > MAX_PERSISTED_DESIGN_DOC_CHARS) {
    markdown = markdown.slice(0, MAX_PERSISTED_DESIGN_DOC_CHARS)
  }
  return {
    filename: doc.filename,
    type: doc.type,
    revision: doc.revision,
    updatedAt: doc.updatedAt,
    streaming: false,
    dirty: Boolean(doc.dirty),
    source: doc.source,
    markdown
  }
}

function introBeforeMarker(content) {
  for (const marker of MARKERS) {
    const idx = content.indexOf(marker)
    if (idx >= 0) {
      return content.slice(0, idx).trim()
    }
  }
  return ''
}

/**
 * Split assistant reply into chat-visible text and deliverable body.
 * @param {string} content
 */
export function splitArchitectAssistantContent(content) {
  if (!content || typeof content !== 'string') {
    return { chatContent: content || '', deliverable: null }
  }

  const type = architectDeliverableType(content)
  if (!type) {
    return { chatContent: content, deliverable: null }
  }

  const markdown = stripArchitectDeliverableMarker(content)
  const intro = introBeforeMarker(content)
  const chatContent =
    intro ||
    (type === 'change_control'
      ? 'Change control record updated — review it in the design panel.'
      : 'Design document updated — review it in the design panel.')

  return {
    chatContent,
    deliverable: { markdown, type }
  }
}

/**
 * @param {object} session
 * @param {string} content
 * @param {'assistant'|'attachment'|'revision'} [source]
 */
export function applyDeliverableToSession(session, content, source = 'assistant') {
  const split = splitArchitectAssistantContent(content)
  if (!split.deliverable) {
    if (session.designDocument) {
      session.designDocument.streaming = false
    }
    return { chatContent: content, revision: null }
  }

  const previousRevision = session.designDocument?.revision || 0
  session.designDocument = createDesignDocument({
    markdown: split.deliverable.markdown,
    type: split.deliverable.type,
    source,
    filename: architectDeliverableFilename(content),
    revision: previousRevision + 1
  })

  return {
    chatContent: split.chatContent,
    revision: session.designDocument.revision
  }
}

/**
 * @param {object} session
 * @param {{ name: string, kind: string, data: string, mimeType?: string }} attachment
 */
export function seedDesignDocumentFromAttachment(session, attachment) {
  if (!attachment || attachment.kind !== 'config') return false
  if (!isMarkdownAttachmentName(attachment.name)) return false
  const markdown = (attachment.data || '').trim()
  if (!markdown) return false

  const type = architectDeliverableType(markdown) || 'design'
  session.designDocument = createDesignDocument({
    markdown: stripArchitectDeliverableMarker(markdown),
    type,
    source: 'attachment',
    filename: attachment.name,
    revision: 1
  })
  return true
}

export function beginDesignDocumentStreaming(session) {
  const existing = session.designDocument
  if (existing) {
    existing.streaming = true
    existing.updatedAt = new Date().toISOString()
    return
  }
  session.designDocument = createDesignDocument({
    markdown: '',
    type: 'design',
    source: 'assistant',
    revision: 0
  })
  session.designDocument.streaming = true
}

export function loadDesignPanelVisible() {
  try {
    return localStorage.getItem(DESIGN_PANEL_STORAGE_KEY) !== '0'
  } catch {
    return true
  }
}

export function saveDesignPanelVisible(visible) {
  try {
    localStorage.setItem(DESIGN_PANEL_STORAGE_KEY, visible ? '1' : '0')
  } catch {
    // ignore
  }
}
