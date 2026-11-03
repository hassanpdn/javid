<script setup>
// «پایان روز» (the front desk and the manager): today's guest list for the police's guest registration (it is on
// the internet; the program does not send it, the desk copies it), and closing the day: tonight's price goes on the
// folio of every room in the house and the cash counted is set beside the day's cash payments.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { digits } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["changed"])
const police = ref(null), s = ref(null), counted = ref(""), note = ref(""), busy = ref(false)
const load = async () => { police.value = await api("/hotel/police"); s.value = await api("/hotel/close") }
onMounted(() => retryable(load))
const text = () => police.value.map((p) => `${p.guest} · کد ملی ${p.national_id} · اتاق ${p.room} · ${p.people} · ورود ${p.arrive} · خروج ${p.depart}${p.plate ? " · پلاک " + p.plate : ""}`).join("\n")
const copy = async () => { try { await navigator.clipboard.writeText(text()); toast({ tone: "success", title: "فهرست کپی شد" }) } catch {} }
async function close() {
  busy.value = true
  try {
    const r = await api("/hotel/close", { cash_counted: digits(counted.value), note: note.value })
    toast({ tone: r.diff ? "warning" : "success", title: `روز بسته شد؛ ${fa(r.posted)} شب ثبت شد`, body: r.diff ? `صندوق ${fa(r.diff_text)} ${r.diff < 0 ? "کم" : "زیاد"} است` : "صندوق درست بود" })
    await load(); emit("changed")
  } catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div class="grid grid-cols-12 gap-6">
    <section class="card col-span-12 xl:col-span-7 flex flex-col gap-3" data-tour="ht-police">
      <div class="card-head"><span class="grow">ورودهای امروز برای ثبت مسافران</span><button v-if="police?.length" class="btn ghost sm" @click="copy"><Icon name="file" :size="14" />کپی فهرست</button></div>
      <p class="muted small">سامانه‌ی ثبت مسافران پلیس روی اینترنت است و این برنامه چیزی به آن نمی‌فرستد. این فهرست را برای وارد کردن در آن کپی کنید.</p>
      <Skeleton v-if="!police" kind="row" :count="4" />
      <p v-else-if="!police.length" class="muted small">امروز هنوز کسی وارد نشده است.</p>
      <ul v-else class="k-mini"><li v-for="p in police" :key="p.id"><div class="k-row-top"><b>{{ p.guest }}</b><span class="tag">اتاق {{ fa(p.room) }}</span></div>
        <small class="muted">کد ملی <span dir="ltr">{{ fa(p.national_id) || '-' }}</span> · {{ fa(p.people) }} · ساعت {{ fa(p.time) }}<template v-if="p.plate"> · پلاک {{ fa(p.plate) }}</template>
          · <span :class="p.docs ? '' : 'k-late'">{{ p.docs ? 'مدارک دیده شد' : 'مدارک همراهان ثبت نشده' }}</span></small></li></ul>
    </section>
    <section class="card col-span-12 xl:col-span-5 flex flex-col gap-3" data-tour="ht-close">
      <div class="card-head">بستن روز</div>
      <Skeleton v-if="!s" :lines="4" />
      <template v-else-if="s.done">
        <p class="check ok small"><Icon name="check" :size="14" /><span>امروز بسته شده است: {{ fa(s.done.posted) }} شب ثبت شد.</span></p>
        <p class="small">صندوق: دریافت نقدی {{ fa(s.done.cash_expected.toLocaleString()) }}، شمارش {{ fa(s.done.cash_counted.toLocaleString()) }} تومان.</p>
      </template>
      <form v-else class="flex flex-col gap-3" @submit.prevent="close">
        <p class="small">امشب {{ fa(s.rooms) }} اتاق مهمان دارد؛ قیمت امشبشان ({{ fa(s.to_post_text) }}) به صورت‌حسابشان اضافه می‌شود. آخرین روز بسته‌شده: {{ fa(s.last) }}.</p>
        <p class="small">دریافت نقدی ثبت‌شده‌ی امروز: <b>{{ fa(s.cash_text) }}</b></p>
        <label class="field"><span>شمارش صندوق نقدی (تومان)</span><input v-model="counted" inputmode="numeric" required></label>
        <label class="field"><span>یادداشت</span><input v-model="note" maxlength="200" placeholder="اختیاری"></label>
        <button class="btn primary" :disabled="busy || !String(counted).trim()"><Icon name="check" :size="18" />بستن روز</button>
      </form>
    </section>
  </div>
</template>
