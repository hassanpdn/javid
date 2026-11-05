<script setup>
// Registration in a class of one station: its classes (this term's only in its first two weeks, then the next term's)
// with days, hour, teacher and free seats; one click registers. Then the fee, with a payment there and then.
// spec: { student_id, course, class_id? (already chosen, e.g. from the placement test), name? }.
import { ref, reactive, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ spec: Object })
const emit = defineEmits(["close", "saved"])
const d = ref(null), done = ref(null), busy = ref(false), pay = reactive({ amount: "", method: "card" })
onMounted(async () => {
  try { d.value = await api(`/lang/courses/${props.spec.course}/classes`) } catch (e) { toast({ tone: "danger", title: e.message }); emit("close"); return }
  if (props.spec.class_id) { const c = d.value.classes.find((x) => x.id === props.spec.class_id); if (c) enrol(c) }
})
async function enrol(c) {
  busy.value = true
  try { done.value = await api("/lang/enroll", { student_id: props.spec.student_id, class_id: c.id }); pay.amount = String(done.value.fee) }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
const digits = (s) => Number(String(s).replace(/[۰-۹]/g, (x) => "۰۱۲۳۴۵۶۷۸۹".indexOf(x)).replace(/[^\d]/g, "")) || 0
async function paid() {
  busy.value = true
  try { const r = await api(`/lang/students/${props.spec.student_id}/payments`, { enrollment_id: done.value.enrollment_id, amount: digits(pay.amount), method: pay.method })
        toast({ tone: "success", title: "پرداخت ثبت شد", body: "مانده: " + fa(r.left_text) }); emit("saved") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
const METHODS = { card: "کارت‌خوان", cash: "نقد", transfer: "کارت به کارت" }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" v-pop role="dialog" aria-label="ثبت‌نام در کلاس">
      <div class="dialog-head"><h3>ثبت‌نام<template v-if="d"> در {{ d.course }}</template></h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <Skeleton v-if="!d" kind="row" :count="3" />
      <template v-else-if="!done">
        <p v-if="!d.classes.length" class="muted small">برای این ترم آموزشی هنوز کلاسی تعریف نشده است.</p>
        <ul class="lg-opts">
          <li v-for="c in d.classes" :key="c.id"><span><b>{{ c.pair_text }} ساعت {{ fa(c.time) }}</b><small class="muted">{{ fa(c.term_name) }} · {{ c.teacher }} · {{ fa(c.room_name) }} · {{ fa(c.free) }} جای خالی</small></span>
            <button class="btn primary sm" :disabled="busy || c.free <= 0" @click="enrol(c)">ثبت‌نام</button></li>
        </ul>
      </template>
      <template v-else>
        <p class="lg-next"><Icon name="check" :size="20" /><span>ثبت‌نام شد: <b>{{ done.class.course_name }}</b>، {{ done.class.pair_text }} ساعت {{ fa(done.class.time) }} با {{ done.class.teacher }}. شهریه {{ fa(done.fee_text) }}.</span></p>
        <form class="k-pay" @submit.prevent="paid">
          <input v-model="pay.amount" inputmode="numeric" aria-label="مبلغ پرداخت">
          <select v-model="pay.method" class="k-select" aria-label="روش پرداخت"><option v-for="(t, k) in METHODS" :key="k" :value="k">{{ t }}</option></select>
          <button class="btn primary sm" :disabled="busy || !digits(pay.amount)">ثبت پرداخت</button>
        </form>
        <div class="dialog-actions"><button class="btn" @click="emit('saved')">بعداً می‌پردازد</button></div>
      </template>
    </div>
  </div>
</template>
