<script setup>
// The agency's login: a street of houses on one side, the three people on the other.
import { ref, onMounted, onUnmounted } from "vue"
import { api, setEstateSession } from "../lib/api.js"
import { gate } from "../lib/gate.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"
import { agencyInfo, ROLES } from "./lib.js"
import Icon from "../components/Icon.vue"

const error = ref(""), busy = ref(false), picked = ref(""), root = ref(null)
// houses on a street: [x, width, height, colour]
const HOUSES = [[30, 70, 120, "#7367f0"], [108, 56, 170, "#00bad1"], [172, 80, 140, "#ff9f43"], [260, 60, 200, "#28c76f"], [328, 46, 110, "#ea5455"]]
const login = async (username) => {
  error.value = ""; busy.value = true; picked.value = username
  try {
    const d = await api("/estate/login", { username, password: "1234" })
    setEstateSession(d.token, d.user)
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
          <rect x="10" y="296" width="380" height="8" rx="4" style="fill: var(--line)" />
          <g v-for="h in HOUSES" :key="h[0]" class="es-house">
            <rect :x="h[0]" :y="296 - h[2]" :width="h[1]" :height="h[2]" rx="6" :style="{ fill: h[3] }" opacity=".9" />
            <rect v-for="r in Math.floor(h[2] / 34)" :key="r" :x="h[0] + 10" :y="296 - h[2] + 12 + (r - 1) * 34" :width="h[1] - 20" height="16" rx="3" fill="#fff" opacity=".55" />
          </g>
        </svg>
        <div class="float-card fc1" style="top: 2%; right: 0"><span class="tint sm t-success"><Icon name="users" :size="18" /></span><div>۴ متقاضی برای این فایل<small>از روی بودجه و محله</small></div></div>
        <div class="float-card fc2" style="top: 44%; left: -6%"><span class="tint sm t-warning"><Icon name="chart" :size="18" /></span><div>۲۲٪ بالاتر از معامله‌های محله<small>از معامله‌های همین بنگاه</small></div></div>
        <div class="float-card fc3" style="bottom: 2%; right: 8%"><span class="tint sm t-info"><Icon name="calendar" :size="18" /></span><div>بازدید فردا ساعت ۱۷:۳۰<small>پیام تأیید آماده است</small></div></div>
      </div>
    </div>

    <div class="auth-panel">
      <div class="auth-form">
        <div class="flex items-center gap-3"><span class="logo">{{ (agencyInfo.agency.name || 'ب')[0] }}</span><b class="text-ink text-lg">{{ agencyInfo.agency.name }}</b></div>
        <h1>دستیار {{ agencyInfo.agency.name }}</h1>
        <p class="muted">بنگاه املاک · {{ agencyInfo.agency.place }}. با یکی از افراد وارد شوید.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="role-list">
          <button v-for="(r, u) in ROLES" :key="u" type="button" class="role-card" :style="{ '--c': 'var(--' + r.tone + ')' }" :disabled="busy" @click="login(u)">
            <span :class="['tint', 't-' + r.tone]"><Icon :name="r.icon" :size="20" /></span>
            <span class="role-text"><b>{{ r.role }}</b><span>{{ agencyInfo.agency[r.who] }} · {{ r.desc }}</span></span>
            <span v-if="busy && picked === u" class="dots go"><i></i><i></i><i></i></span>
            <Icon v-else name="chevron" :size="18" class="go" />
          </button>
        </div>
        <p class="auth-note"><Icon name="shield" :size="16" /> همه‌ی داده‌های این نسخه ساختگی است.</p>
        <div class="login-tools">
          <button type="button" class="link switch-school" @click="agencyInfo.setupOpen = true"><Icon name="refresh" :size="16" />دموی جدید برای بنگاه دیگر</button>
          <button v-if="gate.hub" type="button" class="link switch-school" @click="gate.app = ''"><Icon name="dashboard" :size="16" />همه‌ی دستیارها</button>
        </div>
      </div>
    </div>
  </main>
</template>
