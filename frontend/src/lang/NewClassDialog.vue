<script setup>
// «کلاس جدید» (manager): the term, the station (its book), a teacher of that level, then only the hours that teacher
// comes and is free in that term, and the rooms still empty at that hour. The server checks it all again.
import { ref, reactive, computed, watch } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { instInfo } from "./lib.js"
import Icon from "../components/Icon.vue"

const props = defineProps({ term: { default: "next" } })
const emit = defineEmits(["close", "saved"])
const f = reactive({ term: props.term, course: "S-1", teacher_id: null, cell: null, room: null })
const teachers = ref([]), cells = ref(null), busy = ref(false)
api("/lang/teachers").then((r) => { teachers.value = r }).catch(() => {})
const level = computed(() => f.course.split("-")[0])
const fit = computed(() => teachers.value.filter((t) => t.levels.includes(level.value)))
watch(fit, (list) => { if (!list.some((t) => t.id === f.teacher_id)) f.teacher_id = list[0]?.id || null })
watch(() => [f.term, f.teacher_id], async () => {
  cells.value = null; f.cell = null; f.room = null
  if (!f.teacher_id) return
  try { cells.value = await api(`/lang/cells?term=${f.term}&teacher_id=${f.teacher_id}`) } catch { cells.value = [] }
}, { immediate: true })
const pick = (c) => { f.cell = c; f.room = c.rooms.reduce((a, b) => (b.seats > a.seats ? b : a)).room }
async function save() {
  busy.value = true
  try { const r = await api("/lang/classes", { term: f.term, course: f.course, teacher_id: f.teacher_id, pair: f.cell.pair, time: f.cell.time, room: f.room })
        toast({ tone: "success", title: "کلاس جدید ساخته شد", body: `${r.course_name}، ${r.pair_text} ساعت ${fa(r.time)}` }); emit("saved", r) }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog" v-pop role="dialog" aria-label="کلاس جدید" @submit.prevent="save">
      <div class="dialog-head"><h3>کلاس جدید</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="field"><span>ترم</span><div class="lg-seg"><button type="button" :class="{ on: f.term === 'current' }" @click="f.term = 'current'">این ترم</button><button type="button" :class="{ on: f.term === 'next' }" @click="f.term = 'next'">ترم بعد</button></div></div>
      <label class="field"><span>ترم آموزشی و کتاب</span>
        <select v-model="f.course" class="k-select"><option v-for="t in instInfo.terms" :key="t.key" :value="t.key">{{ fa(t.fa) }} · {{ t.name }}</option></select></label>
      <label class="field"><span>استاد</span>
        <select v-model="f.teacher_id" class="k-select" :disabled="!fit.length"><option v-for="t in fit" :key="t.id" :value="t.id">{{ t.name }}</option></select>
        <small v-if="teachers.length && !fit.length" class="muted">هیچ استادی این سطح را درس نمی‌دهد.</small></label>
      <div class="field"><span>روز و ساعت</span>
        <p v-if="f.teacher_id && cells === null" class="muted small">در حال دیدن ساعت‌های آزاد…</p>
        <p v-else-if="cells && !cells.length" class="muted small">این استاد در این ترم ساعت آزادی ندارد.</p>
        <div v-else-if="cells" class="k-times" role="radiogroup" aria-label="روز و ساعت">
          <button v-for="c in cells" :key="c.pair + c.time" type="button" role="radio" :aria-checked="f.cell === c" :class="{ on: f.cell === c }" @click="pick(c)">{{ c.pair_text }} {{ fa(c.time) }}</button></div></div>
      <label v-if="f.cell" class="field"><span>اتاق</span>
        <select v-model="f.room" class="k-select"><option v-for="r in f.cell.rooms" :key="r.room" :value="r.room">کلاس {{ fa(r.room) }} · {{ fa(r.seats) }} جا</option></select></label>
      <div class="dialog-actions"><button class="btn primary" :disabled="busy || !f.cell || !f.room"><Icon name="check" :size="18" />ساختن کلاس</button></div>
    </form>
  </div>
</template>
