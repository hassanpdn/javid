<script setup>
// One deed under review: the scanned pages on one side, the form on the other. Every field shows how surely it was
// read and the line it came from; unsure ones are coloured. The reviewer corrects, saves or confirms, and after
// confirming downloads the JSON. While the deed is still being read, the page shows the progress and asks again.
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue"
import { fa } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import DeedField from "./DeedField.vue"
import { getDoc, extractAgain, saveDoc, confirmDoc, exportDoc, download, STATUS, LABELS, GROUPS, shown } from "./lib.js"

const props = defineProps({ id: Number })
const emit = defineEmits(["back"])
const doc = ref(null), error = ref(""), busy = ref(""), page = ref(1), saved = ref("")
const form = reactive({ fields: {}, owners: [], transfers: [] })
let timer = null

const deed = computed(() => doc.value?.deed)
const locked = computed(() => doc.value?.status === "confirmed")
const current = computed(() => doc.value?.pages.find((p) => p.n === page.value))

// the form starts from what was extracted (or what the reviewer saved last)
function fill() {
  const d = deed.value
  if (!d) return
  form.fields = Object.fromEntries(Object.entries(d.fields).map(([k, f]) => [k, shown(f.value)]))
  form.owners = d.owners.map((o) => Object.fromEntries(Object.entries(o).map(([k, f]) => [k, shown(f.value)])))
  form.transfers = d.transfers.map((t) => ({ date: shown(t.date), from: t.from || "", to: t.to || "", share: t.share || "", note: shown(t.note) }))
}

async function load() {
  try {
    doc.value = await getDoc(props.id)
    error.value = ""
    if (doc.value.status === "processing") timer = setTimeout(load, 1000)
    else fill()
  } catch (e) { error.value = e.message }
}
onMounted(load)
onUnmounted(() => clearTimeout(timer))

const progress = computed(() => {
  const p = doc.value?.progress
  if (!p || p.step === "start") return "در حال آماده‌سازی…"
  if (p.step === "ocr") return `در حال خواندن صفحه‌ی ${fa(p.done + 1)} از ${fa(p.total)}…`
  return "در حال استخراج داده‌ها…"
})

// the shares, added up as the reviewer types (the server checks them again when saving)
const WORDS = { "یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "نیم": 0.5 }
const toDang = (s) => {
  const t = String(s || "").replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace("٫", ".").replace("دانگ", " ").trim()
  if (/^\d+(\.\d+)?$/.test(t)) return Number(t)
  const parts = t.split(/\s+و\s+|\s+/).filter(Boolean)
  return parts.length && parts.every((p) => p in WORDS) ? parts.reduce((a, p) => a + WORDS[p], 0) : null
}
const shares = computed(() => {
  const list = form.owners.map((o) => toDang(o.share))
  if (!list.length) return null
  if (list.some((s) => s === null)) return { ok: false, text: "سهم برخی مالکین روشن نیست." }
  const total = Math.round(list.reduce((a, b) => a + b, 0) * 1000) / 1000
  return { ok: total === 6, text: `جمع سهم‌ها: ${fa(total)} دانگ` + (total === 6 ? "" : " (باید ۶ دانگ باشد)") }
})

const edit = () => ({ fields: { ...form.fields }, owners: form.owners.map((o) => ({ ...o })), transfers: form.transfers.map((t) => ({ ...t })) })
async function act(kind) {
  busy.value = kind; error.value = ""; saved.value = ""
  try {
    if (kind === "save") { doc.value = await saveDoc(props.id, edit()); fill(); saved.value = "ذخیره شد." }
    else if (kind === "confirm") { doc.value = await confirmDoc(props.id, edit()); fill(); saved.value = "سند تأیید شد. اکنون می‌توانید JSON را دریافت کنید." }
    else if (kind === "again") { doc.value = await extractAgain(props.id); load() }
    else if (kind === "export") download(`deed-${props.id}.json`, await exportDoc(props.id))
  } catch (e) { error.value = e.message }
  finally { busy.value = "" }
}
const look = (n) => { if (n && doc.value?.pages.some((p) => p.n === n)) page.value = n }
watch(() => doc.value?.pages?.length, () => { if (!current.value && doc.value?.pages?.length) page.value = doc.value.pages[0].n })

const addOwner = () => form.owners.push({ name: "", father_name: "", national_id: "", share: "" })
const addTransfer = () => form.transfers.push({ date: "", from: "", to: "", share: "", note: "" })
const ownerField = (i, k) => deed.value?.owners[i]?.[k]
</script>

<template>
  <section class="dv">
    <div class="dv-top">
      <button class="btn ghost sm" @click="emit('back')"><Icon name="arrowRight" :size="16" />همه‌ی سندها</button>
      <div v-if="doc" class="dv-title">
        <b>{{ doc.name }}</b>
        <span :class="['tag', 'st-' + STATUS[doc.status].tone]">{{ STATUS[doc.status].text }}</span>
        <span v-if="doc.method" class="tag">{{ doc.method === "model" ? "خوانده با مدل" : "خوانده با قاعده‌های ثابت" }}</span>
      </div>
    </div>

    <p v-if="error" class="error-text" role="alert">{{ error }}</p>

    <div v-if="!doc" class="card dv-wait"><span class="dots"><i></i><i></i><i></i></span></div>

    <div v-else-if="doc.status === 'processing'" class="card dv-wait" role="status">
      <span class="dots"><i></i><i></i><i></i></span><b>{{ progress }}</b>
      <small>همه‌ی پردازش روی همین سرور انجام می‌شود.</small>
    </div>

    <div v-else-if="doc.status === 'error'" class="card dv-wait" role="alert">
      <Icon name="alert" :size="28" /><b>{{ doc.message }}</b>
      <p v-for="p in doc.pages.filter((p) => !p.readable)" :key="p.n" class="muted small">صفحه‌ی {{ fa(p.n) }}: {{ p.note }}</p>
      <button class="btn" :disabled="!!busy" @click="act('again')"><Icon name="refresh" :size="16" />دوباره امتحان کنید</button>
    </div>

    <template v-else>
      <ul v-if="deed.issues.length" class="dv-issues" role="status">
        <li v-for="i in deed.issues" :key="i"><Icon name="alert" :size="16" />{{ fa(i) }}</li>
      </ul>

      <div class="dv-grid">
        <!-- the scan -->
        <div class="card dv-scan">
          <div v-if="doc.pages.length > 1" class="dv-tabs" role="tablist">
            <button v-for="p in doc.pages" :key="p.n" role="tab" :aria-selected="p.n === page" :class="{ on: p.n === page, bad: !p.readable }"
                    @click="page = p.n">صفحه‌ی {{ fa(p.n) }}</button>
          </div>
          <p v-if="current && !current.readable" class="dv-bad"><Icon name="alert" :size="16" />{{ current.note }}</p>
          <p v-if="current?.rotation" class="muted small">این صفحه {{ fa(current.rotation) }} درجه چرخیده بود و صاف شد.</p>
          <a v-if="current?.image" :href="`/deed/documents/${doc.id}/pages/${current.n}`" target="_blank" rel="noopener" class="dv-img">
            <img :src="`/deed/documents/${doc.id}/pages/${current.n}`" :alt="`صفحه‌ی ${fa(current.n)} سند`" />
          </a>
          <pre v-else-if="doc.text" class="dv-text">{{ fa(doc.text) }}</pre>
        </div>

        <!-- the form -->
        <div class="dv-form">
          <div v-for="g in GROUPS" :key="g.title" class="card">
            <h3>{{ g.title }}</h3>
            <div class="dv-fields">
              <DeedField v-for="k in g.keys" :key="k" v-model="form.fields[k]" :label="LABELS[k]" :field="deed.fields[k]"
                         :wide="g.wide" :disabled="locked" @look="look" />
            </div>
          </div>

          <div class="card">
            <div class="dv-h"><h3>مالکین</h3><span v-if="shares" :class="['tag', shares.ok ? 'st-success' : 'st-danger']">{{ shares.text }}</span></div>
            <p v-if="!form.owners.length" class="muted small">مالکی در سند پیدا نشد.</p>
            <div v-for="(o, i) in form.owners" :key="i" class="dv-owner">
              <div class="dv-h"><b>مالک {{ fa(i + 1) }}</b>
                <button v-if="!locked" class="btn ghost sm" @click="form.owners.splice(i, 1)"><Icon name="x" :size="14" />حذف</button></div>
              <div class="dv-fields">
                <DeedField v-for="k in ['name', 'father_name', 'national_id', 'share']" :key="k" v-model="o[k]" :label="LABELS[k]"
                           :field="ownerField(i, k)" :disabled="locked" @look="look" />
              </div>
            </div>
            <button v-if="!locked" class="btn ghost sm" @click="addOwner"><Icon name="plus" :size="14" />افزودن مالک</button>
          </div>

          <div class="card">
            <h3>سابقه‌ی انتقال</h3>
            <p v-if="!form.transfers.length" class="muted small">سابقه‌ی انتقالی در سند نیامده است.</p>
            <div v-for="(t, i) in form.transfers" :key="i" class="dv-owner">
              <div class="dv-h"><b>انتقال {{ fa(i + 1) }}</b>
                <button v-if="!locked" class="btn ghost sm" @click="form.transfers.splice(i, 1)"><Icon name="x" :size="14" />حذف</button></div>
              <p v-for="x in deed.transfers[i]?.issues || []" :key="x" class="error-text small">{{ fa(x) }}</p>
              <div class="dv-fields dv-plain">
                <label class="field">تاریخ<input v-model="t.date" :disabled="locked" /></label>
                <label class="field">سهم<input v-model="t.share" :disabled="locked" /></label>
                <label class="field">از<input v-model="t.from" :disabled="locked" /></label>
                <label class="field">به<input v-model="t.to" :disabled="locked" /></label>
                <label class="field dv-wide">توضیح<input v-model="t.note" :disabled="locked" /></label>
              </div>
            </div>
            <button v-if="!locked" class="btn ghost sm" @click="addTransfer"><Icon name="plus" :size="14" />افزودن انتقال</button>
          </div>

          <div class="card dv-actions">
            <p v-if="saved" class="dv-saved" role="status"><Icon name="check" :size="16" />{{ saved }}</p>
            <template v-if="!locked">
              <button class="btn success" :disabled="!!busy" @click="act('confirm')"><Icon name="check" :size="16" />تأیید داده‌ها</button>
              <button class="btn ghost" :disabled="!!busy" @click="act('save')">ذخیره بدون تأیید</button>
              <button class="btn ghost" :disabled="!!busy" @click="act('again')"><Icon name="refresh" :size="16" />استخراج دوباره</button>
            </template>
            <button v-else class="btn primary" :disabled="!!busy" @click="act('export')"><Icon name="file" :size="16" />دریافت JSON</button>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.dv { display: flex; flex-direction: column; gap: 16px; }
.dv-top { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.dv-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.dv-title b { font-size: 16px; color: var(--ink); overflow-wrap: anywhere; }
.dv-wait { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 48px 24px; text-align: center; color: var(--ink); }
.dv-issues { list-style: none; margin: 0; padding: 12px 16px; display: flex; flex-direction: column; gap: 6px; border-radius: var(--radius);
  background: var(--warning-soft); color: var(--warning-ink); font-size: 13.5px; line-height: 1.9; }
.dv-issues li { display: flex; gap: 8px; align-items: flex-start; }
.dv-issues .ico { flex: none; margin-top: 4px; }
.dv-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); gap: 16px; align-items: start; }
.dv-scan { position: sticky; top: 16px; display: flex; flex-direction: column; gap: 10px; padding: 14px; }
.dv-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.dv-tabs button { padding: 4px 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--panel); cursor: pointer; font: inherit; font-size: 13px; color: var(--ink); }
.dv-tabs button.on { background: var(--primary-strong); border-color: transparent; color: #fff; }
.dv-tabs button.bad { border-color: var(--danger); }
.dv-bad { display: flex; gap: 8px; margin: 0; font-size: 13px; color: var(--danger-ink); }
.dv-img img { display: block; width: 100%; height: auto; border-radius: var(--radius-sm); border: 1px solid var(--line); }
.dv-text { margin: 0; white-space: pre-wrap; font: inherit; font-size: 14px; line-height: 2; color: var(--ink); max-height: 70vh; overflow: auto; }
.dv-form { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.dv-form h3 { margin: 0 0 10px; font-size: 15px; color: var(--ink); }
.dv-h { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.dv-h h3 { margin: 0; }
.dv-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 8px; }
.dv-plain { gap: 10px 12px; }
.dv-plain .dv-wide, .dv-fields :deep(.dv-wide) { grid-column: 1 / -1; }
.dv-owner { padding: 10px 0; border-top: 1px solid var(--line); }
.dv-owner:first-of-type { border-top: 0; }
.dv-actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.dv-saved { flex-basis: 100%; display: flex; gap: 6px; margin: 0; font-size: 13.5px; color: var(--success-ink); }
.tag.st-warning { background: var(--warning-soft); color: var(--warning-ink); }
.tag.st-danger { background: var(--danger-soft); color: var(--danger-ink); }
.tag.st-info { background: var(--info-soft); color: var(--info-ink); }
.tag.st-success { background: var(--success-soft); color: var(--success-ink); }
@media (max-width: 900px) {
  .dv-grid { grid-template-columns: minmax(0, 1fr); }
  .dv-scan { position: static; }
}
@media (max-width: 520px) { .dv-fields { grid-template-columns: minmax(0, 1fr); } }
</style>
