<script setup>
// Kit: a business assistant's login (law, dental, hotel, lodge): a drawing with three floating cards on one side, and
// the business's people on the other; one click logs in as that role (the demo's password). The drawing comes in the
// «art» slot; its pieces with class es-house rise in one after another.
// base: the assistant's API; setSession(token, user); info: the store (setupOpen); business: its name, place and
// people; roles: {username: {role, desc, icon, tone, who}}; kind: «دفتر وکالت» before the place; noun: «دفتر» in
// «دموی جدید برای دفتر دیگر»; floats: [{icon, tone, text, small, style}].
import { ref, onMounted, onUnmounted } from "vue"
import { api } from "../../lib/api.js"
import { gate } from "../../lib/gate.js"
import gsap from "gsap"
import { motion } from "../../lib/motion.js"
import Icon from "../Icon.vue"

const props = defineProps({ base: String, setSession: Function, info: Object, business: Object, roles: Object, kind: String, noun: String,
                            letter: { type: String, default: "ا" }, floats: { type: Array, default: () => [] } })
const error = ref(""), busy = ref(false), picked = ref(""), root = ref(null)
const login = async (username) => {
  error.value = ""; busy.value = true; picked.value = username
  try {
    const d = await api(`${props.base}/login`, { username, password: "1234" })
    props.setSession(d.token, d.user)
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
        <slot name="art" />
        <div v-for="(f, i) in floats" :key="i" :class="['float-card', 'fc' + (i + 1)]" :style="f.style"><span :class="['tint', 'sm', 't-' + f.tone]"><Icon :name="f.icon" :size="18" /></span><div>{{ f.text }}<small>{{ f.small }}</small></div></div>
      </div>
    </div>
    <div class="auth-panel">
      <div class="auth-form">
        <div class="flex items-center gap-3"><span class="logo">{{ (business.name || letter)[0] }}</span><b class="text-ink text-lg">{{ business.name }}</b></div>
        <h1>دستیار {{ business.name }}</h1>
        <p class="muted">{{ kind }} · {{ business.place }}. با یکی از افراد وارد شوید.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="role-list">
          <button v-for="(r, u) in roles" :key="u" type="button" class="role-card" :style="{ '--c': 'var(--' + r.tone + ')' }" :disabled="busy" @click="login(u)">
            <span :class="['tint', 't-' + r.tone]"><Icon :name="r.icon" :size="20" /></span>
            <span class="role-text"><b>{{ r.role }}</b><span>{{ business[r.who] }} · {{ r.desc }}</span></span>
            <span v-if="busy && picked === u" class="dots go"><i></i><i></i><i></i></span>
            <Icon v-else name="chevron" :size="18" class="go" />
          </button>
        </div>
        <p class="auth-note"><Icon name="shield" :size="16" /> همه‌ی داده‌های این نسخه ساختگی است.</p>
        <div class="login-tools">
          <button type="button" class="link switch-school" @click="info.setupOpen = true"><Icon name="refresh" :size="16" />دموی جدید برای {{ noun }} دیگر</button>
          <button v-if="gate.hub" type="button" class="link switch-school" @click="gate.app = ''"><Icon name="dashboard" :size="16" />همه‌ی دستیارها</button>
        </div>
      </div>
    </div>
  </main>
</template>
