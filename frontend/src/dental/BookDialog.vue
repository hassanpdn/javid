<script setup>
// «نوبت جدید»: the patient (searched by name or phone, or picked from the waiting list), the service, the day and a
// time it fits in (from the server, which knows the free slots and the length of each service).
// preset: what is already known, e.g. { date, time, fromWaitlist } from an empty hour, or { patient_id, service,
// plan_item_id } from a step of a treatment plan.
import { ref, reactive, computed, watch, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { clinicInfo, service } from "./lib.js"
import Icon from "../components/Icon.vue"
import DatePicker from "../components/core/DatePicker.vue"

const props = defineProps({ preset: { type: Object, default: () => ({}) } })
const emit = defineEmits(["close", "saved"])
const f = reactive({ patient_id: props.preset.patient_id || null, patient: props.preset.patient || "", service: props.preset.service || "checkup",
                     date: props.preset.date || clinicInfo.today, time: props.preset.time || "", plan_item_id: props.preset.plan_item_id || null,
                     waitlist_id: props.preset.waitlist_id || null })
const q = ref(""), found = ref([]), wait = ref([]), times = ref(null), closed = ref(false), busy = ref(false), error = ref("")
onMounted(async () => { if (props.preset.fromWaitlist) { try { wait.value = await api("/dental/waitlist") } catch {} } })
let timer
watch(q, (v) => { clearTimeout(timer); if (v.trim().length < 2) { found.value = []; return }
  timer = setTimeout(async () => { try { found.value = await api("/dental/patients?q=" + encodeURIComponent(v.trim())) } catch {} }, 250) })
const pick = (p) => { f.patient_id = p.id; f.patient = p.name; q.value = ""; found.value = [] }
const fromWait = (w) => { Object.assign(f, { patient_id: w.patient_id, patient: w.patient, service: w.service, waitlist_id: w.id }) }
const minutes = computed(() => service(f.service)?.minutes || 30)
async function loadTimes() {
  times.value = null
  try {
    const r = await api(`/dental/free?d=${encodeURIComponent(f.date)}&minutes=${minutes.value}`)
    times.value = r.times; closed.value = r.closed
    if (f.time && !r.times.includes(f.time)) f.time = ""
  } catch { times.value = [] }
}
watch(() => [f.date, f.service], loadTimes, { immediate: true })
async function save() {
  busy.value = true; error.value = ""
  try {
    await api("/dental/appointments", { patient_id: f.patient_id, service: f.service, date: f.date, time: f.time, plan_item_id: f.plan_item_id, waitlist_id: f.waitlist_id })
    toast({ tone: "success", title: "نوبت ثبت شد", body: `${f.patient}، ${fa(f.date)} ساعت ${fa(f.time)}` }); emit("saved")
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "خانه‌های لازم را پر کنید" : e.message; loadTimes() }
  finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog" v-pop role="dialog" aria-label="نوبت جدید" @submit.prevent="save">
      <div class="dialog-head"><h3>نوبت جدید</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div v-if="preset.fromWaitlist && wait.length && !f.patient_id" class="field"><span>از فهرست انتظار</span>
        <ul class="k-results"><li v-for="w in wait" :key="w.id"><button type="button" @click="fromWait(w)"><span>{{ w.patient }} · {{ w.service_text }}</span><small class="muted">{{ w.note }}</small></button></li></ul></div>
      <div class="field"><span>بیمار</span>
        <div v-if="f.patient_id" class="k-picked"><b>{{ f.patient }}</b><button v-if="!preset.patient_id" type="button" class="link small" @click="f.patient_id = null; f.waitlist_id = null">تغییر</button></div>
        <template v-else>
          <input v-model="q" placeholder="نام یا شماره‌ی همراه" aria-label="جستجوی بیمار">
          <ul v-if="found.length" class="k-results"><li v-for="p in found" :key="p.id"><button type="button" @click="pick(p)"><span>{{ p.name }}</span><small dir="ltr" class="muted">{{ fa(p.phone) }}</small></button></li></ul>
          <small v-else-if="q.trim().length >= 2" class="muted">بیماری پیدا نشد. اول «بیمار جدید» را بزنید.</small>
        </template></div>
      <label class="field"><span>خدمت</span>
        <select v-model="f.service" class="k-select" :disabled="!!f.plan_item_id"><option v-for="s in clinicInfo.services" :key="s.key" :value="s.key">{{ s.name }} · {{ fa(s.minutes) }} دقیقه</option></select></label>
      <div class="field"><span>روز</span><DatePicker v-model="f.date" :min="clinicInfo.today" label="روز نوبت" /></div>
      <div class="field"><span>ساعت</span>
        <p v-if="times === null" class="muted small">در حال دیدن وقت‌های خالی…</p>
        <p v-else-if="closed" class="muted small">مطب در این روز تعطیل است.</p>
        <p v-else-if="!times.length" class="muted small">در این روز وقت خالی برای {{ fa(minutes) }} دقیقه نیست.</p>
        <div v-else class="k-times" role="radiogroup" aria-label="ساعت">
          <button v-for="t in times" :key="t" type="button" role="radio" :aria-checked="f.time === t" :class="{ on: f.time === t }" @click="f.time = t">{{ fa(t) }}</button></div></div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions"><button class="btn primary" :disabled="busy || !f.patient_id || !f.time"><Icon name="check" :size="18" />ثبت نوبت</button></div>
    </form>
  </div>
</template>
