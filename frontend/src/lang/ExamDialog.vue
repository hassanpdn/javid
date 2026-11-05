<script setup>
// «آزمون آنلاین جدید» for a class: a title, how many questions, how many days it stays open and how many minutes it
// gives. The questions come from the bank of the class's level (and a few from the level below); code marks them.
import { reactive, ref } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"

const props = defineProps({ cls: Object })
const emit = defineEmits(["close", "saved"])
const f = reactive({ title: "", count: 8, days: 3, minutes: 15 }), busy = ref(false)
async function save() {
  busy.value = true
  try { await api("/lang/exams", { class_id: props.cls.id, ...f }); toast({ tone: "success", title: "آزمون باز شد", body: `زبان‌آموزان ${props.cls.course_name} آن را در پنل خود می‌بینند.` }); emit("saved") }
  catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "نام آزمون را بنویسید" : e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog" v-pop role="dialog" aria-label="آزمون آنلاین جدید" @submit.prevent="save">
      <div class="dialog-head"><h3>آزمون آنلاین جدید</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <p class="muted small" style="margin: 0">{{ cls.course_name }} · {{ cls.pair_text }} ساعت {{ fa(cls.time) }}. پرسش‌ها از بانک سطح همین کلاس انتخاب می‌شوند و نمره را خود برنامه می‌دهد.</p>
      <label class="field"><span>نام آزمون</span><input v-model="f.title" maxlength="60" placeholder="مثلاً آزمون درس‌های ۱۱ و ۱۲"></label>
      <div class="field"><span>تعداد پرسش</span><div class="lg-seg"><button v-for="n in [6, 8, 10]" :key="n" type="button" :class="{ on: f.count === n }" @click="f.count = n">{{ fa(n) }}</button></div></div>
      <div class="field"><span>وقت</span><div class="lg-seg"><button v-for="n in [10, 15, 20]" :key="n" type="button" :class="{ on: f.minutes === n }" @click="f.minutes = n">{{ fa(n) }} دقیقه</button></div></div>
      <div class="field"><span>باز بماند</span><div class="lg-seg"><button v-for="n in [1, 3, 7]" :key="n" type="button" :class="{ on: f.days === n }" @click="f.days = n">{{ fa(n) }} روز</button></div></div>
      <div class="dialog-actions"><button class="btn primary" :disabled="busy || f.title.trim().length < 3"><Icon name="sparkles" :size="18" />باز کردن آزمون</button></div>
    </form>
  </div>
</template>
