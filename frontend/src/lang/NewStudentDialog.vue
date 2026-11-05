<script setup>
// «زبان‌آموز جدید»: a name and a mobile number, then the next step: the placement test here and now (on this computer
// or a tablet in the office), or a level the learner already knows, which goes on to registration (EnrollDialog).
import { ref, reactive } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { instInfo } from "./lib.js"
import Icon from "../components/Icon.vue"

const emit = defineEmits(["close", "saved", "placement", "enroll"])
const f = reactive({ name: "", phone: "" }), sid = ref(null), busy = ref(false), course = ref("S-1")
async function save() {
  busy.value = true
  try { sid.value = (await api("/lang/students", { name: f.name, phone: f.phone })).id; toast({ tone: "success", title: "پرونده باز شد", body: f.name }) }
  catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "نام و شماره‌ی همراه را درست بنویسید" : e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form v-if="!sid" class="dialog" v-pop role="dialog" aria-label="زبان‌آموز جدید" @submit.prevent="save">
      <div class="dialog-head"><h3>زبان‌آموز جدید</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <label class="field"><span>نام و نام خانوادگی</span><input v-model="f.name" maxlength="60" autocomplete="off"></label>
      <label class="field"><span>شماره‌ی همراه</span><input v-model="f.phone" inputmode="tel" dir="ltr" placeholder="09121234567"></label>
      <div class="dialog-actions"><button class="btn primary" :disabled="busy || f.name.trim().length < 3 || f.phone.trim().length < 10"><Icon name="check" :size="18" />باز کردن پرونده</button></div>
    </form>
    <div v-else class="dialog" v-pop role="dialog" aria-label="سطح زبان‌آموز">
      <div class="dialog-head"><h3>سطح {{ f.name }}</h3><button type="button" class="icon-btn" @click="emit('saved', sid)" aria-label="بستن"><Icon name="x" /></button></div>
      <button type="button" class="lg-test open" style="cursor: pointer; text-align: right; font: inherit" @click="emit('placement', sid)">
        <span class="tint" style="background: rgba(255,255,255,.18); color: #fff"><Icon name="check" :size="22" /></span>
        <span class="lg-test-body"><b>آزمون تعیین سطح، همین حالا</b><small>۱۸ پرسش، ۲۰ دقیقه، از Starter تا Advanced. برنامه سطح و کلاس‌های مناسب را می‌گوید.</small></span></button>
      <div class="field"><span>یا سطحش را می‌دانید</span>
        <div class="flex gap-2 flex-wrap"><select v-model="course" class="k-select grow"><option v-for="t in instInfo.terms" :key="t.key" :value="t.key">{{ fa(t.fa) }} · {{ t.name }}</option></select>
          <button type="button" class="btn" @click="emit('enroll', { student_id: sid, course, name: f.name })">کلاس‌های این سطح</button></div></div>
    </div>
  </div>
</template>
