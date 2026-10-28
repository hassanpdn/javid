<script setup>
// Login: an animated illustration on one side, the demo roles on the other
import { runTour } from "../lib/tour.js"
import { LOGIN } from "../lib/tours.js"
import { ref, onMounted, onUnmounted } from "vue"
import { computed } from "vue"
import { api, session, store } from "../lib/api.js"
import { schoolInfo, setupUi } from "../lib/school.js"
import { gate } from "../lib/gate.js"
import FeatureToggles from "../components/FeatureToggles.vue"
import { gsap, motion } from "../lib/motion.js"
import Icon from "../components/Icon.vue"

const ROLES = [
  { u: "modir", role: "مدیر", desc: "خلاصه روز، هشدارها و تصمیم‌ها", icon: "chart", tone: "primary" },
  { u: "edari", role: "پرسنل اداری", desc: "صندوق نامه هوشمند و دستیار پیگیری", icon: "mail", tone: "info" },
  { u: "moalem", role: "آموزگار", desc: "کلاس و دانش‌آموزان", icon: "book", tone: "success", soon: true },
  { u: "karimi", role: "معلم ورزش", desc: "اعلان‌ها و تذکرها", icon: "users", tone: "warning", soon: true },
  { u: "moshaver", role: "مشاور", desc: "دانش‌آموزان نیازمند توجه و پیام به اولیا", icon: "message", tone: "success" },
  { u: "vali", role: "ولی", desc: "گزارش هفتگی، پیشرفت و فرم‌های سلامت", icon: "user", tone: "danger" },
  { u: "daneshamooz", role: "دانش‌آموز", desc: "نمره‌ها و پیشرفت من", icon: "school", tone: "secondary", soon: true },
]
// role cards: what each role does, with the person's name for the school this demo is set up for
// roles switched off (parent, student) don't get a card
const FEATURE_OF = { vali: "parents", daneshamooz: "students" }
const demo = computed(() => ROLES.filter((d) => !FEATURE_OF[d.u] || schoolInfo.features[FEATURE_OF[d.u]])
  .map((d) => ({ ...d, name: schoolInfo.names[d.u] || "",
                desc: d.u === "moshaver" && !schoolInfo.features.parents ? "دانش‌آموزان نیازمند توجه و پرونده‌ها" : d.desc })))
const rolesOpen = ref(false)
const school = computed(() => schoolInfo.school)
const error = ref(""), busy = ref(false), picked = ref(""), root = ref(null)
// windows of the two school wings in the illustration; a few are "lit" and blink
const windows = [128, 172, 358, 402].flatMap((x, i) => [230, 300].map((y, j) => ({ x, y, lit: (i + j) % 3 === 0 })))
const login = async (username, password) => {
  error.value = ""; busy.value = true; picked.value = username
  try {
    const data = await api("/login", { username, password })
    session.token = data.token; session.user = data.user; store.set("token", data.token)
  } catch (e) {
    error.value = e.message === "Failed to fetch" ? "ارتباط با سرور برقرار نشد." : e.message
  } finally { busy.value = false }
}
let ctx
// the first-visit guide (lib/tours.js); «راهنما» runs it again
const guide = (force = false) => runTour("login", LOGIN, { force })
onMounted(() => {
  guide()
  if (!motion) return
  ctx = gsap.context(() => {
    const clear = { clearProps: "opacity,transform" }
    gsap.timeline({ defaults: { ease: "power3.out" } })
      .from(".auth-form > *", { y: 20, opacity: 0, stagger: .07, duration: .6, ...clear })
      .from(".role-card", { x: -24, opacity: 0, stagger: .05, duration: .5, ...clear }, "-=.35")
    gsap.from(".bld", { y: 40, opacity: 0, stagger: .1, duration: .9, ease: "back.out(1.4)", delay: .1 })
    gsap.from(".float-card", { scale: .6, opacity: 0, stagger: .2, duration: .7, ease: "back.out(1.8)", delay: .8 })
    const float = (sel, y, d) => gsap.to(sel, { y, duration: d, yoyo: true, repeat: -1, ease: "sine.inOut", delay: 1.6 })
    float(".fc1", -12, 2.6); float(".fc2", 10, 3.1); float(".fc3", -9, 2.2)
    gsap.to(".cloud.c1", { x: 40, duration: 8, yoyo: true, repeat: -1, ease: "sine.inOut" })
    gsap.to(".cloud.c2", { x: -30, duration: 10, yoyo: true, repeat: -1, ease: "sine.inOut" })
    gsap.to(".flag", { scaleX: .82, transformOrigin: "left center", duration: .9, yoyo: true, repeat: -1, ease: "sine.inOut" })
    gsap.to(".hand", { rotation: 360, svgOrigin: "280 190", duration: 8, repeat: -1, ease: "none" })
    gsap.to(".win.lit", { opacity: .2, duration: 1.4, yoyo: true, repeat: -1, stagger: .5, ease: "sine.inOut" })
    gsap.to(".spk", { scale: 1.3, rotation: 25, transformOrigin: "50% 50%", duration: 1.5, yoyo: true, repeat: -1, ease: "sine.inOut", stagger: .7 })
  }, root.value)
})
onUnmounted(() => ctx?.revert())
</script>

<template>
  <main class="auth" ref="root">
    <div class="auth-art">
      <div class="art-stage">
        <svg viewBox="0 0 560 460" aria-hidden="true">
          <ellipse cx="280" cy="394" rx="240" ry="22" style="fill: var(--primary-soft)"/>
          <g class="cloud c1"><rect x="60" y="80" width="96" height="26" rx="13" style="fill: var(--panel)"/><circle cx="96" cy="80" r="20" style="fill: var(--panel)"/><circle cx="124" cy="86" r="14" style="fill: var(--panel)"/></g>
          <g class="cloud c2"><rect x="400" y="52" width="80" height="22" rx="11" style="fill: var(--panel)"/><circle cx="432" cy="52" r="17" style="fill: var(--panel)"/></g>
          <g class="bld"><rect x="110" y="200" width="340" height="190" rx="12" style="fill: var(--panel); stroke: var(--line)" stroke-width="2"/>
            <rect v-for="w in windows" :key="w.x + '-' + w.y" :class="['win', { lit: w.lit }]" :x="w.x" :y="w.y" width="30" height="36" rx="5"
                  :style="{ fill: w.lit ? 'var(--warning)' : 'var(--primary-soft)', opacity: w.lit ? .55 : 1 }"/></g>
          <g class="bld"><rect x="220" y="140" width="120" height="250" rx="10" style="fill: var(--primary)"/>
            <path d="M206 152 280 96l74 56Z" style="fill: var(--primary-dark)"/>
            <circle cx="280" cy="190" r="22" style="fill: var(--panel)"/>
            <path class="hand" d="M280 190V175" style="stroke: var(--primary)" stroke-width="3" stroke-linecap="round"/>
            <path d="M280 190h9" style="stroke: var(--ink)" stroke-width="3" stroke-linecap="round"/>
            <rect x="240" y="236" width="26" height="32" rx="5" fill="#fff" opacity=".85"/><rect x="294" y="236" width="26" height="32" rx="5" fill="#fff" opacity=".85"/>
            <path d="M254 390v-48a26 26 0 0 1 52 0v48Z" style="fill: var(--panel)"/></g>
          <g class="bld"><path d="M280 96V40" style="stroke: var(--ink)" stroke-width="3" stroke-linecap="round"/>
            <path class="flag" d="M282 42h42l-9 13 9 13h-42Z" style="fill: var(--warning)"/></g>
          <g class="bld"><rect x="62" y="334" width="8" height="58" rx="3" style="fill: var(--secondary)"/><circle cx="66" cy="318" r="32" style="fill: var(--success)" opacity=".85"/>
            <rect x="488" y="340" width="8" height="52" rx="3" style="fill: var(--secondary)"/><circle cx="492" cy="326" r="26" style="fill: var(--success)" opacity=".7"/></g>
          <path class="spk" d="M470 150c2 11 6.5 15.5 17.5 17.5-11 2-15.5 6.5-17.5 17.5-2-11-6.5-15.5-17.5-17.5 11-2 15.5-6.5 17.5-17.5Z" style="fill: var(--primary)"/>
          <path class="spk" d="M92 200c1 5.5 3.3 7.8 8.8 8.8-5.5 1-7.8 3.3-8.8 8.8-1-5.5-3.3-7.8-8.8-8.8 5.5-1 7.8-3.3 8.8-8.8Z" style="fill: var(--info)"/>
        </svg>
        <div class="float-card fc1" style="top: 4%; right: 0"><span class="tint sm t-primary"><Icon name="sparkles" :size="18" /></span><div>خلاصه امروز آماده شد<small>دستیار مدیر</small></div></div>
        <div class="float-card fc2" style="top: 40%; left: -4%"><span class="tint sm t-info"><Icon name="mail" :size="18" /></span><div>نامه‌ها دسته‌بندی شدند<small>دستیار اداری</small></div></div>
        <div v-if="schoolInfo.features.parents" class="float-card fc3" style="bottom: 4%; right: 10%"><span class="tint sm t-success"><Icon name="message" :size="18" /></span><div>پیام مشاور برای ولی<small>بعد از تأیید مشاور</small></div></div>
      </div>
    </div>

    <div class="auth-panel">
      <div class="auth-form">
        <div class="flex items-center gap-3"><span class="logo">{{ (school.name || 'ج')[0] }}</span><b class="text-ink text-lg">{{ school.full_name }}</b></div>
        <h1>به دستیار هوشمند {{ school.name }} خوش آمدید</h1>
        <p class="muted">نسخه آزمایشی. با یکی از نقش‌ها وارد شوید؛ هر نقش پنل و دسترسی‌های خودش را دارد.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <TransitionGroup name="role" tag="div" class="role-list" data-tour="login-roles">
          <button v-for="d in demo" :key="d.u" type="button" class="role-card" :style="{ '--c': 'var(--' + d.tone + ')' }"
                  :disabled="busy" @click="login(d.u, '1234')">
            <span :class="['tint', 't-' + d.tone]"><Icon :name="d.icon" :size="20" /></span>
            <span class="role-text"><b>{{ d.role }}</b><span>{{ d.name ? d.name + ' · ' : '' }}{{ d.desc }}</span></span>
            <span v-if="d.soon" class="soon">فعلاً فقط پرسش از آیین‌نامه‌ها</span>
            <span v-if="busy && picked === d.u" class="dots go"><i></i><i></i><i></i></span>
            <Icon v-else name="chevron" :size="18" class="go" />
          </button>
        </TransitionGroup>
        <p class="auth-note"><Icon name="shield" :size="16" /> همه داده‌های این نسخه ساختگی است.</p>
        <div class="login-tools">
          <button type="button" class="link switch-school new-demo" data-tour="login-new" @click="setupUi.open = true"><Icon name="school" :size="16" />دموی جدید برای مدرسه دیگر</button>
          <button v-if="gate.hub" type="button" class="link switch-school" data-tour="login-hub" @click="gate.app = ''"><Icon name="dashboard" :size="16" />همه‌ی دستیارها</button>
          <button type="button" class="link switch-school roles-toggle" data-tour="login-roles-toggle" :aria-expanded="rolesOpen" @click="rolesOpen = !rolesOpen"><Icon name="users" :size="16" />چه کسانی وارد شوند</button>
          <button type="button" class="link switch-school" data-tour="login-help" @click="guide(true)"><Icon name="info" :size="16" />راهنما</button>
        </div>
        <div v-if="rolesOpen" v-pop:drop class="roles-panel"><FeatureToggles /></div>
      </div>
    </div>
  </main>
</template>
