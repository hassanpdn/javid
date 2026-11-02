<script setup>
// One listing in a side drawer: the unit, its price against the neighbourhood's deals («از کجا؟» lists them), the
// buyers it fits with why (and whether someone has offered it to them yet), the call with the owner, the owner's
// report, visits and the listing's own history. Every number comes from the server; nothing here works one out.
import { ref, reactive, watch, defineAsyncComponent } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { toMillions, fromMillions } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "../fabric/HowTip.vue"
const VisitDialog = defineAsyncComponent(() => import("./VisitDialog.vue"))
const DealDialog = defineAsyncComponent(() => import("./DealDialog.vue"))

const props = defineProps({ id: Number })
const emit = defineEmits(["close", "changed", "request"])
const d = ref(null), busy = ref(""), visit = ref(null), deal = ref(false)
const call = reactive({ open: false, status: "active", price: "", deposit: "", rent: "", note: "" })
const report = reactive({ text: "", checked: null, open: false })
const load = async () => {
  d.value = await api(`/estate/listings/${props.id}`)
  const l = d.value.listing
  Object.assign(call, { open: false, status: "active", price: toMillions(l.price), deposit: toMillions(l.deposit), rent: toMillions(l.rent), note: "" })
}
watch(() => props.id, () => { d.value = null; report.open = false; load() }, { immediate: true })
const done = async (msg) => { toast({ tone: "success", title: msg }); await load(); emit("changed") }

async function offered(m) {
  busy.value = "call" + m.request_id
  try { await api("/estate/calls", { listing_id: m.listing_id, request_id: m.request_id, outcome: "پیشنهاد شد" }); await done(`فایل به ${m.name} پیشنهاد شد`) }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
async function saveCall() {
  busy.value = "contact"
  const l = d.value.listing
  const body = { status: call.status, note: call.note }
  if (call.status === "active") Object.assign(body, l.kind === "sale" ? { price: fromMillions(call.price) } : { deposit: fromMillions(call.deposit), rent: fromMillions(call.rent) })
  try { await api(`/estate/listings/${props.id}/contact`, body); await done("تماس با مالک ثبت شد") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
async function draftReport() {
  busy.value = "report"
  try { Object.assign(report, await api(`/estate/listings/${props.id}/report/draft`, {}), { open: true }) }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
async function sendReport() {
  busy.value = "sent"
  try { await api(`/estate/listings/${props.id}/report`, { text: report.text }); report.open = false; await done("گزارش برای مالک ثبت شد") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
const copy = async (text) => { try { await navigator.clipboard.writeText(text); toast({ tone: "success", title: "متن کپی شد" }) } catch {} }
const STATUSES = { active: "هنوز موجود است", sold: "فروخته شد", rented: "اجاره داده شد", withdrawn: "مالک منصرف شد" }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer es-drawer" v-drawer aria-label="فایل">
      <div class="drawer-head">
        <b class="text-ink">فایل {{ fa(id) }}</b>
        <button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="5" /></div>
        <template v-else>
          <section class="card es-head">
            <div class="es-row-top"><b class="es-title">{{ fa(d.listing.title) }}</b>
              <span :class="['tag', d.listing.status === 'active' ? 'es-t-success' : 'es-t-secondary']">{{ d.listing.status_text }}</span></div>
            <div class="es-price lg">{{ fa(d.listing.price_text) }}</div>
            <div class="es-tags"><span class="tag">{{ d.listing.kind_text }}</span><span v-for="x in d.listing.features" :key="x" class="tag">{{ fa(x) }}</span></div>
            <dl class="es-dl">
              <dt>نشانی</dt><dd>{{ d.listing.hood }}، {{ d.listing.street || '-' }}</dd>
              <dt>مالک</dt><dd>{{ d.listing.owner_name }} · <span dir="ltr">{{ fa(d.listing.owner_phone) }}</span></dd>
              <dt>مشاور</dt><dd>{{ d.listing.agent }}</dd>
              <dt>ثبت</dt><dd>{{ fa(d.listing.created_text) }} · آخرین تماس با مالک {{ fa(d.listing.contact_text) }}</dd>
              <dt v-if="d.listing.note">یادداشت</dt><dd v-if="d.listing.note">{{ fa(d.listing.note) }}</dd>
            </dl>
          </section>

          <p v-if="d.duplicate" class="check info small"><Icon name="layers" :size="16" /><span>احتمالاً همان فایل {{ fa(d.duplicate.other) }} است: {{ fa(d.duplicate.why) }}.</span></p>

          <section v-if="d.price" class="card">
            <div class="card-head"><span class="grow">قیمت در برابر معامله‌های محله</span><HowTip :lines="d.price.how" /></div>
            <p :class="['es-verdict', d.price.verdict]"><Icon :name="d.price.verdict === 'fair' ? 'check' : 'alert'" :size="16" />{{ fa(d.price.text) }}</p>
          </section>

          <section v-if="d.listing.status === 'active'" class="card">
            <div class="card-head"><span class="grow">متقاضیان مناسب <small>{{ fa(d.matches.length) }} نفر</small></span></div>
            <p v-if="!d.matches.length" class="muted small">فعلاً متقاضی‌ای با این واحد جور نیست. هر متقاضی جدیدی که جور باشد همین‌جا می‌آید.</p>
            <ul class="es-matches">
              <li v-for="m in d.matches" :key="m.request_id">
                <div class="es-row-top"><button class="link es-name" @click="emit('request', m.request_id)">{{ m.name }}</button><span class="es-score">{{ fa(m.score) }}٪</span></div>
                <small class="muted">{{ fa(m.budget_text) }} · {{ m.agent }}</small>
                <div class="es-tags"><span v-for="r in m.reasons" :key="r" class="tag es-t-success">{{ fa(r) }}</span><span v-for="r in m.misses" :key="r" class="tag es-t-warning">{{ fa(r) }}</span></div>
                <div class="es-actions">
                  <small v-if="m.called" class="muted"><Icon name="check" :size="13" /> {{ fa(m.called.when) }}، {{ m.called.who }}: {{ m.called.outcome }}</small>
                  <template v-else>
                    <small :class="m.waiting >= 3 ? 'es-late' : 'muted'">{{ m.waiting >= 3 ? fa(m.waiting) + ' روز است کسی تماس نگرفته' : 'هنوز پیشنهاد نشده' }}</small>
                    <button class="btn sm" :disabled="busy === 'call' + m.request_id" @click="offered(m)">پیشنهاد دادم</button>
                  </template>
                  <button class="btn ghost sm" @click="visit = m"><Icon name="calendar" :size="14" />بازدید</button>
                </div>
              </li>
            </ul>
          </section>

          <section v-if="d.listing.status === 'active'" class="card">
            <div class="card-head"><span class="grow">تماس با مالک</span><button v-if="!call.open" class="btn sm" @click="call.open = true">ثبت تماس</button></div>
            <p v-if="!call.open" class="muted small">آخرین تماس {{ fa(d.listing.contact_text) }}. هر تماس با مالک را ثبت کنید تا فایل روی سایت بماند و فایل فروخته‌شده پیشنهاد نشود.</p>
            <form v-else class="flex flex-col gap-3" @submit.prevent="saveCall">
              <div class="es-seg" role="radiogroup" aria-label="نتیجه‌ی تماس">
                <button v-for="(t, k) in STATUSES" :key="k" v-show="k === 'active' || k === 'withdrawn' || (d.listing.kind === 'sale') === (k === 'sold')"
                        type="button" role="radio" :aria-checked="call.status === k" :class="{ on: call.status === k }" @click="call.status = k">{{ t }}</button>
              </div>
              <div v-if="call.status === 'active'" class="es-grid2">
                <label v-if="d.listing.kind === 'sale'" class="field"><span>قیمت (میلیون تومان)</span><input v-model="call.price" inputmode="numeric"></label>
                <template v-else>
                  <label class="field"><span>ودیعه (میلیون تومان)</span><input v-model="call.deposit" inputmode="numeric"></label>
                  <label class="field"><span>اجاره (میلیون تومان)</span><input v-model="call.rent" inputmode="numeric"></label>
                </template>
              </div>
              <label class="field"><span>یادداشت</span><input v-model="call.note" maxlength="300" placeholder="مثلاً هنوز می‌فروشد، برای نقد تخفیف می‌دهد"></label>
              <div class="btn-row"><button class="btn primary sm" :disabled="busy === 'contact'">ثبت</button><button type="button" class="btn ghost sm" @click="call.open = false">انصراف</button></div>
            </form>
          </section>

          <section v-if="d.listing.status === 'active'" class="card">
            <div class="card-head"><span class="grow">گزارش برای مالک <small v-if="d.report.last">آخرین گزارش {{ fa(d.report.last) }}</small></span>
              <span v-if="d.report.due" class="tag es-t-info">وقت گزارش است</span></div>
            <template v-if="report.open">
              <textarea v-model="report.text" rows="7" class="es-text ai-draft" aria-label="متن گزارش"></textarea>
              <p v-if="report.checked === false" class="check warn small"><Icon name="alert" :size="14" /><span>متن دستیار با عددهای واقعی جور نبود؛ متن ساده با همان عددها جایگزین شد.</span></p>
              <div class="btn-row"><button class="btn sm" @click="copy(report.text)"><Icon name="file" :size="14" />کپی متن</button>
                <button class="btn primary sm" :disabled="busy === 'sent'" @click="sendReport">برای مالک فرستادم</button>
                <button class="btn ghost sm" @click="report.open = false">بستن</button></div>
            </template>
            <template v-else>
              <p class="muted small">چند متقاضی پیدا شد، به چند نفر پیشنهاد شد و بازدیدکنندگان چه گفتند. دستیار متن را می‌نویسد و شما آن را می‌فرستید.</p>
              <button class="btn sm" :disabled="busy === 'report'" @click="draftReport"><Icon name="sparkles" :size="14" />{{ busy === 'report' ? 'در حال نوشتن…' : 'نوشتن گزارش' }}</button>
            </template>
          </section>

          <section v-if="d.visits.length" class="card">
            <div class="card-head">بازدیدها</div>
            <ul class="es-mini">
              <li v-for="v in d.visits" :key="v.id"><b>{{ fa(v.when) }}</b> · {{ v.name }} · {{ v.agent }}<small v-if="v.outcome" class="muted">{{ fa(v.outcome) }}</small></li>
            </ul>
          </section>

          <section v-if="d.history.length" class="card">
            <div class="card-head">سابقه‌ی این فایل</div>
            <ul class="es-mini">
              <li v-for="e in d.history" :key="e.id"><span>{{ fa(e.text) }}</span><small class="muted">{{ e.who }} · {{ fa(e.day) }} {{ fa(e.time) }}</small></li>
            </ul>
          </section>

          <button v-if="d.listing.status === 'active'" class="btn success" @click="deal = true"><Icon name="check" :size="18" />ثبت معامله</button>
        </template>
      </div>
    </aside>
    <VisitDialog v-if="visit" :listing-id="visit.listing_id" :request-id="visit.request_id" :title="`${d.listing.title} · ${visit.name}`" @close="visit = null" @done="visit = null; load(); emit('changed')" />
    <DealDialog v-if="deal" :listing="d.listing" :buyers="d.matches" @close="deal = false" @done="deal = false; load(); emit('changed')" />
  </div>
</template>
