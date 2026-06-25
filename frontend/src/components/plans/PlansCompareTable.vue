<template>
  <div class="plans-compare-table" :class="{ 'plans-compare-table--dialog': dialogMode }">
    <div
      class="plans-compare-table__scroll"
      :class="{ 'plans-compare-table__scroll--dialog': dialogMode }"
    >
      <table class="compare-table">
        <thead>
          <tr>
            <th scope="col" class="compare-table__feature-head">Feature</th>
            <th
              v-for="plan in PRICING_PLANS"
              :key="plan.id"
              scope="col"
              class="compare-table__plan-head"
              :class="[`compare-table__plan-head--${plan.id}`, { 'is-current': isCurrentPlan(plan) }]"
              :style="planAccentVars(plan)"
            >
              <span class="compare-table__plan-name compare-table__plan-name--full">{{ plan.name }}</span>
              <span class="compare-table__plan-name compare-table__plan-name--short">{{ plan.shortName }}</span>
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
                :class="[`compare-table__cell--${plan.id}`, { 'is-current': isCurrentPlan(plan) }]"
                :style="planAccentVars(plan)"
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
    <div v-if="footnotes.length" class="compare-footnotes">
      <p
        v-for="(footnote, index) in footnotes"
        :key="index"
        class="compare-footnote m-0"
      >
        <span class="compare-footnote__marker">{{ footnote.marker }}</span>
        {{ footnote.text }}
      </p>
    </div>
  </div>
</template>

<script setup>
import Tag from 'primevue/tag'
import {
  featureKey,
  featureLabel,
  PLAN_FEATURE_GROUPS,
  planAccentVars,
  planIncludesGroup,
  PRICING_PLANS
} from '../../config/pricingPlans'

defineProps({
  footnotes: { type: Array, default: () => [] },
  dialogMode: { type: Boolean, default: false },
  isCurrentPlan: { type: Function, required: true },
  currentPlanTagLabel: { type: Function, required: true },
  currentPlanTagSeverity: { type: Function, required: true }
})
</script>

<style scoped>
.plans-compare-table__scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.plans-compare-table__scroll--dialog {
  max-height: min(70vh, 42rem);
  overflow: auto;
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
  background: color-mix(in srgb, var(--plan-accent, var(--p-primary-color)) 8%, var(--p-content-background));
  box-shadow: inset 0 2px 0 var(--plan-accent, var(--p-primary-color));
}

.compare-table__plan-name {
  display: block;
  color: var(--plan-accent, var(--p-text-color));
}

.compare-table__plan-name--short {
  display: none;
}

.plans-compare-table--dialog .compare-table__plan-name--full {
  display: none;
}

.plans-compare-table--dialog .compare-table__plan-name--short {
  display: block;
  font-size: 0.75rem;
  line-height: 1.25;
}

.compare-table__plan-tag {
  margin-top: 0.35rem;
}

.compare-table__plan-head :deep(.compare-table__plan-tag) {
  background: color-mix(in srgb, var(--plan-accent, var(--p-primary-color)) 16%, transparent) !important;
  color: var(--plan-accent, var(--p-primary-color)) !important;
  border: 1px solid color-mix(in srgb, var(--plan-accent, var(--p-primary-color)) 32%, transparent) !important;
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
  background: color-mix(in srgb, var(--plan-accent, var(--p-primary-color)) 5%, transparent);
}

.compare-check {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--plan-accent, var(--p-primary-color));
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

/* Drawer / phone: sticky feature column + tighter layout */
.plans-compare-table--dialog .compare-table {
  min-width: 20rem;
}

.plans-compare-table--dialog .compare-table__feature-head,
.plans-compare-table--dialog .compare-table__feature {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--p-content-background);
}

.plans-compare-table--dialog .compare-table__feature-head {
  z-index: 3;
  box-shadow: 4px 0 8px -4px rgba(0, 0, 0, 0.35);
}

.plans-compare-table--dialog .compare-table__feature {
  box-shadow: 4px 0 8px -4px rgba(0, 0, 0, 0.2);
}

.plans-compare-table--dialog .compare-table__group th {
  position: sticky;
  left: 0;
  z-index: 1;
}

@media (max-width: 899px) {
  .plans-compare-table--dialog .plans-compare-table__scroll--dialog {
    max-height: none;
  }

  .plans-compare-table--dialog .compare-table {
    min-width: 18.5rem;
  }

  .plans-compare-table--dialog .compare-table thead th {
    padding: 0.65rem 0.45rem;
    font-size: 0.75rem;
  }

  .plans-compare-table--dialog .compare-table__feature-head {
    width: 9.5rem;
    min-width: 9.5rem;
    max-width: 9.5rem;
    padding-left: 0.85rem !important;
  }

  .plans-compare-table--dialog .compare-table__plan-head {
    min-width: 4.25rem;
    width: 4.25rem;
  }

  .plans-compare-table--dialog .compare-table__feature {
    width: 9.5rem;
    min-width: 9.5rem;
    max-width: 9.5rem;
    padding: 0.55rem 0.45rem 0.55rem 0.85rem;
    font-size: 0.75rem;
  }

  .plans-compare-table--dialog .compare-table__cell {
    padding: 0.55rem 0.35rem;
    min-width: 4.25rem;
    width: 4.25rem;
  }

  .plans-compare-table--dialog .compare-table__group th {
    padding: 0.55rem 0.85rem;
  }

  .plans-compare-table--dialog .compare-table__group-title {
    font-size: 0.75rem;
  }

  .plans-compare-table--dialog .compare-table__group-sub {
    font-size: 0.625rem;
  }

  .plans-compare-table--dialog .compare-table__plan-tag {
    margin-top: 0.25rem;
    font-size: 0.625rem;
  }

  .plans-compare-table--dialog .compare-footnotes {
    padding: 0.65rem 0.85rem 0.85rem;
  }

  .plans-compare-table--dialog .compare-footnote {
    font-size: 0.625rem;
  }
}
</style>
