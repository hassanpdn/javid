<script setup>
// First step of a law office demo: the office's name and its three people. «ساخت دمو» builds the office's open cases,
// their notices and deadlines for these names; the card beside the form shows it being made.
import { ref, reactive, onMounted, onUnmounted } from "vue"
import { api, fa } from "../lib/api.js"
import { gate } from "../lib/gate.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"
import { officeInfo, loadOffice } from "./lib.js"
import Icon from "../components/Icon.vue"

const PEOPLE = [
  { title: "owner_title", name: "owner_name", label: "وکیل (صاحب دفتر)", placeholder: "نام و نام خانوادگی وکیل" },
  { title: "associate_title", name: "associate_name", label: "همکار وکیل", placeholder: "نام و نام خانوادگی همکار" },
  { title: "secretary_title", name: "secretary_name", label: "منشی", placeholder: "نام و نام خانوادگی منشی" },
]
const FIELDS = ["name", "place", ...PEOPLE.flatMap((p) => [p.title, p.name])]
const PARTS = [
  { key: "files", name: "پرونده‌ها", what: "حدود ۶۰ پرونده‌ی حقوقی، کیفری، خانواده و اجرا" },
  { key: "people", name: "ابلاغیه‌ها", what: "دادنامه، اخطار رفع نقص، نظر کارشناس و وقت رسیدگی" },
  { key: "deals", name: "مهلت‌ها", what: "روز آخر هر مهلت، با جمعه‌ها و تعطیلات رسمی" },
]
const form = reactive(Object.fromEntries(FIELDS.map((k) => [k, ""])))
const errors = reactive({}), error = ref(""), building = ref(null), made = reactive(new Set()), page = ref(null)

function check() {
  for (const k of Object.keys(errors)) delete errors[k]
  if (!form.name.trim()) errors.name = "نام دفتر را بنویسید"
  if (!form.place.trim()) errors.place = "نشانی کوتاه را بنویسید"
  for (const p of PEOPLE) {
    if (!form[p.title]) errors[p.name] = "آقای یا خانم؟"
    else if (!form[p.name].trim()) errors[p.name] = `نام ${p.label} را بنویسید`
  }
  return !Object.keys(errors).length
}
async function useDefault() {
  const { office } = await api("/law/setup/default")
  for (const k of FIELDS) form[k] = office[k] || ""
  for (const k of Object.keys(errors)) delete errors[k]
}
const BUILD = ["ساخت پرونده‌ها و موکلان", "ثبت ابلاغیه‌های هر پرونده", "حساب روز آخر هر مهلت", "جلسه‌های پیش رو", "حساب‌های ورود سه نفر"]
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
async function build() {
  if (!check()) { if (motion) gsap.fromTo(".setup-form", { x: -8 }, { x: 0, duration: .5, ease: "elastic.out(1, .3)" }); return }
  error.value = ""; made.clear()
  building.value = BUILD.map((text) => ({ text, done: false }))
  const request = api("/law/setup", { office: { ...form } })
  try {
    for (const [i, item] of building.value.entries()) {
      await wait(motion ? 420 : 0); item.done = true
      if (i < 3) made.add(PARTS[i].key)
    }
    await request
    await wait(motion ? 600 : 0)
    officeInfo.setupOpen = false
    await loadOffice()
  } catch (e) {
    request.catch(() => {})
    building.value = null; made.clear()
    error.value = e.message === "Failed to fetch" ? "ارتباط با سرور برقرار نشد." : e.message
  }
}
let ctx
onMounted(() => {
  if (!motion) return
  ctx = gsap.context(() => {
    gsap.from(".setup-form > *, .xl-card", { y: 20, opacity: 0, stagger: .06, duration: .6, ease: "power3.out", clearProps: "opacity,transform" })
  }, page.value)
})
onUnmounted(() => ctx?.revert())
</script>

<template>
  <main class="setup" ref="page">
    <i class="setup-blob a" aria-hidden="true"></i><i class="setup-blob b" aria-hidden="true"></i>
    <div class="setup-layout">
      <form class="setup-form card" @submit.prevent="build" novalidate>
        <div class="setup-top">
          <div><h1>راه‌اندازی دمو برای دفتر وکالت</h1>
            <p class="muted small">یک دفتر وکالت در تهران با پرونده‌های باز، ابلاغیه‌ها و مهلت‌هایشان. همه‌چیز با همین نام‌ها ساخته می‌شود.</p></div>
          <span class="flex flex-col items-end gap-1">
            <button v-if="gate.hub" type="button" class="link small" @click="gate.app = ''">همه‌ی دستیارها</button>
            <button v-if="officeInfo.set_up" type="button" class="link small" @click="officeInfo.setupOpen = false">بازگشت به ورود</button>
          </span>
        </div>

        <div class="setup-grid">
          <label class="field"><span>نام دفتر</span><input v-model="form.name" maxlength="40" placeholder="مثلاً دفتر وکالت پارسا" :aria-invalid="!!errors.name">
            <small v-if="errors.name" class="error-text">{{ errors.name }}</small></label>
          <label class="field"><span>نشانی کوتاه</span><input v-model="form.place" maxlength="40" placeholder="مثلاً خیابان مطهری، تهران" :aria-invalid="!!errors.place">
            <small v-if="errors.place" class="error-text">{{ errors.place }}</small></label>
        </div>
        <div v-for="p in PEOPLE" :key="p.name" class="field"><span :id="'l-' + p.name">{{ p.label }}</span>
          <div class="name-row">
            <div class="segmented" role="radiogroup" :aria-label="'عنوان ' + p.label">
              <button v-for="t in ['آقای', 'خانم']" :key="t" type="button" role="radio" :aria-checked="form[p.title] === t"
                      :class="{ on: form[p.title] === t }" @click="form[p.title] = t">{{ t }}</button>
            </div>
            <input v-model="form[p.name]" maxlength="40" :placeholder="p.placeholder" :aria-labelledby="'l-' + p.name" :aria-invalid="!!errors[p.name]">
          </div>
          <small v-if="errors[p.name]" class="error-text">{{ errors[p.name] }}</small>
        </div>
        <div class="quick">
          <span class="small muted">یا با یک کلیک:</span>
          <button type="button" class="chip-btn" @click="useDefault"><Icon name="refresh" :size="14" />تنظیمات پیش‌فرض</button>
        </div>
        <p v-if="officeInfo.set_up" class="check bad small">داده‌های فعلی پاک و از نو ساخته می‌شوند و همه از حساب خارج می‌شوند.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="step-actions"><span class="grow"></span>
          <button class="btn primary" type="submit" :disabled="!!building"><Icon name="sparkles" :size="18" />ساخت دمو</button></div>
      </form>

      <aside class="setup-aside">
        <div class="school-card xl-card">
          <header class="sc-head xl-head">
            <i class="sc-circle a"></i><i class="sc-circle b"></i>
            <span class="sc-logo">{{ (form.name || "و")[0] }}</span>
            <div class="sc-title"><small>پرونده‌های این دفتر</small>
              <b :class="{ ghost: !form.name }">{{ form.name || "نام دفتر" }}</b></div>
          </header>
          <div class="sc-body">
            <section v-for="f in PARTS" :key="f.key" :class="['sc-row', made.has(f.key) ? 'done' : 'live']">
              <span class="tint sm t-primary"><Icon :name="f.key === 'files' ? 'file' : f.key === 'people' ? 'users' : 'check'" :size="18" /></span>
              <div class="sc-text"><b>{{ f.name }}</b><small>{{ fa(f.what) }}</small></div>
              <Icon v-if="made.has(f.key)" name="check" :size="18" class="sc-check" />
            </section>
          </div>
          <div v-if="building" class="sc-build" aria-live="polite">
            <div class="sc-build-head"><Icon name="sparkles" :size="22" /><b>در حال ساخت دمو</b></div>
            <ul><li v-for="s in building" :key="s.text" :class="{ done: s.done }">
              <Icon :name="s.done ? 'check' : 'clock'" :size="16" />{{ s.text }}</li></ul>
          </div>
        </div>
        <p class="muted small center">همه‌ی داده‌ها ساختگی است و هر بار از نو ساخته می‌شود.</p>
      </aside>
    </div>
  </main>
</template>
