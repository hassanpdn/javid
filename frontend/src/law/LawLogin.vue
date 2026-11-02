<script setup>
// The law office's login: a stack of case files on one side, the three people on the other.
import { ref, onMounted, onUnmounted } from "vue"
import { api, setLawSession } from "../lib/api.js"
import { gate } from "../lib/gate.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"
import { officeInfo, ROLES } from "./lib.js"
import Icon from "../components/Icon.vue"

const error = ref(""), busy = ref(false), picked = ref(""), root = ref(null)
// houses on a street: [x, width, height, colour]
// case folders on a shelf: [x, height, colour]
const HOUSES = [[40, 150, "#3c4a8f"], [96, 190, "#7367f0"], [152, 130, "#e0a785"], [208, 200, "#00bad1"], [264, 160, "#28c76f"], [320, 140, "#ea5455"]]
const login = async (username) => {
  error.value = ""; busy.value = true; picked.value = username
  try {
    const d = await api("/law/login", { username, password: "1234" })
    setLawSession(d.token, d.user)
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
            <rect :x="h[0]" :y="296 - h[1]" width="46" :height="h[1]" rx="5" :style="{ fill: h[2] }" opacity=".9" />
            <rect :x="h[0] + 9" :y="296 - h[1] + 18" width="28" height="22" rx="3" fill="#fff" opacity=".7" />
            <rect :x="h[0] + 9" :y="296 - 30" width="28" height="4" rx="2" fill="#fff" opacity=".4" />
          </g>
        </svg>
        <div class="float-card fc1" style="top: 2%; right: 0"><span class="tint sm t-danger"><Icon name="clock" :size="18" /></span><div>دو روز به آخر مهلت تجدیدنظر<small>با جمعه‌ها و تعطیلات</small></div></div>
        <div class="float-card fc2" style="top: 44%; left: -6%"><span class="tint sm t-info"><Icon name="mail" :size="18" /></span><div>ابلاغیه‌ی جدید خوانده شد<small>شماره‌ی پرونده و شعبه پیدا شد</small></div></div>
        <div class="float-card fc3" style="bottom: 2%; right: 8%"><span class="tint sm t-success"><Icon name="calendar" :size="18" /></span><div>جلسه‌ی فردا ساعت ۱۰:۳۰<small>شعبه‌ی ۷ دادگاه خانواده</small></div></div>
      </div>
    </div>

    <div class="auth-panel">
      <div class="auth-form">
        <div class="flex items-center gap-3"><span class="logo">{{ (officeInfo.office.name || 'و')[0] }}</span><b class="text-ink text-lg">{{ officeInfo.office.name }}</b></div>
        <h1>دستیار {{ officeInfo.office.name }}</h1>
        <p class="muted">دفتر وکالت · {{ officeInfo.office.place }}. با یکی از افراد وارد شوید.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="role-list">
          <button v-for="(r, u) in ROLES" :key="u" type="button" class="role-card" :style="{ '--c': 'var(--' + r.tone + ')' }" :disabled="busy" @click="login(u)">
            <span :class="['tint', 't-' + r.tone]"><Icon :name="r.icon" :size="20" /></span>
            <span class="role-text"><b>{{ r.role }}</b><span>{{ officeInfo.office[r.who] }} · {{ r.desc }}</span></span>
            <span v-if="busy && picked === u" class="dots go"><i></i><i></i><i></i></span>
            <Icon v-else name="chevron" :size="18" class="go" />
          </button>
        </div>
        <p class="auth-note"><Icon name="shield" :size="16" /> همه‌ی داده‌های این نسخه ساختگی است.</p>
        <div class="login-tools">
          <button type="button" class="link switch-school" @click="officeInfo.setupOpen = true"><Icon name="refresh" :size="16" />دموی جدید برای دفتر دیگر</button>
          <button v-if="gate.hub" type="button" class="link switch-school" @click="gate.app = ''"><Icon name="dashboard" :size="16" />همه‌ی دستیارها</button>
        </div>
      </div>
    </div>
  </main>
</template>
