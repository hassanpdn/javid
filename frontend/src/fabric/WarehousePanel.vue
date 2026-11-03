<script setup>
// The warehouse keeper's panel (انباردار). Someone who hands the fabric over is not the one who writes the invoice:
// - «تحویل امروز»: today's invoices with fabric, rolls and meters (no prices, no payment); «تحویل شد» records who and
//   when, with a note when something differed. Below it, the fabrics running out, to tell the owner.
// - «ورود کالا»: fabric that arrived goes into the stock file at once (the server writes the Excel file too).
// - «شمارش»: a blind count: the keeper writes what is on the shelf before seeing the file's number; the stock is
//   never changed by a count, and a difference goes to the owner's «تطبیق».
// - «موجودی»: the stock list, without prices (the server leaves them out for this role).
import { ref, reactive, computed, onMounted, defineAsyncComponent } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { brand, meters, swatch } from "./lib.js"
import { FABRIC_WAREHOUSE } from "../lib/tours.js"
import { CHAT } from "./chat.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
const StockView = defineAsyncComponent(() => import("./StockView.vue"))

const view = ref("hand"), d = ref(null), stock = ref([]), busy = ref(0), noting = ref(0), note = ref("")
const load = async () => { d.value = await api("/fabric/warehouse/today") }
const loadStock = async () => { stock.value = await api("/fabric/stock") }
onMounted(() => retryable(async () => { await Promise.all([load(), loadStock()]) }))
const nav = computed(() => [
  { header: "انبار" },
  { key: "hand", label: "تحویل", icon: "inbox", badge: d.value?.waiting || 0 },
  { key: "receive", label: "ورود کالا", icon: "plus" },
  { key: "count", label: "شمارش", icon: "check" },
  { key: "stock", label: "موجودی", icon: "layers" },
])
const TITLES = { hand: "تحویل امروز", receive: "ورود کالا", count: "شمارش قفسه", stock: "موجودی انبار" }
const products = computed(() => [...stock.value].sort((a, b) => a.title.localeCompare(b.title, "fa")))

async function handOver(h, withNote = false) {
  busy.value = h.invoice
  try {
    await api(`/fabric/warehouse/handover/${h.invoice}`, { note: withNote ? note.value : "" })
    toast({ tone: "success", title: `جنس فاکتور ${fa(h.invoice)} تحویل شد` })
    noting.value = 0; note.value = ""; await load()
  } catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = 0 }
}

// ورود کالا: picking a fabric fills in its usual supplier and the meters of a usual roll
const rc = reactive({ code: "", rolls: "", meters: "", supplier: "" }), rcBusy = ref(false), rcDone = ref(null)
const rcProduct = computed(() => stock.value.find((p) => p.code === rc.code))
const pickReceive = () => { const p = rcProduct.value; rc.supplier = p?.supplier || ""; fillMeters() }
const fillMeters = () => { const p = rcProduct.value, n = Number(rc.rolls); if (p?.roll_meters && n > 0) rc.meters = String(n * p.roll_meters) }
async function receive() {
  rcBusy.value = true; rcDone.value = null
  try {
    const r = await api("/fabric/warehouse/receive", { code: rc.code, rolls: Number(rc.rolls), meters: Number(rc.meters), supplier: rc.supplier })
    rcDone.value = { ...r, title: rcProduct.value.title }
    Object.assign(rc, { code: "", rolls: "", meters: "", supplier: "" })
    await Promise.all([load(), loadStock()])
  } catch (e) { toast({ tone: "danger", title: e.message.startsWith("[") ? "خانه‌ها را درست پر کنید" : e.message }) } finally { rcBusy.value = false }
}

// شمارش: the file's number is shown only after the count is saved
const ct = reactive({ code: "", meters: "", rolls: "", note: "" }), ctBusy = ref(false), ctDone = ref(null)
async function count() {
  ctBusy.value = true; ctDone.value = null
  try {
    const title = stock.value.find((p) => p.code === ct.code)?.title
    const r = await api("/fabric/warehouse/count", { code: ct.code, meters: Number(ct.meters), rolls: ct.rolls === "" ? null : Number(ct.rolls), note: ct.note })
    ctDone.value = { ...r, title, counted: Number(ct.meters) }
    Object.assign(ct, { code: "", meters: "", rolls: "", note: "" })
  } catch (e) { toast({ tone: "danger", title: e.message.startsWith("[") ? "خانه‌ها را درست پر کنید" : e.message }) } finally { ctBusy.value = false }
}
</script>

<template>
  <AppLayout app="fabric" :brand="brand()" :chat="CHAT.warehouse" :title="TITLES[view]" subtitle="تحویل، ورود کالا و شمارش" :nav="nav" v-model="view"
             :tour="{ ...FABRIC_WAREHOUSE, ready: !!d && view === 'hand' }">
    <StockView v-if="view === 'stock'" />

    <section v-else-if="view === 'receive'" class="card wh-form">
      <p class="muted small">باری که از تأمین‌کننده رسیده است را بنویسید. همان لحظه به موجودی و فایل اکسل انبار (برگه‌ی «ورود کالا») اضافه می‌شود.</p>
      <form class="flex flex-col gap-3" @submit.prevent="receive">
        <label class="field"><span>جنس</span>
          <select v-model="rc.code" required @change="pickReceive"><option value="" disabled>انتخاب جنس</option>
            <option v-for="p in products" :key="p.code" :value="p.code">{{ p.title }} · {{ fa(p.code) }}</option></select></label>
        <div class="wh-two">
          <label class="field"><span>تعداد توپ</span><input v-model="rc.rolls" type="number" min="1" max="500" inputmode="numeric" required @input="fillMeters"></label>
          <label class="field"><span>متراژ کل (متر)</span><input v-model="rc.meters" type="number" min="1" step="0.5" inputmode="decimal" required></label>
        </div>
        <label class="field"><span>تأمین‌کننده</span><input v-model="rc.supplier" maxlength="60" placeholder="همان تأمین‌کننده‌ی همیشگی"></label>
        <small v-if="rcProduct?.roll_meters" class="muted">هر توپ این جنس معمولاً {{ meters(rcProduct.roll_meters) }} است؛ اگر بار فرق دارد، متراژ را درست کنید.</small>
        <div class="btn-row"><button class="btn primary" :disabled="rcBusy || !rc.code">{{ rcBusy ? 'در حال ثبت…' : 'ثبت ورود کالا' }}</button></div>
      </form>
      <p v-if="rcDone" class="check ok"><Icon name="check" :size="14" /> {{ fa(rcDone.steps[0].text) }}. موجودی اکنون: {{ fa(rcDone.rolls) }} توپ، {{ meters(rcDone.meters) }}.</p>
    </section>

    <section v-else-if="view === 'count'" class="card wh-form">
      <p class="muted small">آن‌چه روی قفسه می‌شمارید را بنویسید. عدد فایل انبار پس از ثبت نشان داده می‌شود. شمارش موجودی را عوض نمی‌کند؛ اگر فرق داشته باشد، صاحب کار در «تطبیق» می‌بیند.</p>
      <form class="flex flex-col gap-3" @submit.prevent="count">
        <label class="field"><span>جنس</span>
          <select v-model="ct.code" required><option value="" disabled>انتخاب جنس</option>
            <option v-for="p in products" :key="p.code" :value="p.code">{{ p.title }} · {{ fa(p.code) }}</option></select></label>
        <div class="wh-two">
          <label class="field"><span>متراژ شمرده‌شده (متر)</span><input v-model="ct.meters" type="number" min="0" step="0.5" inputmode="decimal" required></label>
          <label class="field"><span>تعداد توپ (اختیاری)</span><input v-model="ct.rolls" type="number" min="0" inputmode="numeric"></label>
        </div>
        <label class="field"><span>یادداشت (اختیاری)</span><input v-model="ct.note" maxlength="200" placeholder="مثلاً یک توپ خیس شده بود"></label>
        <div class="btn-row"><button class="btn primary" :disabled="ctBusy || !ct.code || ct.meters === ''">{{ ctBusy ? 'در حال ثبت…' : 'ثبت شمارش' }}</button></div>
      </form>
      <p v-if="ctDone" :class="['check', ctDone.matches ? 'ok' : 'bad']">
        {{ ctDone.title }}: شمرده‌شده {{ meters(ctDone.counted) }}، فایل انبار {{ meters(ctDone.book) }}.
        {{ ctDone.matches ? 'با هم یکی است.' : `${meters(Math.abs(ctDone.diff))} ${ctDone.diff < 0 ? 'کمتر' : 'بیشتر'} است؛ برای صاحب کار در «تطبیق» ثبت شد.` }}</p>
    </section>

    <div v-else class="flex flex-col gap-6">
      <section class="card" data-tour="wh-hand">
        <div class="card-head">فاکتورهای امروز <span v-if="d" class="count">{{ fa(d.waiting) }} منتظر تحویل</span></div>
        <Skeleton v-if="!d" kind="row" :count="4" />
        <p v-else-if="!d.handover.length" class="muted small">امروز فاکتوری ثبت نشده است.</p>
        <ul v-else class="wh-list">
          <li v-for="h in d.handover" :key="h.invoice" :class="{ done: h.handed }">
            <div class="wh-top"><b>فاکتور {{ fa(h.invoice) }}</b><span class="muted small">{{ h.customer }} · {{ h.city }}</span>
              <span v-if="h.handed" class="tag st-done wh-tag">تحویل شد · {{ fa(h.handed.at) }}</span></div>
            <ul class="wh-lines">
              <li v-for="(l, i) in h.lines" :key="i"><span class="fs-swatch" :style="{ background: swatch(l.color) }" aria-hidden="true"></span>
                <span class="wh-name">{{ l.title }} <small class="muted">{{ fa(l.code) }}</small></span>
                <b class="wh-qty">{{ l.rolls ? fa(l.rolls) + ' توپ · ' : '' }}{{ meters(l.meters) }}</b></li>
            </ul>
            <p v-if="h.handed?.note" class="muted small wh-note">یادداشت: {{ h.handed.note }}</p>
            <template v-if="!h.handed">
              <form v-if="noting === h.invoice" class="wh-noteform" @submit.prevent="handOver(h, true)">
                <input v-model="note" maxlength="200" placeholder="چه چیزی فرق داشت؟ مثلاً یک توپ کمتر برد" aria-label="یادداشت تحویل">
                <button class="btn primary sm" :disabled="busy === h.invoice || note.trim().length < 2">تحویل با یادداشت</button>
                <button type="button" class="btn ghost sm" @click="noting = 0">انصراف</button>
              </form>
              <div v-else class="btn-row">
                <button class="btn primary sm" :disabled="busy === h.invoice" @click="handOver(h)"><Icon name="check" :size="14" />تحویل شد</button>
                <button class="btn ghost sm" @click="noting = h.invoice; note = ''">با یادداشت</button>
              </div>
            </template>
          </li>
        </ul>
      </section>
      <section v-if="d?.low.length" class="card" data-tour="wh-low">
        <div class="card-head">رو به تمام شدن <span class="count">{{ fa(d.low.length) }}</span></div>
        <ul class="fs-list">
          <li v-for="p in d.low" :key="p.code" class="low"><span class="fs-swatch" :style="{ background: swatch(p.color) }" aria-hidden="true"></span>
            <div class="fs-main"><b>{{ p.title }}</b><small class="muted">{{ fa(p.code) }} · {{ p.supplier }}</small></div>
            <div class="fs-qty"><b>{{ fa(p.rolls) }} توپ</b><small class="muted">{{ meters(p.meters) }}</small></div>
            <span class="tag st-bad">حدود {{ fa(p.days_left) }} روز</span></li>
        </ul>
      </section>
    </div>
  </AppLayout>
</template>
