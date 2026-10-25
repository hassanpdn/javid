<script setup>
// Roles without their own panel yet (teachers, students): a welcome card, their notifications in the bell,
// and the floating assistant for questions about the school rules.
import { computed } from "vue"
import { session } from "../lib/api.js"
import { chatUi } from "../lib/chat.js"
import { DOCS_CHAT } from "../lib/constants.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import AiOrb from "../components/AiOrb.vue"

const user = computed(() => session.user)
const nav = [{ header: "خانه" }, { key: "home", label: "صفحه اصلی", icon: "dashboard" }]
</script>

<template>
  <AppLayout :chat="DOCS_CHAT" title="صفحه اصلی" :subtitle="user.role_name" :nav="nav" model-value="home">
    <section v-reveal class="card welcome">
      <div class="welcome-text">
        <h2>سلام، {{ user.full_name }}</h2>
        <p>اعلان‌ها و تذکرهای مدرسه در زنگوله بالای صفحه می‌آیند. برای پرسش درباره آیین‌نامه‌ها و مقررات مدرسه از دستیار هوشمند کمک بگیرید.</p>
        <div><button class="btn primary" @click="chatUi.open = true"><Icon name="message" :size="18" />شروع گفتگو با دستیار</button></div>
      </div>
      <div class="welcome-art"><AiOrb :size="130" /></div>
    </section>
  </AppLayout>
</template>
