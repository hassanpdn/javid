<script setup>
// Root: the site's door and the list of assistants (live demo only), the school setup form (first run, or when asked for),
// the login page, or the panel for the user's role
import { computed, watch, onMounted } from "vue"
import { api, session, clearSession, clearFabricSession, lockScroll } from "./lib/api.js"
import { schoolInfo, setupUi, loadSchool } from "./lib/school.js"
import { gate, checkGate } from "./lib/gate.js"
import { access, checkAccess, canOpen } from "./lib/access.js"
import GatePage from "./pages/GatePage.vue"
import HubPage from "./pages/HubPage.vue"
import FabricApp from "./fabric/FabricApp.vue"
import SetupPage from "./pages/SetupPage.vue"
import LoginPage from "./pages/LoginPage.vue"
import ManagerPanel from "./pages/ManagerPanel.vue"
import StaffPanel from "./pages/StaffPanel.vue"
import CounselorPanel from "./pages/CounselorPanel.vue"
import ParentPanel from "./pages/ParentPanel.vue"
import ChatPage from "./pages/ChatPage.vue"

const user = computed(() => session.user)
// Runs once this browser may open an assistant (on the live demo each one needs its own login, access.js),
// and again when the school assistant opens for the first time after its login.
const boot = async () => {
  if (access.on && !access.apps.length) return
  // live demo: every page load forgets the last school, so the setup form comes up empty (once per load)
  if (gate.reset) {
    gate.reset = false
    try { await api("/setup/reset", {}) } catch {}
    clearSession(); clearFabricSession()
  }
  if (!canOpen("school") || schoolInfo.loaded) return
  try { await loadSchool() } catch { schoolInfo.loaded = true }
  if (!session.token) return
  try { session.user = await api("/me") } catch { clearSession() }
}
onMounted(async () => {
  await checkGate()
  if (!gate.ok) return
  await checkAccess()
  await boot()
})
// the door page calls this after a correct username and password (the door also takes the assistants' logins)
const entered = async () => {
  gate.ok = true
  await checkAccess()
  await boot()
}
// a card on the assistants page, after its login when it needed one
const open = async (key) => {
  await boot()
  gate.app = key
}
watch(user, () => lockScroll(false))
</script>

<template>
  <template v-if="!gate.checked"></template>
  <GatePage v-else-if="!gate.ok" @entered="entered" />
  <HubPage v-else-if="gate.hub && !gate.app" @open="open" />
  <FabricApp v-else-if="gate.app === 'fabric'" />
  <template v-else-if="!schoolInfo.loaded"></template>
  <SetupPage v-else-if="!user && (!schoolInfo.set_up || setupUi.open)" />
  <LoginPage v-else-if="!user" />
  <ManagerPanel v-else-if="user.role === 'manager'" />
  <StaffPanel v-else-if="user.role === 'staff'" />
  <CounselorPanel v-else-if="user.role === 'counselor'" />
  <ParentPanel v-else-if="user.role === 'parent'" />
  <ChatPage v-else />
</template>
