<script setup>
// A message for a patient, drafted for the secretary to read, copy and send from the clinic's phone. Nothing is sent
// from here. kind "reminder": an appointment's reminder (written by code), then «بیمار تأیید کرد». kind "followup":
// the follow-up of a plan not started (written by the assistant, its numbers checked), then what came of it.
import { ref, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ spec: Object })
const emit = defineEmits(["close", "done"])
const d = ref(null), text = ref(""), busy = ref(false), note = ref("")
onMounted(async () => {
  try {
    d.value = props.spec.kind === "reminder" ? await api(`/dental/appointments/${props.spec.appt_id}/reminder`) : await api(`/dental/plans/${props.spec.plan_id}/followup/draft`, {})
    text.value = d.value.text
  } catch (e) { toast({ tone: "danger", title: e.message }); emit("close") }
})
const copy = async () => { try { await navigator.clipboard.writeText(text.value); toast({ tone: "success", title: "متن کپی شد" }) } catch {} }
async function act(body, path, title) {
  busy.value = true
  try { await api(path, body); toast({ tone: "success", title }); emit("done") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
const confirmed = () => act({ status: "confirmed" }, `/dental/appointments/${props.spec.appt_id}/status`, "نوبت تأیید شد")
const contact = (kind) => act({ kind, text: note.value }, `/dental/plans/${props.spec.plan_id}/contact`, "ثبت شد")
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog wide" v-pop role="dialog" :aria-label="spec.kind === 'reminder' ? 'پیام یادآوری' : 'پیام پیگیری'">
      <div class="dialog-head"><h3>{{ spec.kind === 'reminder' ? 'پیام یادآوری نوبت' : 'پیام پیگیری طرح درمان' }}</h3>
        <button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <Skeleton v-if="!d" :lines="5" />
      <template v-else>
        <p class="muted small">متن را بخوانید، اگر لازم است تغییر دهید و از تلفن مطب برای <span dir="ltr">{{ fa(d.phone) }}</span> بفرستید.</p>
        <textarea v-model="text" rows="7" class="k-text ai-draft" aria-label="متن پیام"></textarea>
        <p v-if="d.checked === false" class="check warn small"><Icon name="alert" :size="14" /><span>متن دستیار با اطلاعات طرح جور نبود؛ متن ساده جایگزین شد.</span></p>
        <template v-if="spec.kind === 'reminder'">
          <div class="dialog-actions"><button class="btn" @click="copy"><Icon name="file" :size="16" />کپی متن</button>
            <button class="btn primary" :disabled="busy" @click="confirmed"><Icon name="check" :size="16" />بیمار تأیید کرد</button></div>
        </template>
        <template v-else>
          <label class="field"><span>یادداشت (اختیاری)</span><input v-model="note" maxlength="300" placeholder="مثلاً گفت آخر ماه تماس می‌گیرد"></label>
          <div class="dialog-actions"><button class="btn" @click="copy"><Icon name="file" :size="16" />کپی متن</button>
            <button class="btn primary" :disabled="busy" @click="contact('sent')">پیام را فرستادم</button>
            <button class="btn" :disabled="busy" @click="contact('call')">تلفنی صحبت کردم</button>
            <button class="btn ghost" :disabled="busy" @click="contact('declined')">بیمار نمی‌خواهد</button></div>
        </template>
      </template>
    </div>
  </div>
</template>
