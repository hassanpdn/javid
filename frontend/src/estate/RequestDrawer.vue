<script setup>
// One buyer or renter in a side drawer: what they want, the units that fit and why (and which were offered to them),
// their visits and history. «منصرف شد» closes the request; a deal is recorded from the listing.
import { ref, watch, defineAsyncComponent } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
const VisitDialog = defineAsyncComponent(() => import("./VisitDialog.vue"))

const props = defineProps({ id: Number })
const emit = defineEmits(["close", "changed", "listing"])
const d = ref(null), busy = ref(""), visit = ref(null), closing = ref(false), note = ref("")
const load = async () => { d.value = await api(`/estate/requests/${props.id}`) }
watch(() => props.id, () => { d.value = null; load() }, { immediate: true })
async function offered(m) {
  busy.value = "call" + m.listing_id
  try { await api("/estate/calls", { listing_id: m.listing_id, request_id: m.request_id, outcome: "پیشنهاد شد" }); toast({ tone: "success", title: "پیشنهاد ثبت شد" }); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
async function close() {
  busy.value = "close"
  try { await api(`/estate/requests/${props.id}/close`, { status: "lost", note: note.value }); closing.value = false; await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer es-drawer" v-drawer aria-label="متقاضی">
      <div class="drawer-head"><b class="text-ink">متقاضی</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="5" /></div>
        <template v-else>
          <section class="card es-head">
            <div class="es-row-top"><b class="es-title">{{ d.request.name }}</b><span :class="['tag', d.request.status === 'open' ? 'es-t-success' : 'es-t-secondary']">{{ d.request.status_text }}</span></div>
            <div class="es-price lg">{{ d.request.kind === 'sale' ? 'خرید' : 'رهن و اجاره' }} · {{ fa(d.request.budget_text) }}</div>
            <div class="es-tags"><span v-for="h in d.request.hoods_list" :key="h" class="tag">{{ h }}</span><span v-for="w in d.request.wants" :key="w" class="tag">{{ fa(w) }}</span></div>
            <dl class="es-dl">
              <dt>تلفن</dt><dd dir="ltr" class="text-right">{{ fa(d.request.phone) || '-' }}</dd>
              <dt>مشاور</dt><dd>{{ d.request.agent }}</dd>
              <dt>ثبت</dt><dd>{{ fa(d.request.created_text) }} · {{ d.request.source_text }}</dd>
              <dt v-if="d.request.note">یادداشت</dt><dd v-if="d.request.note">{{ fa(d.request.note) }}</dd>
            </dl>
          </section>

          <section v-if="d.request.status === 'open'" class="card">
            <div class="card-head"><span class="grow">فایل‌های مناسب <small>{{ fa(d.matches.length) }} فایل</small></span></div>
            <p v-if="!d.matches.length" class="muted small">فعلاً فایلی جور نیست. هر فایل جدیدی که جور باشد همین‌جا و در کارهای امروز می‌آید.</p>
            <ul class="es-matches">
              <li v-for="m in d.matches" :key="m.listing_id">
                <div class="es-row-top"><button class="link es-name" @click="emit('listing', m.listing_id)">فایل {{ fa(m.listing_id) }}: {{ fa(m.title) }}</button><span class="es-score">{{ fa(m.score) }}٪</span></div>
                <small class="muted">{{ fa(m.price_text) }} · {{ m.agent }}</small>
                <div class="es-tags"><span v-for="r in m.reasons" :key="r" class="tag es-t-success">{{ fa(r) }}</span><span v-for="r in m.misses" :key="r" class="tag es-t-warning">{{ fa(r) }}</span></div>
                <div class="es-actions">
                  <small v-if="m.called" class="muted"><Icon name="check" :size="13" /> {{ fa(m.called.when) }}، {{ m.called.who }}: {{ m.called.outcome }}</small>
                  <template v-else><small :class="m.waiting >= 3 ? 'es-late' : 'muted'">{{ m.waiting >= 3 ? fa(m.waiting) + ' روز است پیشنهاد نشده' : 'هنوز پیشنهاد نشده' }}</small>
                    <button class="btn sm" :disabled="busy === 'call' + m.listing_id" @click="offered(m)">پیشنهاد دادم</button></template>
                  <button class="btn ghost sm" @click="visit = m"><Icon name="calendar" :size="14" />بازدید</button>
                </div>
              </li>
            </ul>
          </section>

          <section v-if="d.visits.length" class="card">
            <div class="card-head">بازدیدها</div>
            <ul class="es-mini"><li v-for="v in d.visits" :key="v.id"><b>{{ fa(v.when) }}</b> · فایل {{ fa(v.listing_id) }}، {{ fa(v.area) }} متر {{ v.hood }}<small v-if="v.outcome" class="muted">{{ fa(v.outcome) }}</small></li></ul>
          </section>
          <section v-if="d.history.length" class="card">
            <div class="card-head">سابقه</div>
            <ul class="es-mini"><li v-for="e in d.history" :key="e.id"><span>{{ fa(e.text) }}</span><small class="muted">{{ e.who }} · {{ fa(e.day) }} {{ fa(e.time) }}</small></li></ul>
          </section>

          <section v-if="d.request.status === 'open'" class="card">
            <template v-if="closing">
              <label class="field"><span>چرا منصرف شد؟</span><input v-model="note" maxlength="300" placeholder="مثلاً از جای دیگری خرید"></label>
              <div class="btn-row"><button class="btn danger-soft sm" :disabled="busy === 'close'" @click="close">بستن درخواست</button><button class="btn ghost sm" @click="closing = false">انصراف</button></div>
            </template>
            <button v-else class="btn ghost sm" @click="closing = true">متقاضی منصرف شد</button>
            <p class="muted small mt-2">اگر معامله شد، از فایل همان واحد «ثبت معامله» را بزنید.</p>
          </section>
        </template>
      </div>
    </aside>
    <VisitDialog v-if="visit" :listing-id="visit.listing_id" :request-id="visit.request_id" :title="`${d.request.name} · فایل ${visit.listing_id}`" @close="visit = null" @done="visit = null; load(); emit('changed')" />
  </div>
</template>
