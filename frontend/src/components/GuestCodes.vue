<script setup>
// Guest codes, for the permanent account only (access.py): a username and a one-time password for chosen assistants
// and a set time. The password is shown once, right after it is made, with a text ready to send.
import { ref, reactive, onMounted } from "vue"
import Icon from "./Icon.vue"
import "./hub-dialog.css"

const props = defineProps({ assistants: Array })
const emit = defineEmits(["close"])
const DURATIONS = [{ hours: 2, text: "۲ ساعت" }, { hours: 24, text: "۱ روز" }, { hours: 72, text: "۳ روز" }, { hours: 168, text: "۷ روز" }]
const STATES = { waiting: "هنوز وارد نشده", in: "وارد شده", expired: "وقتش تمام شده", ended: "بسته شده" }

const form = reactive({ label: "", apps: props.assistants.map((a) => a.key), hours: 24 })
const made = ref(null), list = ref([]), error = ref(""), sending = ref(false), copied = ref(false)

// e.g. «۵ آبان، ساعت ۱۸:۳۰»
const when = (sec) => {
  const d = new Date(sec * 1000)
  return `${d.toLocaleDateString("fa-IR", { day: "numeric", month: "long" })}، ساعت ${d.toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" })}`
}
const names = (apps) => apps.map((k) => props.assistants.find((a) => a.key === k)?.title || k).join("، ")

const call = async (path, body) => {
  const res = await fetch(path, { method: body ? "POST" : "GET", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "کار انجام نشد. دوباره امتحان کنید.")
  return data
}
const load = async () => { try { list.value = await call("/access/guests") } catch {} }
onMounted(load)

const toggle = (key) => {
  form.apps = form.apps.includes(key) ? form.apps.filter((k) => k !== key) : [...form.apps, key]
}
const make = async () => {
  if (sending.value) return
  if (!form.label.trim()) { error.value = "بنویسید رمز را به چه کسی می‌دهید."; return }
  if (!form.apps.length) { error.value = "دست‌کم یک دستیار را انتخاب کنید."; return }
  sending.value = true; error.value = ""
  try {
    made.value = await call("/access/guests", { label: form.label, apps: form.apps, hours: form.hours })
    form.label = ""; copied.value = false
    await load()
  } catch (e) { error.value = e.message }
  sending.value = false
}
const message = (g) => [
  `آدرس: ${location.origin}`, `نام کاربری: ${g.username}`, `رمز عبور: ${g.password}`,
  `این رمز فقط یک بار کار می‌کند و تا ${when(g.expires_at)} معتبر است.`,
].join("\n")
const copy = async () => {
  try { await navigator.clipboard.writeText(message(made.value)); copied.value = true } catch {}
}
const end = async (g) => {
  try { await call(`/access/guests/${g.id}/end`, {}); await load() } catch {}
}
</script>

<template>
  <div class="hd-overlay" @click.self="emit('close')">
    <section class="hd wide" v-pop>
      <div class="hd-head">
        <div>
          <h3>رمزهای مهمان</h3>
          <p>رمز یک‌بار مصرف برای کسی که می‌خواهد دمو را خودش ببیند.</p>
        </div>
        <button type="button" class="hd-x" aria-label="بستن" @click="emit('close')"><Icon name="x" :size="18" /></button>
      </div>

      <div v-if="made" class="gc-made">
        <div class="gc-made-head"><Icon name="check" :size="18" />رمز «{{ made.label }}» ساخته شد</div>
        <dl>
          <div><dt>نام کاربری</dt><dd dir="ltr">{{ made.username }}</dd></div>
          <div><dt>رمز عبور</dt><dd dir="ltr">{{ made.password }}</dd></div>
          <div><dt>دستیار</dt><dd>{{ names(made.apps) }}</dd></div>
          <div><dt>تا</dt><dd>{{ when(made.expires_at) }}</dd></div>
        </dl>
        <p class="gc-note">این رمز را فقط همین حالا می‌بینید. یک بار کار می‌کند؛ بعد از ورود، همان مرورگر تا آخر وقت داخل می‌ماند.</p>
        <div class="gc-made-actions">
          <button type="button" class="hd-btn" @click="copy"><Icon :name="copied ? 'check' : 'file'" :size="18" />{{ copied ? "کپی شد" : "کپی متن برای فرستادن" }}</button>
          <button type="button" class="hd-ghost" @click="made = null; load()">رمز تازه</button>
        </div>
      </div>

      <form v-else class="gc-form" @submit.prevent="make" novalidate>
        <label class="hd-field">
          <span class="hd-label">برای چه کسی؟</span>
          <span class="hd-input"><Icon name="user" :size="19" /><input v-model="form.label" maxlength="60" placeholder="مثلاً مدیر دبستان نمونه" /></span>
        </label>
        <div class="hd-field">
          <span class="hd-label">کدام دستیار</span>
          <div class="gc-chips">
            <button v-for="a in assistants" :key="a.key" type="button" :class="['gc-chip', { on: form.apps.includes(a.key) }]"
                    :aria-pressed="form.apps.includes(a.key)" @click="toggle(a.key)">
              <Icon :name="form.apps.includes(a.key) ? 'check' : a.icon" :size="16" />{{ a.title }}
            </button>
          </div>
        </div>
        <div class="hd-field">
          <span class="hd-label">تا کی کار کند</span>
          <div class="gc-chips">
            <button v-for="d in DURATIONS" :key="d.hours" type="button" :class="['gc-chip', { on: form.hours === d.hours }]"
                    :aria-pressed="form.hours === d.hours" @click="form.hours = d.hours">{{ d.text }}</button>
          </div>
        </div>
        <p class="hd-error" role="alert">{{ error }}</p>
        <button class="hd-btn" :disabled="sending"><span v-if="sending" class="hd-spin" aria-hidden="true"></span>ساختن رمز</button>
      </form>

      <div v-if="list.length" class="gc-list">
        <h4>رمزهای ساخته‌شده</h4>
        <ul>
          <li v-for="g in list" :key="g.id" :class="'s-' + g.state">
            <div class="gc-row">
              <b>{{ g.label }}</b>
              <span class="gc-state">{{ STATES[g.state] }}</span>
            </div>
            <div class="gc-meta">
              <span dir="ltr">{{ g.username }}</span>
              <span>{{ names(g.apps) }}</span>
              <span>تا {{ when(g.expires_at) }}</span>
            </div>
            <button v-if="g.state === 'waiting' || g.state === 'in'" type="button" class="hd-ghost gc-end" @click="end(g)">
              {{ g.state === "in" ? "بیرون کردن" : "باطل کردن" }}
            </button>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gc-form { display: flex; flex-direction: column; gap: 14px; }
.gc-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.gc-chip { display: inline-flex; align-items: center; gap: 6px; height: 40px; padding: 0 14px; border-radius: 12px; cursor: pointer;
  font: inherit; font-size: 14px; color: #dcd8ff; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.14); }
.gc-chip.on { color: #fff; background: rgba(143,133,255,.28); border-color: #8f85ff; }
.gc-chip:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }

.gc-made { display: flex; flex-direction: column; gap: 12px; padding: 16px; border-radius: 16px; background: rgba(62,224,143,.08); border: 1px solid rgba(62,224,143,.3); }
.gc-made-head { display: flex; align-items: center; gap: 8px; font-weight: 700; color: #7ef0b0; }
.gc-made dl { margin: 0; display: grid; gap: 8px; }
.gc-made dl div { display: flex; justify-content: space-between; gap: 12px; }
.gc-made dt { color: #b7b3d9; font-size: 13.5px; }
.gc-made dd { margin: 0; color: #fff; font-weight: 700; text-align: left; }
.gc-made dd[dir="ltr"] { font-size: 17px; letter-spacing: .06em; }
.gc-note { margin: 0; font-size: 13px; line-height: 1.9; color: #c3bfe6; }
.gc-made-actions { display: flex; gap: 10px; align-items: center; }
.gc-made-actions .hd-btn { flex: 1; }
.gc-made-actions .hd-ghost { height: 50px; padding: 0 16px; }

.gc-list h4 { margin: 4px 0 8px; font-size: 14px; color: #d6d3f5; }
.gc-list ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
.gc-list li { position: relative; display: flex; flex-direction: column; gap: 4px; padding: 12px 14px; border-radius: 14px;
  background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1); }
.gc-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.gc-row b { color: #fff; font-size: 14.5px; min-width: 0; overflow-wrap: anywhere; }
.gc-state { flex: none; padding: 2px 10px; border-radius: 999px; font-size: 12px; color: #dcd8ff; background: rgba(255,255,255,.08); }
.s-in .gc-state { color: #7ef0b0; background: rgba(62,224,143,.14); }
.s-waiting .gc-state { color: #ffd38a; background: rgba(255,176,87,.14); }
.s-expired, .s-ended { opacity: .6; }
.gc-meta { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12.5px; color: #b7b3d9; }
.gc-end { align-self: flex-start; margin-top: 6px; }
</style>
