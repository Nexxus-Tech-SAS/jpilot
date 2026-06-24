<template>
  <div
    class="ld-trio"
    :style="ink ? { '--ink': ink } : undefined"
    role="img"
    aria-label="JPilot"
  >
    <i></i><i></i><i></i>
  </div>
</template>

<script setup>
defineProps({
  ink: { type: String, default: '' }
})
</script>
