<script setup>
// Give or change one person's access (permanent account only, access.py): their name, username and password, the
// assistants they may open (one or more), and an optional expiry date and time. After saving with a password, a text ready to send.
import { ref, reactive, computed, watch, onMounted } from "vue"
import { access, accessCall, checkAccess } from "../lib/access.js"
import { today as browserToday, jalaliText, format } from "../lib/jalali.js"
import Icon from "./Icon.vue"
import DatePicker from "./core/DatePicker.vue"
import TimePicker from "./core/TimePicker.vue"
import "./hub-dialog.css"

const props = defineProps({ assistants: Array, person: { type: Object, default: null } })
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
if (!editing) makePassword()

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
    </section>

    <form v-else class="hd wide" v-pop @submit.prevent="save" novalidate>
      <div class="hd-head">
        <div>
          <h3>{{ editing ? `دسترسی ${person.name}` : "دسترسی جدید" }}</h3>
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
