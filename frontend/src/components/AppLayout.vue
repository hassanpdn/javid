<script setup>
// Vuexy vertical layout: sidebar on the right, navbar on top, page content in the slot.
// nav: [{ header }] or [{ key, label, icon, badge }]. v-model is the key of the open page.
// chat: settings for the floating assistant in the bottom-right corner (endpoint, title, examples, ...).
import { ref, computed, watch, onMounted, onUnmounted } from "vue"
import { api, fa, session, clearSession, lockScroll } from "../lib/api.js"
import { theme } from "../lib/theme.js"
import { schoolInfo } from "../lib/school.js"
import { gsap, motion } from "../lib/motion.js"
import Icon from "./Icon.vue"
import Avatar from "./Avatar.vue"
import NotificationBell from "./NotificationBell.vue"
import FloatingChat from "./FloatingChat.vue"

defineProps({ title: String, subtitle: String, nav: Array, chat: { type: Object, default: () => ({}) } })
const page = defineModel()
const user = computed(() => session.user)
const menuOpen = ref(false), userOpen = ref(false), wrap = ref(null), side = ref(null), themeIcon = ref(null)

const pick = (k) => { page.value = k; menuOpen.value = false; window.scrollTo({ top: 0, behavior: "smooth" }) }
const logout = async () => { try { await api("/logout", {}) } catch {} clearSession() }
const toggleTheme = () => {
  theme.dark = !theme.dark
  if (motion && themeIcon.value) gsap.fromTo(themeIcon.value, { rotation: -120, scale: .4 }, { rotation: 0, scale: 1, duration: .6, ease: "back.out(2)" })
}
const outside = (e) => { if (userOpen.value && wrap.value && !wrap.value.contains(e.target)) userOpen.value = false }
watch(menuOpen, lockScroll)
onMounted(() => {
  document.addEventListener("click", outside)
  if (!motion) return
  gsap.from(side.value.querySelectorAll(".side-brand, .side-header, .side-item, .side-user"),
    { x: 30, opacity: 0, stagger: .05, duration: .5, ease: "power3.out", clearProps: "opacity,transform" })
  gsap.from(".navbar-inner", { y: -24, opacity: 0, duration: .6, ease: "power3.out", clearProps: "opacity,transform" })
})
onUnmounted(() => { document.removeEventListener("click", outside); lockScroll(false) })
</script>

<template>
  <div :class="['layout', { 'menu-open': menuOpen }]">
    <aside class="sidebar" ref="side">
      <div class="side-brand">
        <span class="logo">{{ (schoolInfo.school.name || 'ج')[0] }}</span>
        <div><b>{{ schoolInfo.school.full_name }}</b><small>دستیار هوشمند مدرسه</small></div>
        <button class="icon-btn xl:hidden" @click="menuOpen = false" aria-label="بستن منو"><Icon name="x" /></button>
      </div>
      <nav class="side-nav">
        <template v-for="item in nav" :key="item.key || item.header">
          <div v-if="item.header" class="side-header">{{ item.header }}</div>
          <button v-else :class="['side-item', { on: item.key === page }]" @click="pick(item.key)">
            <Icon :name="item.icon" :size="21" /><span>{{ item.label }}</span>
            <span v-if="item.badge" class="side-badge">{{ fa(item.badge) }}</span>
          </button>
        </template>
      </nav>
      <div class="side-foot">
        <div class="side-user"><Avatar :name="user.full_name" :size="38" /><div><b>{{ user.full_name }}</b><small>{{ user.role_name }}</small></div></div>
      </div>
    </aside>
    <div v-if="menuOpen" class="side-backdrop" @click="menuOpen = false"></div>

    <div class="main">
      <header class="navbar">
        <div class="navbar-inner">
          <button class="icon-btn menu-btn" @click="menuOpen = true" aria-label="منو"><Icon name="menu" :size="22" /></button>
          <div class="nav-title"><h1>{{ title }}</h1><small v-if="subtitle">{{ subtitle }}</small></div>
          <div class="nav-actions">
            <button class="icon-btn" @click="toggleTheme" :aria-label="theme.dark ? 'حالت روشن' : 'حالت تیره'">
              <span ref="themeIcon"><Icon :name="theme.dark ? 'sun' : 'moon'" :size="21" /></span>
            </button>
            <NotificationBell />
            <div class="menu-wrap" ref="wrap">
              <button class="avatar-btn" @click="userOpen = !userOpen" aria-label="حساب کاربری"><Avatar :name="user.full_name" :size="38" /></button>
              <div v-if="userOpen" v-pop:drop class="dropdown">
                <div class="dd-head"><Avatar :name="user.full_name" :size="40" /><div><b>{{ user.full_name }}</b><small>{{ user.role_name }}</small></div></div>
                <button class="dd-item" @click="toggleTheme(); userOpen = false"><Icon :name="theme.dark ? 'sun' : 'moon'" :size="18" />{{ theme.dark ? 'حالت روشن' : 'حالت تیره' }}</button>
                <button class="dd-item danger" @click="logout"><Icon name="logout" :size="18" />خروج</button>
              </div>
            </div>
          </div>
        </div>
      </header>
      <main class="main-body"><slot /></main>
      <footer class="footer">نسخه آزمایشی دستیار هوشمند {{ schoolInfo.school.full_name }} · همه داده‌ها ساختگی است</footer>
    </div>
    <FloatingChat v-bind="chat" />
  </div>
</template>
