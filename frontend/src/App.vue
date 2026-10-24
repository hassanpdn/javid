<script setup>
// Root: shows the login page, or the panel for the logged-in user's role
import { computed, watch, onMounted } from "vue"
import { api, session, clearSession, lockScroll } from "./lib/api.js"
import LoginPage from "./pages/LoginPage.vue"
import ManagerPanel from "./pages/ManagerPanel.vue"
import StaffPanel from "./pages/StaffPanel.vue"
import CounselorPanel from "./pages/CounselorPanel.vue"
import ParentPanel from "./pages/ParentPanel.vue"
import ChatPage from "./pages/ChatPage.vue"

const user = computed(() => session.user)
onMounted(async () => {
  if (!session.token) return
  try { session.user = await api("/me") } catch { clearSession() }
})
watch(user, () => lockScroll(false))
</script>

<template>
  <LoginPage v-if="!user" />
  <ManagerPanel v-else-if="user.role === 'manager'" />
  <StaffPanel v-else-if="user.role === 'staff'" />
  <CounselorPanel v-else-if="user.role === 'counselor'" />
  <ParentPanel v-else-if="user.role === 'parent'" />
  <ChatPage v-else />
</template>
