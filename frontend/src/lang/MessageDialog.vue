<script setup>
// A message a person sends from the institute's own phone: written by code from the learner's records (or handed in
// ready, e.g. after a class moved), editable here, copied with one click; «فرستادم» writes it into the learner's
// history. spec: { student_id, kind } or { text, title }.
import { ref, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ spec: Object })
const emit = defineEmits(["close", "done"])
const text = ref(props.spec.text || ""), info = ref(null), busy = ref(false)
const TITLES = { absent: "پیام غیبت", unpaid: "پیام شهریه", renew: "یادآوری ثبت‌نام ترم بعد", placed: "نتیجه‌ی آزمون تعیین سطح" }
onMounted(async () => {
  if (!props.spec.student_id) return
  try { info.value = await api(`/lang/students/${props.spec.student_id}/message?kind=${props.spec.kind}`); text.value = fa(info.value.text) }
  catch (e) { toast({ tone: "danger", title: e.message }); emit("close") }
})
async function copy() {
  try { await navigator.clipboard.writeText(text.value); toast({ tone: "success", title: "متن کپی شد" }) } catch { toast({ tone: "warning", title: "کپی نشد؛ متن را خودتان انتخاب کنید" }) }
}
async function sent() {
  if (!props.spec.student_id) { emit("done"); return }
  busy.value = true
  try { await api(`/lang/students/${props.spec.student_id}/contact`, { kind: "sent", text: TITLES[props.spec.kind] + " فرستاده شد" }); toast({ tone: "success", title: "در سابقه‌ی زبان‌آموز ثبت شد" }); emit("done") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" v-pop role="dialog" :aria-label="spec.title || TITLES[spec.kind]">
      <div class="dialog-head"><h3>{{ spec.title ? fa(spec.title) : TITLES[spec.kind] }}</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <p v-if="info" class="muted small" style="margin: 0">به {{ info.name }} · <span dir="ltr">{{ fa(info.phone) }}</span>. برنامه چیزی نمی‌فرستد؛ متن را بخوانید و از تلفن آموزشگاه بفرستید.</p>
      <p v-else-if="!spec.student_id" class="muted small" style="margin: 0">برنامه چیزی نمی‌فرستد؛ متن را در گروه کلاس یا با پیامک بفرستید.</p>
      <Skeleton v-if="spec.student_id && !info" :lines="4" />
      <textarea v-else v-model="text" rows="7" aria-label="متن پیام"></textarea>
      <div class="dialog-actions"><button class="btn" @click="copy"><Icon name="file" :size="16" />کپی متن</button>
        <button class="btn primary" :disabled="busy" @click="sent"><Icon name="send" :size="16" />فرستادم</button></div>
    </div>
  </div>
</template>
