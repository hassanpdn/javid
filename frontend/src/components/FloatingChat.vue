<script setup>
// The floating assistant: a round button in the bottom-right corner that opens a chat window.
// Every role gets one; the props decide which endpoint, examples and texts it uses.
import { ref, watch, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { chatUi } from "../lib/chat.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"
import Icon from "./Icon.vue"
// shown only when opened, so their code is downloaded only then
const ChatBox = defineAsyncComponent(() => import("./ChatBox.vue"))

defineProps({
  title: { default: "دستیار هوشمند" }, subtitle: { default: "" }, endpoint: { default: "/chat" },
  examples: { default: null }, intro: { default: null }, loadingText: { default: "در حال جستجو در اسناد" },
})
const started = ref(false)        // the chat is created on first open, then kept so the conversation survives closing
const hint = ref(false)           // the small "any questions?" bubble, shown once per browser session
const fab = ref(null), icon = ref(null)
let ctx

watch(() => chatUi.open, (open) => {
  if (open) { started.value = true; hint.value = false }
  if (motion && icon.value) gsap.fromTo(icon.value, { rotation: open ? -90 : 90, scale: .5 }, { rotation: 0, scale: 1, duration: .4, ease: "back.out(2)" })
})

// The window grows out of the button's corner, and shrinks back into it
const enter = (el, done) => motion
  ? gsap.fromTo(el, { opacity: 0, scale: .4, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: .45, ease: "back.out(1.4)", transformOrigin: "100% 100%", onComplete: done })
  : done()
const leave = (el, done) => motion
  ? gsap.to(el, { opacity: 0, scale: .5, y: 30, duration: .25, ease: "power2.in", transformOrigin: "100% 100%", onComplete: done })
  : done()

onMounted(() => {
  if (!hintSeen()) setTimeout(() => { if (!chatUi.open) hint.value = true }, 2500)
  if (!motion) return
  ctx = gsap.context(() => {
    gsap.from(fab.value, { scale: 0, rotation: -180, duration: .8, ease: "back.out(1.8)", delay: .6 })
    // the pulsing ring and the breathing button are CSS animations in main.css (.fab-ring, .fab-core)
  }, fab.value)
})
onUnmounted(() => { ctx?.revert(); chatUi.open = false })

function hintSeen() { try { return sessionStorage.getItem("chat-hint") } catch { return "1" } }
function dismissHint() { hint.value = false; try { sessionStorage.setItem("chat-hint", "1") } catch {} }
const toggle = () => { chatUi.open = !chatUi.open; dismissHint() }
</script>

<template>
  <Transition :css="false" @enter="enter" @leave="leave">
    <section v-if="started" v-show="chatUi.open" class="chat-window" role="dialog" :aria-label="title">
      <header class="cw-head">
        <span class="cw-avatar"><Icon name="sparkles" :size="20" /></span>
        <div class="cw-title"><b>{{ title }}</b><small><span class="online"></span>{{ subtitle || 'آماده پاسخ‌گویی' }}</small></div>
        <button class="cw-close" @click="chatUi.open = false" aria-label="بستن گفتگو"><Icon name="x" :size="20" /></button>
      </header>
      <ChatBox :endpoint="endpoint" :examples="examples" :intro="intro" :loading-text="loadingText" />
    </section>
  </Transition>

  <Transition name="hint">
    <div v-if="hint && !chatUi.open" class="fab-hint" @click="toggle">
      سؤالی دارید؟ از دستیار بپرسید
      <button class="fab-hint-x" @click.stop="dismissHint" aria-label="بستن">×</button>
    </div>
  </Transition>

  <button ref="fab" :class="['fab-chat', { open: chatUi.open }]" @click="toggle"
          :aria-label="chatUi.open ? 'بستن دستیار' : 'باز کردن دستیار هوشمند'" :aria-expanded="chatUi.open">
    <span class="fab-ring"></span><span class="fab-ring"></span>
    <span class="fab-core"><span ref="icon" class="ico"><Icon :name="chatUi.open ? 'x' : 'message'" :size="26" /></span></span>
    <span class="fab-label">دستیار هوشمند</span>
  </button>
</template>
