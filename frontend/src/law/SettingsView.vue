<script setup>
// «مهلت‌ها و تعطیلات» (the lawyer only): how many days each kind of notice gives, and this year's lunar holidays.
// Fridays and the fixed official holidays are counted by the server; lunar holidays move every year, so they are
// entered here. New notices use the new numbers; deadlines already counted stay as they are.
import { ref, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"

const s = ref(null), holidays = ref(""), busy = ref(false), error = ref("")
onMounted(async () => { s.value = await api("/law/settings"); holidays.value = s.value.holidays.join("\n") })
async function save() {
  busy.value = true; error.value = ""
  try {
    const r = await api("/law/settings", { days: s.value.days, holidays: holidays.value.split(/[\n،,]+/).map((h) => h.trim()).filter(Boolean) })
    Object.assign(s.value, r); holidays.value = r.holidays.join("\n"); toast({ tone: "success", title: "ذخیره شد" })
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "عددها درست نیست" : e.message } finally { busy.value = false }
}
</script>

<template>
  <form v-if="s" class="grid grid-cols-12 gap-6" @submit.prevent="save">
    <section class="card col-span-12 lg:col-span-7 flex flex-col gap-3">
      <div class="card-head">مدت هر مهلت (روز)</div>
      <label v-for="k in s.kinds" :key="k.key" class="lw-setting"><span><b>{{ k.name }}</b><small class="muted">{{ k.todo }} · پیش‌فرض {{ fa(k.default) }} روز</small></span>
        <input v-model.number="s.days[k.key]" type="number" min="1" max="120" inputmode="numeric" :aria-label="'روزهای ' + k.name"></label>
      <p class="check info small"><Icon name="info" :size="14" /><span>این عددها مهلت‌های رایج آیین دادرسی است. پیش از تکیه بر آن‌ها، با قانون و رویه‌ی دادگاه‌های خودتان تطبیق دهید.</span></p>
    </section>
    <section class="card col-span-12 lg:col-span-5 flex flex-col gap-3">
      <div class="card-head">تعطیلات قمری امسال</div>
      <p class="muted small">جمعه‌ها و تعطیلات رسمی با تاریخ ثابت شمسی خودبه‌خود حساب می‌شوند. تعطیلات قمری هر سال جابه‌جا می‌شود؛ تاریخ هر کدام را در یک سطر بنویسید، مثلاً ۱۴۰۵/۰۹/۱۰.</p>
      <textarea v-model="holidays" rows="8" dir="ltr" class="lw-text" aria-label="تعطیلات قمری"></textarea>
    </section>
    <div class="col-span-12"><p v-if="error" class="error-text">{{ error }}</p><button class="btn primary" :disabled="busy">ذخیره</button></div>
  </form>
</template>
