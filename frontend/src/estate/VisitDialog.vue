<script setup>
// Book a visit (listingId + requestId), or open one already booked (visitId) to send its messages and confirm it.
// The two confirmation messages, one for the customer and one for the owner, are built by the server; the agent copies
// and sends them, then marks the visit confirmed. Nothing is sent from here.
import { ref, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { agencyInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import DatePicker from "../components/core/DatePicker.vue"
import TimePicker from "../components/core/TimePicker.vue"

const props = defineProps({ listingId: Number, requestId: Number, visitId: Number, title: String })
const emit = defineEmits(["close", "done"])
const date = ref(agencyInfo.today), time = ref("17:30"), busy = ref(false), error = ref(""), drafts = ref(null), when = ref(""), id = ref(props.visitId)
onMounted(async () => { if (props.visitId) drafts.value = await api(`/estate/visits/${props.visitId}/drafts`) })
async function book() {
  busy.value = true; error.value = ""
  try {
    const r = await api("/estate/visits", { listing_id: props.listingId, request_id: props.requestId, date: date.value, time: time.value })
    drafts.value = r.drafts; when.value = r.when; id.value = r.id
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function confirm() {
  busy.value = true
  try { await api(`/estate/visits/${id.value}/confirm`, {}); toast({ tone: "success", title: "بازدید تأیید شد" }); emit("done") }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
const copy = async (t) => { try { await navigator.clipboard.writeText(t); toast({ tone: "success", title: "متن کپی شد" }) } catch {} }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" v-pop role="dialog" aria-label="بازدید">
      <div class="dialog-head"><div><h3>بازدید</h3><small class="muted">{{ fa(title || '') }}</small></div><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <template v-if="!drafts">
        <div class="es-grid2">
          <DatePicker v-model="date" :min="agencyInfo.today" label="روز بازدید" />
          <TimePicker v-model="time" label="ساعت بازدید" />
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions"><button class="btn primary" :disabled="busy || !date || !time" @click="book"><Icon name="calendar" :size="18" />ثبت بازدید</button></div>
      </template>
      <template v-else>
        <p v-if="when" class="check ok small"><Icon name="check" :size="14" /><span>بازدید {{ fa(when) }} ثبت شد. این دو پیام را بفرستید و پس از جواب، بازدید را تأیید کنید.</span></p>
        <div v-for="k in ['customer', 'owner']" :key="k" class="es-msg">
          <div class="es-row-top"><b>{{ k === 'customer' ? 'برای متقاضی' : 'برای مالک' }}</b><span dir="ltr" class="muted small">{{ fa(drafts[k + '_phone']) }}</span></div>
          <p class="ai-draft">{{ fa(drafts[k]) }}</p>
          <button class="btn ghost sm" @click="copy(drafts[k])"><Icon name="file" :size="14" />کپی</button>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions"><button class="btn primary" :disabled="busy" @click="confirm"><Icon name="check" :size="18" />هر دو تأیید کردند</button>
          <button class="btn ghost" @click="emit('done')">بعداً</button></div>
      </template>
    </div>
  </div>
</template>
