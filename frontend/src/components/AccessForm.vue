<script setup>
// Give or change one person's access (permanent account only, access.py): their name, username and password, the
// assistants they may open (one or more), and an optional last day. After saving with a password, a text ready to send.
import { ref, reactive, computed, onMounted } from "vue"
import { accessCall, jalaliIn, jalaliText, MONTHS } from "../lib/access.js"
import Icon from "./Icon.vue"
import "./hub-dialog.css"

const props = defineProps({ assistants: Array, person: { type: Object, default: null } })
const emit = defineEmits(["close", "saved"])
const editing = !!props.person

// ready-made last days; "date" opens the day/month/year boxes
const ENDS = [{ key: "none", text: "بدون تاریخ" }, { key: 7, text: "۱ هفته" }, { key: 30, text: "۱ ماه" }, { key: 90, text: "۳ ماه" }, { key: "date", text: "تاریخ دلخواه" }]
const today = jalaliIn(0)
const asDate = (s) => { const [y, m, d] = s.split("/").map(Number); return { y, m, d } }

const form = reactive({
  name: props.person?.name || "", username: props.person?.username || "", password: "",
  apps: props.person ? [...props.person.apps] : [props.assistants[0].key],
  end: props.person?.expires_on ? "date" : editing ? "none" : 30,
  date: props.person?.expires_on ? asDate(props.person.expires_on) : jalaliIn(30),
})
const show = ref(!editing), error = ref(""), sending = ref(false), done = ref(null), copied = ref(false)
const nameEl = ref(null)
onMounted(() => { if (window.matchMedia("(min-width: 768px)").matches) nameEl.value?.focus() })

const pad = (n) => String(n).padStart(2, "0")
const fa = (v) => String(v).replace(/\d/g, (c) => "۰۱۲۳۴۵۶۷۸۹"[c])
// the last day as the server wants it («1405/08/30»), or null for none
const endsOn = computed(() => {
  if (form.end === "none") return null
  const d = form.end === "date" ? form.date : jalaliIn(form.end)
  return `${d.y}/${pad(d.m)}/${pad(d.d)}`
})
const daysIn = computed(() => (form.date.m <= 6 ? 31 : 30))
const years = [today.y, today.y + 1, today.y + 2]

// a password that is easy to read out on the phone: no 0/O or 1/l
const makePassword = () => {
  const abc = "abcdefghjkmnpqrstuvwxyz23456789", bytes = crypto.getRandomValues(new Uint8Array(8))
  form.password = Array.from(bytes, (b) => abc[b % abc.length]).join("")
  show.value = true
}
if (!editing) makePassword()

const toggle = (key) => {
  form.apps = form.apps.includes(key) ? form.apps.filter((k) => k !== key) : [...form.apps, key]
}
const names = (apps) => apps.map((k) => props.assistants.find((a) => a.key === k)?.title || k).join("، ")

const save = async () => {
  if (sending.value) return
  if (!form.name.trim()) { error.value = "اسم این شخص را بنویسید."; return }
  if (!form.username.trim()) { error.value = "یک نام کاربری بنویسید."; return }
  if (!editing && !form.password) { error.value = "یک رمز عبور بنویسید یا «رمز تازه» را بزنید."; return }
  if (!form.apps.length) { error.value = "دست‌کم یک دستیار را انتخاب کنید."; return }
  if (form.date.d > daysIn.value) form.date.d = daysIn.value
  sending.value = true; error.value = ""
  try {
    const body = { name: form.name, username: form.username, password: form.password, apps: form.apps, expires_on: endsOn.value }
    const p = await accessCall(editing ? `/access/people/${props.person.id}` : "/access/people", body)
    emit("saved")
    if (form.password) done.value = { ...p, password: form.password }
    else emit("close")
  } catch (e) { error.value = e.message }
  sending.value = false
}
const message = (p) => [
  `آدرس: ${location.origin}`, `نام کاربری: ${p.username}`, `رمز عبور: ${p.password}`, `دستیار: ${names(p.apps)}`,
  p.expires_on ? `تا ${jalaliText(p.expires_on)}` : "",
].filter(Boolean).join("\n")
const copy = async () => {
  try { await navigator.clipboard.writeText(message(done.value)); copied.value = true } catch {}
}
</script>

<template>
  <div class="hd-overlay" @click.self="emit('close')">
    <section v-if="done" class="hd" v-pop>
      <div class="hd-head">
        <div><h3>دسترسی {{ done.name }} آماده است</h3><p>این متن را برایش بفرستید. رمز را بعد از بستن این پنجره دیگر نمی‌بینید.</p></div>
        <button type="button" class="hd-x" aria-label="بستن" @click="emit('close')"><Icon name="x" :size="18" /></button>
      </div>
      <dl class="af-done">
        <div><dt>نام کاربری</dt><dd dir="ltr">{{ done.username }}</dd></div>
        <div><dt>رمز عبور</dt><dd dir="ltr">{{ done.password }}</dd></div>
        <div><dt>دستیار</dt><dd>{{ names(done.apps) }}</dd></div>
        <div><dt>تا</dt><dd>{{ done.expires_on ? jalaliText(done.expires_on) : "بدون تاریخ پایان" }}</dd></div>
      </dl>
      <button type="button" class="hd-btn" @click="copy"><Icon :name="copied ? 'check' : 'file'" :size="18" />{{ copied ? "کپی شد" : "کپی متن برای فرستادن" }}</button>
    </section>

    <form v-else class="hd wide" v-pop @submit.prevent="save" novalidate>
      <div class="hd-head">
        <div>
          <h3>{{ editing ? `دسترسی ${person.name}` : "دسترسی تازه" }}</h3>
          <p>چه کسی، با چه رمزی، کدام دستیار را ببیند.</p>
        </div>
        <button type="button" class="hd-x" aria-label="بستن" @click="emit('close')"><Icon name="x" :size="18" /></button>
      </div>

      <label class="hd-field">
        <span class="hd-label">اسم</span>
        <span class="hd-input"><Icon name="user" :size="19" /><input ref="nameEl" v-model="form.name" maxlength="60" placeholder="مثلاً خانم احمدی، مدیر دبستان نمونه" /></span>
      </label>

      <div class="af-two">
        <label class="hd-field">
          <span class="hd-label">نام کاربری</span>
          <span class="hd-input"><Icon name="userCheck" :size="19" />
            <input v-model="form.username" maxlength="30" dir="ltr" autocapitalize="none" autocomplete="off" spellcheck="false" />
          </span>
        </label>
        <label class="hd-field">
          <span class="hd-label">رمز عبور</span>
          <span class="hd-input"><Icon name="lock" :size="19" />
            <input v-model="form.password" :type="show ? 'text' : 'password'" maxlength="100" dir="ltr" autocomplete="new-password" spellcheck="false"
                   :placeholder="editing ? 'خالی = همان رمز قبلی' : ''" />
            <button type="button" class="hd-eye" :aria-label="show ? 'پنهان کردن رمز' : 'نشان دادن رمز'" :aria-pressed="show" @click="show = !show"><Icon :name="show ? 'eyeOff' : 'eye'" :size="19" /></button>
          </span>
          <button type="button" class="af-gen" @click="makePassword"><Icon name="refresh" :size="14" />رمز تازه</button>
        </label>
      </div>

      <div class="hd-field">
        <span class="hd-label">کدام دستیارها</span>
        <div class="af-apps">
          <button v-for="a in assistants" :key="a.key" type="button" :class="['af-app', 'hue-' + a.hue, { on: form.apps.includes(a.key) }]"
                  :aria-pressed="form.apps.includes(a.key)" @click="toggle(a.key)">
            <span class="af-app-icon"><Icon :name="a.icon" :size="22" /></span>
            <span class="af-app-text"><b>{{ a.title }}</b><small>{{ a.roles.join("، ") }}</small></span>
            <span class="af-tick"><Icon name="check" :size="14" /></span>
          </button>
        </div>
      </div>

      <div class="hd-field">
        <span class="hd-label">تا کی</span>
        <div class="af-chips">
          <button v-for="e in ENDS" :key="e.key" type="button" :class="['af-chip', { on: form.end === e.key }]" :aria-pressed="form.end === e.key"
                  @click="form.end = e.key">{{ e.text }}</button>
        </div>
        <div v-if="form.end === 'date'" class="af-date">
          <select v-model.number="form.date.d" aria-label="روز"><option v-for="d in daysIn" :key="d" :value="d">{{ fa(d) }}</option></select>
          <select v-model.number="form.date.m" aria-label="ماه"><option v-for="(m, i) in MONTHS" :key="m" :value="i + 1">{{ m }}</option></select>
          <select v-model.number="form.date.y" aria-label="سال"><option v-for="y in years" :key="y" :value="y">{{ fa(y) }}</option></select>
        </div>
        <p class="af-end"><Icon name="calendar" :size="15" />{{ endsOn ? `تا آخر روز ${jalaliText(endsOn)} باز است، بعد خودش بسته می‌شود.` : "تا وقتی خودتان پاکش نکنید باز است." }}</p>
      </div>

      <p class="hd-error" role="alert">{{ error }}</p>
      <button class="hd-btn" :disabled="sending"><span v-if="sending" class="hd-spin" aria-hidden="true"></span>{{ editing ? "ذخیره" : "دادن دسترسی" }}</button>
    </form>
  </div>
</template>

<style scoped>
.af-two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.af-two > * { min-width: 0; }
@media (max-width: 560px) { .af-two { grid-template-columns: 1fr; } }
.af-gen { align-self: flex-start; display: inline-flex; align-items: center; gap: 5px; padding: 2px 4px; border: 0; background: none; cursor: pointer;
  font: inherit; font-size: 12.5px; color: #a99fff; }
.af-gen:hover, .af-gen:focus-visible { color: #fff; outline: none; }

.af-apps { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }
.af-app { --c1: #7367f0; --c2: #00bad1; position: relative; display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 16px; cursor: pointer; text-align: right;
  font: inherit; color: #dcd8ff; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12); transition: border-color .2s, background .2s, transform .15s; }
.af-app.hue-teal { --c1: #0f8b7d; --c2: #f3b33d; }
.af-app:hover { background: rgba(255,255,255,.08); }
.af-app:active { transform: scale(.98); }
.af-app:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }
.af-app.on { border-color: color-mix(in srgb, var(--c1) 70%, #fff); background: color-mix(in srgb, var(--c1) 22%, transparent); }
.af-app-icon { flex: none; display: grid; place-items: center; width: 44px; height: 44px; border-radius: 14px; color: #fff;
  background: linear-gradient(140deg, var(--c1), color-mix(in srgb, var(--c2) 70%, var(--c1))); box-shadow: 0 8px 20px -8px var(--c1); }
.af-app-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.af-app-text b { color: #fff; font-size: 14.5px; }
.af-app-text small { font-size: 12px; color: #b7b3d9; line-height: 1.7; }
.af-tick { position: absolute; top: 10px; left: 10px; display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%;
  color: #fff; background: var(--c1); opacity: 0; transform: scale(.5); transition: opacity .2s, transform .25s cubic-bezier(.2,.9,.25,1.4); }
.af-app.on .af-tick { opacity: 1; transform: none; }

.af-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.af-chip { height: 38px; padding: 0 14px; border-radius: 12px; cursor: pointer; font: inherit; font-size: 13.5px; color: #dcd8ff;
  background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.14); }
.af-chip.on { color: #fff; background: rgba(143,133,255,.28); border-color: #8f85ff; }
.af-chip:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }
.af-date { display: flex; gap: 8px; margin-top: 4px; }
.af-date select { flex: 1; min-width: 0; height: 44px; padding: 0 10px; border-radius: 12px; font: inherit; font-size: 14px; color: #fff;
  background: rgba(10,9,32,.6); border: 1px solid rgba(255,255,255,.14); }
.af-date select:focus { outline: none; border-color: #8f85ff; box-shadow: 0 0 0 4px rgba(143,133,255,.22); }
.af-date option { color: #000; }
.af-end { display: flex; align-items: center; gap: 6px; margin: 2px 0 0; font-size: 12.5px; color: #b7b3d9; line-height: 1.8; }

.af-done { margin: 0; display: grid; gap: 10px; padding: 16px; border-radius: 16px; background: rgba(62,224,143,.08); border: 1px solid rgba(62,224,143,.3); }
.af-done div { display: flex; justify-content: space-between; gap: 12px; }
.af-done dt { color: #b7b3d9; font-size: 13.5px; }
.af-done dd { margin: 0; color: #fff; font-weight: 700; text-align: left; overflow-wrap: anywhere; }
.af-done dd[dir="ltr"] { font-size: 17px; letter-spacing: .05em; }
</style>
