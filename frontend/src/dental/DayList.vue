<script setup>
// A day's appointments, slot by slot. Each appointment: confirmed by the patient, done (the dentist only), did not
// come, or cancelled; the reminder message. In the full schedule an empty slot has «نوبت» to book it.
import { ref } from "vue"
import { api, fa, dentalSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { STATUS_TONE } from "./lib.js"
import Icon from "../components/Icon.vue"

const props = defineProps({ rows: Array, date: String, compact: Boolean, past: Boolean, future: Boolean })
const emit = defineEmits(["open", "book", "message", "changed"])
const owner = dentalSession.user.role === "owner"
const busy = ref(0)
async function set(a, status) {
  busy.value = a.id
  try { await api(`/dental/appointments/${a.id}/status`, { status }); toast({ tone: "success", title: "ثبت شد" }); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = 0 }
}
const live = (a) => a.status === "booked" || a.status === "confirmed"
</script>

<template>
  <p v-if="!rows.length" class="muted small">نوبتی نیست.</p>
  <ul v-else class="k-day">
    <li v-for="r in rows" :key="r.time" :class="['k-slot', { 'k-free-row': !r.appt }]">
      <span class="k-time">{{ fa(r.time) }}</span>
      <div v-if="r.appt" class="k-slot-body">
        <div class="k-slot-top">
          <button class="k-link" @click="emit('open', r.appt.patient_id)">{{ r.appt.patient }}</button>
          <span :class="['tag', 'k-t-' + STATUS_TONE[r.appt.status]]">{{ r.appt.status_text }}</span>
        </div>
        <small class="muted">{{ r.appt.service_text }} · {{ fa(r.appt.minutes) }} دقیقه</small>
        <div v-if="live(r.appt) && !compact" class="k-btns">
          <button v-if="r.appt.status === 'booked'" class="btn sm" :disabled="busy === r.appt.id" @click="set(r.appt, 'confirmed')"><Icon name="check" :size="14" />بیمار تأیید کرد</button>
          <button v-if="r.appt.status === 'booked'" class="btn ghost sm" @click="emit('message', { kind: 'reminder', appt_id: r.appt.id })">پیام یادآوری</button>
          <button v-if="owner && !future" class="btn sm" :disabled="busy === r.appt.id" @click="set(r.appt, 'done')">انجام شد</button>
          <button v-if="!future" class="btn ghost sm" :disabled="busy === r.appt.id" @click="set(r.appt, 'noshow')">نیامد</button>
          <button v-if="!past" class="btn ghost sm" :disabled="busy === r.appt.id" @click="set(r.appt, 'cancelled')">لغو</button>
        </div>
        <div v-else-if="live(r.appt) && compact" class="k-btns">
          <button v-if="owner" class="btn sm" :disabled="busy === r.appt.id" @click="set(r.appt, 'done')">انجام شد</button>
          <button class="btn ghost sm" :disabled="busy === r.appt.id" @click="set(r.appt, 'noshow')">نیامد</button>
        </div>
      </div>
      <div v-else class="k-slot-body k-free-line">
        <span class="k-free">خالی</span>
        <button v-if="!past" class="btn ghost sm" @click="emit('book', { date, time: r.time })"><Icon name="plus" :size="14" />نوبت</button>
      </div>
    </li>
  </ul>
</template>
