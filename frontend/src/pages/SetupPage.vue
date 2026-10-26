<script setup>
// First step of a demo: the school's details, in four short steps. The card next to the form fills in as
// each step is finished; the last step rebuilds all demo data with these names and opens the login page.
import { ref, reactive, nextTick, onMounted, onUnmounted } from "vue"
import { api } from "../lib/api.js"
import { schoolInfo, setupUi, loadSchool } from "../lib/school.js"
import { gate } from "../lib/gate.js"
import { gsap, motion } from "../lib/motion.js"
import Icon from "../components/Icon.vue"
import SchoolCard from "../components/SchoolCard.vue"
import FeatureToggles from "../components/FeatureToggles.vue"

const STEPS = [
  { title: "مدرسه", hint: "نام و نوع مدرسه", icon: "school" },
  { title: "موقعیت", hint: "شهر و منطقه آموزشی", icon: "mapPin" },
  { title: "کادر مدرسه", hint: "مدیر، مشاور و کارمند", icon: "users" },
  { title: "ساخت دمو", hint: "مرور و ساخت", icon: "sparkles" },
]
const PEOPLE = [
  { title: "manager_title", name: "manager_name", label: "مدیر مدرسه", placeholder: "نام و نام خانوادگی مدیر" },
  { title: "counselor_title", name: "counselor_name", label: "مشاور", placeholder: "نام و نام خانوادگی مشاور" },
  { title: "staff_title", name: "staff_name", label: "کارمند اداری", placeholder: "نام و نام خانوادگی کارمند" },
]
const FIELDS = ["name", "gender", "city", "district", "manager_title", "manager_name",
                "counselor_title", "counselor_name", "staff_title", "staff_name"]

const form = reactive(Object.fromEntries(FIELDS.map((k) => [k, ""])))   // starts empty: nothing is assumed
const step = ref(0), done = reactive(new Set()), errors = reactive({}), direction = ref(1)
const error = ref(""), building = ref(null), success = ref(false)
const page = ref(null), body = ref(null), cardRef = ref(null), lineFill = ref(null)


// ---------- checking each step ----------
const filled = (k) => String(form[k] || "").trim()
function check(i) {
  for (const k of Object.keys(errors)) delete errors[k]
  const need = (k, msg) => { if (!filled(k)) errors[k] = msg }
  if (i === 0) { need("name", "نام مدرسه را بنویسید"); need("gender", "دخترانه یا پسرانه را انتخاب کنید") }
  if (i === 1) { need("city", "شهر را بنویسید"); need("district", "منطقه را بنویسید") }
  if (i === 2) for (const p of PEOPLE) { need(p.title, "آقای یا خانم؟"); need(p.name, `نام ${p.label} را بنویسید`) }
  return Object.keys(errors).length === 0
}

// ---------- moving between steps ----------
async function go(to) {
  direction.value = to > step.value ? 1 : -1
  step.value = to
  await nextTick()
  if (motion && lineFill.value) gsap.to(lineFill.value, { width: `${(to / (STEPS.length - 1)) * 100}%`, duration: .6, ease: "power3.out" })
  body.value?.querySelector("input:not([type=hidden])")?.focus({ preventScroll: true })
}
function next() {
  if (step.value === STEPS.length - 1) return build()
  if (!check(step.value)) {
    if (motion) gsap.fromTo(body.value, { x: -8 }, { x: 0, duration: .5, ease: "elastic.out(1, .3)" })
    return
  }
  done.add(step.value)
  go(step.value + 1)
}
const back = () => step.value > 0 && go(step.value - 1)
const canOpen = (i) => i <= step.value || [...Array(i).keys()].every((j) => done.has(j))
// «تنظیمات پیش‌فرض»: the server sends the default school's details, they replace the form and we jump to the last step
async function useDefault() {
  error.value = ""
  try {
    const { school } = await api("/setup/default")
    for (const k of FIELDS) form[k] = school[k] || ""
    ;[0, 1, 2].forEach((i) => done.add(i))
    go(3)
  } catch (e) { error.value = e.message }
}

// steps slide in from the side they come from
const enter = (el, finish) => motion
  ? gsap.fromTo(el, { opacity: 0, x: -40 * direction.value }, { opacity: 1, x: 0, duration: .45, ease: "power3.out", onComplete: finish })
  : finish()
const leave = (el, finish) => motion
  ? gsap.to(el, { opacity: 0, x: 40 * direction.value, duration: .2, ease: "power2.in", onComplete: finish })
  : finish()

// ---------- building the demo ----------
const BUILD_STEPS = ["ثبت مشخصات مدرسه", "ساخت دانش‌آموزان و معلمان", "حضور و ارزشیابی از مهر تا امروز",
                     "نامه‌های اداری و اعلان‌ها", "حساب‌های ورود نقش‌ها"]
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
async function build() {
  error.value = ""; success.value = false
  building.value = BUILD_STEPS.map((text) => ({ text, done: false }))
  const request = api("/setup", { school: { ...form } })
  try {
    for (const item of building.value) { await wait(motion ? 420 : 0); item.done = true }   // the checklist ticks while the server works
    await request
    success.value = true
    cardRef.value?.celebrate()
    await wait(motion ? 1400 : 0)
    await loadSchool()
    setupUi.open = false
  } catch (e) {
    request.catch(() => {})
    building.value = null
    error.value = e.message === "Failed to fetch" ? "ارتباط با سرور برقرار نشد." : e.message
  }
}

let blobs
onMounted(() => {
  if (!motion) return
  blobs = gsap.context(() => {
    gsap.to(".setup-blob.a", { x: 80, y: 40, duration: 9, yoyo: true, repeat: -1, ease: "sine.inOut" })
    gsap.to(".setup-blob.b", { x: -70, y: -50, duration: 11, yoyo: true, repeat: -1, ease: "sine.inOut" })
    gsap.from(".setup-form > *", { y: 20, opacity: 0, stagger: .06, duration: .6, ease: "power3.out", clearProps: "opacity,transform" })
  }, page.value)
})
onUnmounted(() => blobs?.revert())
</script>

<template>
  <main class="setup" ref="page">
    <i class="setup-blob a" aria-hidden="true"></i><i class="setup-blob b" aria-hidden="true"></i>
    <div class="setup-layout">
      <form class="setup-form card" @submit.prevent="next" novalidate>
        <div class="setup-top">
          <div><h1>راه‌اندازی دمو برای مدرسه</h1><p class="muted small">چند قدم کوتاه؛ همه صفحه‌ها، نامه‌ها و پیام‌ها با همین نام‌ها ساخته می‌شوند.</p></div>
          <span class="flex flex-col items-end gap-1">
            <button v-if="gate.hub" type="button" class="link small" @click="gate.app = ''">همه‌ی دستیارها</button>
            <button v-if="schoolInfo.set_up" type="button" class="link small" @click="setupUi.open = false">بازگشت به ورود</button>
          </span>
        </div>

        <ol class="stepper" aria-label="مراحل">
          <span class="stepper-line" aria-hidden="true"><span ref="lineFill"></span></span>
          <li v-for="(s, i) in STEPS" :key="s.title" :class="{ on: step === i, done: done.has(i) }">
            <button type="button" :disabled="!canOpen(i) || !!building" @click="go(i)" :aria-current="step === i ? 'step' : undefined">
              <span class="st-dot"><Icon :name="done.has(i) && step !== i ? 'check' : s.icon" :size="18" /></span>
              <span class="st-text"><b>{{ s.title }}</b><small>{{ s.hint }}</small></span>
            </button>
          </li>
        </ol>

        <div class="step-body" ref="body">
          <Transition :css="false" mode="out-in" @enter="enter" @leave="leave">
            <section v-if="step === 0" key="0" class="step-panel">
              <div class="field"><span id="l-name">نام مدرسه</span>
                <div class="name-row">
                  <span class="prefix">دبستان</span>
                  <input v-model="form.name" maxlength="40" placeholder="نام مدرسه را بنویسید" aria-labelledby="l-name" :aria-invalid="!!errors.name">
                </div>
                <small v-if="errors.name" class="error-text">{{ errors.name }}</small>
              </div>
              <div class="field"><span id="l-gender">نوع مدرسه</span>
                <div class="choice-grid" role="radiogroup" aria-labelledby="l-gender">
                  <button v-for="g in [{ k: 'girls', t: 'دخترانه', d: 'نام‌های دخترانه، آموزگاران خانم', tone: 'danger' },
                                       { k: 'boys', t: 'پسرانه', d: 'نام‌های پسرانه، آموزگاران آقا و خانم', tone: 'info' }]"
                          :key="g.k" type="button" role="radio" :aria-checked="form.gender === g.k"
                          :class="['choice', { on: form.gender === g.k }]" @click="form.gender = g.k">
                    <span :class="['tint', 't-' + g.tone]"><Icon name="users" :size="22" /></span>
                    <span><b>{{ g.t }}</b><small>{{ g.d }}</small></span>
                    <Icon v-if="form.gender === g.k" name="check" :size="18" class="choice-check" />
                  </button>
                </div>
                <small v-if="errors.gender" class="error-text">{{ errors.gender }}</small>
              </div>
              <div class="quick">
                <span class="small muted">یا همه مراحل با یک کلیک:</span>
                <button type="button" class="chip-btn" @click="useDefault"><Icon name="refresh" :size="14" />تنظیمات پیش‌فرض</button>
              </div>
            </section>

            <section v-else-if="step === 1" key="1" class="step-panel">
              <div class="setup-grid">
                <label class="field"><span>شهر</span><input v-model="form.city" maxlength="30" placeholder="مثلا تهران" :aria-invalid="!!errors.city">
                  <small v-if="errors.city" class="error-text">{{ errors.city }}</small></label>
                <label class="field"><span>منطقه آموزش و پرورش</span><input v-model="form.district" maxlength="30" placeholder="مثلا منطقه ۳" :aria-invalid="!!errors.district">
                  <small v-if="errors.district" class="error-text">{{ errors.district }}</small></label>
              </div>
              <p class="muted small">نامه‌های اداری نمونه از «اداره آموزش و پرورش {{ form.district || '...' }} {{ form.city || '...' }}» می‌آیند.</p>
            </section>

            <section v-else-if="step === 2" key="2" class="step-panel">
              <div v-for="p in PEOPLE" :key="p.name" class="field"><span :id="'l-' + p.name">{{ p.label }}</span>
                <div class="name-row">
                  <div class="segmented" role="radiogroup" :aria-label="'عنوان ' + p.label">
                    <button v-for="t in ['آقای', 'خانم']" :key="t" type="button" role="radio" :aria-checked="form[p.title] === t"
                            :class="{ on: form[p.title] === t }" @click="form[p.title] = t">{{ t }}</button>
                  </div>
                  <input v-model="form[p.name]" maxlength="40" :placeholder="p.placeholder" :aria-labelledby="'l-' + p.name" :aria-invalid="!!errors[p.name]">
                </div>
                <small v-if="errors[p.title] || errors[p.name]" class="error-text">{{ errors[p.title] || errors[p.name] }}</small>
              </div>
            </section>

            <section v-else key="3" class="step-panel">
              <p>همه چیز آماده است. با «ساخت دمو» داده‌های نمونه برای <b class="text-ink">دبستان {{ form.name.replace(/^دبستان\s*/, '') }}</b> ساخته می‌شود و صفحه ورود باز می‌شود.</p>
              <div class="field"><span>نقش‌های این دمو</span><FeatureToggles /></div>
              <p v-if="schoolInfo.set_up" class="check bad small">داده‌های نمونه فعلی پاک و از نو ساخته می‌شوند و همه از حساب خارج می‌شوند.</p>
            </section>
          </Transition>
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="step-actions">
          <button v-if="step > 0" type="button" class="btn ghost" :disabled="!!building" @click="back">
            <Icon name="chevron" :size="18" class="flip" />قبلی</button>
          <span class="grow"></span>
          <button class="btn primary" type="submit" :disabled="!!building">
            <template v-if="step < STEPS.length - 1">بعدی<Icon name="chevron" :size="18" /></template>
            <template v-else><Icon name="sparkles" :size="18" />ساخت دمو</template>
          </button>
        </div>
      </form>

      <aside class="setup-aside">
        <SchoolCard ref="cardRef" :form="form" :done="done" :step="step" :building="building" :success="success" />
      </aside>
    </div>
  </main>
</template>
