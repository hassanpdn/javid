<script setup>
// «رزرو دستی»: a booking that came by phone, WhatsApp or Instagram. Pick the dates and people to see the units free
// for every night with their price, then the guest's name and mobile. It is saved as approved (waiting for its
// deposit), and the guest can later make an account on the website with the same mobile to follow it.
import { ref, reactive, watch } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { lodgeInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import DatePicker from "../components/core/DatePicker.vue"

const emit = defineEmits(["close", "saved"])
const f = reactive({ arrive: lodgeInfo.today, depart: null, adults: 2, unit_id: null, name: "", phone: "", source: "whatsapp", note: "" })
const units = ref(null), busy = ref(false), error = ref("")
watch(() => [f.arrive, f.depart, f.adults], async () => {
  units.value = null; f.unit_id = null; error.value = ""
  if (!f.arrive || !f.depart) return
  try { units.value = await api("/lodge/free", { arrive: f.arrive, depart: f.depart, adults: f.adults }) } catch (e) { error.value = e.message }
})
async function save() {
  busy.value = true; error.value = ""
  try { const r = await api("/lodge/bookings", { ...f }); toast({ tone: "success", title: "رزرو ثبت شد؛ منتظر بیعانه" }); emit("saved", r.id) }
  catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "خانه‌ها را درست پر کنید" : e.message } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog wide" v-pop role="dialog" aria-label="رزرو دستی" @submit.prevent="save">
      <div class="dialog-head"><h3>رزرو دستی</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="k-grid2"><div class="field"><span>ورود</span><DatePicker v-model="f.arrive" :min="lodgeInfo.today" label="ورود" /></div>
        <div class="field"><span>خروج</span><DatePicker v-model="f.depart" :min="f.arrive" label="خروج" /></div></div>
      <label class="field"><span>چند نفر</span><select v-model.number="f.adults" class="k-select"><option v-for="n in 10" :key="n" :value="n">{{ fa(n) }} نفر</option></select></label>
      <div class="field"><span>واحدهای خالی در همه‌ی شب‌ها</span>
        <p v-if="!f.depart" class="muted small">تاریخ خروج را انتخاب کنید.</p>
        <p v-else-if="units && !units.length" class="muted small">برای این شب‌ها واحد خالی نیست.</p>
        <div v-else-if="units" class="lo-chips"><button v-for="u in units" :key="u.id" type="button" :class="{ on: f.unit_id === u.id }" :aria-pressed="f.unit_id === u.id" @click="f.unit_id = u.id">{{ u.name }} · {{ fa(u.quote.total_text) }}</button></div></div>
      <div class="k-grid2"><label class="field"><span>نام مهمان</span><input v-model="f.name" maxlength="60"></label>
        <label class="field"><span>شماره‌ی همراه</span><input v-model="f.phone" dir="ltr" inputmode="tel" maxlength="20" placeholder="09121234567"></label></div>
      <div class="k-grid2"><label class="field"><span>از طریق</span><select v-model="f.source" class="k-select"><option v-for="(t, k) in lodgeInfo.sources" v-show="k !== 'site'" :key="k" :value="k">{{ t }}</option></select></label>
        <label class="field"><span>یادداشت</span><input v-model="f.note" maxlength="300"></label></div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions"><button class="btn primary" :disabled="busy || !f.unit_id || f.name.trim().length < 3 || !f.phone"><Icon name="check" :size="18" />ثبت رزرو</button></div>
    </form>
  </div>
</template>
