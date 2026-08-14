<template>
  <button
    ref="triggerRef"
    type="button"
    class="landing-image-zoom-trigger"
    :class="triggerClass"
    :aria-label="ariaLabel"
    @click="open"
  >
    <img :src="src" :alt="alt" :class="imgClass" />
  </button>

  <Teleport to="body">
    <Transition name="landing-lightbox">
      <div
        v-if="visible"
        ref="dialogRef"
        class="landing-lightbox"
        role="dialog"
        aria-modal="true"
        :aria-label="ariaLabel"
        @click.self="close"
      >
        <button
          ref="closeRef"
          type="button"
          class="landing-lightbox-close"
          aria-label="Close enlarged image"
          @click="close"
        >
          <i class="pi pi-times" aria-hidden="true" />
        </button>
        <img
          :src="src"
          :alt="alt || ariaLabel"
          class="landing-lightbox-image"
          @click.stop
        />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: '' },
  ariaLabel: { type: String, default: 'Enlarge image' },
  imgClass: { type: [String, Array, Object], default: '' },
  triggerClass: { type: [String, Array, Object], default: '' }
})

const visible = ref(false)
const triggerRef = ref(null)
const closeRef = ref(null)
const dialogRef = ref(null)

let previousOverflow = ''

function lockScroll() {
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
}

function unlockScroll() {
  document.body.style.overflow = previousOverflow
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }

  if (event.key !== 'Tab' || !dialogRef.value) return

  const focusable = dialogRef.value.querySelectorAll(
    'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  if (!focusable.length) return

  const first = focusable[0]
  const last = focusable[focusable.length - 1]

  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

function open() {
  visible.value = true
}

function close() {
  visible.value = false
}

watch(visible, async (isOpen) => {
  if (isOpen) {
    lockScroll()
    document.addEventListener('keydown', onKeydown)
    await nextTick()
    closeRef.value?.focus()
  } else {
    document.removeEventListener('keydown', onKeydown)
    unlockScroll()
    await nextTick()
    triggerRef.value?.focus()
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  if (visible.value) unlockScroll()
})
</script>

<style scoped>
.landing-image-zoom-trigger {
  appearance: none;
  border: 0;
  padding: 0;
  margin: 0;
  background: transparent;
  cursor: zoom-in;
  line-height: 0;
  color: inherit;
  font: inherit;
}

.landing-image-zoom-trigger:focus-visible {
  outline: 2px solid var(--landing-primary, #22d3ee);
  outline-offset: 3px;
}
</style>

<style>
.landing-lightbox {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  background: rgba(3, 11, 20, 0.88);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  cursor: zoom-out;
}

.landing-lightbox-image {
  display: block;
  width: auto;
  height: auto;
  max-width: min(96vw, 72rem);
  max-height: min(88vh, 56rem);
  object-fit: contain;
  border-radius: 1rem;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
  cursor: default;
}

.landing-lightbox-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #ecfeff;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.landing-lightbox-close:hover {
  background: rgba(255, 255, 255, 0.16);
  border-color: rgba(255, 255, 255, 0.28);
}

.landing-lightbox-close:focus-visible {
  outline: 2px solid #22d3ee;
  outline-offset: 2px;
}

.landing-lightbox-enter-active,
.landing-lightbox-leave-active {
  transition: opacity 0.2s ease;
}

.landing-lightbox-enter-active .landing-lightbox-image,
.landing-lightbox-leave-active .landing-lightbox-image {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.landing-lightbox-enter-from,
.landing-lightbox-leave-to {
  opacity: 0;
}

.landing-lightbox-enter-from .landing-lightbox-image,
.landing-lightbox-leave-to .landing-lightbox-image {
  opacity: 0;
  transform: scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .landing-lightbox-enter-active,
  .landing-lightbox-leave-active,
  .landing-lightbox-enter-active .landing-lightbox-image,
  .landing-lightbox-leave-active .landing-lightbox-image {
    transition: none;
  }
}
</style>
