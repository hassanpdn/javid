<script setup>
// Kit: the first step of a business assistant's demo (law, dental, hotel, lodge): the business's name, a short address
// and its people (each with آقای or خانم). «تنظیمات پیش‌فرض» fills in the default business; «ساخت دمو» builds the demo
// for these names while the card beside the form shows each part being made.
// base: the assistant's API («/law»); payload: the key the setup sends («office»); info: the assistant's store
// (set_up, setupOpen) and load() refreshes it; noun: the business in one word («دفتر») for labels and errors;
// title, intro, namePlaceholder, placePlaceholder; people: [{role, label, placeholder}]; parts: [{name, what, icon}]
// (the card's rows); steps: the build's lines; letter: the logo's letter before a name is typed; warning: a line under
// the form when a demo already exists.
import { ref, reactive, onMounted, onUnmounted } from "vue"
import { api, fa } from "../../lib/api.js"
import { gate } from "../../lib/gate.js"
import gsap from "gsap"
import { motion } from "../../lib/motion.js"
import Icon from "../Icon.vue"

const props = defineProps({
  base: String, payload: String, info: Object, load: Function, noun: String, title: String, intro: String,
  namePlaceholder: String, placePlaceholder: String, people: Array, parts: Array, steps: Array, letter: { type: String, default: "ا" },
  warning: { type: String, default: "داده‌های فعلی پاک و از نو ساخته می‌شوند و همه از حساب خارج می‌شوند." },
})
const PEOPLE = props.people.map((p) => ({ ...p, title: p.role + "_title", name: p.role + "_name" }))
const FIELDS = ["name", "place", ...PEOPLE.flatMap((p) => [p.title, p.name])]
const form = reactive(Object.fromEntries(FIELDS.map((k) => [k, ""])))
const errors = reactive({}), error = ref(""), building = ref(null), made = reactive(new Set()), page = ref(null)

function check() {
  for (const k of Object.keys(errors)) delete errors[k]
  if (!form.name.trim()) errors.name = `نام ${props.noun} را بنویسید`
  if (!form.place.trim()) errors.place = "نشانی کوتاه را بنویسید"
  for (const p of PEOPLE) {
    if (!form[p.title]) errors[p.name] = "آقای یا خانم؟"
    else if (!form[p.name].trim()) errors[p.name] = `نام ${p.label} را بنویسید`
  }
  return !Object.keys(errors).length
}
async function useDefault() {
  const d = (await api(`${props.base}/setup/default`))[props.payload]
  for (const k of FIELDS) form[k] = d[k] || ""
  for (const k of Object.keys(errors)) delete errors[k]
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
async function build() {
  if (!check()) { if (motion) gsap.fromTo(".setup-form", { x: -8 }, { x: 0, duration: .5, ease: "elastic.out(1, .3)" }); return }
  error.value = ""; made.clear()
  building.value = props.steps.map((text) => ({ text, done: false }))
  const request = api(`${props.base}/setup`, { [props.payload]: { ...form } })
  try {
    for (const [i, item] of building.value.entries()) {
      await wait(motion ? 420 : 0); item.done = true
      if (i < props.parts.length) made.add(i)
    }
    await request
    await wait(motion ? 600 : 0)
    props.info.setupOpen = false
    await props.load()
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
          <div><h1>{{ title }}</h1><p class="muted small">{{ intro }}</p></div>
          <span class="flex flex-col items-end gap-1">
            <button v-if="gate.hub" type="button" class="link small" @click="gate.app = ''">همه‌ی دستیارها</button>
            <button v-if="info.set_up" type="button" class="link small" @click="info.setupOpen = false">بازگشت به ورود</button>
          </span>
        </div>
        <div class="setup-grid">
          <label class="field"><span>نام {{ noun }}</span><input v-model="form.name" maxlength="40" :placeholder="namePlaceholder" :aria-invalid="!!errors.name">
            <small v-if="errors.name" class="error-text">{{ errors.name }}</small></label>
          <label class="field"><span>نشانی کوتاه</span><input v-model="form.place" maxlength="40" :placeholder="placePlaceholder" :aria-invalid="!!errors.place">
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
        <p v-if="info.set_up" class="check bad small">{{ warning }}</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="step-actions"><span class="grow"></span>
          <button class="btn primary" type="submit" :disabled="!!building"><Icon name="sparkles" :size="18" />ساخت دمو</button></div>
      </form>

      <aside class="setup-aside">
        <div class="school-card xl-card">
          <header class="sc-head xl-head">
            <i class="sc-circle a"></i><i class="sc-circle b"></i>
            <span class="sc-logo">{{ (form.name || letter)[0] }}</span>
            <div class="sc-title"><small>داده‌های این {{ noun }}</small>
              <b :class="{ ghost: !form.name }">{{ form.name || "نام " + noun }}</b></div>
          </header>
          <div class="sc-body">
            <section v-for="(f, i) in parts" :key="f.name" :class="['sc-row', made.has(i) ? 'done' : 'live']">
              <span class="tint sm t-primary"><Icon :name="f.icon" :size="18" /></span>
              <div class="sc-text"><b>{{ f.name }}</b><small>{{ fa(f.what) }}</small></div>
              <Icon v-if="made.has(i)" name="check" :size="18" class="sc-check" />
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
