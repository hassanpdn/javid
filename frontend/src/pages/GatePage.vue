<script setup>
// The site's door on the live demo: one username and password before anything else.
// Dark on purpose in both themes, so it looks the same for everyone. No school name here: the school is chosen after.
import { ref, onMounted } from "vue"
import { enterGate } from "../lib/gate.js"
import AiOrb from "../components/AiOrb.vue"
import Icon from "../components/Icon.vue"

const emit = defineEmits(["entered"])
const username = ref(""), password = ref(""), show = ref(false)
const error = ref(""), sending = ref(false), shake = ref(false)
const userEl = ref(null)
// what the assistant does, floating around the card on wide screens
const CHIPS = [
  { text: "خلاصه‌ی هر روز برای مدیر", icon: "dashboard", tone: "a" },
  { text: "نامه‌ها را می‌خواند و جواب می‌نویسد", icon: "mail", tone: "b" },
  { text: "دانش‌آموزی که کمک لازم دارد را نشان می‌دهد", icon: "heart", tone: "c" },
  { text: "گزارش هفتگی برای پدر و مادر", icon: "message", tone: "d" },
  { text: "جواب سؤال‌ها از آیین‌نامه‌ها", icon: "book", tone: "e" },
]
onMounted(() => { if (window.matchMedia("(min-width: 768px)").matches) userEl.value?.focus() })

const submit = async () => {
  if (sending.value) return
  if (!username.value.trim() || !password.value) { fail("نام کاربری و رمز عبور را وارد کنید"); return }
  sending.value = true; error.value = ""
  const msg = await enterGate(username.value, password.value)
  sending.value = false
  if (msg) { fail(msg); password.value = ""; return }
  emit("entered")
}
const fail = (msg) => {
  error.value = msg
  shake.value = false
  requestAnimationFrame(() => { shake.value = true })
}
</script>

<template>
  <main class="gate">
    <div class="g-sky" aria-hidden="true">
      <span class="g-blob b1"></span><span class="g-blob b2"></span><span class="g-blob b3"></span><span class="g-blob b4"></span>
      <span class="g-grid"></span>
      <span v-for="n in 18" :key="n" class="g-star" :style="{ '--x': (n * 53) % 100 + '%', '--y': (n * 37) % 100 + '%', '--d': (n % 6) + 's' }"></span>
    </div>

    <ul class="g-chips" aria-hidden="true">
      <li v-for="(c, i) in CHIPS" :key="c.text" :class="['g-chip', 'c' + i, 't-' + c.tone]"><Icon :name="c.icon" :size="16" />{{ c.text }}</li>
    </ul>

    <section :class="['g-card', { shake }]" @animationend="shake = false">
      <div class="g-orb"><AiOrb :size="104" :busy="sending" /></div>
      <h1>دستیار هوشمند مدرسه</h1>
      <p class="g-sub">نسخه‌ی نمایشی. برای دیدن آن وارد شوید.</p>

      <form class="g-form" @submit.prevent="submit" novalidate>
        <label class="g-field">
          <span class="g-label">نام کاربری</span>
          <span class="g-input">
            <Icon name="user" :size="19" />
            <input ref="userEl" v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" dir="ltr" required />
          </span>
        </label>
        <label class="g-field">
          <span class="g-label">رمز عبور</span>
          <span class="g-input">
            <Icon name="lock" :size="19" />
            <input v-model="password" name="password" :type="show ? 'text' : 'password'" autocomplete="current-password" dir="ltr" required />
            <button type="button" class="g-eye" :aria-label="show ? 'پنهان کردن رمز' : 'نشان دادن رمز'" :aria-pressed="show" @click="show = !show">
              <Icon :name="show ? 'eyeOff' : 'eye'" :size="19" />
            </button>
          </span>
        </label>
        <p class="g-error" role="alert">{{ error }}</p>
        <button class="g-btn" :disabled="sending">
          <span v-if="sending" class="g-spin" aria-hidden="true"></span>
          <span>{{ sending ? "در حال ورود" : "ورود" }}</span>
          <Icon v-if="!sending" name="arrowLeft" :size="18" />
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.gate {
  --g1: #7367f0; --g2: #00bad1; --g3: #ff6fa8; --g4: #ffb057;
  position: relative; min-height: 100vh; min-height: 100dvh; overflow: hidden; isolation: isolate;
  display: grid; grid-template-columns: minmax(0, 1fr); place-items: center; padding: max(24px, env(safe-area-inset-top)) 16px max(24px, env(safe-area-inset-bottom));
  background: radial-gradient(120% 80% at 50% 0%, #1d1b4b 0%, #0d0c24 55%, #07061a 100%); color: #eceaff;
}

/* moving colour clouds behind everything */
.g-sky { position: absolute; inset: 0; z-index: -1; pointer-events: none; }
.g-blob { position: absolute; width: 46vmax; height: 46vmax; border-radius: 50%; filter: blur(70px); opacity: .5; mix-blend-mode: screen; }
.b1 { background: var(--g1); top: -14vmax; right: -10vmax; animation: g-float1 18s ease-in-out infinite alternate; }
.b2 { background: var(--g2); bottom: -18vmax; left: -12vmax; opacity: .38; animation: g-float2 22s ease-in-out infinite alternate; }
.b3 { background: var(--g3); top: 30%; left: 55%; width: 30vmax; height: 30vmax; opacity: .26; animation: g-float3 26s ease-in-out infinite alternate; }
.b4 { background: var(--g4); bottom: 8%; right: 30%; width: 20vmax; height: 20vmax; opacity: .18; animation: g-float1 30s ease-in-out infinite alternate-reverse; }
.g-grid { position: absolute; inset: 0; opacity: .5;
  background-image: linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px);
  background-size: 48px 48px; mask-image: radial-gradient(70% 60% at 50% 45%, #000 20%, transparent 75%); }
.g-star { position: absolute; left: var(--x); top: var(--y); width: 3px; height: 3px; border-radius: 50%; background: #fff;
  box-shadow: 0 0 8px 2px rgba(255,255,255,.5); opacity: 0; animation: g-twinkle 6s ease-in-out var(--d) infinite; }

/* the glass card */
.g-card { position: relative; width: min(100%, 410px); padding: 36px 30px 30px; border-radius: 28px; text-align: center;
  background: linear-gradient(160deg, rgba(255,255,255,.13), rgba(255,255,255,.04));
  border: 1px solid rgba(255,255,255,.16); backdrop-filter: blur(22px) saturate(140%); -webkit-backdrop-filter: blur(22px) saturate(140%);
  box-shadow: 0 30px 80px -20px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.2);
  animation: g-in .9s cubic-bezier(.2,.9,.25,1.1) both; }
.g-card::before { content: ""; position: absolute; inset: -1px; border-radius: inherit; padding: 1px; pointer-events: none;
  background: conic-gradient(from var(--a, 0deg), transparent 0 60%, var(--g2), var(--g1), var(--g3), transparent 95%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude;
  animation: g-ring 6s linear infinite; }
.g-card.shake { animation: g-shake .45s cubic-bezier(.36,.07,.19,.97); }
.g-orb { display: grid; place-items: center; margin: -4px auto 8px; filter: drop-shadow(0 10px 30px rgba(115,103,240,.55)); }
.g-orb :deep(.orb) { --primary: #8f85ff; --info: #2fd6ea; }
h1 { margin: 0; font-size: 26px; font-weight: 700; line-height: 1.5;
  background: linear-gradient(90deg, #fff, #c9c3ff 45%, #8fefff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.g-sub { margin: 4px 0 24px; color: #b7b3d9; font-size: 14px; }

.g-form { display: flex; flex-direction: column; gap: 14px; text-align: right; }
.g-field { display: flex; flex-direction: column; gap: 6px; }
.g-label { font-size: 13px; font-weight: 700; color: #d6d3f5; }
.g-input { display: flex; align-items: center; gap: 10px; padding: 0 14px; height: 52px; border-radius: 14px;
  background: rgba(10,9,32,.55); border: 1px solid rgba(255,255,255,.14); color: #9a96c4; transition: border-color .2s, box-shadow .2s, background .2s; }
.g-input:focus-within { border-color: #8f85ff; background: rgba(10,9,32,.75); box-shadow: 0 0 0 4px rgba(143,133,255,.22); color: #c9c3ff; }
.g-input input { flex: 1; min-width: 0; height: 100%; border: 0; outline: 0; background: transparent; color: #fff;
  font: inherit; font-size: 16px; text-align: left; letter-spacing: .02em; }
.g-input input:-webkit-autofill { -webkit-text-fill-color: #fff; transition: background-color 9999s; caret-color: #fff; }
.g-eye { display: grid; place-items: center; width: 40px; height: 40px; margin-inline-end: -8px; border: 0; border-radius: 10px; background: transparent; color: inherit; cursor: pointer; }
.g-eye:hover, .g-eye:focus-visible { color: #fff; background: rgba(255,255,255,.08); outline: none; }
.g-error { min-height: 22px; margin: -2px 0 0; font-size: 13px; color: #ffa3b0; }

.g-btn { position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; gap: 10px; height: 54px;
  border: 0; border-radius: 15px; cursor: pointer; color: #fff; font: inherit; font-size: 16px; font-weight: 700;
  background: linear-gradient(110deg, #6a5cf5, #8f6bff 45%, #1fb8d6); background-size: 180% 100%; background-position: 0 0;
  box-shadow: 0 14px 30px -10px rgba(115,103,240,.8); transition: background-position .5s, transform .15s, box-shadow .2s; }
.g-btn::after { content: ""; position: absolute; inset: 0; transform: translateX(120%) skewX(-20deg);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent); animation: g-shine 3.6s ease-in-out 1.2s infinite; }
.g-btn:hover { background-position: 100% 0; box-shadow: 0 18px 36px -10px rgba(31,184,214,.7); }
.g-btn:active { transform: scale(.98); }
.g-btn:focus-visible { outline: 3px solid #8fefff; outline-offset: 3px; }
.g-btn:disabled { cursor: wait; opacity: .85; }
.g-spin { width: 18px; height: 18px; border-radius: 50%; border: 2.5px solid rgba(255,255,255,.35); border-top-color: #fff; animation: g-rot .8s linear infinite; }

/* chips floating around the card (wide screens only) */
.g-chips { display: none; }
@media (min-width: 1000px) {
  .g-chips { display: block; position: absolute; inset: 0; margin: 0; padding: 0; list-style: none; pointer-events: none; }
  .g-chip { position: absolute; display: inline-flex; align-items: center; gap: 8px; padding: 9px 16px; border-radius: 999px; font-size: 13.5px; color: #e9e7ff;
    background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.14); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 10px 30px -12px rgba(0,0,0,.6); opacity: 0; animation: g-chip-in .8s ease forwards, g-bob 7s ease-in-out infinite alternate; }
  .g-chip .ico { color: var(--c); }
  .t-a { --c: #a99fff; } .t-b { --c: #5fe3f3; } .t-c { --c: #ff8fbc; } .t-d { --c: #ffc27a; } .t-e { --c: #7ef0b0; }
  .c0 { top: 16%; right: 9%; animation-delay: .5s, 0s; }
  .c1 { top: 44%; right: 4%; animation-delay: .7s, 1.2s; }
  .c2 { bottom: 15%; right: 12%; animation-delay: .9s, .6s; }
  .c3 { top: 22%; left: 8%; animation-delay: .8s, 1.8s; }
  .c4 { bottom: 22%; left: 6%; animation-delay: 1s, .3s; }
}
@media (max-width: 420px) {
  .g-card { padding: 30px 20px 22px; border-radius: 24px; }
  h1 { font-size: 23px; }
}

@keyframes g-in { from { opacity: 0; transform: translateY(26px) scale(.96); filter: blur(6px); } to { opacity: 1; transform: none; filter: none; } }
@keyframes g-shake { 10%, 90% { transform: translateX(-2px); } 20%, 80% { transform: translateX(4px); } 30%, 50%, 70% { transform: translateX(-8px); } 40%, 60% { transform: translateX(8px); } }
@keyframes g-float1 { to { transform: translate(-8vmax, 10vmax) scale(1.12); } }
@keyframes g-float2 { to { transform: translate(10vmax, -8vmax) scale(1.08); } }
@keyframes g-float3 { to { transform: translate(-18vmax, 6vmax) scale(.9); } }
@keyframes g-twinkle { 0%, 100% { opacity: 0; transform: scale(.6); } 50% { opacity: .9; transform: scale(1); } }
@keyframes g-shine { 0% { transform: translateX(120%) skewX(-20deg); } 35%, 100% { transform: translateX(-160%) skewX(-20deg); } }
@keyframes g-rot { to { transform: rotate(360deg); } }
@keyframes g-chip-in { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; } }
@keyframes g-bob { from { translate: 0 0; } to { translate: 0 -12px; } }
@property --a { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
@keyframes g-ring { to { --a: 360deg; } }

@media (prefers-reduced-motion: reduce) {
  .gate *, .gate *::before, .gate *::after, .gate { animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
  .g-chip { opacity: 1; }
}
</style>
