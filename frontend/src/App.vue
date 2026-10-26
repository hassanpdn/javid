<script setup>
// Root: the site's door and the list of assistants (live demo only), the school setup form (first run, or when asked for),
// the login page, or the panel for the user's role
import { computed, watch, onMounted } from "vue"
import { api, session, clearSession, lockScroll } from "./lib/api.js"
import { schoolInfo, setupUi, loadSchool } from "./lib/school.js"
import { gate, checkGate } from "./lib/gate.js"
import GatePage from "./pages/GatePage.vue"
import HubPage from "./pages/HubPage.vue"
import SetupPage from "./pages/SetupPage.vue"
import LoginPage from "./pages/LoginPage.vue"
import ManagerPanel from "./pages/ManagerPanel.vue"
import StaffPanel from "./pages/StaffPanel.vue"
import CounselorPanel from "./pages/CounselorPanel.vue"
import ParentPanel from "./pages/ParentPanel.vue"
import ChatPage from "./pages/ChatPage.vue"

const user = computed(() => session.user)
const boot = async () => {
  // live demo: every page load forgets the last school, so the setup form comes up empty (once per load)
  if (gate.reset) {
    gate.reset = false
    try { await api("/setup/reset", {}) } catch {}
    clearSession()
  }
  try { await loadSchool() } catch { schoolInfo.loaded = true }
  if (!session.token) return
  try { session.user = await api("/me") } catch { clearSession() }
}
onMounted(async () => {
  await checkGate()
  if (gate.ok) await boot()
})
// the door page calls this after a correct username and password
const entered = async () => {
  gate.ok = true
  if (!schoolInfo.loaded || gate.reset) await boot()
}
watch(user, () => lockScroll(false))
</script>

<template>
  <template v-if="!gate.checked"></template>
  <GatePage v-else-if="!gate.ok" @entered="entered" />
  <HubPage v-else-if="gate.hub && !gate.app" @open="(key) => gate.app = key" />
  <template v-else-if="!schoolInfo.loaded"></template>
  <SetupPage v-else-if="!user && (!schoolInfo.set_up || setupUi.open)" />
  <LoginPage v-else-if="!user" />
  <ManagerPanel v-else-if="user.role === 'manager'" />
  <StaffPanel v-else-if="user.role === 'staff'" />
  <CounselorPanel v-else-if="user.role === 'counselor'" />
  <ParentPanel v-else-if="user.role === 'parent'" />
  <ChatPage v-else />
</template>
