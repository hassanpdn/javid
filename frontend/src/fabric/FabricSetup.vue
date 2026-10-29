<script setup>
// First step of a fabric demo: the shop's name and its three people. «ساخت دمو» makes three Excel files
// (stock, sales, accounts) with four months of business for these names; the card beside the form shows them being made.
import { ref, reactive, onMounted, onUnmounted } from "vue"
import { api, fa } from "../lib/api.js"
import { gate } from "../lib/gate.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"
import { shop, loadShop } from "./lib.js"
import Icon from "../components/Icon.vue"

const PEOPLE = [
  { title: "owner_title", name: "owner_name", label: "صاحب کار", placeholder: "نام و نام خانوادگی صاحب کار" },
  { title: "seller_title", name: "seller_name", label: "فروشنده (پشت تلفن)", placeholder: "نام و نام خانوادگی فروشنده" },
  { title: "accountant_title", name: "accountant_name", label: "حسابدار", placeholder: "نام و نام خانوادگی حسابدار" },
]
const FIELDS = ["name", "place", ...PEOPLE.flatMap((p) => [p.title, p.name])]
const FILES = [
  { key: "stock", name: "انبار.xlsx", what: "۳۳ جنس پارچه، توپ و متراژ، قیمت‌ها" },
  { key: "sales", name: "فروش.xlsx", what: "فاکتورهای چهار ماه گذشته" },
  { key: "accounts", name: "حسابداری.xlsx", what: "مشتری‌ها از سراسر کشور، چک‌ها و دریافتی‌ها" },
]
const form = reactive(Object.fromEntries(FIELDS.map((k) => [k, ""])))
const errors = reactive({}), error = ref(""), building = ref(null), made = reactive(new Set()), page = ref(null)

function check() {
  for (const k of Object.keys(errors)) delete errors[k]
  if (!form.name.trim()) errors.name = "نام فروشگاه را بنویسید"
  if (!form.place.trim()) errors.place = "نشانی کوتاه را بنویسید"
  for (const p of PEOPLE) {
    if (!form[p.title]) errors[p.name] = "آقای یا خانم؟"
    else if (!form[p.name].trim()) errors[p.name] = `نام ${p.label.split(" (")[0]} را بنویسید`
  }
  return !Object.keys(errors).length
}
async function useDefault() {
  const { business } = await api("/fabric/setup/default")
  for (const k of FIELDS) form[k] = business[k] || ""
  for (const k of Object.keys(errors)) delete errors[k]
}
const BUILD = ["ساخت فایل انبار", "ساخت فایل فروش چهار ماه گذشته", "ساخت فایل حسابداری و چک‌ها", "خواندن و مرتب کردن سه فایل", "حساب‌های ورود سه نقش"]
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
async function build() {
  if (!check()) { if (motion) gsap.fromTo(".setup-form", { x: -8 }, { x: 0, duration: .5, ease: "elastic.out(1, .3)" }); return }
  error.value = ""; made.clear()
  building.value = BUILD.map((text) => ({ text, done: false }))
  const request = api("/fabric/setup", { business: { ...form } })
  try {
    for (const [i, item] of building.value.entries()) {
      await wait(motion ? 480 : 0); item.done = true
      if (i < 3) made.add(FILES[i].key)
    }
    await request
    await wait(motion ? 700 : 0)
    shop.setupOpen = false
    await loadShop()
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
    // the two background clouds drift with CSS (.setup-blob in main.css)
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
          <div><h1>راه‌اندازی دمو برای پارچه‌فروشی</h1>
            <p class="muted small">یک عمده‌فروشی پارچه در تهران با مشتری از سراسر کشور. سه فایل اکسل انبار، فروش و حسابداری با همین نام‌ها ساخته می‌شود.</p></div>
          <span class="flex flex-col items-end gap-1">
            <button v-if="gate.hub" type="button" class="link small" @click="gate.app = ''">همه‌ی دستیارها</button>
            <button v-if="shop.set_up" type="button" class="link small" @click="shop.setupOpen = false">بازگشت به ورود</button>
          </span>
        </div>

        <div class="setup-grid">
          <label class="field"><span>نام فروشگاه</span><input v-model="form.name" maxlength="40" placeholder="مثلاً پارچه‌سرای مهرگان" :aria-invalid="!!errors.name">
            <small v-if="errors.name" class="error-text">{{ errors.name }}</small></label>
          <label class="field"><span>نشانی کوتاه</span><input v-model="form.place" maxlength="40" placeholder="مثلاً بازار بزرگ تهران" :aria-invalid="!!errors.place">
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
        <p v-if="shop.set_up" class="check bad small">داده‌ها و فایل‌های فعلی پاک و از نو ساخته می‌شوند و همه از حساب خارج می‌شوند.</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="step-actions"><span class="grow"></span>
          <button class="btn primary" type="submit" :disabled="!!building"><Icon name="sparkles" :size="18" />ساخت دمو</button></div>
      </form>

      <aside class="setup-aside">
        <div class="school-card xl-card">
          <header class="sc-head xl-head">
            <i class="sc-circle a"></i><i class="sc-circle b"></i>
            <span class="sc-logo">{{ (form.name || "پ")[0] }}</span>
            <div class="sc-title"><small>فایل‌های این فروشگاه</small>
              <b :class="{ ghost: !form.name }">{{ form.name || "نام فروشگاه" }}</b></div>
          </header>
          <div class="sc-body">
            <section v-for="f in FILES" :key="f.key" :class="['sc-row', made.has(f.key) ? 'done' : 'live']">
              <span class="xl-file"><Icon name="file" :size="18" /><i>X</i></span>
              <div class="sc-text"><b>فایل {{ f.name.replace('.xlsx', '') }}</b><small>{{ fa(f.what) }}</small></div>
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
