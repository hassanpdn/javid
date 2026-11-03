<script setup>
// «سایت هتل»: the hotel's website as a guest would see it, with its assistant. You play the
// guest. Beside it, «پشت صحنه» shows what the assistant read from each message and how many rooms were left. A name
// and a mobile number at the end make a tentative booking waiting for its deposit, and the panels get a toast.
import { ref, nextTick, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { hotelInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import AiOrb from "../components/AiOrb.vue"

const emit = defineEmits(["open"])
const chat = ref(""), msgs = ref([]), chips = ref([]), input = ref(""), typing = ref(false), trace = ref([]), booking = ref(null), box = ref(null), turn = ref(0)
const scroll = async () => { await nextTick(); box.value?.scrollTo({ top: box.value.scrollHeight, behavior: "smooth" }) }
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const show = async (r) => {
  for (const m of r.messages) { typing.value = true; await scroll(); await wait(340); typing.value = false; msgs.value.push({ from: "bot", text: m }); await scroll() }
  chips.value = r.chips || []
  if (r.trace?.length) { turn.value++; trace.value.push({ turn: turn.value, lines: r.trace }) }
  if (r.booking) booking.value = r.booking
}
const start = async () => {
  msgs.value = []; chips.value = []; trace.value = []; booking.value = null; turn.value = 0
  const r = await api("/hotel/site/chat", { chat: "", text: "" })
  chat.value = r.chat
  await show(r)
}
const send = async (text) => {
  text = (text ?? input.value).trim()
  if (!text || typing.value) return
  input.value = ""; chips.value = []
  msgs.value.push({ from: "me", text }); await scroll()
  try { await show(await api("/hotel/site/chat", { chat: chat.value, text })) }
  catch { msgs.value.push({ from: "bot", text: "ارتباط برقرار نشد. دوباره بنویسید." }) }
}
onMounted(start)
</script>

<template>
  <div class="shop-view">
    <div class="sv-site">
      <div class="sv-browser">
        <div class="sv-bar"><i></i><i></i><i></i><span class="sv-url"><Icon name="shield" :size="13" />{{ hotelInfo.hotel.name }} · سایت هتل</span></div>
        <header class="sv-head">
          <span class="logo">{{ (hotelInfo.hotel.name || 'ه')[0] }}</span>
          <div><b>{{ hotelInfo.hotel.name }}</b><small>هتل · {{ hotelInfo.hotel.place }}</small></div>
        </header>
        <div class="sv-hero ht-hero" aria-hidden="true"><i></i><i></i><i></i></div>
        <div class="sv-chat">
          <div class="sv-chat-head"><AiOrb :size="34" :busy="typing" /><div><b>دستیار رزرو</b><small>{{ typing ? 'در حال نوشتن…' : 'آنلاین' }}</small></div>
            <button class="icon-btn sm" @click="start" aria-label="گفت‌وگوی جدید"><Icon name="refresh" :size="16" /></button></div>
          <div ref="box" class="sv-msgs" role="log" aria-live="polite">
            <div v-for="(m, i) in msgs" :key="i" :class="['sv-msg', m.from]">{{ fa(m.text) }}</div>
            <div v-if="typing" class="sv-msg bot sv-typing"><i></i><i></i><i></i></div>
            <div v-if="booking && !typing" v-pop class="sv-done"><Icon name="check" :size="18" />رزرو {{ fa(booking.id) }} ثبت شد</div>
          </div>
          <div v-if="chips.length && !typing" class="sv-chips"><button v-for="c in chips" :key="c" class="chip-btn" @click="send(c)">{{ fa(c) }}</button></div>
          <form class="sv-input" @submit.prevent="send()">
            <input v-model="input" placeholder="بنویسید، مثلاً: ۱۵ تا ۱۸ آذر برای دو نفر" aria-label="پیام به دستیار" :disabled="typing">
            <button class="btn primary" :disabled="!input.trim() || typing" aria-label="فرستادن"><Icon name="send" :size="18" /></button>
          </form>
        </div>
      </div>
    </div>
    <aside class="sv-behind">
      <section class="card">
        <div class="card-head"><Icon name="sparkles" :size="18" class="text-primary" />پشت صحنه</div>
        <p class="muted small">مهمان فقط گفت‌وگو را می‌بیند. این‌جا پیداست دستیار از هر پیام چه خواند و برای آن شب‌ها چند اتاق مانده بود. قیمت‌ها و اتاق‌های خالی را خود برنامه می‌نویسد؛ رزرو سایت موقت است و منتظر بیعانه می‌ماند.</p>
        <ol class="sv-trace"><li v-for="t in trace" :key="t.turn"><small class="muted">پاسخ {{ fa(t.turn) }}</small><span v-for="l in t.lines" :key="l" class="sv-line f-info">{{ fa(l) }}</span></li></ol>
        <p v-if="!trace.length" class="muted small">با اولین پیام، این‌جا پر می‌شود.</p>
      </section>
      <section v-if="booking" v-pop class="card sv-order">
        <span class="tint lg t-success"><Icon name="check" :size="24" /></span>
        <div class="grow"><b>رزرو موقت {{ fa(booking.id) }} برای {{ booking.guest }} ثبت شد</b><small class="muted">به رزرو و پذیرش هم خبر داده شد.</small></div>
        <button class="btn sm" @click="emit('open', booking.id)">دیدن رزرو</button>
      </section>
    </aside>
  </div>
</template>
