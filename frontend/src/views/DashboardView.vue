<template>
  <div class="home">
    <Message
      v-if="updateInfo?.update_available"
      severity="warn"
      :closable="false"
      class="home-update"
    >
      <strong>{{ updateInfo.latest_display_version }}</strong> is available
      (you are on {{ updateInfo.display_version }}).
      <RouterLink to="/settings?section=about" class="home-update-link">View in About &amp; Updates</RouterLink>
    </Message>

    <!-- Hero -->
    <header class="home-hero" :style="{ '--stagger': '0ms' }">
      <p class="home-eyebrow">
        <i class="pi pi-sparkles" aria-hidden="true" />
        JPilot Home
      </p>
      <h1 class="home-greeting">{{ greeting }}</h1>
      <p class="home-subtitle">Pick a role to start a guided chat, or jump straight into JPilot.</p>
      <div class="home-hero-actions">
        <button type="button" class="home-cta" @click="openChat()">
          <i class="pi pi-comments" aria-hidden="true" />
          Open JPilot chat
        </button>
        <RouterLink to="/calibration-studio" class="home-cta home-cta-ghost">
          <i class="pi pi-sliders-h" aria-hidden="true" />
          Calibration Studio
        </RouterLink>
      </div>
    </header>

    <!-- Role launch tiles -->
    <ul class="home-roles" role="list">
      <li
        v-for="(role, index) in roles"
        :key="role.id"
        :style="{ '--stagger': `${120 + index * 70}ms` }"
      >
        <button
          type="button"
          class="home-role glass-panel"
          :style="{ '--persona-accent': role.accent }"
          @click="openChat(role.id)"
        >
          <span class="home-role-icon"><i :class="role.icon" aria-hidden="true" /></span>
          <span class="home-role-copy">
            <span class="home-role-head">
              <span class="home-role-name">{{ role.label }}</span>
              <span class="home-role-cap">{{ role.capability }}</span>
            </span>
            <span class="home-role-desc">{{ role.description }}</span>
          </span>
          <i class="pi pi-arrow-right home-role-arrow" aria-hidden="true" />
        </button>
      </li>
    </ul>

    <!-- Lower region: usage (left) + overview & articles (right rail) -->
    <div class="home-lower">
      <section class="home-activity" :style="{ '--stagger': '320ms' }" aria-label="Usage activity">
        <DashboardActivityPanel :is-admin="isAdmin" />
      </section>

      <div class="home-rail">
        <section class="home-overview glass-panel" :style="{ '--stagger': '380ms' }" aria-label="Platform overview">
          <div class="home-stat-row">
            <RouterLink to="/appliances" class="home-stat">
              <span class="home-stat-label">Appliances</span>
              <span class="home-stat-value">{{ stats.netscalers + stats.otherAppliances }}</span>
              <span class="home-stat-detail">{{ stats.netscalers }} NetScaler · {{ stats.otherAppliances }} other</span>
            </RouterLink>
            <RouterLink :to="isAdmin ? '/settings?section=ai-providers' : '/'" class="home-stat">
              <span class="home-stat-label">AI Providers</span>
              <span class="home-stat-value">{{ stats.providers }}</span>
              <span class="home-stat-detail">{{ stats.providers === 1 ? '1 configured' : `${stats.providers} configured` }}</span>
            </RouterLink>
          </div>

          <ul class="home-status">
            <li><span class="home-dot home-dot-ok" aria-hidden="true" />API online</li>
            <li>
              <span class="home-dot" :class="mcpStatus.online ? 'home-dot-ok' : 'home-dot-bad'" aria-hidden="true" />
              MCP {{ mcpStatus.online ? 'online' : 'offline' }}
            </li>
            <li><span class="home-dot home-dot-ok" aria-hidden="true" />MongoDB connected</li>
          </ul>

          <div v-if="quickActions.length" class="home-quick">
            <button
              v-for="action in quickActions"
              :key="action.to"
              type="button"
              class="home-quick-btn"
              :class="{ 'home-quick-btn-primary': action.to === '/jpilot' }"
              @click="router.push(action.to)"
            >
              <i :class="action.icon" aria-hidden="true" />
              <span>{{ action.label }}</span>
            </button>
          </div>
        </section>

        <!-- Nexxus Tech articles -->
        <section class="home-articles glass-panel" :style="{ '--stagger': '440ms' }" aria-label="Articles from Nexxus Tech">
          <div class="home-articles-head">
            <div>
              <p class="home-articles-eyebrow">From Nexxus Tech</p>
              <h3 class="home-articles-title">Articles of interest</h3>
            </div>
            <a :href="NEXXUS_TECH.blogUrl" target="_blank" rel="noopener noreferrer" class="home-articles-all">
              View all <i class="pi pi-arrow-up-right" aria-hidden="true" />
            </a>
          </div>

          <div v-if="articlesLoading" class="home-articles-loading">
            <ProgressSpinner style="width: 1.5rem; height: 1.5rem" />
          </div>

          <ul v-else class="home-articles-list">
            <li v-for="article in articles" :key="article.slug">
              <a
                :href="nexxusBlogArticleUrl(article.slug)"
                target="_blank"
                rel="noopener noreferrer"
                class="home-article"
              >
                <span class="home-article-bar" :style="{ background: article.coverColor || 'var(--p-primary-500)' }" />
                <span class="home-article-body">
                  <span class="home-article-meta">
                    <span class="home-article-cat">{{ article.category }}</span>
                    <span class="home-article-read">{{ article.readTime }} min</span>
                  </span>
                  <span class="home-article-title">{{ article.title }}</span>
                </span>
                <i class="pi pi-arrow-right home-article-arrow" aria-hidden="true" />
              </a>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import DashboardActivityPanel from '../components/DashboardActivityPanel.vue'
import { JPILOT_ROLES, writeLastUsedPersona } from '../config/jpilotRoles'
import { getDashboardQuickActions } from '../config/jpilotRecommendedActions'
import { isNetScalerVendor } from '../config/applianceVendors'
import { NEXXUS_TECH, nexxusBlogArticleUrl } from '../config/nexxusTech'
import { fetchNexxusBlogArticles } from '../services/nexxusBlog'
import api from '../services/api'
import { getMcpStatus } from '../services/mcp'
import { checkForUpdates } from '../services/system'
import { getStoredUser } from '../services/auth'

const router = useRouter()
const currentUser = ref(getStoredUser())
const updateInfo = ref(null)
const isAdmin = computed(() => currentUser.value?.role === 'admin')
const roles = JPILOT_ROLES
const quickActions = computed(() => getDashboardQuickActions(isAdmin.value))

const stats = reactive({ netscalers: 0, providers: 0, otherAppliances: 0 })
const mcpStatus = reactive({ online: false })
const articles = ref([])
const articlesLoading = ref(true)

const greeting = computed(() => {
  const name = currentUser.value?.displayName || currentUser.value?.username
  const hour = new Date().getHours()
  const part = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : hour < 22 ? 'Good evening' : 'Hello'
  return name ? `${part}, ${name}.` : `${part}.`
})

function openChat(roleId) {
  if (roleId) writeLastUsedPersona(roleId)
  router.push('/jpilot')
}

onMounted(async () => {
  fetchNexxusBlogArticles()
    .then((list) => {
      articles.value = list
    })
    .finally(() => {
      articlesLoading.value = false
    })

  try {
    const meRes = await api.get('/auth/me')
    currentUser.value = meRes.data
  } catch {
    // Home remains usable without role refresh.
  }
  try {
    const [appliancesRes, providersRes, status, updates] = await Promise.all([
      api.get('/appliances'),
      api.get('/ai-providers'),
      getMcpStatus().catch(() => ({ online: false })),
      checkForUpdates(false).catch(() => null)
    ])
    stats.netscalers = appliancesRes.data.filter((item) => isNetScalerVendor(item.vendor)).length
    stats.providers = providersRes.data.length
    stats.otherAppliances = appliancesRes.data.filter((item) => !isNetScalerVendor(item.vendor)).length
    mcpStatus.online = status.online
    updateInfo.value = updates
  } catch {
    // Home remains usable without stats.
  }
})
</script>

<style scoped>
.home {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1.25rem 1.25rem 0.5rem;
}

.home-update {
  margin: 0;
}

.home-update-link {
  margin-left: 0.4rem;
  color: inherit;
  font-weight: 600;
  text-decoration: underline;
}

/* ---- Entrance ---- */
.home-hero,
.home-roles > li,
.home-activity,
.home-overview,
.home-articles {
  animation: home-rise 320ms cubic-bezier(0.4, 0, 0.2, 1) both;
  animation-delay: var(--stagger, 0ms);
}

@keyframes home-rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: none; }
}

/* ---- Hero ---- */
.home-hero {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.home-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.home-eyebrow .pi {
  color: var(--p-primary-color);
}

.home-greeting {
  margin: 0;
  font-size: clamp(1.5rem, 1rem + 2vw, 2.1rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--p-text-color);
}

.home-subtitle {
  margin: 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}

.home-hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.25rem;
}

.home-cta {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 0.95rem;
  border-radius: 0.7rem;
  border: 1px solid transparent;
  font: inherit;
  font-size: 0.85rem;
  font-weight: 650;
  cursor: pointer;
  text-decoration: none;
  color: #fff;
  background: var(--p-primary-color);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--p-primary-color) 30%, transparent);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.home-cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px color-mix(in srgb, var(--p-primary-color) 38%, transparent);
}

.home-cta-ghost {
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-content-background) 60%, transparent);
  border-color: color-mix(in srgb, var(--p-content-border-color) 60%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: none;
}

.home-cta-ghost:hover {
  background: color-mix(in srgb, var(--p-content-background) 82%, transparent);
  box-shadow: 0 6px 16px rgba(2, 6, 23, 0.08);
}

/* ---- Role tiles ---- */
.home-roles {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.home-role {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  width: 100%;
  text-align: left;
  padding: 0.85rem;
  border-radius: var(--content-radius);
  cursor: pointer;
  color: inherit;
  font: inherit;
  transition: transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

.home-role:hover,
.home-role:focus-visible {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--persona-accent) 50%, transparent);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.22),
    0 12px 28px color-mix(in srgb, var(--persona-accent) 22%, rgba(2, 6, 23, 0.12));
  outline: none;
}

.home-role-icon {
  flex-shrink: 0;
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 0.6rem;
  display: grid;
  place-items: center;
  font-size: 1.05rem;
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 14%, transparent);
}

.home-role-copy {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
  flex: 1;
}

.home-role-head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.home-role-name {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--p-text-color);
}

.home-role-cap {
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 0.08rem 0.4rem;
  border-radius: 999px;
  color: var(--persona-accent);
  background: color-mix(in srgb, var(--persona-accent) 12%, transparent);
}

.home-role-desc {
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-role-arrow {
  flex-shrink: 0;
  font-size: 0.8rem;
  margin-top: 0.3rem;
  color: var(--p-text-muted-color);
  transition: transform 0.18s ease, color 0.18s ease;
}

.home-role:hover .home-role-arrow,
.home-role:focus-visible .home-role-arrow {
  transform: translateX(3px);
  color: var(--persona-accent);
}

/* ---- Lower region ---- */
.home-lower {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.55fr 1fr;
  gap: 0.9rem;
}

.home-activity {
  min-height: 0;
  overflow: auto;
  border-radius: var(--content-radius);
}

/* DashboardActivityPanel ships its own .content-panel root (glassed by the
   global atmosphere rule); let it take its natural height and scroll the cell. */
.home-activity :deep(.activity-panel) {
  min-height: 100%;
}

.home-rail {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.home-overview {
  border-radius: var(--content-radius);
  padding: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.home-stat-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
}

.home-stat {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding: 0.6rem 0.7rem;
  border-radius: 0.6rem;
  text-decoration: none;
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 45%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 40%, transparent);
  transition: border-color 0.16s ease, transform 0.16s ease;
}

.home-stat:hover {
  transform: translateY(-1px);
  border-color: var(--p-primary-300);
}

.home-stat-label {
  font-size: 0.66rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.home-stat-value {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--p-text-color);
}

.home-stat-detail {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}

.home-status {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
}

.home-status li {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--p-text-color);
}

.home-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.home-dot-ok {
  background: var(--p-green-500);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-green-500) 22%, transparent);
}

.home-dot-bad {
  background: var(--p-red-500);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-red-500) 22%, transparent);
}

.home-quick {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.home-quick-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.65rem;
  border-radius: 0.55rem;
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 45%, transparent);
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

.home-quick-btn:hover {
  transform: translateY(-1px);
  border-color: var(--p-primary-300);
}

.home-quick-btn-primary {
  color: var(--p-primary-color);
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}

.home-quick-btn .pi {
  font-size: 0.8rem;
}

/* ---- Articles ---- */
.home-articles {
  flex: 1;
  min-height: 0;
  border-radius: var(--content-radius);
  padding: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  overflow: hidden;
}

.home-articles-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.home-articles-eyebrow {
  margin: 0;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--p-primary-color);
}

.home-articles-title {
  margin: 0.1rem 0 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.home-articles-all {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.76rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--p-primary-color);
  text-decoration: none;
}

.home-articles-all:hover {
  text-decoration: underline;
}

.home-articles-all .pi {
  font-size: 0.66rem;
}

.home-articles-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.home-articles-list {
  list-style: none;
  margin: 0;
  padding: 0.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 0;
  overflow: auto;
}

.home-article {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.55rem 0.6rem;
  border-radius: 0.65rem;
  text-decoration: none;
  color: inherit;
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 45%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 40%, transparent);
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.home-article:hover {
  transform: translateY(-1px);
  border-color: var(--p-primary-300);
  box-shadow: 0 6px 16px rgba(2, 6, 23, 0.08);
}

.home-article-bar {
  width: 3px;
  align-self: stretch;
  border-radius: 999px;
  flex-shrink: 0;
}

.home-article-body {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
}

.home-article-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.66rem;
  color: var(--p-text-muted-color);
}

.home-article-cat {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--p-primary-color);
}

.home-article-title {
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.3;
  color: var(--p-text-color);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-article-arrow {
  flex-shrink: 0;
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
  transition: transform 0.16s ease, color 0.16s ease;
}

.home-article:hover .home-article-arrow {
  transform: translateX(2px);
  color: var(--p-primary-color);
}

/* ---- Responsive: stack and allow normal page scroll on small screens ---- */
@media (max-width: 991px) {
  .home {
    height: auto;
    flex: none;
    padding: 0.25rem 0.25rem 1rem;
  }

  .home-roles {
    grid-template-columns: 1fr;
  }

  .home-lower {
    grid-template-columns: 1fr;
  }

  .home-activity {
    overflow: visible;
  }

  /* No backdrop on mobile — keep panels readable over the app surface. */
  .home-role.glass-panel,
  .home-overview.glass-panel,
  .home-articles.glass-panel {
    background: var(--p-content-background);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}

/* ---- Reduced motion ---- */
@media (prefers-reduced-motion: reduce) {
  .home-hero,
  .home-roles > li,
  .home-activity,
  .home-overview,
  .home-articles {
    animation: none;
  }

  .home-role:hover,
  .home-role:focus-visible,
  .home-cta:hover,
  .home-quick-btn:hover,
  .home-article:hover {
    transform: none;
  }
}
</style>
