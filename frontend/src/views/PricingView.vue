<template>
  <div class="page plans-page" :class="{ 'plans-page--overlay': compareUsesOverlay }">
    <!-- Hero -->
    <header class="plans-hero">
      <p class="plans-eyebrow m-0">
        <i class="pi pi-tags" aria-hidden="true" />
        Plans
      </p>
      <h1 class="plans-hero-title m-0">Plans built for secure ADC operations</h1>
      <p class="plans-hero-copy m-0">
        JPilot runs <strong>on-premises</strong> with Docker, manages
        <strong>multiple NetScaler/ADC environments</strong>, and keeps appliance
        credentials and configuration <strong>under your control</strong> — encrypted,
        inside your network, and never sent to the LLM.
      </p>
    </header>

    <!-- Plan cards -->
    <section
      class="plans-cards"
      :class="{ 'plans-cards--overlay': compareUsesOverlay }"
      aria-label="Plan options"
    >
      <div
        v-for="plan in PRICING_PLANS"
        :key="plan.id"
        class="plans-card-column"
      >
        <article
          class="plan-card glass-panel"
          :class="[
            `plan-card--${plan.id}`,
            {
              'plan-card--current': isCurrentPlan(plan),
              'plan-card--recommended': plan.highlighted && !isCurrentPlan(plan)
            }
          ]"
          :style="planAccentVars(plan)"
        >
          <span class="plan-card__accent" aria-hidden="true" />

          <header class="plan-card__head">
            <div class="plan-card__title-row">
              <h2 class="plan-card__name m-0">{{ plan.name }}</h2>
              <Tag
                v-if="isCurrentPlan(plan)"
                :value="currentPlanTagLabel(plan)"
                :severity="currentPlanTagSeverity(plan)"
                class="plan-card__tag"
              />
              <Tag
                v-else-if="plan.highlighted"
                value="Recommended"
                severity="info"
              />
            </div>
            <p class="plan-card__tagline m-0">{{ plan.tagline }}</p>

            <div v-if="plan.priceLabel || (plan.priceDetail && !compareUsesOverlay)" class="plan-card__price">
              <span v-if="plan.priceLabel" class="plan-card__price-value">{{ plan.priceLabel }}</span>
              <span v-if="plan.priceDetail && !compareUsesOverlay" class="plan-card__price-detail">
                {{ plan.priceDetail }}
              </span>
            </div>
          </header>

          <template v-if="!compareUsesOverlay">
            <p v-if="planInheritNote(plan)" class="plan-card__inherit m-0">
              {{ planInheritNote(plan) }}
            </p>

            <ul class="plan-card__bullets m-0 p-0">
              <li v-for="bullet in planBullets(plan)" :key="bullet">
                <i class="pi pi-check" aria-hidden="true" />
                <span>{{ bullet }}</span>
              </li>
            </ul>

            <p v-if="planMoreCount(plan) > 0" class="plan-card__more m-0">
              + {{ planMoreCount(plan) }} more in the comparison below
            </p>
          </template>

          <div v-if="plan.ctaHref || plan.ctaLabel" class="plan-card__cta">
            <Button
              v-if="plan.ctaHref"
              as="a"
              :href="plan.ctaHref"
              target="_blank"
              rel="noopener noreferrer"
              :label="plan.ctaLabel"
              icon="pi pi-envelope"
              icon-pos="right"
              class="w-full"
            />
            <Button
              v-else-if="plan.ctaLabel"
              :label="plan.ctaLabel"
              class="w-full"
              severity="secondary"
              outlined
              disabled
            />
          </div>
        </article>

        <div
          v-if="compareUsesOverlay"
          class="plan-column-features"
          :style="planAccentVars(plan)"
        >
          <p v-if="planInheritNote(plan)" class="plan-column-features__inherit m-0">
            {{ planInheritNote(plan) }}
          </p>
          <ul class="plan-column-features__list m-0 p-0">
            <li v-for="(label, index) in planAllFeatures(plan)" :key="`${plan.id}-${index}`">
              <i class="pi pi-check" aria-hidden="true" />
              <span>{{ label }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Comparison + platform highlights (desktop) -->
    <div v-if="!compareUsesOverlay" class="plans-details">
      <section class="plans-compare" aria-labelledby="compare-heading">
        <div class="plans-compare__head">
          <h2 id="compare-heading" class="plans-section-title m-0">What's included</h2>
          <p class="plans-section-copy m-0">
            Each tier builds on the one before it. Compare side by side, or expand a group to see the details.
          </p>
        </div>

        <div class="compare-table-card content-panel">
          <PlansCompareTable
            :footnotes="planFootnotes"
            :is-current-plan="isCurrentPlan"
            :current-plan-tag-label="currentPlanTagLabel"
            :current-plan-tag-severity="currentPlanTagSeverity"
          />
        </div>
      </section>

      <aside class="plans-details__aside">
        <PlansTrustCards />

        <section class="plans-enterprise" aria-label="Enterprise contact">
          <div class="enterprise-cta glass-panel">
            <span class="enterprise-cta__accent" aria-hidden="true" />
            <div class="enterprise-cta__head">
              <span class="enterprise-cta__icon" aria-hidden="true">
                <i class="pi pi-building-columns" />
              </span>
              <div class="enterprise-cta__body min-w-0">
                <h2 class="enterprise-cta__title m-0">Need Enterprise?</h2>
                <p class="enterprise-cta__copy m-0">{{ NEXXUS_TECH.enterpriseCtaCopy }}</p>
              </div>
            </div>
            <a
              :href="NEXXUS_TECH.contactUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="enterprise-cta__btn"
            >
              Contact us
              <i class="pi pi-arrow-up-right" aria-hidden="true" />
            </a>
          </div>
        </section>
      </aside>
    </div>

    <!-- Bottom row (tablet / iPad) -->
    <div v-else class="plans-footer">
      <button
        id="compare-heading"
        type="button"
        class="plans-footer__compare glass-panel"
        @click="openComparePanel"
      >
        <div class="plans-footer__compare-head">
          <span class="plans-footer__compare-icon-wrap" aria-hidden="true">
            <i class="pi pi-table" />
          </span>
          <div class="plans-footer__compare-body min-w-0">
            <span class="plans-section-title m-0">What's included</span>
            <p class="plans-footer__compare-hint m-0">
              Compare all features across Early Access, Enterprise, and Enterprise Pro.
            </p>
          </div>
        </div>
        <span class="plans-footer__compare-btn">
          View comparison
          <i class="pi pi-arrow-up-right" aria-hidden="true" />
        </span>
      </button>

      <section class="plans-footer__enterprise" aria-label="Enterprise contact">
        <div class="enterprise-cta enterprise-cta--compact glass-panel">
          <span class="enterprise-cta__accent" aria-hidden="true" />
          <div class="enterprise-cta__head">
            <span class="enterprise-cta__icon" aria-hidden="true">
              <i class="pi pi-building-columns" />
            </span>
            <div class="enterprise-cta__body min-w-0">
              <h2 class="enterprise-cta__title m-0">Need Enterprise?</h2>
              <p class="enterprise-cta__copy m-0">{{ NEXXUS_TECH.enterpriseCtaCopyShort }}</p>
            </div>
          </div>
          <a
            :href="NEXXUS_TECH.contactUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="enterprise-cta__btn"
          >
            Contact us
            <i class="pi pi-arrow-up-right" aria-hidden="true" />
          </a>
        </div>
      </section>
    </div>

    <Teleport to="body">
      <Drawer
        v-model:visible="comparePanelVisible"
        position="bottom"
        modal
        dismissable
        :show-close-icon="true"
        header="What's included"
        class="plans-compare-drawer"
      >
        <PlansCompareTable
          dialog-mode
          :footnotes="planFootnotes"
          :is-current-plan="isCurrentPlan"
          :current-plan-tag-label="currentPlanTagLabel"
          :current-plan-tag-severity="currentPlanTagSeverity"
        />
      </Drawer>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import PlansCompareTable from '../components/plans/PlansCompareTable.vue'
import PlansTrustCards from '../components/plans/PlansTrustCards.vue'
import { licenseTypeToPlanId, resolveLicensePlanTheme } from '../config/licensePlanThemes'
import { NEXXUS_TECH } from '../config/nexxusTech'
import {
  comparisonFootnotes,
  featureKey,
  featureLabel,
  PLAN_FEATURE_GROUPS,
  planAccentVars,
  PRICING_PLANS
} from '../config/pricingPlans'
import { getLicense } from '../services/system'

const PLAN_CARD_BULLET_LIMIT = 4
const COMPARE_OVERLAY_MEDIA = ['(max-width: 1280px)', '(pointer: coarse)']

const license = ref(null)
const compareUsesOverlay = ref(false)
const comparePanelVisible = ref(false)
const compareOverlayMediaList = []

const activePlanId = computed(() => {
  if (!license.value?.hasLicenseCode) return 'free'
  const type = license.value.details?.licenseType ?? license.value.licenseType
  const planTheme = resolveLicensePlanTheme(type)
  if (planTheme === 'trial') return 'free'
  return licenseTypeToPlanId(type) || 'free'
})

const licensePlanTheme = computed(() => {
  if (!license.value?.hasLicenseCode) return 'free'
  const type = license.value.details?.licenseType ?? license.value.licenseType
  return resolveLicensePlanTheme(type)
})

const planFootnotes = comparisonFootnotes()

function isCurrentPlan(plan) {
  return activePlanId.value === plan.id
}

function currentPlanTagLabel(plan) {
  if (!isCurrentPlan(plan)) return 'Current'
  if (licensePlanTheme.value === 'trial') return 'Trial'
  return 'Current plan'
}

function currentPlanTagSeverity(plan) {
  if (!isCurrentPlan(plan)) return 'success'
  if (licensePlanTheme.value === 'trial') return 'warn'
  return 'success'
}

/** The feature group that a plan tier introduces (drives card bullets). */
function planGroup(plan) {
  return PLAN_FEATURE_GROUPS.find((group) => group.minPlan === plan.id) ?? null
}

function planBullets(plan) {
  const group = planGroup(plan)
  if (!group) return []
  return group.features.slice(0, PLAN_CARD_BULLET_LIMIT).map(featureLabel)
}

function planMoreCount(plan) {
  const group = planGroup(plan)
  if (!group) return 0
  return Math.max(0, group.features.length - PLAN_CARD_BULLET_LIMIT)
}

function planAllFeatures(plan) {
  const group = planGroup(plan)
  if (!group) return []
  return group.features.map(featureLabel)
}

/** "Everything in <previous tier>, plus" note for inheriting tiers. */
function planInheritNote(plan) {
  const index = PRICING_PLANS.findIndex((item) => item.id === plan.id)
  if (index <= 0) return ''
  const previous = PRICING_PLANS[index - 1]
  return `Everything in ${previous.name}, plus`
}

function syncCompareOverlay() {
  compareUsesOverlay.value = COMPARE_OVERLAY_MEDIA.some((query) => window.matchMedia(query).matches)
}

function openComparePanel() {
  comparePanelVisible.value = true
}

watch(compareUsesOverlay, (overlay) => {
  if (!overlay) comparePanelVisible.value = false
})

onMounted(async () => {
  syncCompareOverlay()
  for (const query of COMPARE_OVERLAY_MEDIA) {
    const media = window.matchMedia(query)
    media.addEventListener('change', syncCompareOverlay)
    compareOverlayMediaList.push(media)
  }
  try {
    license.value = await getLicense()
  } catch {
    // Plans page works without license data.
  }
})

onUnmounted(() => {
  for (const media of compareOverlayMediaList) {
    media.removeEventListener('change', syncCompareOverlay)
  }
})
</script>

<style scoped>
.plans-page {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1.25rem 1.25rem 0.5rem;
  animation: page-in 0.35s ease;
  flex: 1;
  min-height: 0;
}

/* ---------- Hero ---------- */
.plans-hero {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.plans-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

.plans-eyebrow .pi {
  color: var(--p-primary-color);
}

.plans-hero-title {
  font-size: clamp(1.5rem, 1rem + 2vw, 2.1rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
  color: var(--p-text-color);
}

.plans-hero-copy {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--p-text-muted-color);
  max-width: 46rem;
}

.plans-hero-copy strong {
  color: var(--p-text-color);
  font-weight: 600;
}

/* ---------- Section headings ---------- */
.plans-section-title {
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--p-text-color);
}

.plans-section-copy {
  margin-top: 0.4rem;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--p-text-muted-color);
  max-width: 44rem;
}

/* ---------- Plan cards ---------- */
.plans-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  align-items: start;
}

.plans-cards:not(.plans-cards--overlay) .plans-card-column {
  display: contents;
}

.plans-cards--overlay .plans-card-column {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.plan-column-features {
  --tier-accent: var(--p-primary-color);
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0 0.35rem;
}

.plan-column-features__inherit {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.plan-column-features__list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  list-style: none;
}

.plan-column-features__list li {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--p-text-color);
}

.plan-column-features__list li i {
  flex-shrink: 0;
  margin-top: 0.2rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--tier-accent);
}

.plan-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: var(--content-radius);
  overflow: hidden;
  transition:
    transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.18s cubic-bezier(0.4, 0, 0.2, 1);
  /* Per-tier accent — drives top bar, checks, and hover glow. */
  --tier-accent: var(--p-primary-color);
  --tier-accent-soft: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  --card-accent: var(--tier-accent);
}

.plan-card :deep(.plan-card__tag) {
  background: color-mix(in srgb, var(--tier-accent) 16%, transparent) !important;
  color: var(--tier-accent) !important;
  border: 1px solid color-mix(in srgb, var(--tier-accent) 32%, transparent) !important;
}

.plan-card__accent {
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: var(--tier-accent);
  opacity: 0.85;
}

@media (hover: hover) {
  .plan-card:hover,
  .enterprise-cta:hover {
    transform: translateY(-3px);
    border-color: color-mix(in srgb, #3b82f6 42%, transparent);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.22),
      0 12px 28px color-mix(in srgb, #3b82f6 16%, rgba(2, 6, 23, 0.12)),
      0 16px 34px color-mix(in srgb, #8b5cf6 14%, rgba(2, 6, 23, 0.1));
  }
}

.plan-card--current {
  border-color: color-mix(in srgb, var(--card-accent) 50%, transparent);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.22),
    0 12px 28px color-mix(in srgb, var(--card-accent) 22%, rgba(2, 6, 23, 0.12));
}

.plan-card--current .plan-card__accent {
  opacity: 1;
}

.plan-card__head {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.plan-card__title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.plan-card__name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.plan-card__tagline {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}

.plan-card__price {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-top: 0.5rem;
}

.plan-card__price-value {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  color: var(--p-text-color);
}

.plan-card__price-detail {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
}

.plan-card__inherit {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.plan-card__bullets {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  list-style: none;
  flex: 1;
}

.plan-card__bullets li {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--p-text-color);
}

.plan-card__bullets li i {
  flex-shrink: 0;
  margin-top: 0.2rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--tier-accent);
}

.plan-card__more {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.plan-card__cta {
  margin-top: auto;
  min-height: 2.35rem;
}

/* ---------- Comparison + highlights layout ---------- */
.plans-details {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: stretch;
}

.plans-details__aside {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ---------- Comparison ---------- */
.plans-compare {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.compare-table-card {
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.compare-table-card :deep(.plans-compare-table) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.compare-table-card :deep(.plans-compare-table__scroll) {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

:global(.plans-compare-drawer.p-drawer) {
  height: min(92dvh, 52rem) !important;
  max-height: 92dvh;
  width: 100% !important;
  max-width: 100% !important;
}

:global(.plans-compare-drawer .p-drawer-header) {
  padding: 0.9rem 1rem;
  flex-shrink: 0;
}

:global(.plans-compare-drawer .p-drawer-title) {
  font-size: 1.05rem;
  font-weight: 700;
}

:global(.plans-compare-drawer .p-drawer-content) {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

:global(.plans-compare-drawer .plans-compare-table) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

:global(.plans-compare-drawer .plans-compare-table__scroll--dialog) {
  flex: 1;
  min-height: 0;
  max-height: none;
}

@media (max-width: 899px) {
  :global(.plans-compare-drawer.p-drawer) {
    height: min(94dvh, 100%) !important;
    max-height: 94dvh;
    border-radius: 1rem 1rem 0 0;
  }

  :global(.plans-compare-drawer .p-drawer-header) {
    padding: 0.75rem 0.85rem;
    padding-top: max(0.75rem, env(safe-area-inset-top, 0px));
  }

  :global(.plans-compare-drawer .p-drawer-title) {
    font-size: 0.9375rem;
  }

  :global(.plans-compare-drawer .p-drawer-content) {
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }

  :global(.plans-compare-drawer .plans-compare-table__scroll--dialog) {
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
  }
}

.plans-page--overlay .plan-card.glass-panel {
  border-color: color-mix(in srgb, var(--tier-accent) 32%, var(--p-content-border-color));
}

.plans-page--overlay .plan-card--enterprise {
  --tier-accent: #3b82f6;
  --card-accent: #3b82f6;
}

.plans-page--overlay .plan-card--enterprise-pro {
  --tier-accent: #8b5cf6;
  --card-accent: #8b5cf6;
}

@media (min-width: 900px) {
  .plans-page--overlay {
    flex: 1;
    min-height: 0;
  }

  .plans-page--overlay .plans-cards {
    flex: 1;
    min-height: 0;
  }

  .plans-page--overlay .plans-footer {
    margin-top: auto;
    flex-shrink: 0;
  }

  .plans-page--overlay .plan-card {
    gap: 0.65rem;
    padding: 1.15rem 1.25rem;
    min-height: 8.25rem;
  }

  .plans-page--overlay .plan-card__title-row {
    min-height: 1.875rem;
    align-items: center;
  }

  .plans-page--overlay .plan-card__tagline {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: calc(2 * 1.45 * 0.8125rem);
  }
}

@media (max-width: 899px) {
  .plans-page--overlay {
    flex: 1 1 auto;
    min-height: auto;
    gap: 1rem;
    padding-bottom: 1rem;
  }

  .plans-page--overlay .plans-cards {
    flex: 0 0 auto;
    min-height: auto;
    gap: 1.25rem;
  }

  .plans-page--overlay .plans-footer {
    margin-top: 0.25rem;
  }

  .plans-page--overlay .plan-card {
    min-height: auto;
  }

  .plans-page--overlay .plan-card__tagline {
    min-height: auto;
    -webkit-line-clamp: unset;
  }

  .plans-cards--overlay .plans-card-column + .plans-card-column {
    padding-top: 0.25rem;
    border-top: 1px solid color-mix(in srgb, var(--p-content-border-color) 70%, transparent);
  }

  .plans-footer__compare,
  .plans-footer__enterprise .enterprise-cta {
    height: auto;
  }

  .plans-footer {
    gap: 0.65rem;
  }
}

/* ---------- Tablet / iPad footer ---------- */
.plans-footer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.75rem;
  align-items: stretch;
}

.plans-footer__compare {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: space-between;
  gap: 0.65rem;
  width: 100%;
  height: 100%;
  padding: 0.85rem 1rem;
  border-radius: var(--content-radius);
  text-align: left;
  cursor: pointer;
  color: inherit;
  font: inherit;
  transition:
    transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.18s cubic-bezier(0.4, 0, 0.2, 1);
  --card-accent: var(--p-primary-color);
}

.plans-footer__compare-head {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
}

.plans-footer__compare-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  color: var(--p-primary-color);
}

.plans-footer__compare-icon-wrap i {
  font-size: 0.9rem;
}

.plans-footer__compare-body {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.plans-footer__compare .plans-section-title {
  font-size: 0.875rem;
  font-weight: 600;
}

.plans-footer__compare-hint {
  font-size: 0.75rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
}

.plans-footer__compare-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  width: 100%;
  margin-top: auto;
  padding: 0.65rem 1rem;
  border-radius: var(--content-radius);
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 42%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
  font-weight: 600;
  font-size: 0.8125rem;
  line-height: 1.2;
}

.plans-footer__compare-btn i {
  font-size: 0.75rem;
}

.plans-footer__compare:hover,
.plans-footer__compare:focus-visible {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--card-accent) 50%, transparent);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.22),
    0 12px 28px color-mix(in srgb, var(--card-accent) 22%, rgba(2, 6, 23, 0.12));
  outline: none;
}

.plans-footer__enterprise {
  min-width: 0;
  display: flex;
}

.plans-footer__enterprise .enterprise-cta {
  flex: 1;
  height: 100%;
}

.enterprise-cta--compact {
  gap: 0.65rem;
  padding: 0.85rem 1rem;
}

.enterprise-cta--compact .enterprise-cta__head {
  gap: 0.65rem;
}

.enterprise-cta--compact .enterprise-cta__icon {
  width: 2rem;
  height: 2rem;
}

.enterprise-cta--compact .enterprise-cta__copy {
  line-height: 1.4;
}

.enterprise-cta--compact .enterprise-cta__btn {
  flex-shrink: 0;
  margin-top: auto;
}

/* ---------- Enterprise CTA ---------- */
.enterprise-cta {
  --card-accent: #3b82f6;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 1rem;
  padding: 1rem 1.1rem;
  border-radius: var(--content-radius);
  overflow: hidden;
  transition:
    transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

.enterprise-cta__accent {
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
  opacity: 0.95;
}

.enterprise-cta__head {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.enterprise-cta__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.6rem;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, #3b82f6 14%, transparent) 0%,
    color-mix(in srgb, #8b5cf6 14%, transparent) 100%
  );
  color: #3b82f6;
}

.enterprise-cta__icon i {
  font-size: 0.95rem;
}

.enterprise-cta__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.enterprise-cta__copy {
  margin-top: 0.2rem;
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}

.enterprise-cta__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  width: 100%;
  padding: 0.65rem 1rem;
  border-radius: var(--content-radius);
  border: 1px solid color-mix(in srgb, #8b5cf6 40%, transparent);
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: #fff;
  font-weight: 600;
  font-size: 0.8125rem;
  line-height: 1.2;
  text-decoration: none;
  box-shadow: 0 4px 14px color-mix(in srgb, #3b82f6 24%, transparent);
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.enterprise-cta__btn:hover {
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  border-color: color-mix(in srgb, #8b5cf6 55%, transparent);
  color: #fff;
  box-shadow: 0 6px 18px color-mix(in srgb, #6366f1 32%, transparent);
}

.enterprise-cta__btn i {
  font-size: 0.75rem;
}

/* ---------- Responsive ---------- */
/* Tablet / iPad landscape: three plan cards, stacked compare + highlights */
@media (max-width: 1100px) {
  .plans-details:not(.plans-details--overlay) {
    grid-template-columns: 1fr;
  }

  .plans-details:not(.plans-details--overlay) .plans-details__aside {
    justify-content: flex-start;
  }
}

@media (min-width: 900px) and (max-width: 1100px) {
  .plans-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 899px) {
  .plans-cards {
    grid-template-columns: 1fr;
  }

  .plans-footer {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .plans-page--overlay .plan-card {
    gap: 0.65rem;
    padding: 1.15rem 1.25rem;
  }
}

@media (min-width: 1101px) {
  .plans-page {
    overflow: hidden;
    gap: 1.25rem;
  }

  .plans-hero,
  .plans-cards {
    flex-shrink: 0;
  }

  .plans-details {
    flex: 1;
    min-height: 0;
  }

  .plans-details__aside {
    justify-content: flex-end;
    min-height: 100%;
    max-height: 100%;
    overflow-y: auto;
  }

  .plans-compare {
    min-height: 0;
    overflow: hidden;
  }

  .compare-table-card {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .compare-table-card :deep(.plans-compare-table__scroll) {
    max-height: none;
  }
}

@media (max-width: 991px) {
  .plans-page {
    padding: 0.25rem 0.25rem 1rem;
  }

  .plan-card.glass-panel,
  .enterprise-cta.glass-panel,
  .plans-footer__compare.glass-panel {
    background: var(--p-content-background);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .plans-hero-title {
    font-size: 1.4rem;
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

@media (prefers-reduced-motion: reduce) {
  .plans-page {
    animation: none;
  }

  .plan-card,
  .enterprise-cta,
  .plans-footer__compare,
  .enterprise-cta__btn,
  .plans-footer__compare-btn {
    transition: none;
  }

  .plan-card:hover,
  .enterprise-cta:hover,
  .plans-footer__compare:hover,
  .enterprise-cta__btn:hover {
    transform: none;
  }
}
</style>
