<script setup>
// «دعوت‌نامه» (permanent account, from «دسترسی‌ها»): آقای or خانم and the guest's name, the assistants to show them,
// Persian or English, and the login to print in it (username, password, until when; all optional). The letter is drawn
// beside the form as it is filled in (lib/invite.js) and «دانلود PDF» saves it. One assistant: its problem, solution
// and gains; two or more: a general overview and their names. person: an access to start from (right after it is
// made, its password too). Nothing is sent to the server and nothing is kept.
import { ref, reactive, computed, watch, onMounted } from "vue"
import { access } from "../lib/access.js"
import { today as browserToday, format } from "../lib/jalali.js"
import { drawInvite, toPdf, PAGE } from "../lib/invite.js"
import Icon from "./Icon.vue"
import DatePicker from "./core/DatePicker.vue"
import TimePicker from "./core/TimePicker.vue"
import "./hub-dialog.css"

const props = defineProps({ assistants: Array, person: { type: Object, default: null } })
const emit = defineEmits(["close"])
const p = props.person || {}
const [day, hour] = (p.expires_on || "").split(" ")
const form = reactive({ hon: "", name: p.name || "", english: false, apps: p.apps ? [...p.apps] : [],
                        username: p.username || "", password: p.password || "", date: day || null, time: day ? hour || "23:55" : null })
const canvas = ref(null), drawing = ref(false), saving = ref(false), error = ref("")
const lang = computed(() => (form.english ? "en" : "fa"))
const ready = computed(() => form.name.trim().length >= 2 && form.apps.length > 0)
const toggle = (k) => { form.apps = form.apps.includes(k) ? form.apps.filter((x) => x !== k) : [...form.apps, k] }
const todayStr = computed(() => access.today || format(browserToday()))
watch(() => form.date, (d) => { if (!d) form.time = null; else if (!form.time) form.time = "20:00" })
const HONS = computed(() => form.english ? [["m", "Mr."], ["f", "Ms."], ["", "بدون عنوان"]] : [["m", "جناب آقای"], ["f", "سرکار خانم"], ["", "بدون عنوان"]])

// redrawn a moment after each change, so typing stays smooth
let timer
async function draw() {
  drawing.value = true
  try {
    const apps = props.assistants.filter((a) => form.apps.includes(a.key))
    const name = form.name.trim() || (form.english ? "Your guest" : "نام مهمان")
    const login = { username: form.username.trim(), password: form.password.trim(), expires: form.date ? `${form.date} ${form.time || "23:55"}` : "" }
    await drawInvite(canvas.value, { lang: lang.value, hon: form.hon, name, apps: apps.length ? apps : [props.assistants[0]], login, today: todayStr.value })
  } catch (e) { error.value = "پیش‌نمایش ساخته نشد: " + e.message }
  drawing.value = false
}
watch(form, () => { clearTimeout(timer); timer = setTimeout(draw, 220) }, { deep: true })
onMounted(draw)

async function download() {
  if (!ready.value) { error.value = form.apps.length ? "نام مهمان را بنویسید." : "دست‌کم یک دستیار را انتخاب کنید."; return }
  error.value = ""; saving.value = true
  try {
    clearTimeout(timer); await draw()
    const title = (form.english ? "Invitation - " : "دعوت‌نامه - ") + form.name.trim()
    const url = URL.createObjectURL(await toPdf(canvas.value, title))
    const a = document.createElement("a")
    a.href = url; a.download = title.replace(/[\\/:*?"<>|]/g, "").replace(/\u200c/g, " ") + ".pdf"   // Chrome turns the zero-width non-joiner of «دعوت‌نامه» into «_»
    document.body.appendChild(a); a.click(); a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 4000)
  } catch (e) { error.value = "PDF ساخته نشد: " + e.message }
  saving.value = false
}
</script>

<template>
  <div class="hd-overlay" @click.self="emit('close')">
    <section class="hd iv" v-pop role="dialog" aria-label="دعوت‌نامه">
      <div class="hd-head">
        <div><h3>دعوت‌نامه</h3><p>نام مهمان و دستیارها را انتخاب کنید؛ دعوت‌نامه کنار فرم ساخته می‌شود. چیزی جایی ذخیره نمی‌شود.</p></div>
        <button type="button" class="hd-x" aria-label="بستن" @click="emit('close')"><Icon name="x" :size="18" /></button>
      </div>

      <div class="iv-body">
        <form class="iv-form" @submit.prevent="download" novalidate>
          <div class="hd-field">
            <span class="hd-label">عنوان</span>
            <div class="iv-seg" role="radiogroup" aria-label="عنوان">
              <button v-for="[k, t] in HONS" :key="k" type="button" role="radio" :aria-checked="form.hon === k" :class="{ on: form.hon === k }" @click="form.hon = k">{{ t }}</button>
            </div>
          </div>
          <label class="hd-field">
            <span class="hd-label">نام و نام خانوادگی مهمان</span>
            <span class="hd-input"><Icon name="user" :size="19" />
              <input v-model="form.name" maxlength="60" :dir="form.english ? 'ltr' : 'rtl'" :placeholder="form.english ? 'e.g. Sara Ahmadi' : 'مثلاً سارا احمدی'" autocomplete="off" /></span>
          </label>

          <button type="button" role="switch" :aria-checked="form.english" :class="['iv-switch', { on: form.english }]" @click="form.english = !form.english">
            <span class="iv-switch-text"><b>دعوت‌نامه به انگلیسی</b><small>{{ form.english ? "همه‌ی متن‌ها و نام‌ها انگلیسی است؛ نام مهمان را هم انگلیسی بنویسید." : "متن فارسی است." }}</small></span>
            <span class="iv-knob" aria-hidden="true"><i></i></span>
          </button>

          <div class="hd-field">
            <span class="hd-label">کدام دستیارها <small class="iv-hint">{{ form.apps.length === 1 ? "توضیح همین دستیار در دعوت‌نامه می‌آید" : form.apps.length > 1 ? "یک معرفی کلی با نام دستیارها می‌آید" : "دست‌کم یکی" }}</small></span>
            <div class="iv-apps">
              <button v-for="a in assistants" :key="a.key" type="button" :class="['iv-app', 'hue-' + a.hue, { on: form.apps.includes(a.key) }]"
                      :aria-pressed="form.apps.includes(a.key)" @click="toggle(a.key)">
                <span class="iv-app-icon"><Icon :name="a.icon" :size="18" /></span><span class="iv-app-name">{{ a.title }}</span>
                <span class="iv-tick"><Icon name="check" :size="12" /></span>
              </button>
            </div>
          </div>

          <div class="hd-field">
            <span class="hd-label">اطلاعات ورود <small class="iv-hint">اختیاری؛ خالی بماند یعنی «جداگانه فرستاده می‌شود»</small></span>
            <div class="iv-two">
              <span class="hd-input"><Icon name="userCheck" :size="18" /><input v-model="form.username" maxlength="30" dir="ltr" placeholder="نام کاربری" autocomplete="off" spellcheck="false" aria-label="نام کاربری" /></span>
              <span class="hd-input"><Icon name="lock" :size="18" /><input v-model="form.password" maxlength="100" dir="ltr" placeholder="رمز عبور" autocomplete="off" spellcheck="false" aria-label="رمز عبور" /></span>
            </div>
            <div class="iv-when">
              <div class="iv-picker"><DatePicker v-model="form.date" :min="todayStr" clearable label="معتبر تا" placeholder="معتبر تا (بدون تاریخ)" /></div>
              <div class="iv-picker"><TimePicker v-model="form.time" :disabled="!form.date" label="ساعت" /></div>
            </div>
          </div>

          <p class="hd-error" role="alert">{{ error }}</p>
          <button class="hd-btn" :disabled="saving"><span v-if="saving" class="hd-spin" aria-hidden="true"></span><Icon v-else name="file" :size="18" />دانلود PDF</button>
        </form>

        <div class="iv-preview" :class="{ busy: drawing }">
          <span class="iv-preview-label"><Icon name="eye" :size="15" />پیش‌نمایش</span>
          <canvas ref="canvas" :width="PAGE.w" :height="PAGE.h" role="img" aria-label="پیش‌نمایش دعوت‌نامه"></canvas>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hd.iv { width: min(100%, 1080px); }
.iv-body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; align-items: start; }
.iv-form { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.iv-hint { font-weight: 400; color: #9a96c4; margin-inline-start: 6px; }
.iv-switch { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; border-radius: 14px; cursor: pointer; text-align: right; font: inherit; color: inherit;
  background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12); }
.iv-switch:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }
.iv-switch-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.iv-switch-text b { color: #fff; font-size: 14px; }
.iv-switch-text small { color: #b7b3d9; font-size: 12px; line-height: 1.7; }
.iv-knob { flex: none; position: relative; width: 46px; height: 26px; border-radius: 999px; background: rgba(255,255,255,.18); transition: background .2s; }
.iv-knob i { position: absolute; top: 3px; right: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; transition: transform .25s; }
.iv-switch.on .iv-knob { background: #6a5cf5; }
.iv-switch.on .iv-knob i { transform: translateX(-20px); }
.iv-apps { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 200px), 1fr)); gap: 8px; }
.iv-app { --c1: #7367f0; --c2: #00bad1; position: relative; display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 12px; cursor: pointer; text-align: right;
  font: inherit; font-size: 13px; color: #dcd8ff; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12); transition: border-color .2s, background .2s; }
.iv-app.hue-teal { --c1: #0f8b7d; --c2: #f3b33d; }
.iv-app.hue-rose { --c1: #b23a62; --c2: #36c2a3; }
.iv-app.hue-indigo { --c1: #3c4a8f; --c2: #e0a785; }
.iv-app.hue-sky { --c1: #1d6fa3; --c2: #f28b82; }
.iv-app.hue-ocean { --c1: #0d5c7a; --c2: #e8c27a; }
.iv-app.hue-clay { --c1: #8a4320; --c2: #f2c27a; }
.iv-app.hue-amber { --c1: #8a5a1c; --c2: #5fb3f0; }
.iv-app.hue-cobalt { --c1: #2a5bd0; --c2: #f5b82e; }
.iv-app:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }
.iv-app.on { border-color: color-mix(in srgb, var(--c1) 70%, #fff); background: color-mix(in srgb, var(--c1) 22%, transparent); }
.iv-app-icon { flex: none; display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; color: #fff;
  background: linear-gradient(140deg, var(--c1), color-mix(in srgb, var(--c2) 70%, var(--c1))); }
.iv-app-name { flex: 1; min-width: 0; line-height: 1.6; color: #fff; padding-left: 20px; }
.iv-tick { position: absolute; top: 50%; left: 10px; display: grid; place-items: center; width: 20px; height: 20px; margin-top: -10px; border-radius: 50%;
  color: #fff; background: var(--c1); opacity: 0; transform: scale(.5); transition: opacity .2s, transform .25s; }
.iv-app.on .iv-tick { opacity: 1; transform: none; }
.iv-seg { display: flex; gap: 6px; padding: 4px; border-radius: 14px; background: rgba(10,9,32,.5); border: 1px solid rgba(255,255,255,.12); }
.iv-seg button { flex: 1; height: 38px; border: 0; border-radius: 10px; cursor: pointer; font: inherit; font-size: 13.5px; color: #cfcbf3; background: transparent; white-space: nowrap; }
.iv-seg button.on { color: #fff; background: #6a5cf5; font-weight: 700; }
.iv-seg button:focus-visible { outline: 3px solid #8fefff; outline-offset: 1px; }
.iv-two, .iv-when { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.iv-when { grid-template-columns: 2fr 1fr; margin-top: 10px; }
.iv-two > *, .iv-when > * { min-width: 0; }
.iv-picker { --dp-panel: #1c1a3f; --dp-field-bg: rgba(10,9,32,.6); --dp-field-line: rgba(255,255,255,.14); --dp-text: #fff; --dp-muted: #9a96c4; --dp-accent: #8f85ff; }
.iv-picker :deep(.dp-field) { --dp-panel: inherit; --dp-field-bg: inherit; --dp-field-line: inherit; --dp-text: inherit; --dp-muted: inherit; --dp-accent: inherit; height: 50px; border-radius: 14px; }
@media (max-width: 480px) { .iv-two { grid-template-columns: 1fr; } }
.iv-preview { position: sticky; top: 0; display: flex; flex-direction: column; gap: 8px; }
.iv-preview-label { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: #d6d3f5; }
.iv-preview canvas { width: 100%; height: auto; aspect-ratio: 1654 / 2339; border-radius: 10px; background: #fff; box-shadow: 0 20px 50px -20px rgba(0,0,0,.8); transition: opacity .2s; }
.iv-preview.busy canvas { opacity: .75; }
@media (max-width: 820px) {
  .iv-body { grid-template-columns: 1fr; }
  .iv-preview { position: static; }
}
</style>
