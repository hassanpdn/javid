<script setup>
// Root: the school setup form (first run, or when asked for), the login page, or the panel for the user's role
import { computed, watch, onMounted } from "vue"
import { api, session, clearSession, lockScroll } from "./lib/api.js"
import { schoolInfo, setupUi, loadSchool } from "./lib/school.js"
import SetupPage from "./pages/SetupPage.vue"
import LoginPage from "./pages/LoginPage.vue"
import ManagerPanel from "./pages/ManagerPanel.vue"
import StaffPanel from "./pages/StaffPanel.vue"
import CounselorPanel from "./pages/CounselorPanel.vue"
import ParentPanel from "./pages/ParentPanel.vue"
import ChatPage from "./pages/ChatPage.vue"

const user = computed(() => session.user)
onMounted(async () => {
  try { await loadSchool() } catch { schoolInfo.loaded = true }
  if (!session.token) return
  try { session.user = await api("/me") } catch { clearSession() }
})
watch(user, () => lockScroll(false))
</script>

<template>
  <template v-if="!schoolInfo.loaded"></template>
  <SetupPage v-else-if="!user && (!schoolInfo.set_up || setupUi.open)" />
  <LoginPage v-else-if="!user" />
  <ManagerPanel v-else-if="user.role === 'manager'" />
  <StaffPanel v-else-if="user.role === 'staff'" />
  <CounselorPanel v-else-if="user.role === 'counselor'" />
  <ParentPanel v-else-if="user.role === 'parent'" />
  <ChatPage v-else />
</template>
