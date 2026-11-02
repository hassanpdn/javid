<script setup>
// «نوبت‌ها»: one day's schedule, slot by slot, picked with the Jalali calendar (today by default), and the waiting
// list beside it. Free slots and the times an appointment fits are worked out by the server.
import { ref, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { clinicInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import DatePicker from "../components/core/DatePicker.vue"
import DayList from "./DayList.vue"

const emit = defineEmits(["open", "book", "message", "changed"])
const day = ref(clinicInfo.today), d = ref(null), wait = ref(null)
const load = async () => { d.value = await api("/dental/day?d=" + encodeURIComponent(day.value)) }
watch(day, () => { d.value = null; load().catch(() => {}) })
onMounted(() => retryable(async () => { await load(); wait.value = await api("/dental/waitlist") }))
const cmp = (a, b) => a.localeCompare(b)
const changed = () => { load().catch(() => {}); api("/dental/waitlist").then((w) => { wait.value = w }).catch(() => {}); emit("changed") }
</script>

<template>
  <div class="grid grid-cols-12 gap-6">
    <section class="card col-span-12 xl:col-span-8 flex flex-col gap-4">
      <div class="dt-toolbar">
        <div class="field" style="flex: 1 1 220px"><span>روز</span><DatePicker v-model="day" :min="'1400/01/01'" label="روز" /></div>
      </div>
      <Skeleton v-if="!d" kind="row" :count="8" />
      <template v-else>
        <h3 class="dt-group">{{ fa(d.date_text) }}</h3>
        <p v-if="d.closed" class="muted small">مطب در این روز تعطیل است.</p>
        <DayList v-else :rows="d.rows" :date="day" :past="cmp(day, clinicInfo.today) < 0" :future="cmp(day, clinicInfo.today) > 0"
                 @open="emit('open', $event)" @book="emit('book', $event)" @message="emit('message', $event)" @changed="changed" />
        <div v-if="d.cancelled.length" class="flex flex-col gap-1">
          <small class="muted">لغوشده: <template v-for="(a, i) in d.cancelled" :key="a.id">{{ i ? '، ' : '' }}{{ fa(a.time) }} {{ a.patient }}</template></small>
        </div>
      </template>
    </section>
    <section class="card col-span-12 xl:col-span-4 flex flex-col gap-3" data-tour="dt-wait">
      <div class="card-head">فهرست انتظار <span v-if="wait" class="count">{{ fa(wait.length) }}</span></div>
      <p class="muted small">کسانی که نوبت زودتر می‌خواهند. وقتی نوبتی لغو شد، به یکی از آن‌ها بدهید.</p>
      <Skeleton v-if="!wait" kind="row" :count="3" />
      <p v-else-if="!wait.length" class="muted small">کسی در فهرست انتظار نیست.</p>
      <ul v-else class="dt-mini">
        <li v-for="w in wait" :key="w.id">
          <span><button class="dt-link" @click="emit('open', w.patient_id)">{{ w.patient }}</button> · {{ w.service_text }}</span>
          <small class="muted">{{ fa(w.days) }} روز در انتظار<template v-if="w.note"> · {{ w.note }}</template> · <span dir="ltr">{{ fa(w.phone) }}</span></small>
          <button class="btn sm" style="align-self: flex-start" @click="emit('book', { patient_id: w.patient_id, patient: w.patient, service: w.service, waitlist_id: w.id, date: day })">
            <Icon name="calendar" :size="14" />نوبت دادن</button>
        </li>
      </ul>
    </section>
  </div>
</template>
