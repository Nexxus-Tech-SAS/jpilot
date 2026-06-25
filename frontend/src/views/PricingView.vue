<template>
  <div class="page plans-page">
    <!-- Hero -->
    <header class="plans-hero">
      <div class="plans-hero-brand">
        <img :src="logoSrc" alt="JPilot" class="plans-hero-logo" width="36" height="36" />
        <p class="plans-hero-eyebrow m-0">
          <span class="plans-hero-product">JPilot</span>
          <span class="plans-hero-separator" aria-hidden="true">·</span>
          <a
            :href="NEXXUS_TECH.websiteUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="plans-hero-vendor"
          >Nexxus Tech</a>
        </p>
      </div>
      <h1 class="plans-hero-title m-0">Plans built for secure ADC operations</h1>
      <p class="plans-hero-copy m-0">
        JPilot runs <strong>on-premises</strong> with Docker, manages
        <strong>multiple NetScaler/ADC environments</strong>, and keeps appliance
        credentials and configuration <strong>under your control</strong> — encrypted,
        inside your network, and never sent to the LLM.
      </p>
    </header>

    <!-- Plan cards -->
    <section class="plans-cards" aria-label="Plan options">
      <article
        v-for="plan in PRICING_PLANS"
        :key="plan.id"
        class="plan-card"
        :class="[
          `plan-card--${plan.id}`,
          {
            'plan-card--current': isCurrentPlan(plan),
            'plan-card--recommended': plan.highlighted && !isCurrentPlan(plan)
          }
        ]"
      >
        <span class="plan-card__accent" aria-hidden="true" />

        <header class="plan-card__head">
          <div class="plan-card__title-row">
            <h2 class="plan-card__name m-0">{{ plan.name }}</h2>
            <Tag
              v-if="isCurrentPlan(plan)"
              :value="currentPlanTagLabel(plan)"
              :severity="currentPlanTagSeverity(plan)"
            />
            <Tag
              v-else-if="plan.highlighted"
              value="Recommended"
              severity="info"
            />
          </div>
          <p class="plan-card__tagline m-0">{{ plan.tagline }}</p>

          <div class="plan-card__price">
            <span v-if="plan.priceLabel" class="plan-card__price-value">{{ plan.priceLabel }}</span>
            <span class="plan-card__price-detail">{{ plan.priceDetail }}</span>
          </div>
        </header>

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

        <div class="plan-card__cta">
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
            v-else
            :label="plan.ctaLabel"
            class="w-full"
            severity="secondary"
            outlined
            disabled
          />
        </div>
      </article>
    </section>

    <!-- Feature comparison -->
    <section class="plans-compare" aria-labelledby="compare-heading">
      <div class="plans-compare__head">
        <h2 id="compare-heading" class="plans-section-title m-0">What's included</h2>
        <p class="plans-section-copy m-0">
          Each tier builds on the one before it. Compare side by side, or expand a group to see the details.
        </p>
      </div>

      <!-- Desktop / wide: table -->
      <div class="compare-table-card content-panel">
        <div class="compare-table-scroll">
          <table class="compare-table">
            <thead>
              <tr>
                <th scope="col" class="compare-table__feature-head">Feature</th>
                <th
                  v-for="plan in PRICING_PLANS"
                  :key="plan.id"
                  scope="col"
                  class="compare-table__plan-head"
                  :class="{ 'is-current': isCurrentPlan(plan) }"
                >
                  <span class="compare-table__plan-name">{{ plan.name }}</span>
                  <Tag
                    v-if="isCurrentPlan(plan)"
                    :value="currentPlanTagLabel(plan)"
                    :severity="currentPlanTagSeverity(plan)"
                    class="compare-table__plan-tag"
                  />
                </th>
              </tr>
            </thead>
            <tbody>
              <template v-for="group in PLAN_FEATURE_GROUPS" :key="group.id">
                <tr class="compare-table__group">
                  <th scope="rowgroup" :colspan="PRICING_PLANS.length + 1">
                    <span class="compare-table__group-title">{{ group.title }}</span>
                    <span class="compare-table__group-sub">{{ group.subtitle }}</span>
                  </th>
                </tr>
                <tr
                  v-for="feature in group.features"
                  :key="`${group.id}-${featureKey(feature)}`"
                  class="compare-table__row"
                >
                  <th scope="row" class="compare-table__feature">{{ featureLabel(feature) }}</th>
                  <td
                    v-for="plan in PRICING_PLANS"
                    :key="`${group.id}-${featureKey(feature)}-${plan.id}`"
                    class="compare-table__cell"
                    :class="{ 'is-current': isCurrentPlan(plan) }"
                  >
                    <i
                      v-if="planIncludesGroup(plan.id, group)"
                      class="pi pi-check compare-check"
                      role="img"
                      aria-label="Included"
                    />
                    <span v-else class="compare-dash" role="img" aria-label="Not included">—</span>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <div v-if="planFootnotes.length" class="compare-footnotes">
          <p
            v-for="(footnote, index) in planFootnotes"
            :key="index"
            class="compare-footnote m-0"
          >
            <span class="compare-footnote__marker">{{ footnote.marker }}</span>
            {{ footnote.text }}
          </p>
        </div>
      </div>

      <!-- Tablet / mobile: accordions -->
      <div class="compare-accordion">
        <details
          v-for="(group, index) in PLAN_FEATURE_GROUPS"
          :key="group.id"
          class="compare-acc"
          :class="`compare-acc--${group.id}`"
          :open="index === 0"
        >
          <summary class="compare-acc__summary">
            <span class="compare-acc__heading">
              <span class="compare-acc__title">{{ group.title }}</span>
              <span class="compare-acc__sub">{{ group.subtitle }}</span>
            </span>
            <i class="pi pi-chevron-down compare-acc__chevron" aria-hidden="true" />
          </summary>
          <ul class="compare-acc__list m-0 p-0">
            <li v-for="feature in group.features" :key="featureKey(feature)">
              <i class="pi pi-check" aria-hidden="true" />
              <span>{{ featureLabel(feature) }}</span>
            </li>
          </ul>
        </details>
        <div v-if="planFootnotes.length" class="compare-footnotes compare-footnotes--accordion">
          <p
            v-for="(footnote, index) in planFootnotes"
            :key="index"
            class="compare-footnote m-0"
          >
            <span class="compare-footnote__marker">{{ footnote.marker }}</span>
            {{ footnote.text }}
          </p>
        </div>
      </div>
    </section>

    <!-- Trust highlights -->
    <section class="plans-trust" aria-label="Platform highlights">
      <div
        v-for="item in PLATFORM_HIGHLIGHTS"
        :key="item.title"
        class="trust-card"
      >
        <span class="trust-card__icon" aria-hidden="true">
          <i :class="item.icon" />
        </span>
        <div class="trust-card__body min-w-0">
          <h3 class="trust-card__title m-0">{{ item.title }}</h3>
          <p class="trust-card__copy m-0">{{ item.description }}</p>
        </div>
      </div>
    </section>

    <!-- Enterprise CTA -->
    <section class="plans-enterprise" aria-label="Enterprise contact">
      <div class="enterprise-cta content-panel">
        <div class="enterprise-cta__body">
          <h2 class="plans-section-title m-0">Need Enterprise?</h2>
          <p class="plans-section-copy enterprise-cta__copy m-0">
            Nexxus Tech can add SSO, custom runbooks, WAF/GSLB programs, engineer-led
            rollouts, migrations, health checks, and security enablements for F5, NetScaler,
            NGINX, and CVAD — on-premises, AWS, or Azure.
          </p>
        </div>
        <Button
          as="a"
          :href="NEXXUS_TECH.contactUrl"
          target="_blank"
          rel="noopener noreferrer"
          label="Contact us"
          icon="pi pi-arrow-up-right"
          icon-pos="right"
          class="enterprise-cta__btn"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import logoLight from '../assets/JPilot-logo-big.svg'
import logoDark from '../assets/JPilot-logo-big-black.svg'
import { licenseTypeToPlanId, resolveLicensePlanTheme } from '../config/licensePlanThemes'
import { NEXXUS_TECH } from '../config/nexxusTech'
import {
  comparisonFootnotes,
  featureKey,
  featureLabel,
  PLAN_FEATURE_GROUPS,
  planIncludesGroup,
  PLATFORM_HIGHLIGHTS,
  PRICING_PLANS
} from '../config/pricingPlans'
import { getLicense } from '../services/system'
import { getTheme } from '../services/theme'

const PLAN_CARD_BULLET_LIMIT = 4

const license = ref(null)
const theme = ref(getTheme())

const logoSrc = computed(() => (theme.value === 'dark' ? logoDark : logoLight))

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

/** "Everything in <previous tier>, plus" note for inheriting tiers. */
function planInheritNote(plan) {
  const index = PRICING_PLANS.findIndex((item) => item.id === plan.id)
  if (index <= 0) return ''
  const previous = PRICING_PLANS[index - 1]
  return `Everything in ${previous.name}, plus`
}

onMounted(async () => {
  window.addEventListener('jpilot-theme-change', onThemeChange)
  try {
    license.value = await getLicense()
  } catch {
    // Plans page works without license data.
  }
})

onUnmounted(() => {
  window.removeEventListener('jpilot-theme-change', onThemeChange)
})

function onThemeChange(event) {
  theme.value = event.detail
}
</script>

<style scoped>
.plans-page {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  animation: page-in 0.35s ease;
}

/* ---------- Hero ---------- */
.plans-hero {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.plans-hero-brand {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.plans-hero-logo {
  display: block;
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
}

.plans-hero-eyebrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--p-text-muted-color);
}

.plans-hero-product {
  color: var(--p-text-color);
}

.plans-hero-separator {
  opacity: 0.55;
}

.plans-hero-vendor {
  color: var(--p-primary-color);
  text-decoration: none;
}

.plans-hero-vendor:hover {
  text-decoration: underline;
}

.plans-hero-title {
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: var(--p-text-color);
}

.plans-hero-copy {
  font-size: 0.9375rem;
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
  align-items: stretch;
}

.plan-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  /* Per-tier accent, used only as a thin bar + check color. */
  --tier-accent: var(--p-primary-color);
  --tier-accent-soft: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}

.plan-card--enterprise {
  --tier-accent: #3b82f6;
  --tier-accent-soft: rgba(59, 130, 246, 0.12);
}

.plan-card--enterprise-pro {
  --tier-accent: #8b5cf6;
  --tier-accent-soft: rgba(139, 92, 246, 0.12);
}

.plan-card__accent {
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: var(--tier-accent);
  opacity: 0.85;
}

@media (hover: hover) {
  .plan-card:hover {
    border-color: color-mix(in srgb, var(--tier-accent) 45%, var(--p-content-border-color));
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.06);
    transform: translateY(-3px);
  }

  html.app-dark .plan-card:hover {
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
  }
}

.plan-card--current {
  border-color: color-mix(in srgb, var(--tier-accent) 55%, var(--p-content-border-color));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--tier-accent) 45%, transparent);
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
}

/* ---------- Comparison ---------- */
.plans-compare {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.compare-table-card {
  padding: 0;
}

.compare-table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.compare-table {
  width: 100%;
  min-width: 38rem;
  border-collapse: collapse;
}

.compare-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 0.9rem 0.85rem;
  font-size: 0.8125rem;
  font-weight: 600;
  text-align: center;
  color: var(--p-text-color);
  background: var(--p-content-background);
  border-bottom: 1px solid var(--p-content-border-color);
}

.compare-table__feature-head {
  width: 46%;
  text-align: left !important;
  padding-left: 1.25rem !important;
}

.compare-table__plan-head.is-current {
  background: color-mix(in srgb, var(--p-primary-color) 7%, var(--p-content-background));
}

.compare-table__plan-name {
  display: block;
}

.compare-table__plan-tag {
  margin-top: 0.35rem;
}

.compare-table__group th {
  padding: 0.7rem 1.25rem;
  text-align: left;
  background: var(--app-nested-surface);
  border-bottom: 1px solid var(--p-content-border-color);
}

.compare-table__group-title {
  display: block;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.compare-table__group-sub {
  display: block;
  margin-top: 0.1rem;
  font-size: 0.6875rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
}

.compare-table__row:not(:last-child) th,
.compare-table__row:not(:last-child) td {
  border-bottom: 1px solid color-mix(in srgb, var(--p-content-border-color) 60%, transparent);
}

.compare-table__feature {
  padding: 0.65rem 0.85rem 0.65rem 1.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.45;
  text-align: left;
  color: var(--p-text-color);
}

.compare-table__cell {
  padding: 0.65rem 0.85rem;
  text-align: center;
  vertical-align: middle;
}

.compare-table__cell.is-current {
  background: color-mix(in srgb, var(--p-primary-color) 4%, transparent);
}

.compare-check {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--p-primary-color);
}

.compare-dash {
  color: var(--p-text-muted-color);
  opacity: 0.55;
  font-size: 0.9rem;
}

.compare-footnotes {
  padding: 0.85rem 1.25rem 1.1rem;
  border-top: 1px solid var(--p-content-border-color);
  background: var(--app-nested-surface);
}

.compare-footnote {
  font-size: 0.6875rem;
  line-height: 1.55;
  color: var(--p-text-muted-color);
}

.compare-footnote + .compare-footnote {
  margin-top: 0.5rem;
}

.compare-footnote__marker {
  font-weight: 700;
  color: var(--p-text-color);
}

/* Accordion (tablet / mobile) */
.compare-accordion {
  display: none;
  flex-direction: column;
  gap: 0.75rem;
}

.compare-acc {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
  overflow: hidden;
  --acc-accent: var(--p-primary-color);
}

.compare-acc--enterprise {
  --acc-accent: #3b82f6;
}

.compare-acc--enterprise-pro {
  --acc-accent: #8b5cf6;
}

.compare-acc__summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1.1rem;
  cursor: pointer;
  list-style: none;
  user-select: none;
}

.compare-acc__summary::-webkit-details-marker {
  display: none;
}

.compare-acc__summary:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: -2px;
}

.compare-acc__heading {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.compare-acc__title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.compare-acc__sub {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.compare-acc__chevron {
  flex-shrink: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  transition: transform 0.2s ease;
}

.compare-acc[open] .compare-acc__chevron {
  transform: rotate(180deg);
}

.compare-acc__list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  list-style: none;
  padding: 0 1.1rem 1.1rem !important;
}

.compare-acc__list li {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--p-text-color);
}

.compare-acc__list li i {
  flex-shrink: 0;
  margin-top: 0.2rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--acc-accent);
}

.compare-footnotes--accordion {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
}

/* ---------- Trust highlights ---------- */
.plans-trust {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.trust-card {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.1rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--content-radius);
  transition: border-color 0.2s ease;
}

.trust-card:hover {
  border-color: var(--p-primary-200);
}

html.app-dark .trust-card:hover {
  border-color: var(--p-primary-700);
}

.trust-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
}

.trust-card__icon i {
  font-size: 0.95rem;
}

.trust-card__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.trust-card__copy {
  margin-top: 0.2rem;
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}

/* ---------- Enterprise CTA ---------- */
.enterprise-cta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.5rem 1.75rem;
  background: linear-gradient(
    135deg,
    var(--p-content-background) 0%,
    color-mix(in srgb, var(--p-primary-50) 45%, var(--p-content-background)) 100%
  );
}

html.app-dark .enterprise-cta {
  background: linear-gradient(
    135deg,
    var(--p-content-background) 0%,
    color-mix(in srgb, var(--p-primary-900) 32%, var(--p-content-background)) 100%
  );
}

.enterprise-cta__copy {
  margin-top: 0.4rem;
}

.enterprise-cta__btn {
  flex-shrink: 0;
  white-space: nowrap;
}

/* ---------- Responsive ---------- */
@media (max-width: 1100px) {
  .plans-cards {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 991px) {
  .compare-table-card {
    display: none;
  }

  .compare-accordion {
    display: flex;
  }

  .plans-trust {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .plans-hero-title {
    font-size: 1.4rem;
  }
}

@media (max-width: 640px) {
  .plans-trust {
    grid-template-columns: 1fr;
  }

  .enterprise-cta {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .enterprise-cta__btn {
    width: 100%;
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
  .compare-acc__chevron {
    transition: none;
  }
}
</style>
