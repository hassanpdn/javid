<script setup>
// Give or change one person's access (permanent account only, access.py): their name, username and password (both made
// here for a new access), the assistants they may open (one or more), and an optional expiry date and time. With
// «دعوت‌نامه‌ی PDF» ticked, the invitation letter for the same person is drawn beside the form (آقای/خانم, Persian or
// English; lib/invite.js) and downloaded as soon as the access is saved, with this username and password in it.
// After saving with a password, a text ready to send. invite: open with the letter already ticked (a person's card).
import { ref, reactive, computed, watch, onMounted, nextTick } from "vue"
import { access, accessCall, checkAccess } from "../lib/access.js"
import { today as browserToday, jalaliText, format } from "../lib/jalali.js"
import Icon from "./Icon.vue"
import { drawInvite, toPdf, PAGE } from "../lib/invite.js"
import DatePicker from "./core/DatePicker.vue"
import TimePicker from "./core/TimePicker.vue"
import "./hub-dialog.css"

const props = defineProps({ assistants: Array, person: { type: Object, default: null }, invite: { type: Boolean, default: false } })
const emit = defineEmits(["close", "saved"])
const editing = !!props.person

// Today and now come from the server's clock (access.today, access.now); the browser's only if the server hasn't said.
const todayStr = computed(() => access.today || format(browserToday()))
const nowStr = computed(() => access.now || new Date().toTimeString().slice(0, 5))
// an access saved before times existed has only a date: it ended at the end of that day
const [oldDate, oldTime] = (props.person?.expires_on || "").split(" ")

const form = reactive({
  name: props.person?.name || "", username: props.person?.username || "", password: "",
  apps: props.person ? [...props.person.apps] : [props.assistants[0].key],
  date: oldDate || null, time: oldDate ? oldTime || "23:55" : null,   // no date = no expiry
})
// on today, times before now are out; a new date gets 20:00, or the next full hour when today is already past it
const minTime = computed(() => form.date === todayStr.value ? nowStr.value : null)
watch(() => form.date, (d) => {
  if (!d) { form.time = null; return }
  const min = minTime.value
  if (!form.time) form.time = "20:00"
  if (min && form.time <= min) {
    const next = Number(min.slice(0, 2)) + 1
    form.time = next <= 23 ? `${String(next).padStart(2, "0")}:00` : "23:55"
  }
})
const expiresOn = computed(() => form.date ? `${form.date} ${form.time || "23:55"}` : null)
const show = ref(!editing), error = ref(""), sending = ref(false), done = ref(null), copied = ref(false)
const nameEl = ref(null)
onMounted(() => {
  checkAccess()   // a fresh «today» and «now» from the server
  if (window.matchMedia("(min-width: 768px)").matches) nameEl.value?.focus()
})

// a password that is easy to read out on the phone: no 0/O or 1/l
const makePassword = () => {
  const abc = "abcdefghjkmnpqrstuvwxyz23456789", bytes = crypto.getRandomValues(new Uint8Array(8))
  form.password = Array.from(bytes, (b) => abc[b % abc.length]).join("")
  show.value = true
}
// a username nobody has to think of: «pd» and five letters or digits, easy to read out (the server says if it is taken)
const makeUsername = () => {
  const abc = "abcdefghjkmnpqrstuvwxyz23456789", bytes = crypto.getRandomValues(new Uint8Array(5))
  form.username = "pd" + Array.from(bytes, (b) => abc[b % abc.length]).join("")
}
if (!editing) { makePassword(); makeUsername() }

// ---------- the invitation letter ----------
const letter = reactive({ on: !editing || props.invite, hon: "", english: false })
const canvas = ref(null), drawing = ref(false)
const HONS = computed(() => letter.english ? [["m", "Mr."], ["f", "Ms."], ["", "بدون عنوان"]] : [["m", "جناب آقای"], ["f", "سرکار خانم"], ["", "بدون عنوان"]])
const chosen = () => props.assistants.filter((a) => form.apps.includes(a.key))
async function draw() {
  if (!letter.on || !canvas.value) return
  drawing.value = true
  try {
    const apps = chosen()
    const name = form.name.trim() || (letter.english ? "Your guest" : "نام مهمان")
    await drawInvite(canvas.value, { lang: letter.english ? "en" : "fa", hon: letter.hon, name, apps: apps.length ? apps : [props.assistants[0]], today: todayStr.value,
                                     login: { username: form.username.trim(), password: form.password.trim(), expires: expiresOn.value || "" } })
  } catch (e) { error.value = "پیش‌نمایش دعوت‌نامه ساخته نشد: " + e.message }
  drawing.value = false
}
// redrawn a moment after each change, so typing stays smooth
let timer
watch([form, letter], () => { clearTimeout(timer); timer = setTimeout(draw, 220) }, { deep: true })
watch(() => letter.on, (on) => { if (on) nextTick(draw) })
onMounted(() => nextTick(draw))
// the PDF is made in this browser and downloaded; nothing of it goes to the server
async function download() {
  clearTimeout(timer); await draw()
  const title = (letter.english ? "Invitation - " : "دعوت‌نامه - ") + form.name.trim()
  const url = URL.createObjectURL(await toPdf(canvas.value, title))
  const a = document.createElement("a")
  a.href = url; a.download = title.replace(/[\\/:*?"<>|]/g, "").replace(/\u200c/g, " ") + ".pdf"   // Chrome turns the zero-width non-joiner of «دعوت‌نامه» into «_»
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 4000)
}
// phones: once the keyboard is up (the sheet has shrunk to the visible part), keep the field being typed in on screen
const keepInView = (e) => { if (e.target.matches("input")) setTimeout(() => e.target.scrollIntoView({ block: "center", behavior: "smooth" }), 320) }

const toggle = (key) => {
  form.apps = form.apps.includes(key) ? form.apps.filter((k) => k !== key) : [...form.apps, key]
}
const names = (apps) => apps.map((k) => props.assistants.find((a) => a.key === k)?.title || k).join("، ")

const save = async () => {
  if (sending.value) return
  if (!form.name.trim()) { error.value = "اسم این شخص را بنویسید."; return }
  if (!form.username.trim()) { error.value = "یک نام کاربری بنویسید."; return }
  if (!editing && !form.password) { error.value = "یک رمز عبور بنویسید یا «رمز جدید» را انتخاب کنید."; return }
  if (!form.apps.length) { error.value = "دست‌کم یک دستیار را انتخاب کنید."; return }
  sending.value = true; error.value = ""
  try {
    const body = { name: form.name, username: form.username, password: form.password, apps: form.apps, expires_on: expiresOn.value }
    const p = await accessCall(editing ? `/access/people/${props.person.id}` : "/access/people", body)
    emit("saved")
    if (letter.on) { try { await download() } catch (e) { error.value = "دسترسی ذخیره شد ولی PDF ساخته نشد: " + e.message; sending.value = false; return } }
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
        <div><dt>تا</dt><dd>{{ done.expires_on ? jalaliText(done.expires_on) : "بدون تاریخ انقضا" }}</dd></div>
      </dl>
      <button type="button" class="hd-btn" @click="copy"><Icon :name="copied ? 'check' : 'file'" :size="18" />{{ copied ? "کپی شد" : "کپی متن برای فرستادن" }}</button>
      <button v-if="letter.on" type="button" class="hd-ghost" @click="download"><Icon name="file" :size="16" />دانلود دوباره‌ی دعوت‌نامه</button>
    </section>

    <form v-else :class="['hd', 'wide', { 'af-letter': letter.on }]" v-pop @submit.prevent="save" @focusin="keepInView" novalidate>
      <div class="hd-head">
        <div>
          <h3>{{ editing ? `دسترسی ${person.name}` : "دسترسی جدید" }}</h3>
          <p>چه کسی، با چه رمزی، کدام دستیار را ببیند؛ و اگر بخواهید، دعوت‌نامه‌ی PDF برای همین شخص.</p>
        </div>
        <button type="button" class="hd-x" aria-label="بستن" @click="emit('close')"><Icon name="x" :size="18" /></button>
      </div>

      <div class="af-body">
      <div class="af-fields">
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
          <button type="button" class="af-gen" @click="makeUsername"><Icon name="refresh" :size="14" />نام کاربری جدید</button>
        </label>
        <label class="hd-field">
          <span class="hd-label">رمز عبور</span>
          <span class="hd-input"><Icon name="lock" :size="19" />
            <input v-model="form.password" :type="show ? 'text' : 'password'" maxlength="100" dir="ltr" autocomplete="new-password" spellcheck="false"
                   :placeholder="editing ? 'خالی = همان رمز قبلی' : ''" />
            <button type="button" class="hd-eye" :aria-label="show ? 'پنهان کردن رمز' : 'نشان دادن رمز'" :aria-pressed="show" @click="show = !show"><Icon :name="show ? 'eyeOff' : 'eye'" :size="19" /></button>
          </span>
          <button type="button" class="af-gen" @click="makePassword"><Icon name="refresh" :size="14" />رمز جدید</button>
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
        <span class="hd-label">تاریخ انقضای دسترسی</span>
        <div class="af-when">
          <div class="af-picker"><DatePicker v-model="form.date" :min="todayStr" clearable label="تاریخ انقضا" placeholder="بدون تاریخ انقضا" /></div>
          <div class="af-picker"><TimePicker v-model="form.time" :min="minTime" :disabled="!form.date" label="ساعت انقضا" /></div>
        </div>
        <p class="af-end"><Icon name="info" :size="15" />{{ expiresOn ? `تا ${jalaliText(expiresOn)} باز است، بعد خودش بسته می‌شود.` : "خالی بماند یعنی تاریخ انقضا ندارد و تا وقتی خودتان پاکش نکنید باز است." }}</p>
      </div>

      <button type="button" role="switch" :aria-checked="letter.on" :class="['af-switch', { on: letter.on }]" @click="letter.on = !letter.on">
        <span class="af-switch-text"><b>دعوت‌نامه‌ی PDF هم ساخته شود</b>
          <small>{{ letter.on ? "پس از ذخیره، دعوت‌نامه با همین نام کاربری و رمز دانلود می‌شود. جایی ذخیره نمی‌شود." : "فقط دسترسی ساخته می‌شود." }}</small></span>
        <span class="af-knob" aria-hidden="true"><i></i></span>
      </button>
      <template v-if="letter.on">
        <div class="hd-field">
          <span class="hd-label">عنوان در دعوت‌نامه</span>
          <div class="af-seg" role="radiogroup" aria-label="عنوان">
            <button v-for="[k, t] in HONS" :key="k" type="button" role="radio" :aria-checked="letter.hon === k" :class="{ on: letter.hon === k }" @click="letter.hon = k">{{ t }}</button>
          </div>
        </div>
        <button type="button" role="switch" :aria-checked="letter.english" :class="['af-switch', 'sub', { on: letter.english }]" @click="letter.english = !letter.english">
          <span class="af-switch-text"><b>دعوت‌نامه به انگلیسی</b><small>{{ letter.english ? "همه‌ی متن‌ها و نام‌ها انگلیسی است؛ اسم را هم انگلیسی بنویسید." : "متن فارسی است." }}</small></span>
          <span class="af-knob" aria-hidden="true"><i></i></span>
        </button>
        <p v-if="editing && !form.password" class="af-end"><Icon name="info" :size="15" />رمز فعلی دیده نمی‌شود؛ برای آمدن رمز در دعوت‌نامه «رمز جدید» را بزنید، وگرنه در آن نوشته می‌شود «جداگانه فرستاده می‌شود».</p>
      </template>

      <p class="hd-error" role="alert">{{ error }}</p>
      <button class="hd-btn" :disabled="sending"><span v-if="sending" class="hd-spin" aria-hidden="true"></span>
        <Icon v-else-if="letter.on" name="file" :size="18" />{{ (editing ? "ذخیره" : "دادن دسترسی") + (letter.on ? " و دانلود دعوت‌نامه" : "") }}</button>
      </div>

      <div v-if="letter.on" :class="['af-preview', { busy: drawing }]">
        <span class="af-preview-label"><Icon name="eye" :size="15" />پیش‌نمایش دعوت‌نامه</span>
        <canvas ref="canvas" :width="PAGE.w" :height="PAGE.h" role="img" aria-label="پیش‌نمایش دعوت‌نامه"></canvas>
      </div>
      </div>
    </form>
  </div>
</template>

<style scoped>
/* with the letter: the form on one side, its preview on the other (one under the other on phones) */
.hd.wide.af-letter { width: min(100%, 1120px); }
.af-body { display: flex; flex-direction: column; gap: 14px; }
.af-fields { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.af-letter .af-body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .9fr); gap: 22px; align-items: start; }
.af-preview { position: sticky; top: 0; display: flex; flex-direction: column; gap: 8px; }
.af-preview-label { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: #d6d3f5; }
.af-preview canvas { width: 100%; height: auto; aspect-ratio: 1654 / 2339; border-radius: 10px; background: #fff; box-shadow: 0 20px 50px -20px rgba(0,0,0,.8); transition: opacity .2s; }
.af-preview.busy canvas { opacity: .75; }
@media (max-width: 860px) { .af-letter .af-body { grid-template-columns: 1fr; } .af-preview { position: static; } }
.af-switch { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; border-radius: 14px; cursor: pointer; text-align: right; font: inherit; color: inherit;
  background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12); }
.af-switch.on:not(.sub) { border-color: rgba(143,133,255,.6); background: rgba(106,92,245,.14); }
.af-switch:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }
.af-switch-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.af-switch-text b { color: #fff; font-size: 14px; }
.af-switch-text small { color: #b7b3d9; font-size: 12px; line-height: 1.7; }
.af-knob { flex: none; position: relative; width: 46px; height: 26px; border-radius: 999px; background: rgba(255,255,255,.18); transition: background .2s; }
.af-knob i { position: absolute; top: 3px; right: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; transition: transform .25s; }
.af-switch.on .af-knob { background: #6a5cf5; }
.af-switch.on .af-knob i { transform: translateX(-20px); }
.af-seg { display: flex; gap: 6px; padding: 4px; border-radius: 14px; background: rgba(10,9,32,.5); border: 1px solid rgba(255,255,255,.12); }
.af-seg button { flex: 1; height: 38px; border: 0; border-radius: 10px; cursor: pointer; font: inherit; font-size: 13.5px; color: #cfcbf3; background: transparent; white-space: nowrap; }
.af-seg button.on { color: #fff; background: #6a5cf5; font-weight: 700; }
.af-seg button:focus-visible { outline: 3px solid #8fefff; outline-offset: 1px; }
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
.af-app.hue-rose { --c1: #b23a62; --c2: #36c2a3; }
.af-app.hue-indigo { --c1: #3c4a8f; --c2: #e0a785; }
.af-app.hue-sky { --c1: #1d6fa3; --c2: #f28b82; }
.af-app.hue-ocean { --c1: #0d5c7a; --c2: #e8c27a; }
.af-app.hue-clay { --c1: #8a4320; --c2: #f2c27a; }
.af-app.hue-cobalt { --c1: #2a5bd0; --c2: #f5b82e; }
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

/* date and time side by side, looking like the other inputs of this always-dark dialog */
.af-when { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; }
.af-when > * { min-width: 0; }
.af-picker { --dp-panel: #1c1a3f; --dp-field-bg: rgba(10,9,32,.6); --dp-field-line: rgba(255,255,255,.14); --dp-text: #fff; --dp-muted: #9a96c4; --dp-accent: #8f85ff; }
.af-picker :deep(.dp-field) { --dp-panel: inherit; --dp-field-bg: inherit; --dp-field-line: inherit; --dp-text: inherit; --dp-muted: inherit; --dp-accent: inherit; height: 50px; border-radius: 14px; }
.af-end { display: flex; align-items: center; gap: 6px; margin: 2px 0 0; font-size: 12.5px; color: #b7b3d9; line-height: 1.8; }

.af-done { margin: 0; display: grid; gap: 10px; padding: 16px; border-radius: 16px; background: rgba(62,224,143,.08); border: 1px solid rgba(62,224,143,.3); }
.af-done div { display: flex; justify-content: space-between; gap: 12px; }
.af-done dt { color: #b7b3d9; font-size: 13.5px; }
.af-done dd { margin: 0; color: #fff; font-weight: 700; text-align: left; overflow-wrap: anywhere; }
.af-done dd[dir="ltr"] { font-size: 17px; letter-spacing: .05em; }
</style>
