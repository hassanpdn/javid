<script setup>
// «سایت فروشگاه»: the shop's website as an end customer would see it, with the assistant that takes orders.
// You play the customer. Beside it, «پشت صحنه» shows what the assistant read and wrote in which file,
// and when an order is placed the panel's notice arrives like it would for the owner.
import { ref, nextTick, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { shop, swatch } from "./lib.js"
import Icon from "../components/Icon.vue"
import AiOrb from "../components/AiOrb.vue"

const emit = defineEmits(["orders"])
const chat = ref(""), msgs = ref([]), chips = ref([]), input = ref(""), typing = ref(false)
const trace = ref([]), order = ref(null), phones = ref([]), box = ref(null), turn = ref(0)
const SWATCHES = ["آبی نفتی", "زرشکی", "کرم", "سبز یشمی", "طلایی", "مشکی", "صورتی", "آبی آسمانی"]

const scroll = async () => { await nextTick(); box.value?.scrollTo({ top: box.value.scrollHeight, behavior: "smooth" }) }
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
// the assistant's messages arrive one after another, like someone typing
const show = async (r) => {
  for (const m of r.messages) { typing.value = true; await scroll(); await wait(380); typing.value = false; msgs.value.push({ from: "bot", text: m }); await scroll() }
  chips.value = r.chips || []
  if (r.trace?.length) { turn.value++; trace.value.push({ turn: turn.value, lines: r.trace }) }
  if (r.order) order.value = r.order
}
const start = async () => {
  msgs.value = []; chips.value = []; trace.value = []; order.value = null; turn.value = 0
  const r = await api("/fabric/shop/chat", { chat: "", text: "" })
  chat.value = r.chat
  await show(r)
}
const send = async (text) => {
  text = (text ?? input.value).trim()
  if (!text || typing.value) return
  input.value = ""; chips.value = []
  msgs.value.push({ from: "me", text }); await scroll()
  try { await show(await api("/fabric/shop/chat", { chat: chat.value, text })) }
  catch { msgs.value.push({ from: "bot", text: "ارتباط برقرار نشد. دوباره بنویسید." }) }
}
onMounted(async () => { await start(); try { phones.value = await api("/fabric/shop/demo-phones") } catch {} })
const fileOf = (l) => l.startsWith("انبار") ? "stock" : l.startsWith("فروش") ? "sales" : l.startsWith("حسابداری") ? "accounts" : "info"
</script>

<template>
  <div class="shop-view">
    <div class="sv-site">
      <div class="sv-browser">
        <div class="sv-bar"><i></i><i></i><i></i><span class="sv-url"><Icon name="shield" :size="13" />{{ shop.business.name }} · فروشگاه آنلاین</span></div>
        <header class="sv-head">
          <span class="logo">{{ (shop.business.name || 'پ')[0] }}</span>
          <div><b>{{ shop.business.name }}</b><small>عمده‌فروشی پارچه · {{ shop.business.place }}</small></div>
        </header>
        <div class="sv-hero" aria-hidden="true">
          <span v-for="c in SWATCHES" :key="c" class="sv-roll" :style="{ background: swatch(c) }"></span>
        </div>
        <div class="sv-chat">
          <div class="sv-chat-head"><AiOrb :size="34" :busy="typing" /><div><b>دستیار فروش</b><small>{{ typing ? 'در حال نوشتن…' : 'آنلاین' }}</small></div>
            <button class="icon-btn sm" @click="start" aria-label="گفت‌وگوی تازه"><Icon name="refresh" :size="16" /></button></div>
          <div ref="box" class="sv-msgs" role="log" aria-live="polite">
            <div v-for="(m, i) in msgs" :key="i" :class="['sv-msg', m.from]">{{ fa(m.text) }}</div>
            <div v-if="typing" class="sv-msg bot sv-typing"><i></i><i></i><i></i></div>
            <div v-if="order && !typing" v-pop class="sv-done"><Icon name="check" :size="18" />سفارش {{ fa(order.id) }} ثبت شد</div>
          </div>
          <div v-if="chips.length && !typing" class="sv-chips">
            <button v-for="c in chips" :key="c" class="chip-btn" @click="send(c)">{{ fa(c) }}</button>
          </div>
          <form class="sv-input" @submit.prevent="send()">
            <input v-model="input" placeholder="بنویسید، مثلاً: ۲ توپ کتان کش مشکی" aria-label="پیام به دستیار" :disabled="typing">
            <button class="btn primary" :disabled="!input.trim() || typing" aria-label="فرستادن"><Icon name="send" :size="18" /></button>
          </form>
        </div>
      </div>
      <div v-if="phones.length" class="sv-try">
        <small class="muted">برای امتحان، جای مشتری قدیمی:</small>
        <button v-for="p in phones" :key="p.phone" class="chip-btn" :disabled="typing" @click="send(p.phone)">{{ p.name }} · <span dir="ltr">{{ fa(p.phone) }}</span></button>
      </div>
    </div>

    <aside class="sv-behind">
      <section class="card">
        <div class="card-head"><Icon name="sparkles" :size="18" class="text-primary" />پشت صحنه</div>
        <p class="muted small">مشتری فقط گفت‌وگو را می‌بیند. اینجا پیداست دستیار هر جواب را از کدام فایل آورد. قیمت و موجودی را خود برنامه از فایل انبار می‌خواند، نه مدل.</p>
        <ol class="sv-trace">
          <li v-for="t in trace" :key="t.turn">
            <small class="muted">جواب {{ fa(t.turn) }}</small>
            <span v-for="l in t.lines" :key="l" :class="['sv-line', 'f-' + fileOf(l)]">{{ fa(l) }}</span>
          </li>
        </ol>
        <p v-if="!trace.length" class="muted small">با اولین سؤال درباره‌ی پارچه، اینجا پر می‌شود.</p>
      </section>
      <section v-if="order" v-pop class="card sv-order">
        <span class="tint lg t-success"><Icon name="check" :size="24" /></span>
        <div class="grow"><b>سفارش {{ fa(order.id) }} در فایل فروش ثبت شد</b>
          <small class="muted">با وضعیت «پرداخت نشده». به صاحب کار و فروشنده هم خبر داده شد.</small></div>
        <button class="btn sm" @click="emit('orders')">دیدن در سفارش‌ها</button>
      </section>
    </aside>
  </div>
</template>
