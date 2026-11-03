<script setup>
// The eco-lodge's root: its setup form (first run, or when asked for), its login, or the panel.
import { onMounted, watch, defineAsyncComponent } from "vue"
import { api, lodgeSession, clearLodgeSession, lockScroll } from "../lib/api.js"
import { lodgeInfo, loadLodge } from "./lib.js"
const LodgeSetup = defineAsyncComponent(() => import("./LodgeSetup.vue"))
const LodgeLogin = defineAsyncComponent(() => import("./LodgeLogin.vue"))
const LodgePanel = defineAsyncComponent(() => import("./LodgePanel.vue"))

onMounted(async () => {
  try { await loadLodge() } catch { lodgeInfo.loaded = true }
  if (lodgeInfo.set_up && lodgeSession.token && !lodgeSession.user) {
    try { lodgeSession.user = await api("/lodge/me") } catch { clearLodgeSession() }
  }
})
watch(() => lodgeSession.user, () => lockScroll(false))
</script>

<template>
  <template v-if="!lodgeInfo.loaded"></template>
  <LodgeSetup v-else-if="!lodgeSession.user && (!lodgeInfo.set_up || lodgeInfo.setupOpen)" />
  <LodgeLogin v-else-if="!lodgeSession.user" />
  <LodgePanel v-else :key="lodgeSession.user.id" />
</template>
