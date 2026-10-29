<script setup>
// The site's door on the live demo: one username and password before anything else.
// In English and left to right: it is the front page of Pudineh Agent Center, not of one assistant.
// Dark on purpose in both themes, so it looks the same for everyone. Not about schools: after the door comes
// the list of assistants (HubPage), and the school assistant is one of them.
import { ref, onMounted } from "vue"
import { enterGate } from "../lib/gate.js"
import AiOrb from "../components/AiOrb.vue"
import AuroraBg from "../components/AuroraBg.vue"
import Icon from "../components/Icon.vue"

const emit = defineEmits(["entered"])
const username = ref(""), password = ref(""), show = ref(false)
const error = ref(""), sending = ref(false), shake = ref(false)
const userEl = ref(null)
// what the assistants do, floating around the card on wide screens
const CHIPS = [
  { text: "Works with your own data", icon: "book", tone: "a" },
  { text: "Every number checked, never guessed", icon: "chart", tone: "b" },
  { text: "You make the final call", icon: "check", tone: "c" },
  { text: "Drafts the routine work for you", icon: "edit", tone: "d" },
  { text: "One assistant for every role", icon: "users", tone: "e" },
]
onMounted(() => {
  document.title = "Pudineh Agent Center"
  if (window.matchMedia("(min-width: 768px)").matches) userEl.value?.focus()
})

const submit = async () => {
  if (sending.value) return
  if (!username.value.trim() || !password.value) { fail("Enter your username and password."); return }
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
  <main class="gate" dir="ltr" lang="en">
    <AuroraBg />

    <ul class="g-chips" aria-hidden="true">
      <li v-for="(c, i) in CHIPS" :key="c.text" :class="['g-chip', 'c' + i, 't-' + c.tone]"><Icon :name="c.icon" :size="16" />{{ c.text }}</li>
    </ul>

    <section :class="['g-card', { shake }]" @animationend="shake = false">
      <div class="g-orb"><AiOrb :size="104" :busy="sending" /></div>
      <h1>Pudineh Agent Center</h1>
      <p class="g-sub">Demo access. Sign in to see the assistants.</p>

      <form class="g-form" @submit.prevent="submit" novalidate>
        <label class="g-field">
          <span class="g-label">Username</span>
          <span class="g-input">
            <Icon name="user" :size="19" />
            <input ref="userEl" v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" dir="ltr" required />
          </span>
        </label>
        <label class="g-field">
          <span class="g-label">Password</span>
          <span class="g-input">
            <Icon name="lock" :size="19" />
            <input v-model="password" name="password" :type="show ? 'text' : 'password'" autocomplete="current-password" dir="ltr" required />
            <button type="button" class="g-eye" :aria-label="show ? 'Hide password' : 'Show password'" :aria-pressed="show" @click="show = !show">
              <Icon :name="show ? 'eyeOff' : 'eye'" :size="19" />
            </button>
          </span>
        </label>
        <p class="g-error" role="alert">{{ error }}</p>
        <button class="g-btn" :disabled="sending">
          <span v-if="sending" class="g-spin" aria-hidden="true"></span>
          <span>{{ sending ? "Signing in" : "Sign in" }}</span>
          <Icon v-if="!sending" name="arrowRight" :size="18" />
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
  color: #eceaff; background: #07061a;
}

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

.g-form { display: flex; flex-direction: column; gap: 14px; text-align: left; }
.g-field { display: flex; flex-direction: column; gap: 6px; }
.g-label { font-size: 13px; font-weight: 700; color: #d6d3f5; letter-spacing: .02em; }
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

/* the card slides up but does not fade in: text that starts invisible counts as not shown until the fade ends,
   which held back the page's first paint (PageSpeed's LCP) by about 0.7 s */
@keyframes g-in { from { transform: translateY(26px) scale(.96); } to { transform: none; } }
@keyframes g-shake { 10%, 90% { transform: translateX(-2px); } 20%, 80% { transform: translateX(4px); } 30%, 50%, 70% { transform: translateX(-8px); } 40%, 60% { transform: translateX(8px); } }
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
