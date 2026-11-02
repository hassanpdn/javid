<script setup>
// «سایت بنگاه»: the agency's website as someone looking for a home would see it, with its assistant. You play the
// visitor. Beside it, «پشت صحنه» shows what the assistant read from each message and which listings it took the units
// from. A mobile number at the end becomes a request for an agent, and the panels get a toast.
import { ref, nextTick, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { agencyInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import AiOrb from "../components/AiOrb.vue"

const emit = defineEmits(["request"])
const chat = ref(""), msgs = ref([]), chips = ref([]), input = ref(""), typing = ref(false), trace = ref([]), lead = ref(null), box = ref(null), turn = ref(0)
const scroll = async () => { await nextTick(); box.value?.scrollTo({ top: box.value.scrollHeight, behavior: "smooth" }) }
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const show = async (r) => {
  for (const m of r.messages) { typing.value = true; await scroll(); await wait(340); typing.value = false; msgs.value.push({ from: "bot", text: m }); await scroll() }
  chips.value = r.chips || []
  if (r.trace?.length) { turn.value++; trace.value.push({ turn: turn.value, lines: r.trace }) }
  if (r.lead) lead.value = r.lead
}
const start = async () => {
  msgs.value = []; chips.value = []; trace.value = []; lead.value = null; turn.value = 0
  const r = await api("/estate/site/chat", { chat: "", text: "" })
  chat.value = r.chat
  await show(r)
}
const send = async (text) => {
  text = (text ?? input.value).trim()
  if (!text || typing.value) return
  input.value = ""; chips.value = []
  msgs.value.push({ from: "me", text }); await scroll()
  try { await show(await api("/estate/site/chat", { chat: chat.value, text })) }
  catch { msgs.value.push({ from: "bot", text: "ارتباط برقرار نشد. دوباره بنویسید." }) }
}
onMounted(start)
</script>

<template>
  <div class="shop-view">
    <div class="sv-site">
      <div class="sv-browser">
        <div class="sv-bar"><i></i><i></i><i></i><span class="sv-url"><Icon name="shield" :size="13" />{{ agencyInfo.agency.name }} · سایت بنگاه</span></div>
        <header class="sv-head">
          <span class="logo">{{ (agencyInfo.agency.name || 'ب')[0] }}</span>
          <div><b>{{ agencyInfo.agency.name }}</b><small>مشاور املاک · {{ agencyInfo.agency.place }}</small></div>
        </header>
        <div class="sv-hero es-hero" aria-hidden="true"><span v-for="n in 7" :key="n" class="es-hero-h" :style="{ height: 26 + (n * 37) % 44 + 'px' }"></span></div>
        <div class="sv-chat">
          <div class="sv-chat-head"><AiOrb :size="34" :busy="typing" /><div><b>دستیار بنگاه</b><small>{{ typing ? 'در حال نوشتن…' : 'آنلاین' }}</small></div>
            <button class="icon-btn sm" @click="start" aria-label="گفت‌وگوی جدید"><Icon name="refresh" :size="16" /></button></div>
          <div ref="box" class="sv-msgs" role="log" aria-live="polite">
            <div v-for="(m, i) in msgs" :key="i" :class="['sv-msg', m.from]">{{ fa(m.text) }}</div>
            <div v-if="typing" class="sv-msg bot sv-typing"><i></i><i></i><i></i></div>
            <div v-if="lead && !typing" v-pop class="sv-done"><Icon name="check" :size="18" />درخواست {{ fa(lead.id) }} ثبت شد</div>
          </div>
          <div v-if="chips.length && !typing" class="sv-chips"><button v-for="c in chips" :key="c" class="chip-btn" @click="send(c)">{{ fa(c) }}</button></div>
          <form class="sv-input" @submit.prevent="send()">
            <input v-model="input" placeholder="بنویسید، مثلاً: دو خواب برای اجاره در سعادت‌آباد" aria-label="پیام به دستیار" :disabled="typing">
            <button class="btn primary" :disabled="!input.trim() || typing" aria-label="فرستادن"><Icon name="send" :size="18" /></button>
          </form>
        </div>
      </div>
    </div>
    <aside class="sv-behind">
      <section class="card">
        <div class="card-head"><Icon name="sparkles" :size="18" class="text-primary" />پشت صحنه</div>
        <p class="muted small">بازدیدکننده فقط گفت‌وگو را می‌بیند. این‌جا پیداست دستیار از هر پیام چه خواند و واحدها را از کدام فایل‌ها آورد. قیمت‌ها را خود برنامه از فایل‌ها می‌نویسد؛ نام و تلفن مالک و نشانی دقیق هرگز به سایت نمی‌رود.</p>
        <ol class="sv-trace"><li v-for="t in trace" :key="t.turn"><small class="muted">پاسخ {{ fa(t.turn) }}</small><span v-for="l in t.lines" :key="l" class="sv-line f-info">{{ fa(l) }}</span></li></ol>
        <p v-if="!trace.length" class="muted small">با اولین پیام، این‌جا پر می‌شود.</p>
      </section>
      <section v-if="lead" v-pop class="card sv-order">
        <span class="tint lg t-success"><Icon name="check" :size="24" /></span>
        <div class="grow"><b>درخواست {{ fa(lead.id) }} برای {{ lead.agent }} ثبت شد</b><small class="muted">به مدیر و مشاوران هم خبر داده شد.</small></div>
        <button class="btn sm" @click="emit('request', lead.id)">دیدن متقاضی</button>
      </section>
    </aside>
  </div>
</template>
