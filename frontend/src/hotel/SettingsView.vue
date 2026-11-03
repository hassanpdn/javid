<script setup>
// «قیمت‌ها و قاعده‌ها» (the manager): the base price a night of each room type (the season and the weekend are worked
// on top of it by the server), an extra bed, meals per person, the deposit and the largest discount anyone but the
// manager may give. New bookings use the new numbers; existing ones keep their price.
import { ref, onMounted } from "vue"
import { api, fa, hotelSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { loadHotel, digits } from "./lib.js"

const s = ref(null), busy = ref(false), error = ref("")
const manager = hotelSession.user.role === "manager"
onMounted(async () => { s.value = await api("/hotel/settings") })
const n = (v) => digits(v)
async function save() {
  busy.value = true; error.value = ""
  try {
    const body = { prices: Object.fromEntries(Object.entries(s.value.prices).map(([k, v]) => [k, n(v)])), extra_bed: n(s.value.extra_bed), HB: n(s.value.HB), FB: n(s.value.FB),
                   deposit: n(s.value.deposit), max_discount: n(s.value.max_discount) }
    Object.assign(s.value, await api("/hotel/settings", body)); await loadHotel(); toast({ tone: "success", title: "ذخیره شد" })
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "عددها درست نیست" : e.message } finally { busy.value = false }
}
</script>

<template>
  <form v-if="s" class="grid grid-cols-12 gap-6" @submit.prevent="save">
    <section class="card col-span-12 lg:col-span-7 flex flex-col gap-2">
      <div class="card-head">قیمت پایه‌ی هر شب (تومان)</div>
      <label v-for="(name, k) in s.types" :key="k" class="ht-setting"><span><b>{{ name }}</b><small class="muted">{{ fa(Number(n(s.prices[k])).toLocaleString()) }} تومان</small></span>
        <input v-model="s.prices[k]" inputmode="numeric" :aria-label="'قیمت ' + name" :disabled="!manager"></label>
      <p class="check info small"><span>روی این قیمت‌ها، نوروز ۱.۶ برابر، تابستان ۱.۳ برابر، ماه‌های کم‌مسافر ۰.۸ برابر و شب‌های چهارشنبه و پنجشنبه ۱.۲ برابر حساب می‌شود. این ضریب‌ها نمونه‌اند و هر هتل عدد خودش را دارد.</span></p>
    </section>
    <section class="card col-span-12 lg:col-span-5 flex flex-col gap-2">
      <div class="card-head">قاعده‌ها</div>
      <label class="ht-setting"><span><b>تخت اضافه، هر شب</b></span><input v-model="s.extra_bed" inputmode="numeric" :disabled="!manager"></label>
      <label class="ht-setting"><span><b>نیم‌پانسیون، هر نفر هر شب</b></span><input v-model="s.HB" inputmode="numeric" :disabled="!manager"></label>
      <label class="ht-setting"><span><b>پانسیون کامل، هر نفر هر شب</b></span><input v-model="s.FB" inputmode="numeric" :disabled="!manager"></label>
      <label class="ht-setting"><span><b>بیعانه</b><small class="muted">درصد از جمع رزرو</small></span><input v-model="s.deposit" inputmode="numeric" :disabled="!manager"></label>
      <label class="ht-setting"><span><b>سقف تخفیف</b><small class="muted">درصد؛ بیشتر از این را فقط مدیر می‌دهد</small></span><input v-model="s.max_discount" inputmode="numeric" :disabled="!manager"></label>
    </section>
    <div v-if="manager" class="col-span-12"><p v-if="error" class="error-text">{{ error }}</p><button class="btn primary" :disabled="busy">ذخیره</button></div>
  </form>
</template>
