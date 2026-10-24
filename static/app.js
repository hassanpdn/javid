const { createApp, ref, reactive, computed, nextTick, onMounted, onUnmounted, watch } = Vue

// ---------- shared helpers ----------
const store = {
  get: (k) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k, v) => { try { localStorage.setItem(k, v) } catch {} },
  del: (k) => { try { localStorage.removeItem(k) } catch {} },
}
// Persian digits for everything we show
const fa = (v) => String(v ?? "").replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d])

// One shared session object; every component reads the token from here
const session = reactive({ token: store.get("token"), user: null })
const clearSession = () => { session.token = null; session.user = null; store.del("token") }

async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token || ""}` },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401 && path !== "/login") { clearSession(); throw new Error("401") }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || res.status)
  return data
}

// Light/dark theme. index.html already applied the saved one before the first paint.
const theme = reactive({ dark: document.documentElement.classList.contains("dark") })
watch(() => theme.dark, (dark) => {
  document.documentElement.classList.toggle("dark", dark)
  store.set("theme", dark ? "dark" : "light")
})

// ---------- motion (GSAP) ----------
// All animation goes through these helpers. They do nothing when GSAP is missing
// or when the person asked their system for less motion.
const motion = typeof gsap !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches

// v-reveal: an element fades up when it appears. Elements that appear in the same
// frame are animated together with a small delay between them, so a page builds up in order.
let revealBatch = []
const vReveal = {
  mounted(el) {
    if (!motion) return
    gsap.set(el, { opacity: 0, y: 18 })
    revealBatch.push(el)
    if (revealBatch.length > 1) return
    requestAnimationFrame(() => {
      const els = revealBatch; revealBatch = []
      gsap.to(els, { opacity: 1, y: 0, duration: .6, ease: "power3.out", stagger: .07, clearProps: "opacity,transform" })
    })
  },
}
// v-pop: dialogs spring in. v-pop:drop is the smaller version for dropdown menus.
const vPop = {
  mounted(el, { arg }) {
    if (!motion) return
    const drop = arg === "drop"
    gsap.fromTo(el, drop ? { opacity: 0, y: -10, scale: .96 } : { opacity: 0, y: 30, scale: .94 },
      { opacity: 1, y: 0, scale: 1, duration: drop ? .3 : .45, ease: drop ? "power2.out" : "back.out(1.5)", clearProps: "opacity,transform" })
  },
}
// v-drawer: side drawers slide in from the right edge
const vDrawer = {
  mounted(el) {
    if (!motion) return
    gsap.fromTo(el, { xPercent: 100 }, { xPercent: 0, duration: .5, ease: "power4.out", clearProps: "transform" })
  },
}

// ---------- icons (line icons in the style of Tabler, which Vuexy uses) ----------
const ICONS = {
  dashboard: "M19 8.71 13.67 4.56a2.7 2.7 0 0 0-3.34 0L5 8.71a2.67 2.67 0 0 0-1 2.09v7.2A2 2 0 0 0 6 20h12a2 2 0 0 0 2-2v-7.2c0-.81-.37-1.58-1-2.09M16 15c-2.21 1.33-5.79 1.33-8 0",
  mail: "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7zM3 7l9 6 9-6",
  inbox: "M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6zM4 13h3l3 3h4l3-3h3",
  users: "M5 7a4 4 0 1 0 8 0 4 4 0 1 0-8 0M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M16 3.13a4 4 0 0 1 0 7.75M21 21v-2a4 4 0 0 0-3-3.85",
  user: "M8 7a4 4 0 1 0 8 0 4 4 0 0 0-8 0M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2",
  userCheck: "M8 7a4 4 0 1 0 8 0 4 4 0 0 0-8 0M6 21v-2a4 4 0 0 1 4-4h4M15 19l2 2 4-4",
  message: "M8 9h8M8 13h6M18 4a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3h-5l-5 3v-3H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3h12z",
  bell: "M10 5a2 2 0 1 1 4 0 7 7 0 0 1 4 6v3a4 4 0 0 0 2 3H4a4 4 0 0 0 2-3v-3a7 7 0 0 1 4-6M9 17v1a3 3 0 0 0 6 0v-1",
  logout: "M14 8V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2v-2M9 12h12l-3-3M18 15l3-3",
  moon: "M12 3h.39a7.5 7.5 0 0 0 7.92 12.45A9 9 0 1 1 12 3z",
  sun: "M8 12a4 4 0 1 0 8 0 4 4 0 1 0-8 0M3 12h1m8-9v1m8 8h1m-9 8v1M5.6 5.6l.7.7m12.1-.7-.7.7m0 11.4.7.7m-12.1-.7-.7.7",
  menu: "M4 6h16M4 12h16M4 18h16",
  x: "M18 6 6 18M6 6l12 12",
  chevron: "M15 6l-6 6 6 6",
  sparkles: "M16 18a2 2 0 0 1 2 2 2 2 0 0 1 2-2 2 2 0 0 1-2-2 2 2 0 0 1-2 2zm0-12a2 2 0 0 1 2 2 2 2 0 0 1 2-2 2 2 0 0 1-2-2 2 2 0 0 1-2 2zM9 18a6 6 0 0 1 6-6 6 6 0 0 1-6-6 6 6 0 0 1-6 6 6 6 0 0 1 6 6z",
  clock: "M12 7v5l3 3M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z",
  alert: "M12 9v4M12 16v.01M10.24 3.96 2.4 17a2 2 0 0 0 1.71 3h15.78a2 2 0 0 0 1.71-3L13.76 3.96a2 2 0 0 0-3.52 0z",
  check: "M5 12l5 5L20 7",
  file: "M14 3v4a1 1 0 0 0 1 1h4M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2zM9 13h6M9 17h6",
  heart: "M19.5 12.57 12 20l-7.5-7.43A5 5 0 1 1 12 6.01a5 5 0 1 1 7.5 6.57",
  calendar: "M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7zM16 3v4M8 3v4M4 11h16",
  school: "M22 9 12 5 2 9l10 4 10-4v6M6 10.6V16a6 3 0 0 0 12 0v-5.4",
  send: "M10 14 21 3M21 3l-6.5 18a.55.55 0 0 1-1 0L10 14l-7-3.5a.55.55 0 0 1 0-1L21 3",
  search: "M3 10a7 7 0 1 0 14 0 7 7 0 1 0-14 0M21 21l-6-6",
  plus: "M12 5v14M5 12h14",
  chart: "M3 13a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM15 9a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1zM9 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1z",
  forward: "M19 12H5M11 6l-6 6 6 6",
  notebook: "M6 4h11a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1M9 4v16M13 8h2M13 12h2",
  book: "M3 19a9 9 0 0 1 9 0 9 9 0 0 1 9 0M3 6a9 9 0 0 1 9 0 9 9 0 0 1 9 0M3 6v13M12 6v13M21 6v13",
  trendDown: "M3 7l6 6 4-4 8 8M21 10v7h-7",
  shield: "M12 3a12 12 0 0 0 8.5 3A12 12 0 0 1 12 21 12 12 0 0 1 3.5 6 12 12 0 0 0 12 3",
  edit: "M4 20h4L18.5 9.5a2.83 2.83 0 0 0-4-4L4 16v4M13.5 6.5l4 4",
  refresh: "M20 11A8.1 8.1 0 0 0 4.5 9M4 5v4h4M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4",
  pencil: "M4 20h4L18.5 9.5a2.83 2.83 0 0 0-4-4L4 16v4",
}
const Icon = {
  props: { name: String, size: { default: 20 } },
  template: `<span class="ico"><svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="ICONS[name] || ICONS.sparkles"/></svg></span>`,
  setup() { return { ICONS } },
}

// Each name always gets the same color, so a person is easy to spot across pages
const TONES = ["primary", "success", "info", "warning", "danger", "secondary"]
const toneOf = (s) => TONES[[...String(s || "")].reduce((n, c) => n + c.charCodeAt(0), 0) % TONES.length]
const Avatar = {
  props: ["name", "size", "tone"],
  template: `<span :class="['avatar', 't-' + (tone || toneOf(name))]" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px', fontSize: (size || 40) * 0.42 + 'px' }">{{ (name || '?')[0] }}</span>`,
  setup() { return { toneOf } },
}

// A number that counts up to its value (the value itself always comes from the server)
const CountUp = {
  props: { value: { type: Number, default: 0 } },
  template: `<span>{{ fa(Math.round(state.n)) }}</span>`,
  setup(props) {
    const state = reactive({ n: 0 })
    let tween
    watch(() => props.value, (v) => {
      tween?.kill()
      if (!motion) { state.n = v; return }
      tween = gsap.to(state, { n: v, duration: 1.2, ease: "power2.out" })
    }, { immediate: true })
    onUnmounted(() => tween?.kill())
    return { state, fa }
  },
}

// Text written by the assistant appears letter by letter, like it is being typed
const TypeText = {
  props: ["text"],
  template: `<span :class="{ 'typing-caret': typing }">{{ fa(shown) }}</span>`,
  setup(props) {
    const state = reactive({ n: 0 }), typing = ref(false)
    const shown = computed(() => (props.text || "").slice(0, Math.round(state.n)))
    let tween
    watch(() => props.text, (t) => {
      tween?.kill()
      if (!motion || !t) { state.n = (t || "").length; return }
      state.n = 0; typing.value = true
      tween = gsap.to(state, { n: t.length, duration: Math.min(3, t.length / 90), ease: "none", onComplete: () => { typing.value = false } })
    }, { immediate: true })
    onUnmounted(() => tween?.kill())
    return { shown, typing, fa }
  },
}

// The assistant's animated "orb". busy makes it spin faster while the model is working.
const AiOrb = {
  props: { size: { default: 120 }, busy: { default: false } },
  template: `
  <svg ref="el" class="orb" :width="size" :height="size" viewBox="0 0 120 120" aria-hidden="true">
    <defs><linearGradient id="orbGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color: var(--primary)"/><stop offset="1" style="stop-color: var(--info)"/></linearGradient></defs>
    <circle class="halo" cx="60" cy="60" r="56" style="fill: var(--primary)" opacity=".08"/>
    <circle class="ring" cx="60" cy="60" r="50" fill="none" style="stroke: var(--primary)" stroke-opacity=".4" stroke-width="1.5" stroke-dasharray="4 7"/>
    <g class="core">
      <circle cx="60" cy="60" r="34" fill="url(#orbGrad)"/>
      <path d="M60 42c1.6 8.8 5.2 12.4 14 14-8.8 1.6-12.4 5.2-14 14-1.6-8.8-5.2-12.4-14-14 8.8-1.6 12.4-5.2 14-14Z" fill="#fff"/>
      <path d="M74 38c.6 3.4 2 4.8 5.4 5.4-3.4.6-4.8 2-5.4 5.4-.6-3.4-2-4.8-5.4-5.4 3.4-.6 4.8-2 5.4-5.4Z" fill="#fff" opacity=".8"/>
    </g>
    <circle class="sat a" cx="60" cy="10" r="4" style="fill: var(--warning)"/>
    <circle class="sat b" cx="110" cy="60" r="3" style="fill: var(--success)"/>
  </svg>`,
  setup(props) {
    const el = ref(null)
    let ctx, spin
    onMounted(() => {
      if (!motion) return
      ctx = gsap.context(() => {
        const loop = { repeat: -1, ease: "none", svgOrigin: "60 60" }
        spin = gsap.timeline({ repeat: -1 })
        spin.to(".ring", { rotation: 360, duration: 18, ...loop, repeat: 0 }, 0)
        gsap.to(".sat.a", { rotation: 360, duration: 9, ...loop })
        gsap.to(".sat.b", { rotation: -360, duration: 13, ...loop })
        gsap.to(".core", { scale: 1.06, svgOrigin: "60 60", duration: 1.8, yoyo: true, repeat: -1, ease: "sine.inOut" })
        gsap.to(".halo", { scale: 1.1, opacity: .18, svgOrigin: "60 60", duration: 2.2, yoyo: true, repeat: -1, ease: "sine.inOut" })
        spin.timeScale(props.busy ? 8 : 1)
      }, el.value)
    })
    watch(() => props.busy, (b) => spin && gsap.to(spin, { timeScale: b ? 8 : 1, duration: .6 }))
    onUnmounted(() => ctx?.revert())
    return { el }
  },
}

// Round gauge for a percentage, drawn with plain SVG
const RadialGauge = {
  props: ["value", "label"],
  template: `
  <svg class="gauge" viewBox="0 0 140 140" width="180" height="180" role="img" :aria-label="label + ' ' + fa(value) + ' درصد'">
    <circle class="track" cx="70" cy="70" r="56" fill="none" stroke-width="12"/>
    <circle ref="arc" class="val" cx="70" cy="70" r="56" fill="none" stroke-width="12"
            :stroke-dasharray="C" :stroke-dashoffset="C * (1 - value / 100)" transform="rotate(-90 70 70)"/>
    <text x="70" y="74" text-anchor="middle" font-size="28">{{ fa(value) }}٪</text>
    <text class="sub" x="70" y="98" text-anchor="middle" font-size="12">{{ label }}</text>
  </svg>`,
  setup() {
    const C = 2 * Math.PI * 56, arc = ref(null)
    onMounted(() => { if (motion) gsap.from(arc.value, { attr: { "stroke-dashoffset": C }, duration: 1.6, ease: "power3.out", delay: .2 }) })
    return { C, arc, fa }
  },
}

// ---------- login ----------
const DEMO_USERS = [
  { u: "modir", role: "مدیر", name: "آقای دکتر انوشه‌پور", desc: "خلاصه روز، هشدارها و تصمیم‌ها", icon: "chart", tone: "primary" },
  { u: "edari", role: "پرسنل اداری", name: "کارمند اداری", desc: "صندوق نامه هوشمند و دستیار پیگیری", icon: "mail", tone: "info" },
  { u: "moalem", role: "آموزگار", name: "سارا احمدی، پایه چهارم", desc: "کلاس و دانش‌آموزان", icon: "book", tone: "success", soon: true },
  { u: "karimi", role: "معلم ورزش", name: "نرگس کریمی", desc: "اعلان‌ها و تذکرها", icon: "users", tone: "warning", soon: true },
  { u: "moshaver", role: "مشاور", name: "مریم کاظمی", desc: "دانش‌آموزان نیازمند توجه و پیام به اولیا", icon: "message", tone: "success" },
  { u: "vali", role: "ولی", name: "رضا محمدی، پدر آوا", desc: "گزارش هفتگی، پیشرفت و فرم‌های سلامت", icon: "user", tone: "danger" },
  { u: "daneshamooz", role: "دانش‌آموز", name: "آوا محمدی", desc: "نمره‌ها و پیشرفت من", icon: "school", tone: "secondary", soon: true },
]
const LoginPage = {
  template: `
  <div class="auth" ref="root">
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
        <div class="float-card fc3" style="bottom: 4%; right: 10%"><span class="tint sm t-success"><Icon name="message" :size="18" /></span><div>پیام مشاور برای ولی<small>بعد از تأیید مشاور</small></div></div>
      </div>
    </div>

    <div class="auth-panel">
      <div class="auth-form">
        <div class="flex items-center gap-3"><span class="logo">ج</span><b class="text-ink text-lg">دبستان جاوید</b></div>
        <h1>به دستیار هوشمند جاوید خوش آمدید</h1>
        <p class="muted">نسخه آزمایشی. با یکی از نقش‌ها وارد شوید؛ هر نقش پنل و دسترسی‌های خودش را دارد.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="role-list">
          <button v-for="d in demo" :key="d.u" type="button" class="role-card" :style="{ '--c': 'var(--' + d.tone + ')' }"
                  :disabled="busy" @click="login(d.u, '1234')">
            <span :class="['tint', 't-' + d.tone]"><Icon :name="d.icon" :size="20" /></span>
            <span class="role-text"><b>{{ d.role }}</b><span>{{ d.name }} · {{ d.desc }}</span></span>
            <span v-if="d.soon" class="soon">فعلا: چت اسناد</span>
            <span v-if="busy && picked === d.u" class="dots go"><i></i><i></i><i></i></span>
            <Icon v-else name="chevron" :size="18" class="go" />
          </button>
        </div>
        <p class="auth-note"><Icon name="shield" :size="16" /> همه داده‌های این نسخه ساختگی است.</p>
      </div>
    </div>
  </div>`,
  setup() {
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
    onMounted(() => {
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
    return { error, busy, picked, root, windows, demo: DEMO_USERS, login }
  },
}

// ---------- chat (a full page inside every panel) ----------
const EXAMPLES = {
  manager: ["ساعت کار کارکنان اداری چقدره؟", "مدرسه غیرانتفاعی مالیات میده؟", "ساعت شروع کلاس‌ها چنده؟"],
  staff: ["سال مالی مدرسه از کی شروع میشه؟", "مدرسه باید حساب بانکی جدا داشته باشه؟", "غیبت بیماری رو تا کی باید اطلاع داد؟"],
  default: ["ساعت شروع کلاس‌ها چنده؟", "اگه بچه‌م مریض بشه غیبتش چطور موجه میشه؟", "استفاده از موبایل توی مدرسه مجازه؟"],
}
const ChatBox = {
  // endpoint/examples/intro let other panels reuse the same chat (e.g. the parent's questions about their child)
  props: { endpoint: { default: "/chat" }, examples: { default: null }, intro: { default: null }, loadingText: { default: "در حال جستجو در اسناد" },
           title: { default: "" }, subtitle: { default: "" } },
  template: `
  <div class="chatbox">
    <header v-if="title" class="chat-head">
      <span class="bot-avatar"><Icon name="sparkles" :size="20" /></span>
      <div><b>{{ title }}</b><small><span class="online"></span>{{ subtitle }}</small></div>
    </header>
    <main class="chat" ref="box">
      <div v-if="messages.length === 0" class="empty">
        <AiOrb :size="96" />
        <p>{{ intro || 'سؤالتون رو از آیین‌نامه‌ها و دستورالعمل‌ها بپرسید، یا یکی از این‌ها رو امتحان کنید:' }}</p>
        <div class="examples">
          <button v-for="ex in shownExamples" :key="ex" class="example" @click="send(ex)"><Icon name="sparkles" :size="16" />{{ ex }}</button>
        </div>
      </div>
      <div v-for="(m, i) in messages" :key="i" v-reveal :class="['msg-row', m.from]">
        <span v-if="m.from !== 'user'" class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span>
        <div class="msg">
          <div class="bubble">{{ fa(m.text) }}</div>
          <div v-if="m.sources && m.sources.length" class="sources">
            <span>منبع:</span>
            <span v-for="s in m.sources" :key="s.doc + s.article" class="chip">{{ s.doc }}{{ s.article ? '، ' + fa(s.article) : '' }}</span>
            <span v-if="m.checked" class="muted small">· عددها مستقیم از سامانه مدرسه</span>
          </div>
        </div>
      </div>
      <div v-if="loading" class="msg-row bot">
        <span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span>
        <div class="msg"><div class="bubble loading">{{ loadingText }}<span class="dots"><i></i><i></i><i></i></span></div></div>
      </div>
    </main>
    <form class="composer" @submit.prevent="send(input)">
      <input v-model="input" :disabled="loading" placeholder="سؤالتون رو اینجا بنویسید...">
      <button class="btn primary" type="submit" :disabled="loading || !input.trim()"><Icon name="send" :size="18" /><span>ارسال</span></button>
    </form>
  </div>`,
  setup(props) {
    const messages = ref([]), input = ref(""), loading = ref(false), box = ref(null)
    const shownExamples = computed(() => props.examples || EXAMPLES[session.user?.role] || EXAMPLES.default)
    const scrollDown = async () => { await nextTick(); if (box.value) box.value.scrollTo({ top: box.value.scrollHeight, behavior: "smooth" }) }
    const send = async (text) => {
      const question = text.trim()
      if (!question || loading.value) return
      messages.value.push({ from: "user", text: question }); input.value = ""; loading.value = true; scrollDown()
      try {
        const data = await api(props.endpoint, { question })
        messages.value.push({ from: "bot", text: data.answer, sources: data.sources, checked: data.checked })
      } catch (e) {
        if (e.message !== "401") messages.value.push({ from: "bot error", text: "ارتباط با سرور برقرار نشد. چند لحظه بعد دوباره امتحان کنید." })
      } finally { loading.value = false; scrollDown() }
    }
    return { messages, input, loading, box, shownExamples, send, fa }
  },
}

// ---------- notification bell (in every navbar) ----------
const KINDS = {
  warning: { label: "تذکر", icon: "alert", tone: "danger" },
  letter: { label: "نامه", icon: "mail", tone: "primary" },
  reminder: { label: "یادآوری", icon: "clock", tone: "warning" },
  info: { label: "اطلاع", icon: "check", tone: "success" },
  referral: { label: "ارجاع", icon: "forward", tone: "info" },
  suggestion: { label: "پیام مشاور", icon: "message", tone: "success" },
}
// tinted icon for a notification kind
const KindIcon = {
  props: ["kind"],
  template: `<span :class="['tint', 'sm', 't-' + k.tone]"><Icon :name="k.icon" :size="18" /></span>`,
  setup(props) { return { k: computed(() => KINDS[props.kind] || KINDS.info) } },
}
const NotificationBell = {
  components: { KindIcon },
  template: `
  <div class="bell-wrap" ref="wrap">
    <button class="icon-btn" :class="{ on: open }" @click="open = !open" :aria-label="'اعلان‌ها، ' + fa(unread) + ' خوانده‌نشده'">
      <span ref="icon"><Icon name="bell" :size="22" /></span>
      <span v-if="unread" class="badge-dot">{{ fa(unread > 99 ? '99+' : unread) }}</span>
    </button>

    <div v-if="open" v-pop:drop class="bell-panel">
      <header class="bp-head">
        <div class="bp-title-row"><b>اعلان‌ها</b><span v-if="unread" class="chip">{{ fa(unread) }} جدید</span></div>
        <button v-if="unread" class="link small" @click="readAll">همه خوانده شد</button>
      </header>
      <nav class="bp-filters">
        <button v-for="f in filters" :key="f.key" :class="{ on: filter === f.key }" @click="filter = f.key">
          {{ f.label }}<span v-if="f.n" class="bp-n">{{ fa(f.n) }}</span>
        </button>
      </nav>
      <div class="bp-list">
        <div v-if="!visible.length" class="bp-empty">
          <span class="tint lg t-success"><Icon name="check" :size="24" /></span>
          <p>اعلانی در این بخش نیست.</p>
        </div>
        <button v-for="n in visible" :key="n.id" :class="['bp-item', { unread: !n.read_at }]" @click="show(n)">
          <KindIcon :kind="n.kind" />
          <span class="bp-body">
            <span class="bp-title">{{ fa(n.title) }}</span>
            <span class="bp-meta">
              <span>{{ (KINDS[n.kind] || KINDS.info).label }}</span>
              <span class="sep">·</span>
              <span>{{ fa(n.created_at) }}</span>
              <span v-if="n.needs_ack && !n.ack_at" class="bp-pill">نیاز به رؤیت</span>
              <span v-else-if="n.ack_at" class="bp-pill ok">رؤیت شد</span>
            </span>
          </span>
          <span v-if="!n.read_at" class="bp-dot" aria-label="خوانده‌نشده"></span>
        </button>
      </div>
    </div>

    <div v-if="current" class="overlay" @click.self="current = null">
      <div class="dialog" v-pop>
        <div class="dlg-kind"><KindIcon :kind="current.kind" />{{ (KINDS[current.kind] || KINDS.info).label }}</div>
        <h3>{{ fa(current.title) }}</h3>
        <p class="muted small">{{ fa(current.created_at) }}</p>
        <div v-if="current.body" class="letter">{{ fa(current.body) }}</div>
        <p v-if="current.ack_at" class="check ok">✓ رؤیت شد: {{ fa(current.ack_at) }}</p>
        <div class="dialog-actions">
          <button v-if="current.needs_ack && !current.ack_at" class="btn primary" @click="ack"><Icon name="check" :size="18" />رؤیت شد</button>
          <button class="btn ghost" @click="current = null">بستن</button>
        </div>
      </div>
    </div>
  </div>`,
  setup() {
    const items = ref([]), unread = ref(0), open = ref(false), current = ref(null), filter = ref("all"), wrap = ref(null), icon = ref(null)
    const filters = computed(() => [
      { key: "all", label: "همه" },
      { key: "unread", label: "خوانده‌نشده", n: unread.value },
      { key: "ack", label: "نیاز به رؤیت", n: items.value.filter((n) => n.needs_ack && !n.ack_at).length },
    ])
    const visible = computed(() => items.value.filter((n) =>
      filter.value === "unread" ? !n.read_at : filter.value === "ack" ? n.needs_ack && !n.ack_at : true))
    let loaded = false
    const load = async () => {
      try {
        const d = await api("/notifications")
        if (d.unread > unread.value) {
          window.dispatchEvent(new Event("notifications-changed"))
          // ring the bell when something new arrives (not on the first load)
          if (loaded && motion && icon.value) gsap.fromTo(icon.value, { rotation: -18 }, { rotation: 0, duration: 1.2, ease: "elastic.out(1.2, .25)", transformOrigin: "50% 0" })
        }
        items.value = d.items; unread.value = d.unread; loaded = true
      } catch {}
    }
    const show = async (n) => {
      open.value = false; current.value = n
      if (!n.read_at) { await api(`/notifications/${n.id}/read`, {}); load() }
    }
    const ack = async () => {
      await api(`/notifications/${current.value.id}/ack`, {})
      await load(); current.value = items.value.find((n) => n.id === current.value.id)
    }
    const readAll = async () => { await api("/notifications/read-all", {}); load() }
    // close the panel when clicking anywhere outside it
    const outside = (e) => { if (open.value && wrap.value && !wrap.value.contains(e.target)) open.value = false }
    let timer
    onMounted(() => { load(); timer = setInterval(load, 15000); document.addEventListener("click", outside) })
    onUnmounted(() => { clearInterval(timer); document.removeEventListener("click", outside) })
    watch(current, (v) => document.body.classList.toggle("no-scroll", !!v))
    return { KINDS, items, unread, open, current, filter, filters, visible, wrap, icon, show, ack, readAll, fa }
  },
}

// ---------- app layout: sidebar on the right, navbar on top (Vuexy vertical layout) ----------
// nav: [{ header }] or [{ key, label, icon, badge }]. v-model is the key of the open page.
const AppLayout = {
  components: { NotificationBell },
  props: { title: String, subtitle: String, nav: Array, modelValue: String },
  emits: ["update:modelValue"],
  template: `
  <div :class="['layout', { 'menu-open': menuOpen }]">
    <aside class="sidebar" ref="side">
      <div class="side-brand">
        <span class="logo">ج</span>
        <div><b>دبستان جاوید</b><small>دستیار هوشمند مدرسه</small></div>
        <button class="icon-btn xl:hidden" @click="menuOpen = false" aria-label="بستن منو"><Icon name="x" /></button>
      </div>
      <nav class="side-nav">
        <template v-for="item in nav" :key="item.key || item.header">
          <div v-if="item.header" class="side-header">{{ item.header }}</div>
          <button v-else :class="['side-item', { on: item.key === modelValue }]" @click="pick(item.key)">
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
          <div class="nav-title"><b>{{ title }}</b><small v-if="subtitle">{{ subtitle }}</small></div>
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
      <footer class="footer">نسخه آزمایشی دستیار هوشمند دبستان غیرانتفاعی جاوید · همه داده‌ها ساختگی است</footer>
    </div>
  </div>`,
  setup(props, { emit }) {
    const menuOpen = ref(false), userOpen = ref(false), wrap = ref(null), side = ref(null), themeIcon = ref(null)
    const pick = (k) => { emit("update:modelValue", k); menuOpen.value = false; window.scrollTo({ top: 0, behavior: "smooth" }) }
    const logout = async () => { try { await api("/logout", {}) } catch {} clearSession() }
    const toggleTheme = () => {
      theme.dark = !theme.dark
      if (motion && themeIcon.value) gsap.fromTo(themeIcon.value, { rotation: -120, scale: .4 }, { rotation: 0, scale: 1, duration: .6, ease: "back.out(2)" })
    }
    const outside = (e) => { if (userOpen.value && wrap.value && !wrap.value.contains(e.target)) userOpen.value = false }
    watch(menuOpen, (v) => document.body.classList.toggle("no-scroll", v))
    onMounted(() => {
      document.addEventListener("click", outside)
      if (!motion) return
      gsap.from(side.value.querySelectorAll(".side-brand, .side-header, .side-item, .side-user"),
        { x: 30, opacity: 0, stagger: .05, duration: .5, ease: "power3.out", clearProps: "opacity,transform" })
      gsap.from(".navbar-inner", { y: -24, opacity: 0, duration: .6, ease: "power3.out", clearProps: "opacity,transform" })
    })
    onUnmounted(() => { document.removeEventListener("click", outside); document.body.classList.remove("no-scroll") })
    return { user: computed(() => session.user), theme, menuOpen, userOpen, wrap, side, themeIcon, pick, logout, toggleTheme, fa }
  },
}

// roles without their own panel yet get the document chat only
const ChatPage = {
  components: { AppLayout, ChatBox },
  template: `
  <AppLayout title="دستیار اسناد" :subtitle="user.role_name" :nav="nav" model-value="chat">
    <ChatBox v-reveal class="card chat-card" title="دستیار اسناد" subtitle="پاسخ فقط از روی آیین‌نامه‌ها و دستورالعمل‌های مدرسه" />
  </AppLayout>`,
  setup() {
    const nav = [{ header: "دستیار" }, { key: "chat", label: "پرسش از اسناد", icon: "message" }]
    return { user: computed(() => session.user), nav }
  },
}

// ---------- bar chart, drawn with plain SVG ----------
const BarChart = {
  props: ["points"],  // [{ jdate, rate }]
  template: `
  <svg ref="svg" :viewBox="'0 0 ' + W + ' ' + H" class="bars" role="img" aria-label="نمودار درصد حضور">
    <defs>
      <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color: var(--primary)"/><stop offset="1" style="stop-color: var(--primary); stop-opacity: .35"/></linearGradient>
      <linearGradient id="barGradLow" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color: var(--warning)"/><stop offset="1" style="stop-color: var(--warning); stop-opacity: .35"/></linearGradient>
    </defs>
    <line v-for="r in [85, 90, 95, 100]" :key="r" class="gridline" x1="0" :x2="W" :y1="y(r)" :y2="y(r)" />
    <g v-for="(p, i) in points" :key="p.jdate">
      <rect :x="x(i)" :y="y(p.rate)" :width="bw" :height="H - 26 - y(p.rate)" rx="7" :class="p.rate < 95 ? 'bar low' : 'bar'" />
      <text :x="x(i) + bw / 2" :y="y(p.rate) - 7" class="val">{{ fa(p.rate) }}</text>
      <text :x="x(i) + bw / 2" :y="H - 6" class="lbl">{{ fa(p.jdate) }}</text>
    </g>
  </svg>`,
  setup(props) {
    const W = 900, H = 210, gap = 22, svg = ref(null)
    const bw = computed(() => (W - gap * (props.points.length - 1)) / props.points.length)
    const x = (i) => W - (i + 1) * bw.value - i * gap          // right to left, like Persian reading
    const y = (rate) => 30 + (100 - Math.max(rate, 80)) * (H - 66) / 20  // zoom on the 80..100 range
    onMounted(() => {
      if (!motion) return
      gsap.from(svg.value.querySelectorAll(".bar"), { scaleY: 0, transformOrigin: "50% 100%", duration: 1, ease: "power3.out", stagger: .06, delay: .3 })
      gsap.from(svg.value.querySelectorAll(".val"), { opacity: 0, y: 8, duration: .5, stagger: .06, delay: .7 })
    })
    return { W, H, bw, x, y, svg, fa }
  },
}

// ---------- manager panel ----------
const ALERT_LOOK = {
  teacher_late: { icon: "clock", tone: "danger" },
  letter_decision: { icon: "file", tone: "primary" },
  letter_deadline: { icon: "calendar", tone: "warning" },
}
const ManagerPanel = {
  components: { AppLayout, ChatBox, BarChart, RadialGauge },
  template: `
  <AppLayout title="داشبورد مدیر" :subtitle="data ? fa(data.today) : ''" :nav="nav" v-model="view">
    <div v-show="view === 'home'" class="flex flex-col gap-6">
      <div class="grid grid-cols-12 gap-6">
        <section v-reveal class="card welcome brief col-span-12 xl:col-span-8">
          <div class="welcome-text">
            <h2>روز بخیر، {{ user.full_name }}</h2>
            <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه امروز به قلم دستیار</div>
            <p v-if="brief"><TypeText :text="brief" /></p>
            <div v-else class="shimmer"><span></span><span></span><span style="width:60%"></span></div>
          </div>
          <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
        </section>
        <section v-reveal class="card col-span-12 xl:col-span-4 flex flex-col">
          <div class="card-head">حضور امروز <small>دانش‌آموزان</small></div>
          <template v-if="data">
            <RadialGauge :value="presentPct" label="حاضر" />
            <div class="grid grid-cols-3 text-center mt-2">
              <div><b class="text-ink text-lg"><CountUp :value="data.students.present" /></b><small class="block muted">حاضر</small></div>
              <div><b class="text-danger text-lg"><CountUp :value="data.students.absent" /></b><small class="block muted">غایب</small></div>
              <div><b class="text-warning text-lg"><CountUp :value="data.students.late" /></b><small class="block muted">تأخیر</small></div>
            </div>
          </template>
          <div v-else class="shimmer"><span></span><span></span><span></span></div>
        </section>
      </div>

      <div v-if="data" class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6">
        <div v-for="s in stats" :key="s.label" v-reveal class="card stat" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span>
            <div class="stat-num"><CountUp :value="s.value" /> <span v-if="s.of" class="of">از {{ fa(s.of) }}</span></div></div>
          <div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ s.sub }}</div></div>
        </div>
      </div>

      <div v-if="data" class="grid grid-cols-12 gap-6">
        <section v-reveal class="card col-span-12 2xl:col-span-6">
          <div class="card-head">نیاز به توجه شما <span class="count">{{ fa(open) }}</span></div>
          <p v-if="!data.alerts.length" class="muted">موردی نیست.</p>
          <ul class="alerts">
            <li v-for="(a, i) in data.alerts" :key="i" :class="['alert', a.type, { done: a.done }]">
              <span :class="['tint', 't-' + (a.done ? 'success' : look(a).tone)]"><Icon :name="a.done ? 'check' : look(a).icon" :size="20" /></span>
              <div class="alert-body">
                <b>{{ fa(a.title) }}</b>
                <small class="muted">{{ fa(a.detail) }}</small>
                <small v-if="a.done" class="ok">✓ {{ fa(a.done_text) }}</small>
              </div>
              <button v-if="a.type === 'teacher_late' && !a.done" class="btn sm" @click="openDraft(a)"><Icon name="edit" :size="16" />پیش‌نویس تذکر</button>
              <div v-if="a.type === 'letter_decision'" class="btn-row">
                <button class="btn sm success" @click="decide(a, true)">موافقم</button>
                <button class="btn sm danger-soft" @click="decide(a, false)">مخالفم</button>
              </div>
            </li>
          </ul>
        </section>

        <section v-reveal class="card col-span-12 2xl:col-span-6">
          <div class="card-head"><span class="grow">درصد حضور دانش‌آموزان در ده روز اخیر</span>
            <span class="legend-dot" style="--c: var(--primary)">۹۵٪ و بیشتر</span><span class="legend-dot" style="--c: var(--warning)">کمتر از ۹۵٪</span></div>
          <BarChart :points="data.trend" />
        </section>
      </div>
    </div>

    <div v-show="view === 'chat'">
      <ChatBox class="card chat-card" title="دستیار اسناد" subtitle="پاسخ فقط از روی آیین‌نامه‌ها و دستورالعمل‌های مدرسه" />
    </div>

    <!-- written warning dialog -->
    <div v-if="draft.open" class="overlay" @click.self="draft.open = false">
      <div class="dialog" v-pop>
        <h3>تذکر کتبی به {{ draft.alert.name }}</h3>
        <p class="muted small">این متن را دستیار نوشته است. قبل از صدور بخوانید و هر جا لازم است ویرایش کنید.</p>
        <div v-if="draft.loading" class="shimmer tall"><span></span><span></span><span></span><span style="width:50%"></span></div>
        <p v-if="!draft.loading && draft.verified === true" class="check ok">✓ تاریخ‌ها و ساعت‌های این متن با ثبت ورود سامانه تطبیق داده شد.</p>
        <p v-if="!draft.loading && draft.verified === false" class="check bad">این موارد ثبت‌شده در متن نیامده یا متفاوت آمده: {{ fa(draft.missing.join('، ')) }}. قبل از صدور اصلاح کنید.</p>
        <textarea v-if="!draft.loading" v-model="draft.text" rows="10"></textarea>
        <div class="dialog-actions">
          <button class="btn primary" :disabled="draft.loading || !draft.text.trim() || draft.saving" @click="issue">تأیید و صدور</button>
          <button class="btn ghost" @click="draft.open = false">انصراف</button>
        </div>
      </div>
    </div>
  </AppLayout>`,
  setup() {
    const data = ref(null), brief = ref(""), view = ref("home")
    const draft = reactive({ open: false, alert: null, text: "", loading: false, saving: false, verified: null, missing: [] })
    const open = computed(() => data.value ? data.value.alerts.filter((a) => !a.done).length : 0)
    const nav = computed(() => [
      { header: "پیشخوان" },
      { key: "home", label: "داشبورد", icon: "dashboard", badge: open.value },
      { header: "دستیار" },
      { key: "chat", label: "پرسش از اسناد", icon: "message" },
    ])
    const presentPct = computed(() => {
      const s = data.value?.students
      return s && s.total ? Math.round(100 * s.present / s.total) : 0
    })
    const stats = computed(() => {
      const d = data.value
      return [
        { label: "دانش‌آموزان حاضر", value: d.students.present, of: d.students.total, sub: `${fa(d.students.absent)} غایب، ${fa(d.students.late)} تأخیر`, icon: "userCheck", tone: "success" },
        { label: "غیبت امروز", value: d.students.absent, sub: "دانش‌آموزان غایب امروز", icon: "calendar", tone: "danger" },
        { label: "تأخیر معلمان امروز", value: d.late_teachers.length, sub: d.late_teachers.map((t) => t.full_name + " " + fa(t.check_in)).join("، ") || "همه به موقع", icon: "clock", tone: "warning" },
        { label: "نامه‌های منتظر رسیدگی", value: d.open_letters, sub: "در صندوق پرسنل اداری", icon: "mail", tone: "primary" },
      ]
    })
    const look = (a) => ALERT_LOOK[a.type] || { icon: "alert", tone: "warning" }
    const load = async () => { data.value = await api("/manager/overview") }
    // While a dialog is open, freeze the page behind it
    watch(() => draft.open, (open) => document.body.classList.toggle("no-scroll", open))
    const onNotify = () => load()
    window.addEventListener("notifications-changed", onNotify)
    onUnmounted(() => { document.body.classList.remove("no-scroll"); window.removeEventListener("notifications-changed", onNotify) })
    onMounted(async () => {
      await load()
      try { brief.value = (await api("/manager/briefing")).text } catch { brief.value = "خلاصه امروز در دسترس نیست." }
    })
    const openDraft = async (alert) => {
      Object.assign(draft, { open: true, alert, text: "", loading: true, verified: null, missing: [] })
      try {
        const r = await api("/manager/warnings/draft", { teacher_id: alert.teacher_id })
        Object.assign(draft, { text: r.text, verified: r.verified, missing: r.missing })
      }
      catch { draft.text = "" } finally { draft.loading = false }
    }
    const issue = async () => {
      draft.saving = true
      try { await api("/manager/warnings", { teacher_id: draft.alert.teacher_id, text: draft.text }); draft.open = false; await load() }
      finally { draft.saving = false }
    }
    const decide = async (alert, approve) => {
      await api(`/manager/letters/${alert.letter_id}/decide`, { approve }); await load()
    }
    return { user: computed(() => session.user), data, brief, view, nav, draft, open, presentPct, stats, look, openDraft, issue, decide, fa }
  },
}

// ---------- refer a letter to people (staff panel) ----------
const CATEGORY_OPTIONS = [
  ["ack", "اعلام وصول"], ["stats", "درخواست آمار"], ["meeting", "دعوت به جلسه"],
  ["info", "برای اطلاع"], ["decision", "نیازمند تصمیم مدیر"], ["request", "نیازمند اقدام"],
]
const ReferDialog = {
  props: ["letter"],
  emits: ["close", "done"],
  template: `
  <div class="overlay" @click.self="$emit('close')">
    <form class="dialog wide" v-pop @submit.prevent="send">
      <div class="dialog-head">
        <div><h3>ارجاع نامه</h3><p class="muted small">{{ fa(letter.subject) }}</p></div>
        <button type="button" class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>

      <div class="suggest">
        <span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span>
        <div v-if="suggestion.loading" class="muted small flex-1">دستیار در حال پیشنهاد گیرنده<span class="dots"><i></i><i></i><i></i></span></div>
        <div v-else-if="suggestion.keys.length" class="suggest-body">
          <span class="small">پیشنهاد دستیار: <b>{{ suggestion.keys.map(label).join('، ') }}</b></span>
          <small class="muted" v-if="suggestion.reason">{{ fa(suggestion.reason) }}</small>
        </div>
        <div v-else class="muted small">دستیار پیشنهادی نداشت. گیرنده را خودتان انتخاب کنید.</div>
        <button v-if="suggestion.keys.length" type="button" class="btn sm primary" @click="applySuggestion">اعمال پیشنهاد</button>
      </div>

      <div class="picked">
        <span v-if="!picked.length" class="muted small">هنوز گیرنده‌ای انتخاب نشده.</span>
        <span v-for="k in picked" :key="k" v-pop:drop :class="['pick', kindOf(k)]">{{ label(k) }}<button type="button" @click="toggle(k)" aria-label="حذف">×</button></span>
      </div>

      <input class="search" v-model="q" placeholder="جستجوی نام، درس یا نام دانش‌آموز...">
      <div class="people">
        <template v-for="sec in sections" :key="sec.title">
          <div v-if="sec.items.length" class="people-sec">{{ sec.title }}</div>
          <button v-for="p in sec.items" :key="p.key" type="button" :class="['person', { on: picked.includes(p.key) }]" @click="toggle(p.key)">
            <span class="check-box">{{ picked.includes(p.key) ? '✓' : '' }}</span>
            <span class="person-text"><b>{{ p.label }}</b><small v-if="p.sub" class="muted">{{ p.sub }}</small></span>
          </button>
        </template>
      </div>

      <label class="field"><span>یادداشت برای گیرندگان <span class="muted">(اختیاری)</span></span>
        <textarea v-model="note" rows="2" placeholder="مثلا: لطفا تا ۳ دی دو دانش‌آموز معرفی کنید."></textarea></label>

      <div v-if="hasParents" class="parent-box">
        <div class="row-between"><b class="small text-ink">پیام برای اولیا</b>
          <button type="button" class="link small" @click="draftParent" :disabled="parent.loading">{{ parent.loading ? 'در حال نوشتن...' : 'نوشتن دوباره با دستیار' }}</button></div>
        <p class="muted small">اولیا متن اداری نامه را نمی‌بینند؛ فقط این پیام ساده را دریافت می‌کنند.</p>
        <div v-if="parent.loading && !parent.text" class="shimmer"><span></span><span></span><span style="width:60%"></span></div>
        <textarea v-else v-model="parent.text" rows="5"></textarea>
      </div>

      <label class="ack-row"><input type="checkbox" v-model="needsAck"> گیرندگان باید «رؤیت شد» را بزنند</label>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions">
        <button class="btn primary" type="submit" :disabled="!picked.length || sending || (hasParents && !parent.text.trim())">
          <Icon name="send" :size="18" />ارجاع به {{ fa(estimate) }} نفر</button>
        <button class="btn ghost" type="button" @click="$emit('close')">انصراف</button>
      </div>
    </form>
  </div>`,
  setup(props, { emit }) {
    const options = ref({ groups: [], people: [] })
    const picked = ref([]), q = ref(""), note = ref(""), needsAck = ref(true), sending = ref(false), error = ref("")
    const suggestion = reactive({ loading: true, keys: [], reason: "" })
    const parent = reactive({ loading: false, text: "" })
    const all = computed(() => [...options.value.groups, ...options.value.people])
    const find = (k) => all.value.find((p) => p.key === k)
    const label = (k) => find(k)?.label || k
    const kindOf = (k) => find(k)?.kind || "staff"
    const match = (p) => !q.value.trim() || (p.label + " " + (p.sub || "")).includes(q.value.trim())
    const sections = computed(() => [
      { title: "گروه‌ها", items: options.value.groups.filter(match) },
      { title: "کارکنان و معلمان", items: options.value.people.filter((p) => p.kind !== "parent" && match(p)) },
      { title: "اولیا", items: options.value.people.filter((p) => p.kind === "parent" && match(p)) },
    ])
    const hasParents = computed(() => picked.value.some((k) => kindOf(k) === "parent"))
    // rough head count for the button label
    const estimate = computed(() => picked.value.reduce((n, k) => n + (
      k === "group:parents" ? options.value.people.filter((p) => p.kind === "parent").length :
      k === "group:teachers" ? options.value.people.filter((p) => p.kind === "teacher").length :
      k.startsWith("group:class:") ? 15 : 1), 0))
    const toggle = (k) => { picked.value = picked.value.includes(k) ? picked.value.filter((x) => x !== k) : [...picked.value, k] }
    const applySuggestion = () => { picked.value = [...new Set([...picked.value, ...suggestion.keys])] }
    const draftParent = async () => {
      parent.loading = true
      try { parent.text = (await api(`/staff/letters/${props.letter.id}/parent-draft`, {})).text } catch {}
      finally { parent.loading = false }
    }
    // the first time a parent group is picked, the agent writes the parent message automatically
    watch(hasParents, (v) => { if (v && !parent.text) draftParent() })
    const send = async () => {
      sending.value = true; error.value = ""
      try {
        await api(`/staff/letters/${props.letter.id}/refer`,
          { recipients: picked.value, note: note.value, needs_ack: needsAck.value, parent_text: parent.text })
        emit("done")
      } catch (e) { error.value = e.message } finally { sending.value = false }
    }
    onMounted(async () => {
      options.value = await api("/staff/recipients")
      try { Object.assign(suggestion, await api(`/staff/letters/${props.letter.id}/suggest`, {})) } catch {}
      suggestion.loading = false
    })
    return { picked, q, note, needsAck, sending, error, suggestion, parent, sections, hasParents, estimate,
             label, kindOf, toggle, applySuggestion, draftParent, send, fa }
  },
}

// ---------- staff panel: smart letter inbox ----------
const TABS = [
  { key: "mine", label: "منتظر شما", icon: "inbox", match: (l) => ["new", "processing", "awaiting_approval", "todo"].includes(l.status) },
  { key: "manager", label: "ارجاع به مدیر", icon: "forward", match: (l) => ["needs_manager", "forwarded"].includes(l.status) },
  { key: "done", label: "بسته‌شده", icon: "check", match: (l) => l.status === "done" },
  { key: "log", label: "دفترچه دستیار", icon: "notebook" },
]
const StaffPanel = {
  components: { AppLayout, ChatBox, ReferDialog },
  template: `
  <AppLayout title="پنل اداری" subtitle="صندوق نامه‌های اداری" :nav="nav" v-model="view">
    <div v-show="view === 'inbox'" class="flex flex-col gap-6">
      <section v-reveal class="row-between">
        <div><h2>روز بخیر</h2><p class="muted">دستیار نامه‌ها را می‌خواند، دسته‌بندی می‌کند و پیش‌نویس پاسخ می‌نویسد. تصمیم با شماست.</p></div>
        <button class="btn primary" @click="compose.open = true" :disabled="agent.running"><Icon name="plus" :size="18" />ثبت نامه جدید</button>
      </section>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-6">
        <div v-for="s in stats" :key="s.label" v-reveal class="card stat" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 't-' + s.tone]"><Icon :name="s.icon" :size="22" /></span><div class="stat-num"><CountUp :value="s.value" /></div></div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>

      <section v-reveal class="card agent" :class="{ running: agent.running }">
        <div class="agent-row">
          <AiOrb :size="64" :busy="agent.running" />
          <div class="agent-text">
            <b v-if="agent.running">دستیار در حال بررسی نامه‌ها: {{ fa(agent.processed) }} از {{ fa(agent.total) }}</b>
            <b v-else-if="agent.error">{{ agent.error }}</b>
            <b v-else>همه نامه‌ها بررسی شد</b>
            <small class="muted" v-if="agent.running && agent.current">در حال خواندن: {{ fa(agent.current) }}</small>
            <small class="muted" v-else-if="!agent.running && !agent.error">
              {{ fa(count(l => l.status === 'done' && l.category === 'ack')) }} اعلام وصول خودکار بسته شد،
              {{ fa(count(TABS[0].match)) }} مورد منتظر شماست و {{ fa(count(TABS[1].match)) }} مورد به مدیر رفت.
            </small>
          </div>
          <button v-if="agent.error" class="btn" @click="runAgent"><Icon name="refresh" :size="18" />تلاش دوباره</button>
        </div>
        <div v-if="agent.running" class="progress"><span :style="{ width: (agent.total ? 100 * agent.processed / agent.total : 0) + '%' }"></span></div>
      </section>

      <nav v-reveal class="tabs">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">
          <Icon :name="t.icon" :size="18" />{{ t.label }}<span v-if="t.match" class="tab-count">{{ fa(count(t.match)) }}</span>
        </button>
      </nav>

      <section v-if="tab !== 'log'" class="letters">
        <div v-if="!shown.length" class="card empty-state"><span class="tint lg t-success"><Icon name="check" :size="24" /></span><p>موردی نیست.</p></div>
        <article v-for="l in shown" :key="l.id" v-reveal :class="['letter-card', 'card', 'st-' + l.status, { fresh: fresh.has(l.id) }]">
          <div class="lc-top">
            <b>{{ fa(l.subject) }}</b>
            <span v-if="l.deadline_short && l.status !== 'done'" :class="['chip', { hot: l.days_left <= 3 }]">مهلت {{ fa(l.deadline_short) }}</span>
          </div>
          <div class="lc-meta"><Icon name="mail" :size="15" />{{ l.sender }} · {{ fa(l.received_short) }}</div>
          <div class="lc-tags">
            <span v-if="l.category_name" class="tag">{{ l.category_name }}</span>
            <span :class="['tag', 'st-' + l.status]">{{ l.status_name }}</span>
          </div>
          <p v-if="l.summary" class="lc-summary">{{ fa(l.summary) }}</p>
          <p v-if="l.action && l.status !== 'done'" class="lc-action"><Icon name="sparkles" :size="16" /><span>پیشنهاد دستیار: {{ fa(l.action) }}</span></p>
          <div v-if="l.referral" class="ref-line">
            <span>ارجاع به {{ fa(l.referral.count) }} نفر</span>
            <span v-if="l.referral.needs_ack" class="sep">·</span>
            <span v-if="l.referral.needs_ack" :class="l.referral.acked === l.referral.count ? 'ok' : ''">{{ fa(l.referral.acked) }} رؤیت</span>
            <small v-if="l.referral.pending.length" class="muted">منتظر: {{ l.referral.pending.join('، ') }}<span v-if="l.referral.more"> و {{ fa(l.referral.more) }} نفر دیگر</span></small>
          </div>
          <div class="btn-row">
            <button v-if="l.status === 'awaiting_approval'" class="btn primary sm" @click="openLetter(l)">بررسی و تأیید پاسخ</button>
            <button v-if="l.status === 'todo'" class="btn success sm" @click="complete(l)"><Icon name="check" :size="16" />انجام شد</button>
            <button v-if="l.reply && l.status === 'done'" class="btn ghost sm" @click="openLetter(l)">مشاهده پاسخ</button>
            <button v-if="!l.reply" class="btn ghost sm" @click="openLetter(l)">متن نامه</button>
            <button v-if="!['new', 'processing'].includes(l.status)" class="btn sm" @click="referring = l"><Icon name="forward" :size="16" />ارجاع</button>
            <select v-if="l.category" class="cat-select" :value="l.category" @change="changeCategory(l, $event.target.value)" title="اصلاح دسته">
              <option v-for="[k, v] in CATEGORY_OPTIONS" :key="k" :value="k">دسته: {{ v }}</option>
            </select>
          </div>
        </article>
      </section>

      <section v-else v-reveal class="card">
        <div class="card-head">دفترچه دستیار <small>هر کاری که دستیار کرد، با دلیلش</small></div>
        <p v-if="!log.length" class="muted">هنوز کاری ثبت نشده.</p>
        <ol class="timeline">
          <li v-for="g in log" :key="g.id">
            <b>{{ fa(g.action) }}</b>
            <small>{{ fa(g.subject) }}</small>
            <small class="muted">{{ fa(g.reason) }}</small>
            <small class="muted">{{ fa(g.created_at) }}</small>
          </li>
        </ol>
      </section>
    </div>

    <div v-show="view === 'chat'">
      <ChatBox class="card chat-card" title="دستیار اسناد" subtitle="پاسخ فقط از روی آیین‌نامه‌ها و دستورالعمل‌های مدرسه" />
    </div>

    <div v-if="open" class="overlay" @click.self="open = null">
      <div class="dialog" v-pop>
        <h3>{{ fa(open.subject) }}</h3>
        <p class="muted small">{{ open.sender }} · {{ fa(open.received_short) }}</p>
        <div class="letter">{{ fa(open.body) }}</div>
        <template v-if="open.status === 'awaiting_approval'">
          <p class="small text-ink"><b>پیش‌نویس پاسخ دستیار</b> <span class="muted">(قبل از تأیید بخوانید و در صورت نیاز ویرایش کنید)</span></p>
          <textarea v-model="reply" rows="7"></textarea>
          <div class="dialog-actions">
            <button class="btn primary" :disabled="!reply.trim()" @click="approve"><Icon name="send" :size="18" />تأیید و ارسال پاسخ</button>
            <button class="btn ghost" @click="open = null">انصراف</button>
          </div>
        </template>
        <template v-else>
          <template v-if="open.reply"><p class="small text-ink"><b>پاسخ ثبت‌شده</b></p><div class="letter">{{ fa(open.reply) }}</div></template>
          <div class="dialog-actions"><button class="btn ghost" @click="open = null">بستن</button></div>
        </template>
      </div>
    </div>

    <ReferDialog v-if="referring" :letter="referring" @close="referring = null" @done="referring = null; load()" />

    <div v-if="compose.open" class="overlay" @click.self="compose.open = false">
      <form class="dialog" v-pop @submit.prevent="addLetter">
        <h3>ثبت نامه جدید</h3>
        <p class="muted small">متن نامه را کپی کنید. دستیار عنوان، دسته، مهلت و کار لازم را خودش پیدا می‌کند.</p>
        <label class="field"><span>فرستنده <span class="muted">(اختیاری)</span></span><input v-model="compose.sender" placeholder="مثلا اداره آموزش و پرورش منطقه"></label>
        <label class="field"><span>موضوع <span class="muted">(اختیاری)</span></span><input v-model="compose.subject" placeholder="اگر خالی بماند، دستیار می‌نویسد"></label>
        <label class="field">متن نامه<textarea v-model="compose.body" rows="8" placeholder="متن کامل نامه را اینجا بچسبانید..."></textarea></label>
        <p v-if="compose.error" class="error-text">{{ compose.error }}</p>
        <div class="dialog-actions">
          <button class="btn primary" type="submit" :disabled="compose.body.trim().length < 15 || compose.saving"><Icon name="sparkles" :size="18" />ثبت و بررسی با دستیار</button>
          <button class="btn ghost" type="button" @click="compose.open = false">انصراف</button>
        </div>
      </form>
    </div>
  </AppLayout>`,
  setup() {
    const letters = ref([]), log = ref([]), tab = ref("mine"), open = ref(null), reply = ref(""), view = ref("inbox")
    const compose = reactive({ open: false, sender: "", subject: "", body: "", saving: false, error: "" })
    const referring = ref(null)
    const changeCategory = async (l, category) => { await api(`/staff/letters/${l.id}/category`, { category }); await load() }
    const fresh = ref(new Set())
    const agent = reactive({ running: false, processed: 0, total: 0, current: "", error: "" })
    const count = (fn) => letters.value.filter(fn).length
    const shown = computed(() => {
      const t = TABS.find((x) => x.key === tab.value)
      return t.match ? letters.value.filter(t.match) : []
    })
    const nav = computed(() => [
      { header: "نامه‌ها" },
      { key: "inbox", label: "صندوق نامه", icon: "inbox", badge: count(TABS[0].match) },
      { header: "دستیار" },
      { key: "chat", label: "پرسش از اسناد", icon: "message" },
    ])
    const stats = computed(() => [
      { label: "منتظر شما", value: count(TABS[0].match), icon: "inbox", tone: "warning" },
      { label: "ارجاع به مدیر", value: count(TABS[1].match), icon: "forward", tone: "info" },
      { label: "بسته‌شده", value: count(TABS[2].match), icon: "check", tone: "success" },
      { label: "اعلام وصول خودکار", value: count((l) => l.status === "done" && l.category === "ack"), icon: "sparkles", tone: "primary" },
    ])
    const load = async () => {
      letters.value = await api("/staff/letters")
      log.value = await api("/staff/log")
    }
    // The agent runs by itself: it takes the queued letters one at a time until none are left
    const runAgent = async () => {
      agent.error = ""
      const queue = letters.value.filter((l) => l.status === "new")
      if (!queue.length) return
      Object.assign(agent, { running: true, processed: 0, total: queue.length })
      try {
        while (true) {
          agent.current = letters.value.find((l) => l.status === "new")?.subject || ""
          const r = await api("/staff/agent/next", {})
          if (r.done) break
          const i = letters.value.findIndex((l) => l.id === r.letter.id)
          letters.value[i] = r.letter
          fresh.value = new Set([...fresh.value, r.letter.id])
          agent.processed++
          log.value = await api("/staff/log")
        }
      } catch (e) {
        if (e.message !== "401") agent.error = "دستیار در دسترس نیست. مدل محلی روشن است؟"
      } finally { agent.running = false; agent.current = "" }
    }
    const openLetter = (l) => { open.value = l; reply.value = l.reply || "" }
    const approve = async () => { await api(`/staff/letters/${open.value.id}/approve`, { reply: reply.value }); open.value = null; await load() }
    const complete = async (l) => { await api(`/staff/letters/${l.id}/complete`, {}); await load() }
    // A new letter goes into the queue; the agent then picks it up exactly like the others
    const addLetter = async () => {
      compose.saving = true; compose.error = ""
      try {
        await api("/staff/letters", { sender: compose.sender, subject: compose.subject, body: compose.body })
        Object.assign(compose, { open: false, sender: "", subject: "", body: "" })
        await load()
        runAgent()
      } catch (e) { compose.error = e.message } finally { compose.saving = false }
    }
    watch(() => !!open.value || compose.open || !!referring.value, (v) => document.body.classList.toggle("no-scroll", v))
    onMounted(async () => { await load(); runAgent() })
    onUnmounted(() => document.body.classList.remove("no-scroll"))
    return { TABS, CATEGORY_OPTIONS, letters, log, tab, open, reply, view, nav, stats, compose, referring, fresh, agent, count, shown,
             runAgent, load, openLetter, approve, complete, addLetter, changeCategory, fa }
  },
}

// ---------- shared pieces for student data ----------
const LEVEL_NAMES = { 4: "خیلی خوب", 3: "خوب", 2: "قابل قبول", 1: "نیاز به تلاش بیشتر" }
const Sparkline = {
  props: ["points", "change"],
  template: `
  <svg viewBox="0 0 120 36" class="spark-svg" :class="tone" role="img" :aria-label="'روند: ' + points.map(p => LEVEL_NAMES[p]).join('، ')">
    <line v-for="l in [1,2,3,4]" :key="l" x1="4" x2="116" :y1="y(l)" :y2="y(l)" class="grid" />
    <polygon :points="area" class="area" />
    <polyline ref="lineEl" :points="linePts" class="line" />
    <circle v-for="(p, i) in points" :key="i" :cx="x(i)" :cy="y(p)" :r="i === points.length - 1 ? 3.6 : 2.4" class="dot" />
  </svg>`,
  setup(props) {
    // right to left: the oldest point on the right, today on the left
    const x = (i) => 116 - i * (112 / Math.max(props.points.length - 1, 1))
    const y = (l) => 32 - (l - 1) * 9.3
    const tone = computed(() => props.change <= -1 ? "down" : props.change >= 1 ? "up" : "flat")
    const linePts = computed(() => props.points.map((p, i) => x(i) + "," + y(p)).join(" "))
    const area = computed(() => `${linePts.value} ${x(props.points.length - 1)},35 ${x(0)},35`)
    // the line draws itself from right to left
    const lineEl = ref(null)
    onMounted(() => {
      if (!motion || !lineEl.value) return
      const len = lineEl.value.getTotalLength()
      if (len) gsap.fromTo(lineEl.value, { strokeDasharray: len, strokeDashoffset: len },
        { strokeDashoffset: 0, duration: 1.3, ease: "power2.out", delay: .3, clearProps: "strokeDasharray,strokeDashoffset" })
    })
    return { x, y, tone, linePts, area, lineEl, LEVEL_NAMES }
  },
}
const LevelChip = {
  props: ["level"],
  template: `<span :class="['level', 'l' + level]">{{ LEVEL_NAMES[level] }}</span>`,
  setup() { return { LEVEL_NAMES } },
}
// health flags are grouped into one chip so the list stays calm
const groupSignals = (signals) => {
  const health = signals.filter((s) => s.type === "health")
  const rest = signals.filter((s) => s.type !== "health")
  return health.length ? [...rest, { type: "health", text: `فرم سلامت: ${fa(health.length)} مورد` }] : rest
}

// ---------- counselor: one student's file, opened in a side drawer ----------
const StudentProfile = {
  components: { Sparkline, LevelChip },
  props: ["sid"],
  emits: ["close", "changed"],
  template: `
  <div class="overlay" @click.self="$emit('close')">
    <aside class="drawer wide-drawer" v-drawer>
      <div class="drawer-head">
        <div class="head-person" v-if="f"><Avatar :name="f.name" :size="46" /><div><b>{{ f.name }}</b><small class="muted">کلاس {{ f.class }} · آموزگار: {{ f.teacher }}</small></div></div>
        <span v-else></span>
        <button class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div v-if="!f" class="drawer-body"><div class="card"><div class="shimmer"><span></span><span></span><span style="width:60%"></span></div></div></div>
      <div v-else class="drawer-body">

        <section v-reveal class="card brief">
          <div class="card-head"><span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span> جمع‌بندی دستیار</div>
          <p v-if="insight"><TypeText :text="insight" /></p>
          <div v-else class="shimmer"><span></span><span style="width:70%"></span></div>
          <div v-if="f.signals.length" class="chips">
            <span v-for="s in f.signals" :key="s.text" :class="['sig', s.type]">{{ fa(s.text) }}</span>
          </div>
        </section>

        <section v-reveal class="card">
          <div class="card-head">پیام به ولی</div>
          <template v-if="draft">
            <p class="muted small">این متن را دستیار نوشته است. بخوانید، در صورت نیاز ویرایش کنید و بعد بفرستید.</p>
            <label class="field mt-3"><span>گام بعدی برای شما</span><textarea v-model="draft.for_counselor" rows="2"></textarea></label>
            <label class="field mt-3"><span>پیام برای ولی</span><textarea v-model="draft.for_parent" rows="5"></textarea></label>
            <div class="dialog-actions mt-3">
              <button class="btn primary" :disabled="!draft.for_parent.trim()" @click="approve"><Icon name="send" :size="18" />تأیید و ارسال به ولی</button>
              <button class="btn ghost" @click="dismiss">کنار گذاشتن</button>
            </div>
          </template>
          <template v-else>
            <p class="muted small mb-3" v-if="!sent.length">هنوز پیامی برای ولیِ {{ f.first_name }} فرستاده نشده.</p>
            <div v-for="s in sent" :key="s.id" class="sent-msg">
              <small class="ok">✓ ارسال شد · {{ fa(s.approved_at) }}</small>
              <p>{{ fa(s.for_parent) }}</p>
              <small v-if="s.for_counselor" class="muted">گام شما: {{ fa(s.for_counselor) }}</small>
            </div>
            <button class="btn" :disabled="drafting" @click="suggest"><Icon name="sparkles" :size="18" />{{ drafting ? 'دستیار در حال نوشتن...' : 'نوشتن پیام با دستیار' }}</button>
            <p v-if="error" class="error-text mt-2">{{ error }}</p>
          </template>
        </section>

        <section v-reveal class="card">
          <div class="card-head">پیشرفت درسی <small>از مهر تا امروز</small></div>
          <div class="progress-list">
            <div v-for="p in f.progress" :key="p.subject" class="prog-row">
              <span class="prog-sub">{{ p.subject }}</span>
              <Sparkline :points="p.points" :change="p.change" />
              <LevelChip :level="p.now" />
            </div>
          </div>
          <p v-for="p in f.progress.filter(p => p.note)" :key="'n' + p.subject" class="teacher-note">یادداشت آموزگار ({{ p.subject }}): {{ p.note }}</p>
        </section>

        <section v-reveal class="card">
          <div class="card-head">حضور <small>۳۰ روز اخیر</small></div>
          <div class="mini-stats">
            <div class="ok-tile"><b><CountUp :value="f.attendance.present" /></b><small>روز حاضر</small></div>
            <div :class="{ warn: f.attendance.unexcused >= 3 }"><b><CountUp :value="f.attendance.absent" /></b><small>غیبت ({{ fa(f.attendance.unexcused) }} غیرموجه)</small></div>
            <div><b><CountUp :value="f.attendance.late" /></b><small>تأخیر</small></div>
          </div>
          <div v-if="f.attendance.absent_days.length" class="chips">
            <span v-for="d in f.attendance.absent_days" :key="d.date" :class="['day', { ok: d.excused }]">{{ fa(d.date) }}{{ d.excused ? ' · موجه' : '' }}</span>
          </div>
        </section>

        <section v-reveal class="card">
          <div class="card-head">فرم‌های سلامت <small>تکمیل‌شده توسط ولی</small></div>
          <div class="forms-grid">
            <div v-for="k in ['physical', 'wellbeing']" :key="k" class="form-tile">
              <b>{{ k === 'physical' ? 'سلامت جسمی' : 'حال و احوال' }}</b>
              <template v-if="f.forms[k]">
                <small class="muted">{{ fa(f.forms[k].date) }}</small>
                <div class="chips"><span v-for="fl in f.forms[k].flags" :key="fl" class="sig health">{{ fa(fl) }}</span>
                  <span v-if="!f.forms[k].flags.length" class="sig ok">مورد قابل توجهی ندارد</span></div>
                <details><summary class="small">پاسخ‌ها</summary>
                  <dl class="answers"><template v-for="[key, label] in f.fields[k]" :key="key"><dt>{{ label }}</dt><dd>{{ fa(f.forms[k].data[key] ?? '-') }}</dd></template></dl>
                </details>
              </template>
              <small v-else class="muted">هنوز تکمیل نشده</small>
            </div>
          </div>
        </section>

        <section v-reveal class="card">
          <div class="card-head">یادداشت‌های مشاور <small>فقط برای شما، ولی این‌ها را نمی‌بیند</small></div>
          <form class="note-add" @submit.prevent="addNote">
            <textarea v-model="newNote" rows="2" placeholder="یادداشت جدید..."></textarea>
            <button class="btn" :disabled="!newNote.trim()">ثبت</button>
          </form>
          <ul class="notes"><li v-for="(n, i) in f.notes" :key="i"><small class="muted">{{ fa(n.date) }}</small><p>{{ fa(n.note) }}</p></li></ul>
        </section>
      </div>
    </aside>
  </div>`,
  setup(props, { emit }) {
    const f = ref(null), insight = ref(""), draft = ref(null), drafting = ref(false), newNote = ref(""), error = ref("")
    const sent = computed(() => (f.value?.suggestions || []).filter((s) => s.status === "approved"))
    const load = async () => {
      f.value = await api(`/counselor/students/${props.sid}`)
      draft.value = f.value.suggestions.find((s) => s.status === "draft") || null
    }
    const suggest = async () => {
      drafting.value = true; error.value = ""
      try { draft.value = await api(`/counselor/students/${props.sid}/suggest`, {}) }
      catch (e) { error.value = e.message } finally { drafting.value = false }
    }
    const approve = async () => {
      await api(`/counselor/suggestions/${draft.value.id}/approve`, { for_counselor: draft.value.for_counselor, for_parent: draft.value.for_parent })
      await load(); emit("changed")
    }
    const dismiss = async () => { await api(`/counselor/suggestions/${draft.value.id}/dismiss`, {}); draft.value = null }
    const addNote = async () => { await api(`/counselor/students/${props.sid}/notes`, { note: newNote.value }); newNote.value = ""; await load() }
    onMounted(async () => {
      await load()
      try { insight.value = (await api(`/counselor/students/${props.sid}/insight`)).text } catch { insight.value = "جمع‌بندی در دسترس نیست." }
    })
    return { f, insight, draft, drafting, newNote, error, sent, suggest, approve, dismiss, addNote, fa }
  },
}

// ---------- counselor panel ----------
const CounselorPanel = {
  components: { AppLayout, ChatBox, StudentProfile },
  template: `
  <AppLayout title="پنل مشاور" subtitle="دانش‌آموزانی که این روزها به توجه شما نیاز دارند" :nav="nav" v-model="page">
    <div v-show="page === 'students'" class="flex flex-col gap-6">
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-6">
        <div v-for="s in stats" :key="s.label" v-reveal class="card stat" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 't-' + s.tone]"><Icon :name="s.icon" :size="22" /></span><div class="stat-num"><CountUp :value="s.value" /></div></div>
          <div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ s.sub }}</div></div>
        </div>
      </div>

      <section v-reveal class="card p-0 overflow-hidden">
        <div class="toolbar">
          <div class="segmented">
            <button :class="{ on: view === 'flagged' }" @click="view = 'flagged'">نیاز به توجه <span>{{ fa(flagged.length) }}</span></button>
            <button :class="{ on: view === 'all' }" @click="view = 'all'">همه <span>{{ fa(list.length) }}</span></button>
          </div>
          <input v-if="view === 'all'" class="search small-search" v-model="q" placeholder="جستجوی نام یا کلاس...">
        </div>

        <div v-if="!loaded" class="p-6"><div class="shimmer"><span></span><span></span><span></span></div></div>
        <div v-else-if="!shown.length" class="empty-state"><span class="tint lg t-success"><Icon name="check" :size="24" /></span><p>موردی نیست.</p></div>
        <div v-else class="student-list">
          <button v-for="s in shown" :key="s.id" v-reveal class="student-row" @click="openId = s.id">
            <Avatar :name="s.name" />
            <span class="sr-main">
              <b>{{ s.name }}</b>
              <small class="muted">کلاس {{ s.class }}</small>
            </span>
            <span class="chips">
              <span v-for="g in groupSignals(s.signals)" :key="g.text" :class="['sig', g.type]">{{ fa(g.text) }}</span>
              <span v-if="s.has_suggestion" class="sig ok">پیام فرستاده شد</span>
            </span>
            <Icon name="chevron" :size="18" class="chev" />
          </button>
        </div>
      </section>
    </div>

    <div v-show="page === 'chat'">
      <ChatBox class="card chat-card" title="دستیار اسناد" subtitle="پاسخ فقط از روی آیین‌نامه‌ها و دستورالعمل‌های مدرسه" />
    </div>

    <StudentProfile v-if="openId" :sid="openId" @close="openId = null" @changed="load" />
  </AppLayout>`,
  setup() {
    const list = ref([]), loaded = ref(false), view = ref("flagged"), q = ref(""), openId = ref(null), page = ref("students")
    const flagged = computed(() => list.value.filter((s) => s.signals.length))
    const shown = computed(() => view.value === "flagged" ? flagged.value
      : list.value.filter((s) => !q.value.trim() || (s.name + s.class).includes(q.value.trim())))
    const withSignal = (type) => list.value.filter((s) => s.signals.some((g) => g.type === type)).length
    const nav = computed(() => [
      { header: "دانش‌آموزان" },
      { key: "students", label: "دانش‌آموزان", icon: "users", badge: flagged.value.length },
      { header: "دستیار" },
      { key: "chat", label: "پرسش از اسناد", icon: "message" },
    ])
    const stats = computed(() => [
      { label: "نیاز به توجه", value: flagged.value.length, sub: `از ${fa(list.value.length)} دانش‌آموز`, icon: "alert", tone: "warning" },
      { label: "افت درسی", value: withSignal("grade"), sub: "روند نزولی در یک درس", icon: "trendDown", tone: "danger" },
      { label: "غیبت", value: withSignal("absence"), sub: "غیبت قابل توجه", icon: "calendar", tone: "info" },
      { label: "فرم سلامت", value: withSignal("health"), sub: "نکته در فرم ولی", icon: "heart", tone: "success" },
    ])
    const load = async () => { list.value = await api("/counselor/students"); loaded.value = true }
    watch(() => !!openId.value, (v) => document.body.classList.toggle("no-scroll", v))
    onMounted(load)
    onUnmounted(() => document.body.classList.remove("no-scroll"))
    return { list, loaded, view, q, openId, page, nav, stats, flagged, shown, load, groupSignals, fa }
  },
}

// ---------- parent: health and wellbeing form ----------
const SCALE_ENDS = { mood: ["خیلی کم", "خیلی خوب"], sleep_quality: ["بد", "عالی"], school_worry: ["اصلا", "خیلی زیاد"], friends: ["سخت", "خیلی خوب"] }
const HealthFormDialog = {
  props: ["kind"],
  emits: ["close", "saved"],
  template: `
  <div class="overlay" @click.self="$emit('close')">
    <form class="dialog" v-pop @submit.prevent="save">
      <div class="dialog-head">
        <div><h3>{{ kind === 'physical' ? 'فرم سلامت جسمی' : 'فرم حال و احوال' }}</h3>
          <p class="muted small">{{ date ? 'آخرین ثبت: ' + fa(date) + '. پاسخ‌های قبلی را ببینید و اگر چیزی تغییر کرده اصلاح کنید.' : 'چند سؤال کوتاه. پاسخ‌ها فقط برای مشاور مدرسه است.' }}</p></div>
        <button type="button" class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div v-if="!fields.length" class="shimmer"><span></span><span></span></div>
      <div v-for="[key, label, type] in fields" :key="key" class="q">
        <span class="q-label">{{ label }}</span>
        <input v-if="type === 'number'" type="number" inputmode="decimal" v-model="data[key]" class="q-input" min="0">
        <input v-else-if="type === 'text'" v-model="data[key]" class="q-input" placeholder="اگر چیزی هست بنویسید">
        <div v-else-if="type === 'scale'" class="scale">
          <small class="muted">{{ SCALE_ENDS[key]?.[0] }}</small>
          <button v-for="n in 5" :key="n" type="button" :class="['dot-btn', { on: Number(data[key]) === n }]" @click="data[key] = n" :aria-label="fa(n)">{{ fa(n) }}</button>
          <small class="muted">{{ SCALE_ENDS[key]?.[1] }}</small>
        </div>
        <div v-else class="options">
          <button v-for="o in type" :key="o" type="button" :class="{ on: data[key] === o }" @click="data[key] = o">{{ o }}</button>
        </div>
      </div>
      <div class="dialog-actions">
        <button class="btn primary" :disabled="saving">{{ saving ? 'در حال ثبت...' : 'ثبت فرم' }}</button>
        <button type="button" class="btn ghost" @click="$emit('close')">انصراف</button>
      </div>
    </form>
  </div>`,
  setup(props, { emit }) {
    const fields = ref([]), data = reactive({}), date = ref(null), saving = ref(false)
    onMounted(async () => {
      const r = await api(`/parent/forms/${props.kind}`)
      fields.value = r.fields; Object.assign(data, r.data); date.value = r.date
    })
    const save = async () => {
      saving.value = true
      try { await api(`/parent/forms/${props.kind}`, { data: { ...data } }); emit("saved") } finally { saving.value = false }
    }
    return { fields, data, date, saving, save, SCALE_ENDS, fa }
  },
}

// ---------- parent panel ----------
const ParentPanel = {
  components: { AppLayout, ChatBox, Sparkline, LevelChip, HealthFormDialog },
  template: `
  <AppLayout title="پنل ولی" :subtitle="f ? 'گزارش ' + f.name : ''" :nav="nav" v-model="view">
    <div v-show="view === 'child'">
      <div v-if="!f" class="card"><div class="shimmer"><span></span><span></span><span></span></div></div>
      <div v-else class="flex flex-col gap-6">
        <section v-reveal class="card profile">
          <div class="profile-cover" ref="cover">
            <i style="width:180px;height:180px;left:-40px;top:-60px"></i><i style="width:110px;height:110px;left:30%;top:50px"></i><i style="width:70px;height:70px;right:12%;top:20px"></i>
          </div>
          <div class="profile-body">
            <Avatar :name="f.name" :size="96" tone="primary" />
            <div class="profile-meta">
              <h2>{{ f.name }}</h2>
              <div class="meta-row">
                <span><Icon name="school" :size="17" />کلاس {{ f.class }}</span>
                <span><Icon name="user" :size="17" />آموزگار: {{ f.teacher }}</span>
              </div>
            </div>
            <button class="btn primary" @click="view = 'chat'"><Icon name="message" :size="18" />پرسش درباره {{ f.first_name }}</button>
          </div>
        </section>

        <div class="grid grid-cols-12 gap-6">
          <div class="col-span-12 xl:col-span-8 flex flex-col gap-6">
            <section v-reveal class="card welcome brief">
              <div class="welcome-text">
                <div class="card-head mb-0"><span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span> گزارش این هفته</div>
                <p v-if="report"><TypeText :text="report" /></p>
                <div v-else class="shimmer"><span></span><span></span><span style="width:55%"></span></div>
              </div>
              <div class="welcome-art"><AiOrb :size="110" :busy="!report" /></div>
            </section>

            <section v-for="(s, i) in f.suggestions" :key="'s' + i" v-reveal class="card counsel">
              <div class="card-head"><span class="tint sm t-success"><Icon name="message" :size="18" /></span>پیام مشاور مدرسه <small>{{ fa(s.approved_at) }}</small></div>
              <p>{{ fa(s.for_parent) }}</p>
            </section>

            <section v-reveal class="card">
              <div class="card-head">پیشرفت درسی <small>از مهر تا امروز</small></div>
              <div class="progress-list">
                <div v-for="p in f.progress" :key="p.subject" class="prog-row">
                  <span class="prog-sub">{{ p.subject }}</span>
                  <Sparkline :points="p.points" :change="p.change" />
                  <LevelChip :level="p.now" />
                </div>
              </div>
              <div class="legend"><span v-for="l in [4,3,2,1]" :key="l"><LevelChip :level="l" /></span></div>
            </section>
          </div>

          <div class="col-span-12 xl:col-span-4 flex flex-col gap-6">
            <section v-reveal class="card">
              <div class="card-head">حضور <small>۳۰ روز اخیر</small></div>
              <div class="mini-stats">
                <div class="ok-tile"><b><CountUp :value="f.attendance.present" /></b><small>روز حاضر</small></div>
                <div><b><CountUp :value="f.attendance.absent" /></b><small>غیبت</small></div>
                <div><b><CountUp :value="f.attendance.late" /></b><small>تأخیر</small></div>
              </div>
              <div v-if="f.attendance.absent_days.length" class="chips">
                <span v-for="d in f.attendance.absent_days" :key="d.date" :class="['day', { ok: d.excused }]">{{ fa(d.date) }}{{ d.excused ? ' · موجه' : '' }}</span>
              </div>
            </section>

            <section v-reveal class="card">
              <div class="card-head">فرم‌های سلامت</div>
              <div class="forms-grid">
                <button v-for="k in ['physical', 'wellbeing']" :key="k" class="form-tile action" @click="formKind = k">
                  <span :class="['tint', 'sm', k === 'physical' ? 't-danger' : 't-info']"><Icon :name="k === 'physical' ? 'heart' : 'message'" :size="18" /></span>
                  <b>{{ k === 'physical' ? 'سلامت جسمی' : 'حال و احوال' }}</b>
                  <small class="muted">{{ f.forms[k] ? 'آخرین ثبت: ' + fa(f.forms[k].date) : 'هنوز تکمیل نشده' }}</small>
                  <span class="tile-cta">{{ f.forms[k] ? 'به‌روزرسانی' : 'تکمیل فرم' }}<Icon name="chevron" :size="14" /></span>
                </button>
              </div>
            </section>

            <section v-if="f.messages.length" v-reveal class="card">
              <div class="card-head">پیام‌های مدرسه</div>
              <ul class="notes"><li v-for="m in f.messages" :key="m.id"><small class="muted">{{ fa(m.created_at) }}</small><b class="small">{{ fa(m.title) }}</b><p>{{ fa(m.body) }}</p></li></ul>
            </section>
          </div>
        </div>
      </div>
    </div>

    <div v-show="view === 'chat'">
      <ChatBox class="card chat-card" title="پرسش از مدرسه" subtitle="درباره درس و حضور فرزندتان یا مقررات مدرسه"
        endpoint="/parent/ask" loading-text="در حال بررسی" :examples="askExamples"
        :intro="'درباره درس‌ها، غیبت و تأخیر ' + (f ? f.first_name : 'فرزندتون') + ' یا مقررات مدرسه بپرسید:'" />
    </div>

    <HealthFormDialog v-if="formKind" :kind="formKind" @close="formKind = null" @saved="formKind = null; load()" />
  </AppLayout>`,
  setup() {
    const f = ref(null), report = ref(""), formKind = ref(null), view = ref("child")
    const load = async () => { f.value = await api("/parent/child") }
    const nav = computed(() => [
      { header: "فرزند من" },
      { key: "child", label: f.value ? "گزارش " + f.value.first_name : "گزارش فرزند", icon: "user" },
      { header: "دستیار" },
      { key: "chat", label: "پرسش از مدرسه", icon: "message" },
    ])
    watch(() => !!formKind.value, (v) => document.body.classList.toggle("no-scroll", v))
    const onNotify = () => load()
    onMounted(async () => {
      window.addEventListener("notifications-changed", onNotify)
      await load()
      try { report.value = (await api("/parent/report")).text } catch { report.value = "گزارش این هفته در دسترس نیست." }
    })
    onUnmounted(() => { document.body.classList.remove("no-scroll"); window.removeEventListener("notifications-changed", onNotify) })
    const askExamples = computed(() => {
      const n = f.value?.first_name || "بچه‌م"
      return [`${n} توی چه درسی ضعیف‌تره؟`, "توی سه هفته اخیر چند روز غیبت داشته؟", "وضعیت ریاضیش چطوره؟", "ساعت شروع کلاس‌ها چنده؟"]
    })
    return { f, report, formKind, view, nav, load, askExamples, fa }
  },
}

// ---------- root: decides which screen to show ----------
const app = createApp({
  components: { LoginPage, ManagerPanel, StaffPanel, CounselorPanel, ParentPanel, ChatPage },
  template: `
    <LoginPage v-if="!user" />
    <ManagerPanel v-else-if="user.role === 'manager'" />
    <StaffPanel v-else-if="user.role === 'staff'" />
    <CounselorPanel v-else-if="user.role === 'counselor'" />
    <ParentPanel v-else-if="user.role === 'parent'" />
    <ChatPage v-else />`,
  setup() {
    onMounted(async () => {
      if (!session.token) return
      try { session.user = await api("/me") } catch { clearSession() }
    })
    watch(() => session.user, () => document.body.classList.remove("no-scroll"))
    return { user: computed(() => session.user) }
  },
})
// small building blocks every screen uses, registered once for the whole app
app.component("Icon", Icon)
app.component("Avatar", Avatar)
app.component("CountUp", CountUp)
app.component("TypeText", TypeText)
app.component("AiOrb", AiOrb)
app.directive("reveal", vReveal)
app.directive("pop", vPop)
app.directive("drawer", vDrawer)
app.mount("#app")
