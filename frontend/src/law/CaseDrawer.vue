<script setup>
// One case in a side drawer: client and court, every notice with its last day («از کجا؟» shows how it was counted,
// Fridays and holidays included), marking what the notice asked for as done, the client's report, and the history.
import { ref, reactive, watch } from "vue"
import { api, fa, lawSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { toneOf } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "../fabric/HowTip.vue"

const props = defineProps({ id: Number })
const emit = defineEmits(["close", "changed"])
const d = ref(null), busy = ref(""), doing = ref(null), note = ref("")
const report = reactive({ open: false, text: "", checked: null, phone: "" })
const lawyer = lawSession.user.role !== "secretary"
const load = async () => { d.value = await api(`/law/cases/${props.id}`) }
watch(() => props.id, () => { d.value = null; report.open = false; load() }, { immediate: true })
async function done(n) {
  busy.value = "done" + n.id
  try {
    const r = await api(`/law/notices/${n.id}/done`, { note: note.value })
    toast({ tone: r.late ? "warning" : "success", title: "اقدام ثبت شد", body: r.late ? "پس از روز آخر مهلت ثبت شد و در بررسی‌ها دیده می‌شود." : "" })
    doing.value = null; note.value = ""; await load(); emit("changed")
  } catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
async function draft() {
  busy.value = "report"
  try { Object.assign(report, await api(`/law/cases/${props.id}/report/draft`, {}), { open: true }) }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
async function sent() {
  busy.value = "sent"
  try { await api(`/law/cases/${props.id}/report`, { text: report.text }); report.open = false; toast({ tone: "success", title: "گزارش ثبت شد" }); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
const copy = async (t) => { try { await navigator.clipboard.writeText(t); toast({ tone: "success", title: "متن کپی شد" }) } catch {} }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer k-drawer" v-drawer aria-label="پرونده">
      <div class="drawer-head"><b class="text-ink">پرونده</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="5" /></div>
        <template v-else>
          <section class="card k-head">
            <b class="k-title">{{ d.case.title }}</b>
            <div class="k-tags"><span class="tag">{{ d.case.field_text }}</span><span class="tag">{{ d.case.stage_text }}</span><span class="tag">{{ d.case.side }}</span></div>
            <dl class="k-dl">
              <dt>موکل</dt><dd>{{ d.case.client }} · <span dir="ltr">{{ fa(d.case.client_phone) }}</span></dd>
              <dt>طرف دعوا</dt><dd>{{ d.case.opponent || '-' }}</dd>
              <dt>مرجع</dt><dd>{{ d.case.court }}، شعبه‌ی {{ fa(d.case.branch) }}</dd>
              <dt>شماره</dt><dd dir="ltr" class="text-right">{{ fa(d.case.number) || '-' }}</dd>
              <dt>وکیل</dt><dd>{{ d.case.lawyer }}</dd>
            </dl>
          </section>

          <section class="card">
            <div class="card-head">ابلاغیه‌ها و مهلت‌ها</div>
            <p v-if="!d.notices.length" class="muted small">هنوز ابلاغیه‌ای ثبت نشده است.</p>
            <ul class="k-notices">
              <li v-for="n in d.notices" :key="n.id" :class="{ done: n.status === 'done' }">
                <div class="k-row-top"><b>{{ n.kind_text }}</b>
                  <span v-if="n.status === 'done'" class="tag k-t-success">انجام شد</span>
                  <span v-else-if="n.left !== undefined" :class="['tag', 'k-t-' + toneOf(n.left, n.kind)]">{{ fa(n.left_text) }}</span></div>
                <small class="muted">ابلاغ {{ fa(n.served_text) }}</small>
                <div v-if="n.deadline" class="k-deadline"><span>روز آخر {{ n.todo }}: <b>{{ fa(n.deadline_text) }}</b></span><HowTip v-if="n.how" :lines="n.how" /></div>
                <div v-if="n.hearing" class="k-deadline"><span>جلسه: <b>{{ fa(n.hearing_text) }}</b></span></div>
                <small v-if="n.status === 'done'" class="muted">{{ n.done_by_name }}، {{ fa(n.done_text) }}<template v-if="n.note"> · {{ fa(n.note) }}</template></small>
                <template v-else-if="lawyer">
                  <form v-if="doing === n.id" class="k-done" @submit.prevent="done(n)">
                    <input v-model="note" maxlength="300" :placeholder="n.kind === 'hearing' ? 'مثلاً جلسه برگزار شد، وقت بعدی داده شد' : 'مثلاً دادخواست تجدیدنظر تقدیم شد'" aria-label="یادداشت">
                    <button class="btn primary sm" :disabled="busy === 'done' + n.id">ثبت</button><button type="button" class="btn ghost sm" @click="doing = null">انصراف</button>
                  </form>
                  <button v-else class="btn sm k-done-btn" @click="doing = n.id; note = ''"><Icon name="check" :size="14" />{{ n.kind === 'hearing' ? 'جلسه برگزار شد' : n.todo + ' انجام شد' }}</button>
                </template>
              </li>
            </ul>
          </section>

          <section v-if="lawyer" class="card">
            <div class="card-head"><span class="grow">گزارش به موکل <small v-if="d.report.last">آخرین گزارش {{ fa(d.report.last) }}</small></span></div>
            <template v-if="report.open">
              <textarea v-model="report.text" rows="7" class="k-text ai-draft" aria-label="متن گزارش"></textarea>
              <p v-if="report.checked === false" class="check warn small"><Icon name="alert" :size="14" /><span>متن دستیار با تاریخ‌های پرونده جور نبود؛ متن ساده با همان تاریخ‌ها جایگزین شد.</span></p>
              <div class="btn-row"><button class="btn sm" @click="copy(report.text)"><Icon name="file" :size="14" />کپی متن</button>
                <button class="btn primary sm" :disabled="busy === 'sent'" @click="sent">برای موکل فرستادم</button><button class="btn ghost sm" @click="report.open = false">بستن</button></div>
            </template>
            <template v-else>
              <p class="muted small">آخرین وضعیت پرونده به زبان ساده برای موکل. دستیار متن را می‌نویسد و شما آن را می‌خوانید و می‌فرستید.</p>
              <button class="btn sm" :disabled="busy === 'report'" @click="draft"><Icon name="sparkles" :size="14" />{{ busy === 'report' ? 'در حال نوشتن…' : 'نوشتن گزارش' }}</button>
            </template>
          </section>

          <section v-if="d.history.length" class="card">
            <div class="card-head">سابقه‌ی پرونده</div>
            <ul class="k-mini"><li v-for="e in d.history" :key="e.id"><span>{{ fa(e.text) }}</span><small class="muted">{{ e.who }} · {{ fa(e.day) }} {{ fa(e.time) }}</small></li></ul>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>
