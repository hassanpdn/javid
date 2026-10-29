<script setup>
// The fabric demo's login: shelves of fabric rolls on one side, the three roles on the other.
import { ref, onMounted, onUnmounted } from "vue"
import { api, fa, setFabricSession } from "../lib/api.js"
import { gate } from "../lib/gate.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"
import { shop, ROLES } from "./lib.js"
import Icon from "../components/Icon.vue"

const error = ref(""), busy = ref(false), picked = ref(""), root = ref(null)
// rolls of fabric lying on three shelves: [x, shelf, color]
const ROLLS = [[48, 0, "#1f3b57"], [124, 0, "#7b1e2b"], [200, 0, "#e8dcc2"], [276, 0, "#2e6b55"],
               [86, 1, "#c9a243"], [162, 1, "#1d1d1f"], [238, 1, "#f1b8c8"],
               [48, 2, "#b08954"], [124, 2, "#f4f4f2"], [200, 2, "#1f2a4d"], [276, 2, "#8cc4ec"]]
const login = async (username) => {
  error.value = ""; busy.value = true; picked.value = username
  try {
    const d = await api("/fabric/login", { username, password: "1234" })
    setFabricSession(d.token, d.user)
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
    gsap.from(".roll", { y: -40, opacity: 0, stagger: .05, duration: .7, ease: "bounce.out", delay: .2 })
    gsap.from(".float-card", { scale: .6, opacity: 0, stagger: .2, duration: .7, ease: "back.out(1.8)", delay: 1 })
    // the cards' endless floating is CSS in main.css (.float-card)
  }, root.value)
})
onUnmounted(() => ctx?.revert())
</script>

<template>
  <main class="auth" ref="root">
    <div class="auth-art">
      <div class="art-stage">
        <svg viewBox="0 0 380 330" aria-hidden="true" class="shelves">
          <ellipse cx="190" cy="312" rx="170" ry="12" style="fill: var(--primary-soft)" />
          <rect v-for="s in 3" :key="s" x="30" :y="72 + (s - 1) * 92" width="320" height="8" rx="4" style="fill: var(--line)" />
          <rect x="30" y="20" width="8" height="300" rx="4" style="fill: var(--line)" /><rect x="342" y="20" width="8" height="300" rx="4" style="fill: var(--line)" />
          <g v-for="r in ROLLS" :key="r[0] + '-' + r[1]" class="roll">
            <rect :x="r[0]" :y="34 + r[1] * 92" width="64" height="38" rx="19" :style="{ fill: r[2] }" />
            <rect :x="r[0]" :y="34 + r[1] * 92" width="64" height="38" rx="19" fill="url(#rollShade)" />
            <ellipse :cx="r[0] + 13" :cy="53 + r[1] * 92" rx="11" ry="18" :style="{ fill: r[2] }" stroke="#000" stroke-opacity=".18" />
            <ellipse :cx="r[0] + 13" :cy="53 + r[1] * 92" rx="6" ry="10" fill="none" stroke="#fff" stroke-opacity=".35" />
            <ellipse :cx="r[0] + 13" :cy="53 + r[1] * 92" rx="2.5" ry="4" fill="#000" opacity=".35" />
          </g>
          <defs><linearGradient id="rollShade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".25" />
            <stop offset=".45" stop-color="#fff" stop-opacity=".18" /><stop offset="1" stop-color="#000" stop-opacity=".3" /></linearGradient></defs>
        </svg>
        <div class="float-card fc1" style="top: 2%; right: 0"><span class="tint sm t-danger"><Icon name="alert" :size="18" /></span><div>چک برگشتی پیدا شد<small>از روی فایل حسابداری</small></div></div>
        <div class="float-card fc2" style="top: 44%; left: -6%"><span class="tint sm t-success"><Icon name="file" :size="18" /></span><div>پیش‌فاکتور آماده شد<small>از روی سفارش تلفنی</small></div></div>
        <div class="float-card fc3" style="bottom: 2%; right: 8%"><span class="tint sm t-warning"><Icon name="clock" :size="18" /></span><div>این جنس رو به تمام شدن است<small>از روی فروش سی روز اخیر</small></div></div>
      </div>
    </div>

    <div class="auth-panel">
      <div class="auth-form">
        <div class="flex items-center gap-3"><span class="logo">{{ (shop.business.name || 'پ')[0] }}</span><b class="text-ink text-lg">{{ shop.business.name }}</b></div>
        <h1>دستیار {{ shop.business.name }}</h1>
        <p class="muted">عمده‌فروشی پارچه · {{ shop.business.place }}. با یکی از نقش‌ها وارد شوید.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="role-list">
          <button v-for="(r, u) in ROLES" :key="u" type="button" class="role-card" :style="{ '--c': 'var(--' + r.tone + ')' }" :disabled="busy" @click="login(u)">
            <span :class="['tint', 't-' + r.tone]"><Icon :name="r.icon" :size="20" /></span>
            <span class="role-text"><b>{{ r.role }}</b><span>{{ shop.business[r.who] }} · {{ r.desc }}</span></span>
            <span v-if="busy && picked === u" class="dots go"><i></i><i></i><i></i></span>
            <Icon v-else name="chevron" :size="18" class="go" />
          </button>
        </div>
        <p class="auth-note"><Icon name="shield" :size="16" /> همه‌ی داده‌ها و فایل‌های این نسخه ساختگی است.</p>
        <div class="login-tools">
          <button type="button" class="link switch-school" @click="shop.setupOpen = true"><Icon name="refresh" :size="16" />دموی جدید برای فروشگاه دیگر</button>
          <button v-if="gate.hub" type="button" class="link switch-school" @click="gate.app = ''"><Icon name="dashboard" :size="16" />همه‌ی دستیارها</button>
        </div>
      </div>
    </div>
  </main>
</template>
