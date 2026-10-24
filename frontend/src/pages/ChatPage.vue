<script setup>
// Roles without their own panel yet (teachers, students) get the document chat only
import { computed } from "vue"
import { session } from "../lib/api.js"
import AppLayout from "../components/AppLayout.vue"
import ChatBox from "../components/ChatBox.vue"

const user = computed(() => session.user)
const nav = [{ header: "دستیار" }, { key: "chat", label: "پرسش از اسناد", icon: "message" }]
</script>

<template>
  <AppLayout title="دستیار اسناد" :subtitle="user.role_name" :nav="nav" model-value="chat">
    <ChatBox v-reveal class="card chat-card" title="دستیار اسناد" subtitle="پاسخ فقط از روی آیین‌نامه‌ها و دستورالعمل‌های مدرسه" />
  </AppLayout>
</template>
