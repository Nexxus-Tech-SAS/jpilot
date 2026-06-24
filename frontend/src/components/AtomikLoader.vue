<template>
  <div
    class="ld-atom"
    :style="ink ? { '--ink': ink } : undefined"
    role="status"
    aria-label="Loading"
  >
    <i></i><i></i>
  </div>
</template>

<script setup>
defineProps({
  ink: { type: String, default: '' }
})
</script>
