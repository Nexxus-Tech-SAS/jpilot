<template>
  <div class="page copilot-page flex flex-column">
    <Message v-if="providersChecked && !ready" severity="warn" :closable="false" class="copilot-warn mb-3">
      No enabled AI provider found.
      <RouterLink to="/settings?section=ai-providers" class="ml-2">Configure AI Providers →</RouterLink>
    </Message>

    <div class="stage flex-1" :class="{ 'stage-plain': background === 'none' }">
      <BetaChatBackground v-if="background !== 'none'" :background-id="background" />
      <div
        class="beta-chat-layout"
        :class="{
          'beta-chat-layout-sidebar-hidden': !chatSidebarVisible,
          'beta-chat-layout-lab': showBetaLabel
        }"
        :style="chatGlassStyle"
      >
        <div
          v-show="!isMobileLayout"
          class="beta-sidebar-card content-panel"
          :class="{ 'beta-sidebar-card-collapsed': !chatSidebarVisible }"
        >
          <div class="beta-sidebar-card-inner">
            <BetaChatSidebar
              :panes="paneSummaries"
              :active-session-id="activeSessionId"
              :can-add="canAddConversation"
              :conversation-count="betaChatState.conversations.length"
              :max-conversations="MAX_BETA_CONVERSATIONS"
              :show-beta-label="showBetaLabel"
              @select="setActiveBetaConversation"
              @new-chat="onNewChat"
              @delete="onDeleteChat"
            />
          </div>
        </div>
        <div
          class="beta-chat-workspace"
          :class="{
            'beta-chat-workspace-split': designPanelOpen && !isMobileLayout,
            'beta-chat-workspace-lab': showBetaLabel
          }"
        >
          <div class="beta-chat-card content-panel">
            <ChatPane
              v-if="activeConversation"
              :key="`${chatNamespace}-${activeSessionId}`"
              class="beta-chat-pane"
              :session-id="activeSessionId"
              :initial-role="activeConversation.initialRole"
              ui-variant="beta"
              :providers="providers"
              :appliances="appliances"
              :default-provider-id="defaultProviderId"
              :web-search-available="webSearchAvailable"
              :can-close="false"
              :show-conversation-switcher="isMobileLayout"
              :show-chat-sidebar-toggle="!isMobileLayout"
              :chat-sidebar-visible="chatSidebarVisible"
              :beta-background="background"
              :beta-backgrounds="backgrounds"
              :chat-namespace="chatNamespace"
              :show-beta-label="showBetaLabel"
              @update:beta-background="onBetaBackgroundChange"
              @open-conversations="mobileChatsOpen = true"
              @toggle-chat-sidebar="toggleChatSidebar"
              @design-panel-visible-change="onDesignPanelVisibleChange"
            />
          </div>
          <div
            v-if="!isMobileLayout"
            id="beta-architect-design-slot"
            class="beta-design-card content-panel"
            aria-label="Document Editor"
          />
        </div>
      </div>
    </div>

    <Drawer
      v-model:visible="mobileChatsOpen"
      position="left"
      :modal="true"
      :dismissable="true"
      :show-close-icon="false"
      class="beta-chats-drawer"
    >
      <div class="beta-chats-drawer-head">
        <div class="ld-cursor beta-chats-drawer-title">Chats</div>
        <button type="button" class="beta-chats-drawer-close" aria-label="Close chats" @click.stop="mobileChatsOpen = false">
          <i class="pi pi-times" />
        </button>
      </div>
      <BetaChatSidebar
        variant="drawer"
        :panes="paneSummaries"
        :active-session-id="activeSessionId"
        :can-add="canAddConversation"
        :conversation-count="betaChatState.conversations.length"
        :max-conversations="MAX_BETA_CONVERSATIONS"
        :show-beta-label="showBetaLabel"
        @select="onMobileSelectChat"
        @new-chat="onMobileNewChat"
        @delete="onDeleteChat"
      />
    </Drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Drawer from 'primevue/drawer'
import Message from 'primevue/message'
import BetaChatBackground from '../components/BetaChatBackground.vue'
import BetaChatSidebar from '../components/BetaChatSidebar.vue'
import ChatPane from '../components/ChatPane.vue'
import { getRoleById } from '../config/jpilotRoles'
import {
  MAX_BETA_CONVERSATIONS,
  getBetaChatStore
} from '../stores/betaChatConversations'
import { handoffState } from '../stores/copilotHandoff'
import { isSessionLoading } from '../stores/copilotChatRuns'
import { getSession } from '../stores/copilotSessions'
import {
  BETA_CHAT_BACKGROUNDS,
  getBetaChatBackground,
  listChatProviders,
  listCopilotAppliances,
  setBetaChatBackground
} from '../services/copilot'
import { getCopilotPlatformSettings } from '../services/copilotPlatform'
import { MOBILE_CHAT_LAYOUT_MQL } from '../utils/responsiveLayout'
import { getBetaChatGlassStyle, onBetaChatAppearanceChange } from '../services/betaChatAppearance'

const toast = useToast()
const confirm = useConfirm()
const route = useRoute()

const chatNamespace = computed(() => route.meta.chatNamespace || 'main')
// Keep the lab look/namespace; this flag drives the immersive lab styling.
const showBetaLabel = computed(() => chatNamespace.value === 'lab')
const chatStore = computed(() => getBetaChatStore(chatNamespace.value))
const betaChatState = computed(() => chatStore.value.state)

const CHAT_SIDEBAR_STORAGE_KEYS = {
  main: 'jpilot_beta_chat_sidebar_v1',
  lab: 'jpilot_beta_lab_chat_sidebar_v1'
}

function loadChatSidebarVisible() {
  const storageKey = CHAT_SIDEBAR_STORAGE_KEYS[chatNamespace.value] || CHAT_SIDEBAR_STORAGE_KEYS.main
  try {
    const raw = localStorage.getItem(storageKey)
    if (raw === '0') return false
    if (raw === '1') return true
  } catch {
    /* ignore */
  }
  return true
}

const providers = ref([])
const providersChecked = ref(false)
const appliances = ref([])
const backgrounds = BETA_CHAT_BACKGROUNDS
const background = ref(getBetaChatBackground(chatNamespace.value))
const webSearchAvailable = ref(false)
const mobileChatsOpen = ref(false)
const chatSidebarVisible = ref(loadChatSidebarVisible())
const chatSidebarBeforeDesignPanel = ref(null)
const designPanelOpen = ref(false)
const chatAppearanceTick = ref(0)
let chatAppearanceCleanup = null

const chatGlassStyle = computed(() => {
  chatAppearanceTick.value
  return getBetaChatGlassStyle(chatNamespace.value)
})

function toggleChatSidebar() {
  chatSidebarVisible.value = !chatSidebarVisible.value
  const storageKey = CHAT_SIDEBAR_STORAGE_KEYS[chatNamespace.value] || CHAT_SIDEBAR_STORAGE_KEYS.main
  try {
    localStorage.setItem(storageKey, chatSidebarVisible.value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

function onDesignPanelVisibleChange(visible) {
  designPanelOpen.value = visible
  if (visible) {
    if (chatSidebarBeforeDesignPanel.value === null) {
      chatSidebarBeforeDesignPanel.value = chatSidebarVisible.value
    }
    chatSidebarVisible.value = false
    return
  }
  if (chatSidebarBeforeDesignPanel.value !== null) {
    chatSidebarVisible.value = chatSidebarBeforeDesignPanel.value
    chatSidebarBeforeDesignPanel.value = null
  }
}

const MOBILE_LAYOUT_MQL = typeof window !== 'undefined' ? window.matchMedia(MOBILE_CHAT_LAYOUT_MQL) : null
const isMobileLayout = ref(MOBILE_LAYOUT_MQL?.matches ?? false)

function syncMobileLayout() {
  isMobileLayout.value = MOBILE_LAYOUT_MQL?.matches ?? false
  if (!isMobileLayout.value) {
    mobileChatsOpen.value = false
  }
}

const ready = computed(() => providers.value.length > 0)
const canAddConversation = computed(() => chatStore.value.canAddBetaConversation())
const activeSessionId = computed(() => betaChatState.value.activeId)

const activeConversation = computed(() =>
  betaChatState.value.conversations.find((c) => c.sessionId === activeSessionId.value) ||
  betaChatState.value.conversations[0] ||
  null
)

const defaultProviderId = computed(() => {
  const def = providers.value.find((p) => p.isDefault)
  return (def || providers.value[0])?.id || ''
})

function lastMessagePreview(session) {
  const conversational = (session.messages || []).filter(
    (msg) => (msg.role === 'user' || msg.role === 'assistant') && msg.content && !msg.appliancePicker
  )
  const last = conversational[conversational.length - 1]
  if (!last?.content) return 'No messages yet'
  const text = String(last.content).replace(/\s+/g, ' ').trim()
  return text.length > 72 ? `${text.slice(0, 72)}…` : text
}

function paneStatus(session, sessionId) {
  if (isSessionLoading(sessionId)) return 'busy'
  if (session.connectedAppliance) return 'active'
  if (session.applianceChoice) return 'away'
  return 'away'
}

const paneSummaries = computed(() =>
  betaChatState.value.conversations.map((conversation) => {
    const session = getSession(conversation.sessionId, conversation.initialRole)
    const role = getRoleById(session.role)
    return {
      sessionId: conversation.sessionId,
      title: chatStore.value.conversationDisplayTitle(conversation),
      preview: lastMessagePreview(session),
      role,
      busy: isSessionLoading(conversation.sessionId),
      status: paneStatus(session, conversation.sessionId)
    }
  })
)

function onNewChat() {
  if (!chatStore.value.canAddBetaConversation()) {
    toast.add({
      severity: 'warn',
      summary: 'Conversation limit',
      detail: `You can keep up to ${MAX_BETA_CONVERSATIONS} chats in this tab. Delete one to add another.`,
      life: 5000
    })
    return
  }
  createBetaConversation('operator', 'New chat')
}

function createBetaConversation(initialRole, label) {
  chatStore.value.createBetaConversation(initialRole, label)
}

function setActiveBetaConversation(sessionId) {
  chatStore.value.setActiveBetaConversation(sessionId)
}

function onMobileSelectChat(sessionId) {
  setActiveBetaConversation(sessionId)
  mobileChatsOpen.value = false
}

function onMobileNewChat() {
  onNewChat()
  mobileChatsOpen.value = false
}

function onDeleteChat(sessionId) {
  const pane = paneSummaries.value.find((p) => p.sessionId === sessionId)
  confirm.require({
    message: `Delete "${pane?.title || 'this chat'}"? This cannot be undone.`,
    header: 'Delete conversation',
    icon: 'pi pi-trash',
    rejectLabel: 'Cancel',
    acceptLabel: 'Delete',
    acceptClass: 'p-button-danger',
    accept: () => {
      const result = chatStore.value.removeBetaConversation(sessionId)
      if (!result.ok) {
        toast.add({
          severity: 'warn',
          summary: 'Could not delete',
          detail: result.reason,
          life: 4000
        })
      }
    }
  })
}

function onBetaBackgroundChange(id) {
  background.value = id
  setBetaChatBackground(id, chatNamespace.value)
}

async function loadProviders() {
  try {
    providers.value = await listChatProviders()
  } catch {
    providers.value = []
  } finally {
    providersChecked.value = true
  }
}

async function loadAppliances() {
  try {
    appliances.value = await listCopilotAppliances()
  } catch {
    appliances.value = []
  }
}

async function loadWebSearchAvailability() {
  try {
    const settings = await getCopilotPlatformSettings()
    webSearchAvailable.value = !!(settings.allowWebSearch && settings.hasBraveSearchApiKey)
  } catch {
    webSearchAvailable.value = false
  }
}

onMounted(() => {
  syncMobileLayout()
  MOBILE_LAYOUT_MQL?.addEventListener('change', syncMobileLayout)
  chatAppearanceCleanup = onBetaChatAppearanceChange(() => {
    chatAppearanceTick.value += 1
  })
  chatSidebarVisible.value = loadChatSidebarVisible()
  background.value = getBetaChatBackground(chatNamespace.value)
  if (!betaChatState.value.conversations.length) {
    chatStore.value.createBetaConversation('architect', 'Architect')
  }
  loadProviders()
  loadAppliances()
  loadWebSearchAvailability()
})

onUnmounted(() => {
  chatAppearanceCleanup?.()
  MOBILE_LAYOUT_MQL?.removeEventListener('change', syncMobileLayout)
})

watch(
  () => handoffState.pending,
  (pending) => {
    if (pending?.targetSessionId?.startsWith('beta-')) {
      chatStore.value.setActiveBetaConversation(pending.targetSessionId)
    }
  }
)

watch(chatNamespace, () => {
  chatSidebarVisible.value = loadChatSidebarVisible()
  background.value = getBetaChatBackground(chatNamespace.value)
  chatAppearanceTick.value += 1
  if (!betaChatState.value.conversations.length) {
    chatStore.value.createBetaConversation('architect', 'Architect')
  }
})
</script>

<style scoped>
.copilot-page {
  height: calc(100vh - 5rem);
  min-height: 32rem;
  overflow: hidden;
  background: transparent;
}

@media (max-width: 991px) {
  .copilot-page {
    flex: 1;
    min-height: 0;
    height: 100%;
    margin: 0;
    width: 100%;
    max-width: none;
    overflow: hidden;
  }

  .stage {
    border-radius: 0;
    flex: 1;
    min-height: 0;
  }

  .stage :deep(.beta-chat-bg) {
    display: none;
  }

  .beta-chat-layout {
    padding: 0;
    gap: 0;
    height: 100%;
  }

  .beta-chat-layout-sidebar-hidden .beta-chat-card {
    flex: 1;
  }

  .beta-sidebar-card {
    display: none;
  }

  .beta-chat-card,
  .beta-chat-card.content-panel {
    flex: 1;
    min-height: 0;
    height: 100%;
    border-radius: 0;
    box-shadow: none;
    border: 0;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    background: #f8fafc;
  }

  :global(html.app-dark) .beta-chat-card,
  :global(html.app-dark) .beta-chat-card.content-panel {
    background: #000000;
  }
}

.stage {
  position: relative;
  border-radius: 1rem;
  overflow: hidden;
  background-color: transparent;
  min-height: 0;
}

.stage-plain {
  background-color: #ffffff;
}

:global(html.app-dark) .stage-plain {
  background-color: #000000;
}

.beta-chat-layout {
  --beta-chat-panel-mix: 42%;
  --beta-chat-sidebar-mix: 42%;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
  min-height: 0;
  padding: 0.75rem;
  background: transparent;
}

.beta-chat-layout-lab {
  --beta-glass-panel-bg: color-mix(in srgb, var(--p-content-background) var(--beta-chat-panel-mix), transparent);
  --beta-glass-panel-bg-dark: color-mix(in srgb, rgb(8, 12, 22) var(--beta-chat-panel-mix), transparent);
  --beta-glass-sidebar-bg: color-mix(in srgb, var(--p-content-background) var(--beta-chat-sidebar-mix), transparent);
  --beta-glass-sidebar-bg-dark: color-mix(in srgb, rgb(8, 12, 22) var(--beta-chat-sidebar-mix), transparent);
}
.beta-sidebar-card.content-panel,
.beta-chat-card.content-panel {
  min-height: 0;
  overflow: hidden;
  padding: 0;
}

@media (min-width: 992px) {
  .beta-sidebar-card.content-panel {
    background: color-mix(in srgb, var(--p-content-background) var(--beta-chat-sidebar-mix), transparent);
    border-color: color-mix(in srgb, var(--p-content-border-color) 52%, transparent);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 8px 28px rgba(2, 6, 23, 0.06);
  }

  .beta-chat-card.content-panel {
    background: color-mix(in srgb, var(--p-content-background) var(--beta-chat-panel-mix), transparent);
    border-color: color-mix(in srgb, var(--p-content-border-color) 52%, transparent);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 8px 28px rgba(2, 6, 23, 0.06);
  }

  :global(.app-dark) .beta-sidebar-card.content-panel,
  :global(.app-dark) .beta-chat-card.content-panel {
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
  }

  /* Lab: glass sidebar + conversation window */
  .beta-chat-layout-lab .beta-sidebar-card.content-panel {
    background: var(--beta-glass-sidebar-bg);
    border-color: color-mix(in srgb, var(--p-content-border-color) 36%, transparent);
    backdrop-filter: blur(6px) saturate(120%);
    -webkit-backdrop-filter: blur(6px) saturate(120%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.18),
      0 2px 4px rgba(2, 6, 23, 0.05),
      0 14px 32px rgba(2, 6, 23, 0.1),
      0 28px 56px rgba(2, 6, 23, 0.08);
  }

  :global(.app-dark) .beta-chat-layout-lab .beta-sidebar-card.content-panel {
    background: var(--beta-glass-sidebar-bg-dark);
    border-color: rgba(255, 255, 255, 0.09);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      0 2px 4px rgba(0, 0, 0, 0.28),
      0 16px 36px rgba(0, 0, 0, 0.36),
      0 30px 60px rgba(0, 0, 0, 0.3);
  }

  .beta-chat-layout-lab .beta-chat-card.content-panel {
    background: var(--beta-glass-panel-bg);
    border-color: color-mix(in srgb, var(--p-content-border-color) 40%, transparent);
    backdrop-filter: blur(6px) saturate(120%);
    -webkit-backdrop-filter: blur(6px) saturate(120%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.22),
      0 2px 4px rgba(2, 6, 23, 0.06),
      0 14px 32px rgba(2, 6, 23, 0.12),
      0 28px 56px rgba(2, 6, 23, 0.1);
  }

  :global(.app-dark) .beta-chat-layout-lab .beta-chat-card.content-panel {
    background: var(--beta-glass-panel-bg-dark);
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.05),
      0 2px 4px rgba(0, 0, 0, 0.3),
      0 16px 36px rgba(0, 0, 0, 0.4),
      0 30px 60px rgba(0, 0, 0, 0.32);
  }
}

.beta-sidebar-card,
.beta-chat-card,
.beta-chat-workspace {
  min-height: 0;
  overflow: hidden;
  padding: 0;
}

.beta-chat-workspace {
  display: flex;
  flex: 1;
  min-width: 0;
  height: 100%;
  gap: 0.75rem;
}

.beta-chat-workspace-split {
  --beta-split-chat: 72%;
  --beta-split-editor: 23%;
}

.beta-design-card {
  display: none;
  flex: 0 0 var(--beta-split-editor, 23%);
  width: var(--beta-split-editor, 23%);
  max-width: var(--beta-split-editor, 23%);
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: var(--p-content-border-radius, var(--content-radius));
  position: relative;
  z-index: 1;
  isolation: isolate;
}

.beta-chat-workspace-split .beta-chat-card {
  /* Grow to fill the remaining width so the editor sits flush at the right edge.
     (Previously fixed at 72%, which left a dead ~5% strip since chat 72% +
     editor 23% < 100%.) */
  flex: 1 1 0;
  width: auto;
  max-width: none;
  min-width: 0;
  border-radius: var(--p-content-border-radius, var(--content-radius));
  overflow: hidden;
  position: relative;
  z-index: 2;
}

.beta-chat-workspace-split .beta-design-card {
  display: flex;
  flex-direction: column;
}

@media (min-width: 992px) {
  .beta-chat-workspace-split .beta-design-card.content-panel {
    background: var(--p-content-background);
    border-color: var(--p-content-border-color);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    box-shadow: 0 10px 32px rgba(2, 6, 23, 0.1);
  }

  :global(.app-dark) .beta-chat-workspace-split .beta-design-card.content-panel {
    box-shadow: 0 10px 32px rgba(0, 0, 0, 0.32);
  }

  .beta-chat-workspace-lab.beta-chat-workspace-split .beta-design-card.content-panel {
    background: var(--p-content-background);
    border-color: var(--p-content-border-color);
  }

  .beta-chat-workspace:not(.beta-chat-workspace-split) .beta-chat-card {
    flex: 1;
    width: 100%;
    max-width: none;
  }
}

.beta-chat-pane {
  height: 100%;
  border: 0;
  border-radius: inherit;
  box-shadow: none;
}

@media (min-width: 992px) {
  .beta-chat-layout {
    flex-direction: row;
    gap: 2rem;
    padding: 1rem;
    transition: gap 0.32s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .beta-chat-layout-sidebar-hidden {
    gap: 0;
  }

  .beta-chat-workspace {
    flex: 1;
    min-width: 0;
  }

  .beta-sidebar-card {
    width: 20rem;
    flex-shrink: 0;
    overflow: hidden;
    transition:
      width 0.32s cubic-bezier(0.4, 0, 0.2, 1),
      opacity 0.26s ease,
      border-color 0.26s ease,
      box-shadow 0.26s ease;
  }

  .beta-sidebar-card-collapsed {
    width: 0;
    opacity: 0;
    border-color: transparent;
    box-shadow: none;
    pointer-events: none;
  }

  .beta-sidebar-card-inner {
    width: 20rem;
    height: 100%;
    min-height: 0;
    transition: opacity 0.22s ease;
  }

  .beta-sidebar-card-collapsed .beta-sidebar-card-inner {
    opacity: 0;
  }

  .beta-chat-card {
    flex: 1;
    min-width: 0;
    transition: flex 0.32s cubic-bezier(0.4, 0, 0.2, 1);
  }
}

@media (min-width: 992px) and (prefers-reduced-motion: reduce) {
  .beta-chat-layout,
  .beta-sidebar-card,
  .beta-sidebar-card-inner,
  .beta-chat-card {
    transition: none;
  }
}

.beta-chats-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.beta-chats-drawer-title {
  color: var(--p-primary-color);
}

.beta-chats-drawer-close {
  width: 2.25rem;
  height: 2.25rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: var(--p-text-color);
  cursor: pointer;
}

.beta-chats-drawer-close:hover {
  background: var(--p-surface-100);
}

:global(.p-drawer.beta-chats-drawer) {
  width: min(20rem, 100vw) !important;
}

@media (max-width: 991px) {
  :global(.p-drawer.beta-chats-drawer) {
    width: 100vw !important;
    max-width: 100vw;
  }

  :global(.p-drawer.beta-chats-drawer .p-drawer-content) {
    background: var(--p-surface-0);
  }

  :global(.app-dark .p-drawer.beta-chats-drawer .p-drawer-content) {
    background: #0a0a0a;
  }
}

:global(.p-drawer.beta-chats-drawer .p-drawer-content) {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 1rem;
  padding-top: calc(1rem + env(safe-area-inset-top, 0px));
  padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
}
</style>
