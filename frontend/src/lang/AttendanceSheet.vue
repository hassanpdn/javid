<script setup>
// Attendance of one session, made for a phone in class: each learner is a tile; one tap cycles حاضر, با تأخیر, غایب.
// «همه حاضر» marks the rest present. The last sessions are chips on top, for a session written late.
import { ref, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { ATT } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ classId: Number, day: { type: String, default: null } })
const emit = defineEmits(["close", "saved"])
const d = ref(null), marks = ref({}), busy = ref(false)
const load = async (day) => {
  d.value = await api(`/lang/classes/${props.classId}/attendance` + (day ? `?day=${day}` : ""))
  marks.value = Object.fromEntries(d.value.rows.map((r) => [r.student_id, r.status]))
}
onMounted(() => load(props.day).catch((e) => toast({ tone: "danger", title: e.message })))
const NEXT = { undefined: "present", null: "present", present: "late", late: "absent", absent: "present" }
const LETTER = { present: "ح", late: "ت", absent: "غ" }
const cycle = (sid) => { marks.value[sid] = NEXT[marks.value[sid]] }
const allPresent = () => { for (const k in marks.value) if (!marks.value[k]) marks.value[k] = "present" }
const left = () => Object.values(marks.value).filter((v) => !v).length
async function save() {
  busy.value = true
  try { const r = await api(`/lang/classes/${props.classId}/attendance`, { day: d.value.day, marks: marks.value })
        toast({ tone: "success", title: "حضور و غیاب ثبت شد", body: `${d.value.day_text}، ${fa(r.absent)} غایب` }); emit("saved") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog" v-pop role="dialog" aria-label="حضور و غیاب" @submit.prevent="save" style="max-width: 640px">
      <div class="dialog-head"><h3>حضور و غیاب<template v-if="d"> · جلسه‌ی {{ fa(d.n) }}</template></h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <Skeleton v-if="!d" :lines="4" />
      <template v-else>
        <div class="lg-days" role="tablist" aria-label="جلسه">
          <button v-for="x in d.days" :key="x.day" type="button" role="tab" :aria-selected="x.day === d.day" :class="{ on: x.day === d.day }" @click="load(x.day)">{{ fa(x.text) }}</button>
        </div>
        <p class="muted small" style="margin: 0">روی هر نام بزنید: یک بار حاضر، دو بار با تأخیر، سه بار غایب.<template v-if="d.written"> این جلسه قبلاً ثبت شده است؛ تغییرها جای قبلی را می‌گیرند.</template></p>
        <div class="lg-att">
          <button v-for="r in d.rows" :key="r.student_id" type="button" :class="marks[r.student_id]" :aria-label="r.name + '، ' + (ATT[marks[r.student_id]] || 'ثبت نشده')" @click="cycle(r.student_id)">
            <i>{{ LETTER[marks[r.student_id]] || "؟" }}</i><span>{{ r.name }}</span></button>
        </div>
        <div class="dialog-actions">
          <button v-if="left()" type="button" class="btn" @click="allPresent"><Icon name="check" :size="16" />بقیه حاضر</button>
          <button class="btn primary" :disabled="busy || left() > 0"><Icon name="check" :size="18" />ثبت<template v-if="left()"> ({{ fa(left()) }} نفر مانده)</template></button>
        </div>
      </template>
    </form>
  </div>
</template>
