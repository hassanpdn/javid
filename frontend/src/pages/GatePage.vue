<script setup>
// The site's door on the live demo: one username and password before anything else.
// In English and left to right: it is the front page of Pudineh Agent Center, not of one assistant.
// Dark on purpose in both themes, so it looks the same for everyone. Not about schools: after the door comes
// the list of assistants (HubPage), and the school assistant is one of them.
// It wears pudineh.com's look (the dark theme of that site): warm near-black paper, cream text, one copper accent,
// a serif for headings, thin rules and the Pudineh mark large and faint in the background. Flat, no glass or glow.
import { ref, onMounted } from "vue"
import { enterGate } from "../lib/gate.js"
import BrandMark from "../components/core/BrandMark.vue"
import Icon from "../components/Icon.vue"

const emit = defineEmits(["entered"])
const username = ref(""), password = ref(""), show = ref(false)
const error = ref(""), sending = ref(false), shake = ref(false)
const userEl = ref(null)
// what the assistants do, listed beside the card on wide screens
const POINTS = [
  "Works with your own data",
  "Every number checked, never guessed",
  "You make the final call",
  "Drafts the routine work for you",
  "One assistant for every role",
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
    <!-- the big faint mark, like on pudineh.com -->
    <BrandMark class="g-bigmark" :size="640" />

    <header class="g-top">
      <a class="g-brand" href="https://pudineh.com" target="_blank" rel="noopener"><BrandMark :size="22" /><span>Pudineh</span></a>
      <span class="g-tag">Agent Center</span>
    </header>

    <div class="g-body">
      <section class="g-intro">
        <span class="g-rule" aria-hidden="true"></span>
        <h1>Pudineh<br />Agent Center</h1>
        <p class="g-lead">AI assistants built around the way your organization already works.</p>
        <ol class="g-points" aria-hidden="true">
          <li v-for="(p, i) in POINTS" :key="p" :style="{ '--i': i }"><span class="g-num">0{{ i + 1 }}</span>{{ p }}</li>
        </ol>
      </section>

      <section :class="['g-card', { shake }]" @animationend="shake = false">
        <h2>Sign in</h2>
        <p class="g-sub">Demo access. Sign in to see the assistants.</p>

        <form class="g-form" @submit.prevent="submit" novalidate>
          <label class="g-field">
            <span class="g-label">Username</span>
            <span class="g-input">
              <Icon name="user" :size="18" />
              <input ref="userEl" v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" dir="ltr" required />
            </span>
          </label>
          <label class="g-field">
            <span class="g-label">Password</span>
            <span class="g-input">
              <Icon name="lock" :size="18" />
              <input v-model="password" name="password" :type="show ? 'text' : 'password'" autocomplete="current-password" dir="ltr" required />
              <button type="button" class="g-eye" :aria-label="show ? 'Hide password' : 'Show password'" :aria-pressed="show" @click="show = !show">
                <Icon :name="show ? 'eyeOff' : 'eye'" :size="18" />
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
    </div>

    <footer class="g-foot">
      <a href="mailto:info@pudineh.com">info@pudineh.com</a>
    </footer>
  </main>
</template>

<style scoped>
.gate {
  /* pudineh.com's dark theme */
  --paper: #191512; --surface: #211d1a; --ink: #e8e2de; --muted: #aba19c; --rule: #36322f; --accent: #e0a785; --mark: #2a231e;
  /* the door downloads no font: the phone's own sans for text, and a serif already on the computer for headings
     (Cormorant Garamond like pudineh.com when installed, else Georgia) */
  --serif: "Cormorant Garamond", "Cormorant", Georgia, "Times New Roman", serif;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  position: relative; min-height: 100vh; min-height: 100dvh; overflow: hidden; isolation: isolate;
  display: flex; flex-direction: column;
  padding: max(20px, env(safe-area-inset-top)) clamp(16px, 6vw, 88px) max(20px, env(safe-area-inset-bottom));
  color: var(--ink); background: var(--paper);
}
/* thin vertical rules at the edges, like the site's side lines */
.gate::before, .gate::after { content: ""; position: absolute; top: 28%; bottom: 0; width: 1px; background: var(--rule); z-index: -1; }
.gate::before { left: clamp(8px, 2.5vw, 32px); }
.gate::after { right: clamp(8px, 2.5vw, 32px); }

.g-bigmark { position: absolute; z-index: -1; right: -6vw; bottom: -14vh; width: min(78vh, 640px); height: auto; color: var(--mark); pointer-events: none; }

.g-top { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.g-brand { display: inline-flex; align-items: center; gap: 10px; color: var(--ink); text-decoration: none; font-family: var(--serif); font-size: 20px; }
.g-brand .brand-mark { color: var(--accent); }
.g-brand:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
.g-tag { font-size: 12px; letter-spacing: .16em; text-transform: uppercase; color: var(--muted); }

.g-body { flex: 1; display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; justify-items: center; gap: 28px; padding: 28px 0; }

.g-intro { width: min(100%, 410px); }
.g-rule { display: block; width: 36px; height: 2px; background: var(--accent); margin-bottom: 18px; }
h1 { margin: 0; font-family: var(--serif); font-weight: 500; font-size: 34px; line-height: 1.12; letter-spacing: -.01em; color: var(--ink); }
.g-lead { margin: 12px 0 0; color: var(--muted); font-size: 15px; line-height: 1.6; max-width: 34ch; }
.g-points { display: none; }

/* the sign-in card: flat, one hairline border */
.g-card { position: relative; width: min(100%, 410px); padding: 30px 28px 28px; border-radius: 6px;
  background: var(--surface); border: 1px solid var(--rule); box-shadow: 0 30px 60px -30px rgba(0,0,0,.7);
  animation: g-in .8s cubic-bezier(.2,.9,.25,1) both; }
.g-card.shake { animation: g-shake .45s cubic-bezier(.36,.07,.19,.97); }
h2 { margin: 0; font-family: var(--serif); font-weight: 500; font-size: 28px; line-height: 1.2; color: var(--ink); }
.g-sub { margin: 6px 0 24px; color: var(--muted); font-size: 14px; }

.g-form { display: flex; flex-direction: column; gap: 16px; text-align: left; }
.g-field { display: flex; flex-direction: column; gap: 7px; }
.g-label { font-size: 11.5px; font-weight: 600; color: var(--muted); letter-spacing: .14em; text-transform: uppercase; }
.g-input { display: flex; align-items: center; gap: 10px; padding: 0 14px; height: 50px; border-radius: 4px;
  background: var(--paper); border: 1px solid var(--rule); color: #7d736d; transition: border-color .2s, color .2s; }
.g-input:focus-within { border-color: var(--accent); color: var(--accent); }
.g-input input { flex: 1; min-width: 0; height: 100%; border: 0; outline: 0; background: transparent; color: var(--ink);
  font: inherit; font-size: 16px; text-align: left; letter-spacing: .02em; }
.g-input input:-webkit-autofill { -webkit-text-fill-color: var(--ink); transition: background-color 9999s; caret-color: var(--ink); }
.g-eye { display: grid; place-items: center; width: 40px; height: 40px; margin-inline-end: -8px; border: 0; border-radius: 4px; background: transparent; color: inherit; cursor: pointer; }
.g-eye:hover, .g-eye:focus-visible { color: var(--ink); background: rgba(232,226,222,.06); outline: none; }
.g-error { min-height: 22px; margin: -4px 0 0; font-size: 13px; color: #f0a593; }

.g-btn { display: flex; align-items: center; justify-content: center; gap: 10px; height: 52px; margin-top: 2px;
  border: 0; border-radius: 4px; cursor: pointer; color: var(--paper); font: inherit; font-size: 15.5px; font-weight: 600; letter-spacing: .02em;
  background: var(--accent); transition: background .2s, transform .15s; }
.g-btn .ico { transition: transform .2s; }
.g-btn:hover { background: #ebbb9e; }
.g-btn:hover .ico { transform: translateX(3px); }
.g-btn:active { transform: scale(.985); }
.g-btn:focus-visible { outline: 2px solid var(--ink); outline-offset: 3px; }
.g-btn:disabled { cursor: wait; opacity: .85; }
.g-spin { width: 17px; height: 17px; border-radius: 50%; border: 2.5px solid rgba(25,21,18,.3); border-top-color: var(--paper); animation: g-rot .8s linear infinite; }

.g-foot { display: flex; justify-content: center; font-size: 12.5px; letter-spacing: .06em; }
.g-foot a { color: var(--muted); text-decoration: none; }
.g-foot a:hover, .g-foot a:focus-visible { color: var(--accent); outline: none; }

/* wide screens: the site's hero on the left, the card on the right */
@media (min-width: 960px) {
  .g-body { grid-template-columns: minmax(0, 1fr) 410px; justify-items: stretch; gap: clamp(40px, 7vw, 120px); max-width: 1120px; width: 100%; margin: 0 auto; }
  .g-intro { width: auto; }
  h1 { font-size: clamp(48px, 5.2vw, 68px); line-height: 1.04; }
  .g-lead { font-size: 16px; margin-top: 18px; }
  .g-points { display: block; list-style: none; margin: 36px 0 0; padding: 0; max-width: 380px; border-top: 1px solid var(--rule); }
  .g-points li { display: flex; align-items: baseline; gap: 14px; padding: 11px 0; border-bottom: 1px solid var(--rule); font-size: 14.5px; color: var(--ink);
    opacity: 0; animation: g-up .6s ease forwards; animation-delay: calc(.35s + var(--i) * .08s); }
  .g-num { font-size: 12px; color: var(--accent); font-variant-numeric: tabular-nums; }
  .g-foot { justify-content: flex-end; }
}
@media (max-width: 767px) {
  .gate::before, .gate::after { display: none; }
  .g-bigmark { width: 130vw; right: -45vw; bottom: -20vh; }
}
@media (max-width: 420px) {
  .g-card { padding: 26px 20px 22px; }
  h1 { font-size: 30px; }
}

/* the card slides up but does not fade in: text that starts invisible counts as not shown until the fade ends,
   which held back the page's first paint (PageSpeed's LCP) by about 0.7 s */
@keyframes g-in { from { transform: translateY(20px); } to { transform: none; } }
@keyframes g-up { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes g-shake { 10%, 90% { transform: translateX(-2px); } 20%, 80% { transform: translateX(4px); } 30%, 50%, 70% { transform: translateX(-8px); } 40%, 60% { transform: translateX(8px); } }
@keyframes g-rot { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .gate *, .gate *::before, .gate *::after, .gate { animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
  .g-points li { opacity: 1; }
}
</style>
