<script setup>
// The law office's root: its setup form (first run, or when asked for), its login, or the panel.
import { onMounted, watch, defineAsyncComponent } from "vue"
import { api, lawSession, clearLawSession, lockScroll } from "../lib/api.js"
import { officeInfo, loadOffice } from "./lib.js"
const LawSetup = defineAsyncComponent(() => import("./LawSetup.vue"))
const LawLogin = defineAsyncComponent(() => import("./LawLogin.vue"))
const LawPanel = defineAsyncComponent(() => import("./LawPanel.vue"))

onMounted(async () => {
  try { await loadOffice() } catch { officeInfo.loaded = true }
  if (officeInfo.set_up && lawSession.token && !lawSession.user) {
    try { lawSession.user = await api("/law/me") } catch { clearLawSession() }
  }
})
watch(() => lawSession.user, () => lockScroll(false))
</script>

<template>
  <template v-if="!officeInfo.loaded"></template>
  <LawSetup v-else-if="!lawSession.user && (!officeInfo.set_up || officeInfo.setupOpen)" />
  <LawLogin v-else-if="!lawSession.user" />
  <LawPanel v-else :key="lawSession.user.id" />
</template>
