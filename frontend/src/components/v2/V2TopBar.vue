<template>
  <header class="v2-topbar">
    <div class="v2-topbar-side v2-topbar-start">
      <button
        type="button"
        class="v2-topbar-btn"
        aria-label="Open menu"
        @click="$emit('open-drawer')"
      >
        <i class="pi pi-bars" aria-hidden="true" />
      </button>
    </div>

    <RouterLink to="/" replace class="v2-topbar-brand" aria-label="JPilot dashboard">
      <JPilotMark :size="34" />
    </RouterLink>

    <div class="v2-topbar-side v2-topbar-end">
      <button
        type="button"
        class="v2-topbar-btn v2-topbar-avatar-btn"
        :aria-label="username || 'Account'"
        @click="(event) => $emit('open-user-menu', event)"
      >
        <Avatar :label="initials" shape="circle" class="v2-avatar" />
      </button>
    </div>
  </header>
</template>

<script setup>
import Avatar from 'primevue/avatar'
import JPilotMark from '../JPilotMark.vue'

defineProps({
  initials: { type: String, default: 'A' },
  username: { type: String, default: '' }
})

defineEmits(['open-drawer', 'open-user-menu'])
</script>

<style scoped>
/* Phone-only glass app bar (<768px). */
.v2-topbar,
.v2-topbar * {
  box-sizing: border-box;
}

.v2-topbar {
  display: none;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
  z-index: 30;
  min-height: calc(3.5rem + env(safe-area-inset-top, 0px));
  padding:
    calc(env(safe-area-inset-top, 0px) + 0.375rem)
    max(0.75rem, env(safe-area-inset-right, 0px))
    0.375rem
    max(0.75rem, env(safe-area-inset-left, 0px));
  background: var(--v2-surface-glass);
  backdrop-filter: blur(var(--v2-blur)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--v2-blur)) saturate(140%);
  border-bottom: 1px solid var(--v2-border);
  animation: v2-topbar-in var(--v2-dur-slow) var(--v2-ease) both;
}

@media (max-width: 767.98px) {
  .v2-topbar {
    display: grid;
  }
}

@keyframes v2-topbar-in {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.v2-topbar-side {
  display: flex;
  align-items: center;
  min-width: var(--v2-touch-target);
}

.v2-topbar-start {
  justify-self: start;
}

.v2-topbar-end {
  justify-self: end;
  justify-content: flex-end;
}

.v2-topbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--v2-touch-target);
  height: var(--v2-touch-target);
  padding: 0;
  border: none;
  border-radius: var(--v2-radius-md);
  background: transparent;
  color: var(--v2-text);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    background var(--v2-dur-fast) var(--v2-ease),
    transform var(--v2-dur-fast) var(--v2-ease-spring);
}

.v2-topbar-btn i {
  font-size: 1.15rem;
  line-height: 1;
}

.v2-topbar-btn:active {
  transform: scale(0.92);
}

.v2-topbar-btn:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: -2px;
}

@media (hover: hover) {
  .v2-topbar-btn:hover {
    background: var(--v2-surface-hover);
  }
}

.v2-topbar-brand {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  justify-self: center;
  min-height: var(--v2-touch-target);
  padding: 0 0.25rem;
  border-radius: var(--v2-radius-md);
  text-decoration: none;
}

.v2-topbar-brand:focus-visible {
  outline: 2px solid var(--v2-accent);
  outline-offset: 2px;
}

.v2-avatar {
  width: 2.125rem !important;
  height: 2.125rem !important;
  background: var(--v2-gradient-brand) !important;
  color: var(--v2-text-on-accent) !important;
  font-size: 0.7rem !important;
  font-weight: 700 !important;
}

@media (prefers-reduced-motion: reduce) {
  .v2-topbar {
    animation: none !important;
  }
}
</style>
