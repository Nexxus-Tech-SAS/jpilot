<template>
  <div class="page settings-beta">
    <div class="settings-beta-layout" :class="{ 'show-detail': mobileShowDetail }">
      <!-- Master: grouped navigation rail -->
      <aside class="settings-rail" aria-label="Settings sections">
        <div class="settings-rail-head">
          <div class="settings-rail-title">
            <i class="pi pi-cog" />
            <span>Settings</span>
          </div>
          <IconField class="settings-search">
            <InputIcon class="pi pi-search" />
            <InputText
              v-model="search"
              placeholder="Search settings…"
              aria-label="Search settings"
            />
          </IconField>
        </div>

        <nav class="settings-rail-nav">
          <template v-for="group in visibleGroups" :key="group.id">
            <p class="rail-group-label">{{ group.label }}</p>
            <button
              v-for="section in group.sections"
              :key="section.key"
              type="button"
              class="rail-link"
              :class="{ 'rail-link-active': section.key === activeKey }"
              @click="selectSection(section.key)"
            >
              <i :class="section.icon" class="rail-link-icon" />
              <span class="rail-link-label">{{ section.label }}</span>
              <i class="pi pi-chevron-right rail-link-chevron" />
            </button>
          </template>

          <p v-if="!hasResults" class="rail-empty">No settings match “{{ search }}”.</p>
        </nav>
      </aside>

      <!-- Detail: active section -->
      <section class="settings-detail">
        <header class="detail-head">
          <button
            type="button"
            class="detail-back"
            aria-label="Back to settings list"
            @click="mobileShowDetail = false"
          >
            <i class="pi pi-arrow-left" />
          </button>
          <div class="detail-head-text">
            <h1 class="detail-title">
              <i :class="activeSection.icon" class="detail-title-icon" />
              {{ activeSection.label }}
            </h1>
            <p v-if="activeSection.description" class="detail-desc">{{ activeSection.description }}</p>
          </div>
        </header>

        <!-- Sub-tabs for sections that bundle multiple panels -->
        <div v-if="activeSection.tabs" class="detail-tabs">
          <button
            v-for="tab in activeSection.tabs"
            :key="tab.key"
            type="button"
            class="detail-tab"
            :class="{ 'detail-tab-active': tab.key === activeTabKey }"
            @click="selectTab(tab.key)"
          >
            <i :class="tab.icon" />
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <div class="detail-body">
          <KeepAlive>
            <component
              :is="activeComponent"
              :key="activeComponentKey"
              v-bind="activeComponentProps"
            />
          </KeepAlive>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import OtherAppliancesView from './OtherAppliancesView.vue'
import BraveSearchPanel from '../components/BraveSearchPanel.vue'
import NextGenApiPanel from '../components/NextGenApiPanel.vue'
import SlackNotificationsPanel from '../components/SlackNotificationsPanel.vue'
import UsersPanel from '../components/UsersPanel.vue'
import UpdatesPanel from '../components/UpdatesPanel.vue'
import LicensePanel from '../components/LicensePanel.vue'
import AiModelsPanel from '../components/settings-beta/AiModelsPanel.vue'
import McpServerPanel from '../components/settings-beta/McpServerPanel.vue'
import SmtpEmailPanel from '../components/settings-beta/SmtpEmailPanel.vue'
import AssistantSettingsPanel from '../components/settings-beta/AssistantSettingsPanel.vue'
import SecuritySettingsPanel from '../components/settings-beta/SecuritySettingsPanel.vue'
import LegalLinksPanel from '../components/settings-beta/LegalLinksPanel.vue'
import api from '../services/api'
import { getStoredUser } from '../services/auth'

const route = useRoute()
const router = useRouter()

const currentUser = ref(getStoredUser())
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const GROUP_LABELS = {
  workspace: 'Workspace',
  access: 'People & access',
  system: 'System'
}

// Single source of truth for the redesigned information architecture.
const allSections = [
  {
    key: 'appliances',
    label: 'Appliances',
    icon: 'pi pi-server',
    group: 'workspace',
    description: 'Managed devices, vendors, and SSL certificates.',
    component: OtherAppliancesView
  },
  {
    key: 'ai-models',
    label: 'AI & models',
    icon: 'pi pi-sparkles',
    group: 'workspace',
    adminOnly: true,
    description: 'Language model providers and usage.',
    component: AiModelsPanel
  },
  {
    key: 'web-search',
    label: 'Web search',
    icon: 'pi pi-globe',
    group: 'workspace',
    adminOnly: true,
    description: 'Web search provider for grounded answers.',
    component: BraveSearchPanel
  },
  {
    key: 'tools-mcp',
    label: 'Tools & MCP',
    icon: 'pi pi-microchip',
    group: 'workspace',
    adminOnly: true,
    description: 'The MCP server and the tools your agents can call.',
    tabs: [
      { key: 'server', label: 'Server', icon: 'pi pi-server', component: McpServerPanel },
      { key: 'netscaler', label: 'NetScaler tools', icon: 'pi pi-sliders-h', component: NextGenApiPanel }
    ]
  },
  {
    key: 'assistant',
    label: 'Assistant',
    icon: 'pi pi-comments',
    group: 'workspace',
    adminOnly: true,
    description: 'Chat portal, attachments, notifications, and orchestration.',
    component: AssistantSettingsPanel,
    props: () => ({ isAdmin: isAdmin.value })
  },
  {
    key: 'integrations',
    label: 'Integrations',
    icon: 'pi pi-send',
    group: 'workspace',
    adminOnly: true,
    description: 'Outbound notifications and email delivery.',
    tabs: [
      { key: 'slack', label: 'Slack', icon: 'pi pi-send', component: SlackNotificationsPanel },
      { key: 'email', label: 'SMTP / Email', icon: 'pi pi-envelope', component: SmtpEmailPanel }
    ]
  },
  {
    key: 'users',
    label: 'Users',
    icon: 'pi pi-users',
    group: 'access',
    adminOnly: true,
    description: 'Accounts, roles, and access.',
    component: UsersPanel
  },
  {
    key: 'security',
    label: 'Security',
    icon: 'pi pi-shield',
    group: 'access',
    description: 'Passkeys and platform sign-in policy.',
    component: SecuritySettingsPanel
  },
  {
    key: 'about',
    label: 'About & updates',
    icon: 'pi pi-info-circle',
    group: 'system',
    description: 'Version information and available updates.',
    component: UpdatesPanel,
    props: () => ({ isAdmin: isAdmin.value })
  },
  {
    key: 'license',
    label: 'License',
    icon: 'pi pi-id-card',
    group: 'system',
    description: 'Activation and entitlements.',
    component: LicensePanel
  },
  {
    key: 'legal',
    label: 'Legal',
    icon: 'pi pi-book',
    group: 'system',
    description: 'Policies and agreements.',
    component: LegalLinksPanel
  }
]

// Maps deprecated/old section keys to the new IA so existing deep links keep working.
const LEGACY_SECTION_MAP = {
  'ai-providers': 'ai-models',
  usage: 'ai-models',
  jpilot: 'assistant',
  mcp: 'tools-mcp',
  nextgen: 'tools-mcp',
  'beta-features': 'tools-mcp',
  slack: 'integrations',
  about: 'about',
  'brave-search': 'web-search'
}

const sections = computed(() => allSections.filter((s) => !s.adminOnly || isAdmin.value))
const sectionByKey = computed(() => new Map(sections.value.map((s) => [s.key, s])))
const defaultKey = computed(() => (isAdmin.value ? 'ai-models' : 'security'))

const search = ref('')
const activeKey = ref(defaultKey.value)
const activeTabKey = ref('')
const mobileShowDetail = ref(false)

const matchesSearch = (section) => {
  const q = search.value.trim().toLowerCase()
  if (!q) return true
  return (
    section.label.toLowerCase().includes(q) ||
    (section.description || '').toLowerCase().includes(q) ||
    (GROUP_LABELS[section.group] || '').toLowerCase().includes(q) ||
    (section.tabs || []).some((t) => t.label.toLowerCase().includes(q))
  )
}

const visibleGroups = computed(() => {
  const groups = []
  for (const section of sections.value) {
    if (!matchesSearch(section)) continue
    let group = groups.find((g) => g.id === section.group)
    if (!group) {
      group = { id: section.group, label: GROUP_LABELS[section.group] || section.group, sections: [] }
      groups.push(group)
    }
    group.sections.push(section)
  }
  return groups
})

const hasResults = computed(() => visibleGroups.value.length > 0)

const activeSection = computed(() => sectionByKey.value.get(activeKey.value) || sections.value[0])

const activeTab = computed(() => {
  const tabs = activeSection.value?.tabs
  if (!tabs) return null
  return tabs.find((t) => t.key === activeTabKey.value) || tabs[0]
})

const activeComponent = computed(() =>
  activeSection.value?.tabs ? activeTab.value?.component : activeSection.value?.component
)

const activeComponentKey = computed(() =>
  activeSection.value?.tabs ? `${activeKey.value}:${activeTab.value?.key}` : activeKey.value
)

const activeComponentProps = computed(() => activeSection.value?.props?.() || {})

function resolveKeyFromQuery() {
  const raw = route.query.section
  if (typeof raw !== 'string' || !raw) return defaultKey.value
  if (sectionByKey.value.has(raw)) return raw
  const mapped = LEGACY_SECTION_MAP[raw]
  if (mapped && sectionByKey.value.has(mapped)) return mapped
  return defaultKey.value
}

function syncFromQuery() {
  activeKey.value = resolveKeyFromQuery()
  const section = activeSection.value
  if (section?.tabs) {
    // Use a dedicated `pane` param so it never clashes with child panels
    // (NextGenApiPanel, OtherAppliancesView) that drive their own `tab` query.
    const pane = route.query.pane
    const valid = section.tabs.some((t) => t.key === pane)
    activeTabKey.value = valid ? pane : section.tabs[0].key
  } else {
    activeTabKey.value = ''
  }
}

function selectSection(key) {
  activeKey.value = key
  mobileShowDetail.value = true
  const section = sectionByKey.value.get(key)
  const query = { ...route.query, section: key }
  // Drop any child-panel tab state carried over from the previous section.
  delete query.tab
  if (section?.tabs) {
    activeTabKey.value = section.tabs[0].key
    query.pane = section.tabs[0].key
  } else {
    delete query.pane
    activeTabKey.value = ''
  }
  router.replace({ query })
}

function selectTab(key) {
  activeTabKey.value = key
  router.replace({ query: { ...route.query, section: activeKey.value, pane: key } })
}

watch(() => [route.query.section, route.query.pane], syncFromQuery)

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me')
    currentUser.value = data
  } catch {
    // Fall back to stored user from login.
  }
  syncFromQuery()
})

syncFromQuery()
</script>

<style scoped>
.page {
  animation: page-in 0.35s ease;
}

.settings-beta-layout {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}

/* ---- Navigation rail (master) ---- */
.settings-rail {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
  background: var(--p-content-background);
  padding: 1rem 0.75rem;
}

.settings-rail-head {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0 0.25rem;
}

.settings-rail-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.settings-search :deep(input) {
  width: 100%;
}

.settings-rail-nav {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.rail-group-label {
  margin: 0.65rem 0.5rem 0.2rem;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.rail-group-label:first-child {
  margin-top: 0;
}

.rail-link {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  padding: 0.55rem 0.6rem;
  border: 1px solid transparent;
  border-radius: 0.6rem;
  background: transparent;
  color: var(--p-text-color);
  font-size: 0.875rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.rail-link-icon {
  font-size: 1rem;
  color: var(--p-text-muted-color);
  flex-shrink: 0;
}

.rail-link-label {
  flex: 1;
}

.rail-link-chevron {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
  opacity: 0;
}

.rail-link:hover {
  background: var(--p-surface-100);
  border-color: var(--p-content-border-color);
}

.rail-link-active {
  background: var(--p-surface-100);
  border-color: var(--p-content-border-color);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.rail-link-active .rail-link-icon,
.rail-link-active .rail-link-label {
  color: var(--p-primary-color);
}

.rail-empty {
  padding: 0.75rem 0.6rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

/* ---- Detail pane ---- */
.settings-detail {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.detail-back {
  display: none;
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.6rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  cursor: pointer;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.detail-title-icon {
  font-size: 1.2rem;
  color: var(--p-primary-color);
}

.detail-desc {
  margin: 0.3rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

.detail-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  border-bottom: 1px solid var(--p-content-border-color);
  padding-bottom: 0.5rem;
}

.detail-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.8rem;
  border: 1px solid transparent;
  border-radius: 0.6rem;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.detail-tab:hover {
  background: var(--p-surface-100);
  color: var(--p-text-color);
}

.detail-tab-active {
  background: var(--p-surface-100);
  border-color: var(--p-content-border-color);
  color: var(--p-primary-color);
}

.detail-body {
  min-width: 0;
}

@media (max-width: 991px) {
  .settings-beta-layout {
    grid-template-columns: 1fr;
    gap: 0;
  }

  /* Mobile: drill-in master/detail — show one pane at a time. */
  .settings-beta-layout.show-detail .settings-rail {
    display: none;
  }

  .settings-beta-layout:not(.show-detail) .settings-detail {
    display: none;
  }

  /* Flat, edge-to-edge list on mobile instead of a boxed card. */
  .settings-rail {
    position: static;
    border: none;
    border-radius: 0;
    background: transparent;
    padding: 0;
    gap: 1.25rem;
  }

  .settings-rail-head {
    padding: 0;
  }

  .settings-rail-title {
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: -0.01em;
  }

  .settings-search :deep(input) {
    height: 2.75rem;
  }

  .rail-group-label {
    margin: 0 0.25rem 0.35rem;
  }

  .settings-rail-nav {
    gap: 0.4rem;
  }

  /* Taller, full-width rows with a clear divider and visible chevron. */
  .rail-link {
    padding: 0.9rem 0.85rem;
    border: 1px solid var(--p-content-border-color);
    border-radius: 0.75rem;
    background: var(--p-content-background);
    font-size: 0.95rem;
  }

  .rail-link-icon {
    font-size: 1.15rem;
  }

  .rail-link-chevron {
    opacity: 1;
    font-size: 0.8rem;
  }

  .detail-back {
    display: inline-flex;
  }

  .detail-title {
    font-size: 1.25rem;
  }

  .detail-tabs {
    gap: 0.4rem;
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
  }

  .detail-tab {
    flex: 0 0 auto;
    white-space: nowrap;
  }
}

@keyframes page-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
