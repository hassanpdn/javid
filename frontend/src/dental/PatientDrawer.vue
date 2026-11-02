<script setup>
// One patient in a side drawer: phone and how often they did not come, what they owe («از کجا؟» shows the sum) and a
// payment, their treatment plans step by step (each step can be booked; a plan not started has its follow-up
// message), the dentist's new plan, appointments, follow-up calls and the history.
import { ref, reactive, watch } from "vue"
import { api, fa, dentalSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { clinicInfo, STATUS_TONE } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "../fabric/HowTip.vue"

const props = defineProps({ id: Number })
const emit = defineEmits(["close", "changed", "book", "message"])
const owner = dentalSession.user.role === "owner"
const d = ref(null), busy = ref(""), pay = reactive({ amount: "", method: "card" })
const plan = reactive({ open: false, title: "", items: [{ service: "filling", tooth: "" }] })
const load = async () => { d.value = await api(`/dental/patients/${props.id}`) }
watch(() => props.id, () => { d.value = null; load() }, { immediate: true })
const digits = (s) => Number(String(s).replace(/[۰-۹]/g, (x) => "۰۱۲۳۴۵۶۷۸۹".indexOf(x)).replace(/[^\d]/g, "")) || 0
async function paid() {
  busy.value = "pay"
  try { const r = await api(`/dental/patients/${props.id}/payments`, { amount: digits(pay.amount), method: pay.method }); toast({ tone: "success", title: "پرداخت ثبت شد", body: "مانده: " + fa(r.left_text) })
        pay.amount = ""; await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "مبلغ را درست بنویسید" : e.message }) } finally { busy.value = "" }
}
async function addPlan() {
  busy.value = "plan"
  try { await api("/dental/plans", { patient_id: props.id, title: plan.title, items: plan.items }); toast({ tone: "success", title: "طرح درمان ثبت شد" })
        Object.assign(plan, { open: false, title: "", items: [{ service: "filling", tooth: "" }] }); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "نام طرح و مراحل را بنویسید" : e.message }) } finally { busy.value = "" }
}
const waiting = (p) => p.status !== "declined" && !p.done_count && !p.next
const METHODS = { card: "کارت‌خوان", cash: "نقد", transfer: "کارت به کارت" }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer dt-drawer" v-drawer aria-label="پرونده‌ی بیمار">
      <div class="drawer-head"><b class="text-ink">پرونده‌ی بیمار</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="5" /></div>
        <template v-else>
          <section class="card dt-head">
            <b class="dt-title">{{ d.patient.name }}</b>
            <div class="dt-tags"><span class="tag" dir="ltr">{{ fa(d.patient.phone) }}</span><span class="tag">از {{ fa(d.patient.created_text) }}</span>
              <span v-if="d.noshows" class="tag dt-t-warning">{{ fa(d.noshows) }} بار نیامده</span>
              <span v-for="w in d.waiting" :key="w.id" class="tag dt-t-info">در فهرست انتظار: {{ w.service_text }}</span></div>
            <div class="btn-row"><button class="btn sm" @click="emit('book', { patient_id: d.patient.id, patient: d.patient.name })"><Icon name="calendar" :size="14" />نوبت جدید</button></div>
          </section>

          <section class="card">
            <div class="dt-balance"><span>مانده‌ی حساب: <b :class="{ 'dt-owe': d.balance.left > 0 }">{{ fa(d.balance.left_text) }}</b></span><HowTip :lines="d.balance.how" /></div>
            <form class="dt-pay" @submit.prevent="paid">
              <input v-model="pay.amount" inputmode="numeric" placeholder="مبلغ به تومان" aria-label="مبلغ پرداخت">
              <select v-model="pay.method" class="dt-select" aria-label="روش پرداخت"><option v-for="(t, k) in METHODS" :key="k" :value="k">{{ t }}</option></select>
              <button class="btn primary sm" :disabled="busy === 'pay' || !digits(pay.amount)">ثبت پرداخت</button>
            </form>
          </section>

          <section class="card">
            <div class="card-head"><span class="grow">طرح‌های درمان</span><button v-if="owner && !plan.open" class="btn ghost sm" @click="plan.open = true"><Icon name="plus" :size="14" />طرح جدید</button></div>
            <form v-if="plan.open" class="flex flex-col gap-2" @submit.prevent="addPlan">
              <label class="field"><span>نام طرح</span><input v-model="plan.title" maxlength="60" placeholder="مثلاً دو روکش"></label>
              <div v-for="(it, i) in plan.items" :key="i" class="dt-item-row">
                <select v-model="it.service" class="dt-select" :aria-label="'خدمت مرحله‌ی ' + (i + 1)"><option v-for="s in clinicInfo.services" :key="s.key" :value="s.key">{{ s.name }} · {{ fa(s.price_text) }}</option></select>
                <input v-model="it.tooth" maxlength="6" placeholder="دندان" :aria-label="'دندان مرحله‌ی ' + (i + 1)" class="dt-search">
                <button type="button" class="icon-btn" :disabled="plan.items.length === 1" @click="plan.items.splice(i, 1)" aria-label="حذف مرحله"><Icon name="x" :size="16" /></button>
              </div>
              <div class="btn-row"><button type="button" class="btn ghost sm" @click="plan.items.push({ service: 'filling', tooth: '' })"><Icon name="plus" :size="14" />مرحله</button>
                <button class="btn primary sm" :disabled="busy === 'plan' || plan.title.trim().length < 2">ثبت طرح</button><button type="button" class="btn ghost sm" @click="plan.open = false">انصراف</button></div>
            </form>
            <p v-if="!d.plans.length && !plan.open" class="muted small">طرح درمانی ثبت نشده است.</p>
            <div v-for="p in d.plans" :key="p.id" class="dt-plan">
              <div class="dt-row-top"><b>{{ p.title }} · {{ fa(p.total_text) }}</b>
                <span v-if="p.status === 'declined'" class="tag dt-t-secondary">بیمار نخواست</span>
                <span v-else-if="p.done_count === p.items.length" class="tag dt-t-success">تمام شد</span>
                <span v-else-if="waiting(p)" class="tag dt-t-warning">شروع نشده</span>
                <span v-else class="tag dt-t-info">{{ fa(p.done_count) }} از {{ fa(p.items.length) }}</span></div>
              <small class="muted">پیشنهاد {{ fa(p.created_text) }}<template v-if="p.last_contact"> · آخرین تماس {{ fa(p.last_contact_text) }}</template></small>
              <ul class="dt-items">
                <li v-for="it in p.items" :key="it.id"><b>{{ it.service_text }}{{ it.tooth ? "، دندان " + it.tooth : "" }}</b><span>{{ fa(it.price_text) }}</span>
                  <span v-if="it.status === 'done'" class="tag dt-t-success">{{ fa(it.done_text) }}</span>
                  <button v-else-if="p.status !== 'declined'" class="btn ghost sm" @click="emit('book', { patient_id: d.patient.id, patient: d.patient.name, service: it.service, plan_item_id: it.id })">نوبت این مرحله</button></li>
              </ul>
              <div v-if="waiting(p)" class="btn-row"><button class="btn sm" @click="emit('message', { kind: 'followup', plan_id: p.id })"><Icon name="message" :size="14" />پیام پیگیری</button></div>
            </div>
          </section>

          <section class="card">
            <div class="card-head">نوبت‌ها</div>
            <p v-if="!d.appointments.length" class="muted small">نوبتی ثبت نشده است.</p>
            <ul class="dt-mini"><li v-for="a in d.appointments" :key="a.id">
              <div class="dt-row-top"><span>{{ a.service_text }} · {{ fa(a.date_text) }} ساعت {{ fa(a.time) }}</span><span :class="['tag', 'dt-t-' + STATUS_TONE[a.status]]">{{ a.status_text }}</span></div>
              <small v-if="a.status === 'done'" class="muted">{{ fa(a.price_text) }}</small></li></ul>
          </section>

          <section v-if="d.payments.length" class="card">
            <div class="card-head">پرداخت‌ها</div>
            <ul class="dt-mini"><li v-for="p in d.payments" :key="p.id"><span>{{ fa(p.amount_text) }} · {{ p.method_text }}</span><small class="muted">{{ fa(p.date_text) }}</small></li></ul>
          </section>

          <section v-if="d.history.length" class="card">
            <div class="card-head">سابقه</div>
            <ul class="dt-mini"><li v-for="e in d.history" :key="e.id"><span>{{ fa(e.text) }}</span><small class="muted">{{ e.who }} · {{ fa(e.day) }} {{ fa(e.time) }}</small></li></ul>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>
