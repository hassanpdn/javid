<script setup>
// The dental clinic's root: its setup form (first run, or when asked for), its login, or the panel.
import { onMounted, watch, defineAsyncComponent } from "vue"
import { api, dentalSession, clearDentalSession, lockScroll } from "../lib/api.js"
import { clinicInfo, loadClinic } from "./lib.js"
const DentalSetup = defineAsyncComponent(() => import("./DentalSetup.vue"))
const DentalLogin = defineAsyncComponent(() => import("./DentalLogin.vue"))
const DentalPanel = defineAsyncComponent(() => import("./DentalPanel.vue"))

onMounted(async () => {
  try { await loadClinic() } catch { clinicInfo.loaded = true }
  if (clinicInfo.set_up && dentalSession.token && !dentalSession.user) {
    try { dentalSession.user = await api("/dental/me") } catch { clearDentalSession() }
  }
})
watch(() => dentalSession.user, () => lockScroll(false))
</script>

<template>
  <template v-if="!clinicInfo.loaded"></template>
  <DentalSetup v-else-if="!dentalSession.user && (!clinicInfo.set_up || clinicInfo.setupOpen)" />
  <DentalLogin v-else-if="!dentalSession.user" />
  <DentalPanel v-else :key="dentalSession.user.id" />
</template>
