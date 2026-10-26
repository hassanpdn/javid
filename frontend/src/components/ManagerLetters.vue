<script setup>
// The manager's letters: decide on what the office sent up, mark letters sent for information as seen,
// and look at what the office still has open. The office writes and sends the formal replies; the manager decides.
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue"
import { api, fa, lockScroll } from "../lib/api.js"
import { toast, busy, idle } from "../lib/notify.js"
import Icon from "./Icon.vue"

const props = defineProps({ focus: { default: null } })   // id of a letter to open right away (from a dashboard alert)
const emit = defineEmits(["changed"])
// the office's statuses, worded for the manager ("waiting for you" in the office panel means the office)
const OFFICE_STATUS = { new: "در صف دستیار", processing: "در حال بررسی", awaiting_approval: "پاسخ آماده، منتظر تأیید دفتر", todo: "در دست اقدام دفتر" }
const data = ref(null), open = ref(null), note = ref(""), saving = ref(false)
const queued = computed(() => data.value ? data.value.office.filter((l) => ["new", "processing"].includes(l.status)).length : 0)
const load = async () => { data.value = await api("/manager/letters") }
// Letters reach the manager only after the assistant has read them. If nobody opened the office panel yet,
// the queue is still full, so this page runs the assistant on it the same way the office panel does.
const agent = reactive({ running: false, processed: 0, total: 0, error: "" })
const runAgent = async () => {
  if (!queued.value) return
  Object.assign(agent, { running: true, processed: 0, total: queued.value, error: "" })
  const before = data.value.decide.length + data.value.info.length
  const label = () => busy("agent", `دستیار در حال خواندن نامه‌های تازه: ${agent.processed} از ${agent.total}`)
  label()
  try {
    while (!(await api("/staff/agent/next", {})).done) { agent.processed++; label(); await load() }
  } catch { agent.error = "دستیار در دسترس نیست. مدل محلی روشن است؟" }
  finally {
    agent.running = false; idle("agent"); await load(); emit("changed")
    const added = data.value.decide.length + data.value.info.length - before
    if (added > 0) toast({ tone: "primary", title: `${fa(added)} نامه‌ی تازه برای شما`, body: "دستیار نامه‌ها را خواند؛ تصمیم و رؤیت با شماست." })
  }
}
const show = (l) => { open.value = l; note.value = "" }
const done = async () => { open.value = null; await load(); emit("changed") }
const decide = async (approve) => {
  saving.value = true
  try {
    await api(`/manager/letters/${open.value.id}/decide`, { approve, note: note.value })
    toast({ tone: "success", title: approve ? "موافقت شما ثبت شد" : "مخالفت شما ثبت شد", body: "دفتر خبردار شد و نتیجه را به فرستنده اعلام می‌کند." })
    await done()
  }
  finally { saving.value = false }
}
const markSeen = async (l) => {
  await api(`/manager/letters/${l.id}/seen`, {})
  toast({ tone: "success", title: "رؤیت شد", body: "نامه بسته شد و دفتر در جریان قرار گرفت." })
  await done()
}
watch(() => !!open.value, lockScroll)
onMounted(async () => {
  await load()
  const d = data.value, l = props.focus && [...d.decide, ...d.info, ...d.office].find((x) => x.id === props.focus)
  if (l) show(l)
  runAgent()
})
onUnmounted(() => { lockScroll(false); idle("agent") })
</script>

<template>
  <div class="flex flex-col gap-6">
    <section v-reveal>
      <h2>نامه‌ها</h2>
      <p class="muted">تصمیم با شماست. پاسخ رسمی را دفتر می‌نویسد و می‌فرستد.</p>
    </section>
    <p v-if="agent.error" class="check bad" role="status">{{ agent.error }}</p>

    <div v-if="!data" class="card shimmer"><span></span><span></span><span style="width:60%"></span></div>
    <template v-else>
      <section class="letters">
        <h3 class="group-head">منتظر تصمیم شما <span v-if="data.decide.length" class="count">{{ fa(data.decide.length) }}</span></h3>
        <p v-if="!data.decide.length" class="muted small">نامه‌ای منتظر تصمیم شما نیست.</p>
        <article v-for="l in data.decide" :key="l.id" v-reveal class="letter-card card st-needs_manager">
          <div class="lc-top">
            <b>{{ fa(l.subject) }}</b>
            <span v-if="l.deadline_short" :class="['chip', { hot: l.days_left <= 3 }]">مهلت {{ fa(l.deadline_short) }}</span>
          </div>
          <div class="lc-meta"><Icon name="mail" :size="15" />{{ l.sender }} · {{ fa(l.received_short) }}</div>
          <p v-if="l.summary" class="lc-summary">{{ fa(l.summary) }}</p>
          <p v-if="l.action" class="lc-action"><Icon name="sparkles" :size="16" /><span>پیشنهاد دستیار: {{ fa(l.action) }}</span></p>
          <div class="btn-row"><button class="btn primary sm" @click="show(l)">خواندن نامه و تصمیم</button></div>
        </article>
      </section>

      <section class="letters">
        <h3 class="group-head">برای اطلاع شما</h3>
        <p v-if="!data.info.length" class="muted small">نامه‌ای برای اطلاع شما نیامده.</p>
        <article v-for="l in data.info" :key="l.id" v-reveal :class="['letter-card', 'card', 'st-' + l.status]">
          <div class="lc-top">
            <b>{{ fa(l.subject) }}</b>
            <span v-if="l.manager_seen_at" class="tag st-done">دیدید · {{ fa(l.manager_seen_at) }}</span>
          </div>
          <div class="lc-meta"><Icon name="mail" :size="15" />{{ l.sender }} · {{ fa(l.received_short) }}</div>
          <p v-if="l.summary" class="lc-summary">{{ fa(l.summary) }}</p>
          <div class="btn-row">
            <button class="btn ghost sm" @click="show(l)">متن نامه</button>
            <button v-if="l.status === 'forwarded'" class="btn success sm" @click="markSeen(l)"><Icon name="check" :size="16" />دیدم</button>
          </div>
        </article>
      </section>

      <section v-reveal class="card">
        <div class="card-head">در دست دفتر <small>فقط برای دیدن؛ کار این نامه‌ها با دفتر است</small></div>
        <p v-if="queued && !agent.running" class="muted small">{{ fa(queued) }} نامه هنوز در صف بررسی دستیار در دفتر است.</p>
        <p v-if="!data.office.length" class="muted small">دفتر نامه بازی ندارد.</p>
        <ul class="office-list">
          <li v-for="l in data.office" :key="l.id">
            <button class="office-row" @click="show(l)">
              <span class="grow">{{ fa(l.subject) }}</span>
              <span :class="['tag', 'st-' + l.status]">{{ OFFICE_STATUS[l.status] || l.status_name }}</span>
              <span v-if="l.deadline_short" :class="['chip', { hot: l.days_left <= 3 }]">مهلت {{ fa(l.deadline_short) }}</span>
            </button>
          </li>
        </ul>
      </section>
    </template>

    <div v-if="open" class="overlay" @click.self="open = null">
      <div class="dialog" v-pop>
        <h3>{{ fa(open.subject) }}</h3>
        <p class="muted small">{{ open.sender }} · {{ fa(open.received_short) }}<span v-if="open.deadline_short"> · مهلت {{ fa(open.deadline_short) }}</span></p>
        <div class="letter">{{ fa(open.body) }}</div>
        <template v-if="open.status === 'needs_manager'">
          <p v-if="open.action" class="lc-action"><Icon name="sparkles" :size="16" /><span>پیشنهاد دستیار: {{ fa(open.action) }}</span></p>
          <label class="field"><span>یادداشت برای دفتر <span class="muted">(اختیاری)</span></span>
            <textarea v-model="note" rows="3" maxlength="500" placeholder="مثلا: موافقم، به شرط اینکه هزینه از بودجه فوق‌برنامه پرداخت شود"></textarea></label>
          <div class="dialog-actions">
            <button class="btn success" :disabled="saving" @click="decide(true)"><Icon name="check" :size="18" />موافقم</button>
            <button class="btn danger-soft" :disabled="saving" @click="decide(false)">مخالفم</button>
            <button class="btn ghost" @click="open = null">انصراف</button>
          </div>
        </template>
        <div v-else class="dialog-actions">
          <button v-if="open.status === 'forwarded'" class="btn primary" @click="markSeen(open)"><Icon name="check" :size="18" />دیدم</button>
          <button class="btn ghost" @click="open = null">بستن</button>
        </div>
      </div>
    </div>
  </div>
</template>
