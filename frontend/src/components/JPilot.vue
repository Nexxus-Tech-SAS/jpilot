<template>
  <div class="flex justify-content-center">
    <JPilotMark variant="full" :size="size" />
  </div>
</template>

<script setup>
import JPilotMark from './JPilotMark.vue'

defineProps({
  size: { type: [Number, String], default: 52 }
})
</script>
