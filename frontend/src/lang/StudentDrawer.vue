<script setup>
// One learner in a side drawer, for the office: the road (compact), the enrolments with what is left of each fee
// («از کجا؟») and a payment, the messages a person sends (registration, fee, absences, placement), the placement test
// for someone without a class, past tests, calls and the history.
import { ref, reactive, computed, watch } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "../fabric/HowTip.vue"
import RoadMap from "./RoadMap.vue"

const props = defineProps({ id: Number })
const emit = defineEmits(["close", "changed", "message", "enroll", "placement"])
const d = ref(null), picked = ref(null), pay = reactive({ amount: "", method: "card", enrollment: null }), busy = ref(false)
const load = async () => {
  d.value = await api(`/lang/students/${props.id}`)
  picked.value = d.value.road.stations.find((s) => s.state === "current" || s.state === "next")?.key
  pay.enrollment = d.value.enrollments.find((e) => e.left > 0)?.id || null
}
watch(() => props.id, () => { d.value = null; load() }, { immediate: true })
const digits = (s) => Number(String(s).replace(/[۰-۹]/g, (x) => "۰۱۲۳۴۵۶۷۸۹".indexOf(x)).replace(/[^\d]/g, "")) || 0
const owing = computed(() => d.value?.enrollments.filter((e) => e.left > 0) || [])
async function paid() {
  busy.value = true
  try { const r = await api(`/lang/students/${props.id}/payments`, { enrollment_id: pay.enrollment, amount: digits(pay.amount), method: pay.method })
        toast({ tone: "success", title: "پرداخت ثبت شد", body: "مانده: " + fa(r.left_text) }); pay.amount = ""; await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "مبلغ را درست بنویسید" : e.message }) } finally { busy.value = false }
}
const hasNow = computed(() => d.value?.enrollments.some((e) => e.status === "active"))
const hasNext = computed(() => d.value?.enrollments.some((e) => e.status === "registered"))
const nextKey = computed(() => d.value?.road.next?.key)
const METHODS = { card: "کارت‌خوان", cash: "نقد", transfer: "کارت به کارت" }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer k-drawer" v-drawer aria-label="پرونده‌ی زبان‌آموز">
      <div class="drawer-head"><b class="text-ink">پرونده‌ی زبان‌آموز</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="6" /></div>
        <template v-else>
          <section class="card k-head">
            <b class="k-title">{{ d.road.student.name }}</b>
            <div class="k-tags"><span class="tag" dir="ltr">{{ fa(d.road.student.phone) }}</span><span class="tag">از {{ fa(d.road.student.created_text) }}</span>
              <span class="tag k-t-info">{{ fa(d.road.pct) }}٪ مسیر</span></div>
            <div class="btn-row" style="margin-top: 6px">
              <button v-if="!hasNext && nextKey" class="btn primary sm" @click="emit('enroll', { student_id: d.road.student.id, course: nextKey, name: d.road.student.name })"><Icon name="plus" :size="14" />ثبت‌نام ترم بعد</button>
              <button v-if="!hasNow && !hasNext" class="btn sm" @click="emit('placement', d.road.student.id)"><Icon name="check" :size="14" />آزمون تعیین سطح</button>
              <button v-if="hasNow && !hasNext && nextKey" class="btn sm" @click="emit('message', { student_id: d.road.student.id, kind: 'renew' })"><Icon name="message" :size="14" />یادآوری ثبت‌نام</button>
              <button v-if="d.tests.some((t) => t.placed_name) && !hasNow && !hasNext" class="btn sm" @click="emit('message', { student_id: d.road.student.id, kind: 'placed' })"><Icon name="message" :size="14" />پیام نتیجه‌ی آزمون</button>
            </div>
          </section>

          <section class="card"><div class="card-head">مسیر</div><RoadMap :stations="d.road.stations" v-model="picked" compact :detail="false" /></section>

          <section class="card">
            <div class="card-head">شهریه</div>
            <p v-if="!d.enrollments.length" class="muted small">ثبت‌نامی در این ترم و ترم بعد نیست.</p>
            <ul class="k-mini"><li v-for="e in d.enrollments" :key="e.id">
              <div class="k-row-top"><span>{{ e.course }} · {{ fa(e.term) }}</span><span :class="['tag', e.left > 0 ? 'k-t-warning' : 'k-t-success']">{{ e.left > 0 ? 'مانده ' + fa(e.left_text) : 'پرداخت شد' }}</span></div>
              <small class="muted flex items-center gap-1">شهریه {{ fa(e.fee_text) }} <HowTip :lines="e.how" /></small></li></ul>
            <form v-if="owing.length" class="k-pay" @submit.prevent="paid" style="margin-top: 10px">
              <select v-if="owing.length > 1" v-model="pay.enrollment" class="k-select" aria-label="کدام شهریه"><option v-for="e in owing" :key="e.id" :value="e.id">{{ e.course }}</option></select>
              <input v-model="pay.amount" inputmode="numeric" placeholder="مبلغ به تومان" aria-label="مبلغ پرداخت">
              <select v-model="pay.method" class="k-select" aria-label="روش پرداخت"><option v-for="(t, k) in METHODS" :key="k" :value="k">{{ t }}</option></select>
              <button class="btn primary sm" :disabled="busy || !digits(pay.amount)">ثبت پرداخت</button>
            </form>
            <div v-if="owing.length" class="btn-row" style="margin-top: 8px"><button class="btn ghost sm" @click="emit('message', { student_id: d.road.student.id, kind: 'unpaid' })"><Icon name="message" :size="14" />پیام شهریه</button></div>
          </section>

          <section v-if="d.road.current" class="card">
            <div class="card-head">این ترم</div>
            <div class="lg-facts">
              <div><b>{{ fa(d.road.current.attendance.counts.absent) }}</b><small>غیبت</small></div>
              <div><b>{{ fa(d.road.current.so_far ?? "—") }}</b><small>نمره تا این‌جا</small></div>
              <div><b>{{ fa(d.road.current.sessions) }}/۲۰</b><small>جلسه</small></div>
            </div>
            <div v-if="d.road.current.attendance.counts.absent >= 3" class="btn-row" style="margin-top: 8px"><button class="btn ghost sm" @click="emit('message', { student_id: d.road.student.id, kind: 'absent' })"><Icon name="message" :size="14" />پیام غیبت</button></div>
          </section>

          <section v-if="d.tests.length" class="card">
            <div class="card-head">آزمون‌ها</div>
            <ul class="k-mini"><li v-for="t in d.tests" :key="t.id"><div class="k-row-top"><span>{{ fa(t.title) }}</span><b>{{ fa(t.score) }}</b></div>
              <small class="muted">{{ fa(t.date_text) }}<template v-if="t.placed_name"> · سطح: {{ t.placed_name }}</template></small></li></ul>
          </section>

          <section v-if="d.contacts.length || d.history.length" class="card">
            <div class="card-head">سابقه</div>
            <ul class="k-mini">
              <li v-for="c in d.contacts" :key="'c' + c.id"><span>{{ fa(c.text) }}</span><small class="muted">{{ fa(c.date_text) }}</small></li>
              <li v-for="e in d.history" :key="e.id"><span>{{ fa(e.text) }}</span><small class="muted">{{ e.who }} · {{ fa(e.day) }} {{ fa(e.time) }}</small></li>
            </ul>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>
