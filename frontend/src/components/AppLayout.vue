<script setup>
// Vuexy vertical layout: sidebar on the right, navbar on top, page content in the slot.
// nav: [{ header }] or [{ key, label, icon, badge, more }]. v-model is the key of the open page.
// chat: settings for the floating assistant in the bottom-right corner (endpoint, title, examples, ...).
// app: "school" (default) or "fabric"; brand: { letter, name, sub } for the sidebar (default: the school).
// tour: the panel's first-visit guide (lib/tour.js) { key, intro: { title, text }, steps: () => [...], pages: { navKey: text },
// ready }. It runs once when ready turns true; «راهنمای این صفحه» in the account menu runs it again. Around the
// panel's own steps this layout adds the same frame everywhere: the pages in the menu, the assistant, notifications,
// the account menu and a last step that says where the guide can be found again.
import { ref, computed, watch, onMounted, onUnmounted } from "vue"
import { api, fa, session, clearSession, fabricSession, clearFabricSession, lockScroll } from "../lib/api.js"
import { theme } from "../lib/theme.js"
import { schoolInfo } from "../lib/school.js"
import { gsap, motion } from "../lib/motion.js"
import Icon from "./Icon.vue"
import Avatar from "./Avatar.vue"
import NotificationBell from "./NotificationBell.vue"
import FloatingChat from "./FloatingChat.vue"
import ToastHost from "./ToastHost.vue"
import ActivityPill from "./ActivityPill.vue"
import { chatUi } from "../lib/chat.js"
import { phone } from "../lib/viewport.js"
import { runTour } from "../lib/tour.js"
import { toast } from "../lib/notify.js"

const page = defineModel()
const props = defineProps({ title: String, subtitle: String, nav: Array, chat: { type: Object, default: () => ({}) },
  app: { default: "school" }, brand: { type: Object, default: null }, tour: { type: Object, default: null } })
const fabric = computed(() => props.app === "fabric")
const user = computed(() => fabric.value ? fabricSession.user : session.user)
const brandInfo = computed(() => props.brand ||
  { letter: (schoolInfo.school.name || "ج")[0], name: schoolInfo.school.full_name, sub: "دستیار هوشمند مدرسه" })
const menuOpen = ref(false), userOpen = ref(false), wrap = ref(null), side = ref(null), themeIcon = ref(null)
// phones: the bottom tab bar holds the pages, the assistant, notifications and an account sheet ("me")
// items marked more: true stay in the sidebar on wide screens but go into the account sheet on phones
const tabs = computed(() => (props.nav || []).filter((i) => i.key && !i.more))
const moreItems = computed(() => (props.nav || []).filter((i) => i.key && i.more))
const meOpen = ref(false)
watch(meOpen, lockScroll)

const pick = (k) => { page.value = k; menuOpen.value = false; window.scrollTo({ top: 0, behavior: "smooth" }) }
const logout = async () => {
  if (fabric.value) { try { await api("/fabric/logout", {}) } catch {} clearFabricSession(); return }
  try { await api("/logout", {}) } catch {} clearSession()
}
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

// ---------- the first-visit guide ----------
const shown = (sel) => [...document.querySelectorAll(sel)].some((e) => e.getBoundingClientRect().width > 0)
const tourSteps = () => {
  const t = props.tour, pages = (props.nav || []).filter((i) => i.key && t.pages?.[i.key])
  const steps = [{ title: t.intro.title, text: t.intro.text }, ...t.steps()]
  const end = { title: "آماده‌اید", text: "هر وقت خواستید این راهنما را دوباره ببینید، از منوی " + (phone.value ? "«من»" : "حساب") + " گزینه‌ی «راهنمای این صفحه» را انتخاب کنید." }
  if (t.frame === false) return [...steps, end]
  // the pages of this panel: one step each in the sidebar or the bottom bar; on mid-size screens the sidebar is
  // folded away, so one step on the menu button lists them all
  if (pages.length > 1) {
    if (shown(".side-item")) {
      for (const i of pages) steps.push({ el: `[data-tour="nav-${i.key}"]`, title: i.label, text: t.pages[i.key], side: "left" })
    } else if (phone.value) {
      for (const i of pages.filter((i) => !i.more)) steps.push({ el: `[data-tour="tab-${i.key}"]`, title: i.label, text: t.pages[i.key], side: "top" })
    } else {
      steps.push({ el: ".menu-btn", title: "منو", text: "صفحه‌های این پنل اینجاست: " + pages.map((i) => `«${i.label}»: ${t.pages[i.key]}`).join(" "), side: "bottom" })
    }
  }
  steps.push({ el: [".fab-chat", '[data-tour="tab-ai"]'], title: "دستیار هوشمند", side: phone.value ? "top" : "left",
    text: props.tour.chat || "هر سؤالی درباره‌ی آیین‌نامه‌ها و مقررات دارید از این‌جا بپرسید. پاسخ از روی همان اسناد نوشته می‌شود و منبعش هم نشان داده می‌شود." })
  if (!fabric.value) steps.push({ el: [".bell-wrap:not(.bell-tab)", ".bell-tab"], title: "اعلان‌ها", side: phone.value ? "top" : "bottom",
    text: "هر پیام، تذکر یا کاری که برای شما فرستاده شود این‌جا می‌آید. عدد قرمز یعنی اعلان خوانده‌نشده دارید." })
  if (!phone.value) steps.push({ el: ".avatar-btn", title: "حساب شما", side: "bottom",
    text: "حالت روشن و تیره، «راهنمای این صفحه» و خروج از حساب در این منو هستند." })
  else {
    // phones: «من» holds the pages that do not fit in the bottom bar, and the account
    const more = pages.length > 1 ? pages.filter((i) => i.more) : []
    steps.push({ el: '[data-tour="tab-me"]', side: "top", title: more.length ? "«من»: صفحه‌های دیگر و حساب" : "«من»: حساب شما",
      text: (more.length ? "صفحه‌های " + more.map((i) => `«${i.label}»`).join("، ") + " این‌جا هستند، همراه با" : "این‌جا") +
        " حالت روشن و تیره، «راهنمای این صفحه» و خروج از حساب." })
  }
  return [...steps, end]
}
const closed = (finished) => {
  if (!finished) toast({ tone: "info", title: "راهنما بسته شد", body: "هر وقت خواستید، از منوی " + (phone.value ? "«من»" : "حساب") + " گزینه‌ی «راهنمای این صفحه» را انتخاب کنید." })
}
const startTour = (force = false) => {
  if (!props.tour) return
  userOpen.value = false; meOpen.value = false
  runTour(props.tour.key, tourSteps, { force, onClose: closed })
}
watch(() => [props.tour?.key, props.tour?.ready], ([, ready]) => { if (ready) startTour() }, { immediate: true })
</script>

<template>
  <div :class="['layout', { 'menu-open': menuOpen, 'is-phone': phone }]">
    <aside class="sidebar" ref="side">
      <div class="side-brand">
        <span class="logo">{{ brandInfo.letter }}</span>
        <div><b>{{ brandInfo.name }}</b><small>{{ brandInfo.sub }}</small></div>
        <button class="icon-btn xl:hidden" @click="menuOpen = false" aria-label="بستن منو"><Icon name="x" /></button>
      </div>
      <nav class="side-nav">
        <template v-for="item in nav" :key="item.key || item.header">
          <div v-if="item.header" class="side-header">{{ item.header }}</div>
          <button v-else :class="['side-item', { on: item.key === page }]" :data-tour="'nav-' + item.key" @click="pick(item.key)">
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
          <button v-if="!phone" class="icon-btn menu-btn" @click="menuOpen = true" aria-label="منو"><Icon name="menu" :size="22" /></button>
          <span v-else class="logo sm">{{ brandInfo.letter }}</span>
          <div class="nav-title"><h1>{{ title }}</h1><small v-if="subtitle">{{ subtitle }}</small></div>
          <ActivityPill />
          <div v-if="!phone" class="nav-actions">
            <button class="icon-btn" @click="toggleTheme" :aria-label="theme.dark ? 'حالت روشن' : 'حالت تیره'">
              <span ref="themeIcon"><Icon :name="theme.dark ? 'sun' : 'moon'" :size="21" /></span>
            </button>
            <NotificationBell v-if="!fabric" />
            <div class="menu-wrap" ref="wrap">
              <button class="avatar-btn" @click="userOpen = !userOpen" aria-label="حساب کاربری"><Avatar :name="user.full_name" :size="38" /></button>
              <div v-if="userOpen" v-pop:drop class="dropdown">
                <div class="dd-head"><Avatar :name="user.full_name" :size="40" /><div><b>{{ user.full_name }}</b><small>{{ user.role_name }}</small></div></div>
                <button v-if="tour" class="dd-item" @click="startTour(true)"><Icon name="info" :size="18" />راهنمای این صفحه</button>
                <button class="dd-item" @click="toggleTheme(); userOpen = false"><Icon :name="theme.dark ? 'sun' : 'moon'" :size="18" />{{ theme.dark ? 'حالت روشن' : 'حالت تیره' }}</button>
                <button class="dd-item danger" @click="logout"><Icon name="logout" :size="18" />خروج</button>
              </div>
            </div>
          </div>
        </div>
      </header>
      <main class="main-body"><slot /></main>
      <footer class="footer">نسخه آزمایشی دستیار هوشمند {{ brandInfo.name }} · همه داده‌ها ساختگی است</footer>
    </div>
    <FloatingChat v-bind="chat" />
    <ToastHost />

    <!-- phones: tabs within thumb reach, the assistant in the middle -->
    <nav v-if="phone" class="tabbar" aria-label="بخش‌ها">
      <button v-for="t in tabs" :key="t.key" :class="['tab', { on: t.key === page && !chatUi.open && !meOpen }]" :data-tour="'tab-' + t.key" @click="chatUi.open = false; meOpen = false; pick(t.key)">
        <span class="tab-ico"><Icon :name="t.icon" :size="22" /><i v-if="t.badge" class="tab-badge">{{ fa(t.badge > 99 ? '99+' : t.badge) }}</i></span>
        <span class="tab-label">{{ t.label }}</span>
      </button>
      <button :class="['tab', 'tab-ai', { on: chatUi.open }]" data-tour="tab-ai" @click="meOpen = false; chatUi.open = !chatUi.open" :aria-expanded="chatUi.open">
        <span class="tab-orb"><Icon :name="chatUi.open ? 'x' : 'sparkles'" :size="24" /></span>
        <span class="tab-label">دستیار</span>
      </button>
      <NotificationBell v-if="!fabric" tab />
      <button :class="['tab', { on: meOpen }]" data-tour="tab-me" @click="chatUi.open = false; meOpen = !meOpen" :aria-expanded="meOpen">
        <span class="tab-ico"><Avatar :name="user.full_name" :size="26" /></span>
        <span class="tab-label">من</span>
      </button>
    </nav>
    <div v-if="phone && meOpen" class="overlay" @click.self="meOpen = false">
      <div class="dialog me-sheet" v-pop>
        <div class="me-head"><Avatar :name="user.full_name" :size="54" /><div><b>{{ user.full_name }}</b><small>{{ user.role_name }} · {{ brandInfo.name }}</small></div></div>
        <button v-for="m in moreItems" :key="m.key" :class="['me-item', { on: m.key === page }]" @click="meOpen = false; pick(m.key)">
          <Icon :name="m.icon" :size="22" /><span>{{ m.label }}</span></button>
        <button v-if="tour" class="me-item" @click="startTour(true)"><Icon name="info" :size="22" /><span>راهنمای این صفحه</span></button>
        <button class="me-item" @click="toggleTheme"><Icon :name="theme.dark ? 'sun' : 'moon'" :size="22" /><span>{{ theme.dark ? 'حالت روشن' : 'حالت تیره' }}</span></button>
        <button class="me-item danger" @click="logout"><Icon name="logout" :size="22" /><span>خروج از حساب</span></button>
      </div>
    </div>
  </div>
</template>
