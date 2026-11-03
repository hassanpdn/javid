<script setup>
// The eco-lodge's login: a calendar of nights on one side, the two people on the other.
import { ref, onMounted, onUnmounted } from "vue"
import { api, setLodgeSession } from "../lib/api.js"
import { gate } from "../lib/gate.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"
import { lodgeInfo, ROLES } from "./lib.js"
import Icon from "../components/Icon.vue"

const error = ref(""), busy = ref(false), picked = ref(""), root = ref(null)
// a calendar of the day's slots: [x, y, colour]; the empty one is the hour the assistant fills
const SLOTS = [[30, 40, "#7367f0"], [140, 40, "#00bad1"], [250, 40, "#28c76f"], [30, 120, "#00bad1"], [140, 120, ""], [250, 120, "#7367f0"],
               [30, 200, "#28c76f"], [140, 200, "#7367f0"], [250, 200, "#00bad1"]]
const login = async (username) => {
  error.value = ""; busy.value = true; picked.value = username
  try {
    const d = await api("/lodge/login", { username, password: "1234" })
    setLodgeSession(d.token, d.user)
  } catch (e) { error.value = e.message === "Failed to fetch" ? "ارتباط با سرور برقرار نشد." : e.message }
  finally { busy.value = false }
}
let ctx
onMounted(() => {
  if (!motion) return
  ctx = gsap.context(() => {
    gsap.timeline({ defaults: { ease: "power3.out" } })
      .from(".auth-form > *", { y: 20, opacity: 0, stagger: .07, duration: .6, clearProps: "opacity,transform" })
      .from(".role-card", { x: -24, opacity: 0, stagger: .06, duration: .5, clearProps: "opacity,transform" }, "-=.35")
    gsap.from(".es-house", { y: 60, opacity: 0, stagger: .08, duration: .8, ease: "back.out(1.4)", delay: .2 })
    gsap.from(".float-card", { scale: .6, opacity: 0, stagger: .2, duration: .7, ease: "back.out(1.8)", delay: 1 })
  }, root.value)
})
onUnmounted(() => ctx?.revert())
</script>

<template>
  <main class="auth" ref="root">
    <div class="auth-art">
      <div class="art-stage">
        <svg viewBox="0 0 400 330" aria-hidden="true" class="shelves">
          <ellipse cx="200" cy="312" rx="180" ry="12" style="fill: var(--primary-soft)" />
          <g v-for="h in SLOTS" :key="h[0] + '-' + h[1]" class="es-house">
            <rect :x="h[0]" :y="h[1]" width="100" height="62" rx="12" :style="h[2] ? { fill: h[2] } : { fill: 'none', stroke: 'var(--primary)', strokeDasharray: '6 5', strokeWidth: 2 }" :opacity="h[2] ? .88 : 1" />
            <template v-if="h[2]"><rect :x="h[0] + 14" :y="h[1] + 16" width="50" height="7" rx="3" fill="#fff" opacity=".8" /><rect :x="h[0] + 14" :y="h[1] + 32" width="34" height="6" rx="3" fill="#fff" opacity=".5" /></template>
            <text v-else :x="h[0] + 50" :y="h[1] + 38" text-anchor="middle" style="fill: var(--primary); font-size: 26px; font-weight: 700">+</text>
          </g>
        </svg>
        <div class="float-card fc1" style="top: 2%; right: 0"><span class="tint sm t-danger"><Icon name="clock" :size="18" /></span><div>درخواست رزرو از سایت<small>گنبد آبی، دو شب</small></div></div>
        <div class="float-card fc2" style="top: 44%; left: -6%"><span class="tint sm t-info"><Icon name="users" :size="18" /></span><div>رسید بیعانه رسید<small>یک کلیک تا قطعی شدن</small></div></div>
        <div class="float-card fc3" style="bottom: 2%; right: 8%"><span class="tint sm t-success"><Icon name="heart" :size="18" /></span><div>نظر جدید: ۵ ستاره<small>پیش از نمایش در سایت</small></div></div>
      </div>
    </div>

    <div class="auth-panel">
      <div class="auth-form">
        <div class="flex items-center gap-3"><span class="logo">{{ (lodgeInfo.lodge.name || 'ب')[0] }}</span><b class="text-ink text-lg">{{ lodgeInfo.lodge.name }}</b></div>
        <h1>دستیار {{ lodgeInfo.lodge.name }}</h1>
        <p class="muted">اقامتگاه بوم‌گردی · {{ lodgeInfo.lodge.place }}. با یکی از افراد وارد شوید.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="role-list">
          <button v-for="(r, u) in ROLES" :key="u" type="button" class="role-card" :style="{ '--c': 'var(--' + r.tone + ')' }" :disabled="busy" @click="login(u)">
            <span :class="['tint', 't-' + r.tone]"><Icon :name="r.icon" :size="20" /></span>
            <span class="role-text"><b>{{ r.role }}</b><span>{{ lodgeInfo.lodge[r.who] }} · {{ r.desc }}</span></span>
            <span v-if="busy && picked === u" class="dots go"><i></i><i></i><i></i></span>
            <Icon v-else name="chevron" :size="18" class="go" />
          </button>
        </div>
        <p class="auth-note"><Icon name="shield" :size="16" /> همه‌ی داده‌های این نسخه ساختگی است.</p>
        <div class="login-tools">
          <button type="button" class="link switch-school" @click="lodgeInfo.setupOpen = true"><Icon name="refresh" :size="16" />دموی جدید برای اقامتگاه دیگر</button>
          <button v-if="gate.hub" type="button" class="link switch-school" @click="gate.app = ''"><Icon name="dashboard" :size="16" />همه‌ی دستیارها</button>
        </div>
      </div>
    </div>
  </main>
</template>
