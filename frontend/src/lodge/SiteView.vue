<script setup>
// «متن سایت و قاعده‌ها» (the host edits, the helper reads): the website's words (one line under the name, the
// lodge's story, house rules, phone, how to pay and the card number shown after approval) and the booking rules
// (extra person, deposit, hours to pay it, the shortest stay with a weekend night).
import { ref, onMounted } from "vue"
import { api, fa, lodgeSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { digits } from "./lib.js"

const s = ref(null), busy = ref(false), error = ref("")
const host = lodgeSession.user.role === "host"
onMounted(async () => { s.value = await api("/lodge/site") })
async function save() {
  busy.value = true; error.value = ""
  try {
    await api("/lodge/site", { ...s.value, extra_person: digits(s.value.extra_person), deposit: digits(s.value.deposit), deposit_hours: digits(s.value.deposit_hours), min_weekend: digits(s.value.min_weekend) })
    toast({ tone: "success", title: "ذخیره شد؛ سایت همین حالا به‌روز است" })
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "خانه‌ها را درست پر کنید" : e.message } finally { busy.value = false }
}
</script>

<template>
  <form v-if="s" class="grid grid-cols-12 gap-6" @submit.prevent="save">
    <section class="card col-span-12 lg:col-span-7 flex flex-col gap-3">
      <div class="card-head">متن سایت</div>
      <label class="field"><span>یک جمله زیر نام</span><input v-model="s.tagline" maxlength="120" :disabled="!host"></label>
      <label class="field"><span>داستان اقامتگاه</span><textarea v-model="s.story" rows="5" maxlength="1200" class="k-text" :disabled="!host"></textarea></label>
      <label class="field"><span>قاعده‌های خانه</span><textarea v-model="s.rules" rows="3" maxlength="800" class="k-text" :disabled="!host"></textarea></label>
      <div class="k-grid2"><label class="field"><span>تلفن</span><input v-model="s.phone" maxlength="20" :disabled="!host"></label>
        <label class="field"><span>شماره‌ی کارت (پس از تأیید رزرو به مهمان نشان داده می‌شود)</span><input v-model="s.card" maxlength="60" :disabled="!host"></label></div>
    </section>
    <section class="card col-span-12 lg:col-span-5 flex flex-col gap-2">
      <div class="card-head">قاعده‌های رزرو</div>
      <label class="k-setting"><span><b>نفر اضافه، هر شب</b><small class="muted">تومان؛ برای هر نفر بیش از تخت‌ها</small></span><input v-model="s.extra_person" inputmode="numeric" :disabled="!host"></label>
      <label class="k-setting"><span><b>بیعانه</b><small class="muted">درصد از جمع</small></span><input v-model="s.deposit" inputmode="numeric" :disabled="!host"></label>
      <label class="k-setting"><span><b>مهلت بیعانه</b><small class="muted">ساعت پس از تأیید</small></span><input v-model="s.deposit_hours" inputmode="numeric" :disabled="!host"></label>
      <label class="k-setting"><span><b>کمترین شب با آخر هفته</b><small class="muted">رزروی که شب چهارشنبه یا پنجشنبه دارد</small></span><input v-model="s.min_weekend" inputmode="numeric" :disabled="!host"></label>
    </section>
    <div v-if="host" class="col-span-12"><p v-if="error" class="error-text">{{ error }}</p><button class="btn primary" :disabled="busy">ذخیره</button></div>
  </form>
</template>
