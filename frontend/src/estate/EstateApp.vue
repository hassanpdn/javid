<script setup>
// The real estate agency's root: its setup form (first run, or when asked for), its login, or the role's panel.
import { onMounted, watch, defineAsyncComponent } from "vue"
import { api, estateSession, clearEstateSession, lockScroll } from "../lib/api.js"
import { agencyInfo, loadAgency } from "./lib.js"
// each screen is downloaded only when it is shown
const EstateSetup = defineAsyncComponent(() => import("./EstateSetup.vue"))
const EstateLogin = defineAsyncComponent(() => import("./EstateLogin.vue"))
const OwnerPanel = defineAsyncComponent(() => import("./OwnerPanel.vue"))
const AgentPanel = defineAsyncComponent(() => import("./AgentPanel.vue"))

onMounted(async () => {
  try { await loadAgency() } catch { agencyInfo.loaded = true }
  if (agencyInfo.set_up && estateSession.token && !estateSession.user) {
    try { estateSession.user = await api("/estate/me") } catch { clearEstateSession() }
  }
})
watch(() => estateSession.user, () => lockScroll(false))
</script>

<template>
  <template v-if="!agencyInfo.loaded"></template>
  <EstateSetup v-else-if="!estateSession.user && (!agencyInfo.set_up || agencyInfo.setupOpen)" />
  <EstateLogin v-else-if="!estateSession.user" />
  <OwnerPanel v-else-if="estateSession.user.role === 'owner'" />
  <AgentPanel v-else />
</template>
