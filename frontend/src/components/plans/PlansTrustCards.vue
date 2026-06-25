<template>
  <section class="plans-trust" aria-label="Platform highlights">
    <div
      v-for="item in PLATFORM_HIGHLIGHTS"
      :key="item.title"
      class="trust-card glass-panel"
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
</template>

<script setup>
import { PLATFORM_HIGHLIGHTS } from '../../config/pricingPlans'
</script>

<style scoped>
.plans-trust {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.trust-card {
  --card-accent: var(--p-primary-color);
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.1rem;
  border-radius: var(--content-radius);
  transition:
    transform 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.18s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

.trust-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--card-accent) 14%, transparent);
  color: var(--card-accent);
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

@media (hover: hover) {
  .trust-card:hover {
    transform: translateY(-3px);
    border-color: color-mix(in srgb, var(--card-accent) 50%, transparent);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.22),
      0 12px 28px color-mix(in srgb, var(--card-accent) 22%, rgba(2, 6, 23, 0.12));
  }
}

@media (max-width: 991px) {
  .trust-card.glass-panel {
    background: var(--p-content-background);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .trust-card {
    transition: none;
  }

  .trust-card:hover {
    transform: none;
  }
}
</style>
