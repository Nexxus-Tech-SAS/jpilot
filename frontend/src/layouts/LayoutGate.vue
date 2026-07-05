<template>
  <MainLayoutV2 v-if="isV2" />
  <MainLayout v-else />
</template>

<script setup>
// Picks the classic or V2 shell at runtime. Swapping unmounts the whole shell
// (including KeepAlive caches in child views), so both UIs stay isolated.
import { computed } from 'vue'
import MainLayout from './MainLayout.vue'
import MainLayoutV2 from './MainLayoutV2.vue'
import { useUiVersion, UI_V2 } from '../services/uiVersion'

const uiVersion = useUiVersion()
const isV2 = computed(() => uiVersion.value === UI_V2)
</script>
