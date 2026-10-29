<script setup>
// Root: the site's door and the list of assistants (live demo only), the school setup form (first run, or when asked for),
// the login page, or the panel for the user's role
import { computed, watch, onMounted, defineAsyncComponent } from "vue"
import { api, session, clearSession, clearFabricSession, lockScroll } from "./lib/api.js"
import { schoolInfo, setupUi, loadSchool } from "./lib/school.js"
import { gate, checkGate } from "./lib/gate.js"
import { access, checkAccess, canOpen } from "./lib/access.js"
import { PANELS } from "./lib/panels.js"
// Each page is its own file in the build, downloaded only when it is shown: a visitor gets the code of the page they
// are on, not of every panel at once
const page = (load) => defineAsyncComponent(load)
const loadSetup = () => import("./pages/SetupPage.vue"), loadLogin = () => import("./pages/LoginPage.vue")
const GatePage = page(() => import("./pages/GatePage.vue"))
const HubPage = page(() => import("./pages/HubPage.vue"))
const FabricApp = page(() => import("./fabric/FabricApp.vue"))
const SetupPage = page(loadSetup)
const LoginPage = page(loadLogin)
const ManagerPanel = page(PANELS.manager)
const StaffPanel = page(PANELS.staff)
const CounselorPanel = page(PANELS.counselor)
const ParentPanel = page(PANELS.parent)
const ChatPage = page(PANELS.chat)

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
  // signed out, the next page is the setup form or the login page: download both while the school's details arrive,
  // so the phone does not wait for one, then the other
  if (!session.token) { loadSetup().catch(() => {}); loadLogin().catch(() => {}) }
  // signed in: who it is, asked at the same time as the school's details
  const me = session.token ? api("/me").catch(() => null) : null
  try { await loadSchool() } catch { schoolInfo.loaded = true }
  if (!session.token) return
  const user = await me
  if (user) session.user = user
  else clearSession()
}
onMounted(async () => {
  // both questions at once (one wait instead of two on a slow phone connection). With the door closed the access
  // answer is a refusal and means nothing; entered() asks again once the door opens.
  await Promise.all([checkGate(), checkAccess()])
  if (!gate.ok) return
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
