<template>
  <router-view v-slot="{ Component }">
    <Transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </Transition>
  </router-view>
  <CookieConsentBanner />
</template>

<script setup>
import CookieConsentBanner from './components/CookieConsentBanner.vue'
</script>
