<script setup>
// The deed data extraction assistant: send a scanned booklet deed (image or PDF) or paste its text, or open one of
// the three made-up samples; the list shows every deed and where it is; one opens for review (DeedReview).
// The file is checked here first (type and size) so a wrong file gets its message at once; the server checks again.
import { ref, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { fa } from "../lib/api.js"
import { gate } from "../lib/gate.js"
import Icon from "../components/Icon.vue"
import { getInfo, listDocs, uploadFile, pasteText, openSample, STATUS } from "./lib.js"
// the review screen is downloaded only when a deed is opened
const DeedReview = defineAsyncComponent(() => import("./DeedReview.vue"))

const info = ref(null), docs = ref([]), open = ref(null), error = ref(""), busy = ref(""), text = ref(""), pasting = ref(false)
const fileInput = ref(null)
let timer = null

async function refresh() {
  try { docs.value = await listDocs() } catch (e) { error.value = e.message }
  clearTimeout(timer)
  if (!open.value && docs.value.some((d) => d.status === "processing")) timer = setTimeout(refresh, 1500)
}
onMounted(async () => {
  document.title = "دستیار استخراج داده‌ی سند"
  try { info.value = await getInfo() } catch (e) { error.value = e.message }
  refresh()
})
onUnmounted(() => clearTimeout(timer))

const OK = ["image/png", "image/jpeg", "application/pdf"]
async function send(file) {
  error.value = ""
  if (!file) return
  if (!OK.includes(file.type)) { error.value = "فقط تصویر (JPG یا PNG) یا PDF پذیرفته می‌شود."; return }
  if (file.size > info.value.max_mb * 1024 * 1024) { error.value = `حجم فایل بیش از ${fa(info.value.max_mb)} مگابایت است.`; return }
  busy.value = "file"
  try {
    const data = await new Promise((ok, fail) => {
      const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = fail; r.readAsDataURL(file)
    })
    const d = await uploadFile(file.name, data)
    open.value = d.id
  } catch (e) { error.value = e.message }
  finally { busy.value = ""; if (fileInput.value) fileInput.value.value = "" }
}
const dropped = (e) => send(e.dataTransfer.files[0])
async function paste() {
  if (!text.value.trim()) { error.value = "متن سند را بنویسید یا بچسبانید."; return }
  busy.value = "text"; error.value = ""
  try { open.value = (await pasteText("", text.value)).id; text.value = ""; pasting.value = false }
  catch (e) { error.value = e.message }
  finally { busy.value = "" }
}
async function sample(key) {
  busy.value = key; error.value = ""
  try { open.value = (await openSample(key)).id } catch (e) { error.value = e.message }
  finally { busy.value = "" }
}
const back = () => { open.value = null; refresh() }
</script>

<template>
  <div class="dz">
    <header class="dz-bar">
      <div class="dz-brand"><span class="logo">س</span><div><b>دستیار استخراج داده‌ی سند</b><small>از سند دفترچه‌ای تا داده‌ی آماده‌ی سند تک‌برگ</small></div></div>
      <button v-if="gate.hub" class="link small" @click="gate.app = ''">همه‌ی دستیارها</button>
    </header>

    <main class="dz-main">
      <DeedReview v-if="open" :key="open" :id="open" @back="back" />

      <template v-else>
        <p v-if="error" class="error-text" role="alert">{{ error }}</p>
        <p v-if="info && !info.ocr" class="error-text" role="alert">ابزار خواندن متن (Tesseract با زبان فارسی) روی سرور نصب نیست؛ فعلاً فقط متن واردشده خوانده می‌شود.</p>

        <section class="card dz-send">
          <h2>سند جدید</h2>
          <label class="dz-drop" @dragover.prevent @drop.prevent="dropped">
            <input ref="fileInput" type="file" accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf" :disabled="!!busy || !info?.ocr"
                   @change="send($event.target.files[0])" />
            <Icon name="file" :size="30" />
            <b>{{ busy === "file" ? "در حال ارسال…" : "فایل اسکن سند را انتخاب کنید یا اینجا رها کنید" }}</b>
            <small v-if="info">تصویر JPG یا PNG، یا PDF تا {{ fa(info.max_pages) }} صفحه؛ حداکثر {{ fa(info.max_mb) }} مگابایت</small>
          </label>
          <button v-if="!pasting" class="link small" @click="pasting = true">یا متن سند را بچسبانید</button>
          <div v-else class="dz-paste">
            <label class="field">متن سند<textarea v-model="text" rows="7" placeholder="متن سند را اینجا بچسبانید"></textarea></label>
            <div class="flex gap-2"><button class="btn primary" :disabled="!!busy" @click="paste">خواندن متن</button>
              <button class="btn ghost" @click="pasting = false; text = ''">انصراف</button></div>
          </div>
          <p class="muted small dz-note"><Icon name="shield" :size="15" />فایل و متن سند فقط روی همین سرور خوانده و نگه داشته می‌شوند.</p>
        </section>

        <section v-if="info?.samples" class="card">
          <h2>نمونه‌های ساختگی</h2>
          <div class="dz-samples">
            <button v-for="s in info.samples" :key="s.key" class="dz-sample" :disabled="!!busy || !info.ocr" @click="sample(s.key)">
              <b>{{ busy === s.key ? "در حال ارسال…" : s.title }}</b><small>{{ s.desc }}</small>
            </button>
          </div>
        </section>

        <section class="card">
          <h2>سندها</h2>
          <p v-if="!docs.length" class="muted small">هنوز سندی فرستاده نشده است.</p>
          <ul class="dz-list">
            <li v-for="d in docs" :key="d.id">
              <button class="dz-row" @click="open = d.id">
                <span class="dz-row-text"><b>{{ d.name }}</b><small>{{ fa(d.created_at) }}</small></span>
                <span :class="['tag', 'st-' + STATUS[d.status].tone]">{{ STATUS[d.status].text }}</span>
                <Icon name="chevron" :size="18" />
              </button>
            </li>
          </ul>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.dz { min-height: 100vh; min-height: 100dvh; background: var(--bg); }
.dz-bar { position: sticky; top: 0; z-index: 10; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 20px;
  background: var(--panel); box-shadow: var(--shadow-sm); }
.dz-brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.dz-brand b { display: block; font-size: 15px; color: var(--ink); }
.dz-brand small { display: block; font-size: 12px; color: var(--muted); }
.dz-main { width: min(100%, 1240px); margin: 0 auto; padding: 20px 16px 40px; display: flex; flex-direction: column; gap: 16px; }
h2 { margin: 0 0 12px; font-size: 16px; color: var(--ink); }
.dz-send { display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
.dz-drop { position: relative; width: 100%; display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 28px 16px; text-align: center;
  border: 2px dashed var(--line); border-radius: var(--radius); color: var(--primary-ink); cursor: pointer; transition: border-color .2s, background .2s; }
.dz-drop:hover, .dz-drop:focus-within { border-color: var(--primary); background: var(--primary-soft); }
.dz-drop input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.dz-drop b { color: var(--ink); font-size: 14.5px; }
.dz-drop small { color: var(--muted); font-size: 12.5px; }
.dz-paste { width: 100%; display: flex; flex-direction: column; gap: 10px; }
.dz-note { display: flex; align-items: center; gap: 6px; margin: 0; }
.dz-samples { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); gap: 10px; }
.dz-sample { display: flex; flex-direction: column; gap: 4px; padding: 14px; text-align: right; border-radius: var(--radius-sm); border: 1px solid var(--line);
  background: var(--panel); cursor: pointer; font: inherit; transition: border-color .2s; }
.dz-sample:hover { border-color: var(--primary); }
.dz-sample b { font-size: 14px; color: var(--ink); }
.dz-sample small { font-size: 12.5px; line-height: 1.8; color: var(--muted); }
.dz-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.dz-row { width: 100%; display: flex; align-items: center; gap: 12px; padding: 12px 4px; border: 0; border-top: 1px solid var(--line); background: none;
  cursor: pointer; text-align: right; font: inherit; color: var(--ink); }
.dz-list li:first-child .dz-row { border-top: 0; }
.dz-row-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.dz-row-text b { font-size: 14px; overflow-wrap: anywhere; }
.dz-row-text small { font-size: 12px; color: var(--muted); }
.dz-row .tag { flex: none; }
.tag.st-warning { background: var(--warning-soft); color: var(--warning-ink); }
.tag.st-danger { background: var(--danger-soft); color: var(--danger-ink); }
.tag.st-info { background: var(--info-soft); color: var(--info-ink); }
.tag.st-success { background: var(--success-soft); color: var(--success-ink); }
</style>
