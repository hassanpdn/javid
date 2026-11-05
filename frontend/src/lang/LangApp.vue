<script setup>
// The language institute's root: its setup form (first run, or when asked for), its login, or the panel. While it is
// open, body has the class lang-app, which gives it its own colours (lang.css).
import { onMounted, onUnmounted, watch, defineAsyncComponent } from "vue"
import { api, langSession, clearLangSession, lockScroll } from "../lib/api.js"
import { instInfo, loadInstitute } from "./lib.js"
const LangSetup = defineAsyncComponent(() => import("./LangSetup.vue"))
const LangLogin = defineAsyncComponent(() => import("./LangLogin.vue"))
const LangPanel = defineAsyncComponent(() => import("./LangPanel.vue"))

onMounted(async () => {
  document.body.classList.add("lang-app")
  try { await loadInstitute() } catch { instInfo.loaded = true }
  if (instInfo.set_up && langSession.token && !langSession.user) {
    try { langSession.user = await api("/lang/me") } catch { clearLangSession() }
  }
})
onUnmounted(() => document.body.classList.remove("lang-app"))
watch(() => langSession.user, () => lockScroll(false))
</script>

<template>
  <template v-if="!instInfo.loaded"></template>
  <LangSetup v-else-if="!langSession.user && (!instInfo.set_up || instInfo.setupOpen)" />
  <LangLogin v-else-if="!langSession.user" />
  <LangPanel v-else :key="langSession.user.id" />
</template>
