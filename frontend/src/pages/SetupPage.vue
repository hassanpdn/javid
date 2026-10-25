<script setup>
// First step of a demo: the school's details. Saving rebuilds all demo data with these names,
// so each school sees its own name, its own manager and counselor, and boys' or girls' names.
import { ref, reactive, computed, onMounted } from "vue"
import { api } from "../lib/api.js"
import { schoolInfo, setupUi, loadSchool } from "../lib/school.js"
import { gsap, motion } from "../lib/motion.js"
import Icon from "../components/Icon.vue"

const FIELDS = ["name", "gender", "city", "district", "manager_title", "manager_name",
                "counselor_title", "counselor_name", "staff_title", "staff_name"]
const pick = (s) => Object.fromEntries(FIELDS.map((k) => [k, s?.[k] ?? ""]))
const form = reactive(pick(schoolInfo.school))
const password = ref(""), busy = ref(false), error = ref(""), root = ref(null)
const people = [
  { title: "manager_title", name: "manager_name", label: "مدیر مدرسه", placeholder: "مثلا دکتر انوشه‌پور" },
  { title: "counselor_title", name: "counselor_name", label: "مشاور", placeholder: "مثلا مریم کاظمی" },
  { title: "staff_title", name: "staff_name", label: "کارمند اداری", placeholder: "مثلا زهره امینی" },
]
const preview = computed(() => `دبستان ${form.name.replace(/^دبستان\s*/, "") || "..."}`)
const load = (s) => Object.assign(form, pick(s))

const submit = async () => {
  busy.value = true; error.value = ""
  try {
    await api("/setup", { school: { ...form }, password: password.value })
    await loadSchool()
    setupUi.open = false
  } catch (e) {
    error.value = e.message === "Failed to fetch" ? "ارتباط با سرور برقرار نشد." : e.message
  } finally { busy.value = false }
}

onMounted(() => {
  if (motion) gsap.from(root.value.querySelectorAll(".setup-card > *"), { y: 18, opacity: 0, stagger: .05, duration: .5, ease: "power3.out", clearProps: "opacity,transform" })
})
</script>

<template>
  <main class="setup" ref="root">
    <form class="setup-card card" @submit.prevent="submit">
      <div class="flex items-center gap-3">
        <span class="logo">{{ (form.name.replace(/^دبستان\s*/, '') || 'ج')[0] }}</span>
        <div><h1>راه‌اندازی دمو برای مدرسه</h1><p class="muted small">مشخصات مدرسه را وارد کنید. همه صفحه‌ها، نامه‌ها و پیام‌ها با همین نام‌ها ساخته می‌شوند.</p></div>
      </div>

      <div v-if="schoolInfo.saved.length" class="saved">
        <span class="small muted">مدرسه‌های قبلی:</span>
        <button v-for="s in schoolInfo.saved" :key="s.name" type="button" class="chip-btn" :class="{ on: s.name === form.name }" @click="load(s)">{{ s.full_name }}</button>
        <button type="button" class="chip-btn" @click="load(schoolInfo.default)"><Icon name="refresh" :size="14" />جاوید (پیش‌فرض)</button>
      </div>

      <section class="setup-grid">
        <div class="field span-2"><span id="lbl-name">نام مدرسه</span>
          <div class="name-row">
            <span class="prefix">دبستان</span>
            <input v-model="form.name" required maxlength="40" placeholder="مثلا جاوید" aria-labelledby="lbl-name">
            <div class="segmented" role="radiogroup" aria-label="دخترانه یا پسرانه">
              <button type="button" :class="{ on: form.gender === 'girls' }" @click="form.gender = 'girls'" role="radio" :aria-checked="form.gender === 'girls'">دخترانه</button>
              <button type="button" :class="{ on: form.gender === 'boys' }" @click="form.gender = 'boys'" role="radio" :aria-checked="form.gender === 'boys'">پسرانه</button>
            </div>
          </div>
        </div>
        <label class="field"><span>شهر</span><input v-model="form.city" required maxlength="30" placeholder="مثلا تهران"></label>
        <label class="field"><span>منطقه آموزش و پرورش</span><input v-model="form.district" required maxlength="30" placeholder="مثلا منطقه ۳"></label>

        <div v-for="p in people" :key="p.name" class="field span-2"><span :id="'lbl-' + p.name">{{ p.label }}</span>
          <div class="name-row">
            <div class="segmented" role="radiogroup" :aria-label="'عنوان ' + p.label">
              <button v-for="t in ['آقای', 'خانم']" :key="t" type="button" :class="{ on: form[p.title] === t }" @click="form[p.title] = t" role="radio" :aria-checked="form[p.title] === t">{{ t }}</button>
            </div>
            <input v-model="form[p.name]" required maxlength="40" :placeholder="p.placeholder" :aria-labelledby="'lbl-' + p.name">
          </div>
        </div>

        <label v-if="schoolInfo.needs_password" class="field span-2"><span>رمز راه‌اندازی</span>
          <input v-model="password" type="password" autocomplete="off" required></label>
      </section>

      <p class="small muted">پیش‌نمایش: <b class="text-ink">{{ preview }}</b>، {{ form.gender === 'boys' ? 'پسرانه' : 'دخترانه' }}، {{ form.city }} · مدیر: {{ form.manager_title }} {{ form.manager_name }}</p>
      <p v-if="schoolInfo.set_up" class="check bad small">با ساختن دمو، داده‌های نمونه فعلی پاک و از نو ساخته می‌شوند.</p>
      <p v-if="error" class="error-text">{{ error }}</p>

      <div class="dialog-actions">
        <button class="btn primary" type="submit" :disabled="busy">
          <Icon :name="busy ? 'refresh' : 'sparkles'" :size="18" />{{ busy ? 'در حال ساخت داده‌های نمونه...' : 'ساخت دمو' }}</button>
        <button v-if="schoolInfo.set_up" type="button" class="btn ghost" :disabled="busy" @click="setupUi.open = false">انصراف</button>
      </div>
    </form>
  </main>
</template>
