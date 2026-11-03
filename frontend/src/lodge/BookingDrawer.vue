<script setup>
// One booking: the guest (their other stays), the unit and dates with the price night by night, where it stands and
// the buttons for the next step: approve or turn down a request, confirm a receipt (shown beside it) or say it does
// not match, cancel by the lodge's rule. The conversation with the guest, and after the stay the message that asks
// how it was (built by code; the host sends it from the lodge's phone).
import { ref, watch, computed } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { STATUS_TONE } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "../fabric/HowTip.vue"

const props = defineProps({ id: Number })
const emit = defineEmits(["close", "changed"])
const d = ref(null), busy = ref(""), text = ref(""), open = ref(""), fb = ref(null)
const load = async () => { d.value = await api(`/lodge/bookings/${props.id}`) }
watch(() => props.id, () => { d.value = null; open.value = ""; fb.value = null; load() }, { immediate: true })
const b = computed(() => d.value?.booking)
async function act(key, path, body, title) {
  busy.value = key
  try { await api(`/lodge/bookings/${props.id}${path}`, body || {}); toast({ tone: "success", title }); open.value = ""; text.value = ""; await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
const feedback = async () => { try { fb.value = await api(`/lodge/bookings/${props.id}/feedback`) } catch (e) { toast({ tone: "danger", title: e.message }) } }
const copy = async (t) => { try { await navigator.clipboard.writeText(t); toast({ tone: "success", title: "متن کپی شد" }) } catch {} }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer lo-drawer" v-drawer aria-label="رزرو">
      <div class="drawer-head"><b class="text-ink">رزرو {{ d ? fa(b.id) : '' }}</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="6" /></div>
        <template v-else>
          <section class="card lo-head">
            <div class="lo-row-top"><b class="lo-title">{{ b.guest }}</b><span :class="['tag', 'lo-t-' + STATUS_TONE[b.status]]">{{ b.status_text }}</span></div>
            <div class="lo-tags"><span class="tag" dir="ltr">{{ fa(b.phone) }}</span><span class="tag">از {{ b.source_text }}</span><span v-if="b.has_account" class="tag lo-t-success">حساب در سایت دارد</span></div>
            <dl class="lo-dl">
              <dt>واحد</dt><dd>{{ b.unit }}</dd>
              <dt>اقامت</dt><dd>{{ fa(b.stay_text) }} · {{ fa(b.adults) }} نفر</dd>
              <dt>قیمت</dt><dd class="flex items-center gap-2">{{ fa(b.total_text) }} · بیعانه {{ fa(b.deposit_text) }}<HowTip :lines="d.price_how" /></dd>
              <dt v-if="b.status === 'approved'">مهلت بیعانه</dt><dd v-if="b.status === 'approved'">{{ fa(b.deposit_due_text) }}</dd>
              <dt v-if="b.note">یادداشت</dt><dd v-if="b.note">{{ b.note }}</dd>
            </dl>
            <p v-if="d.conflict" class="check warn small"><Icon name="alert" :size="14" /><span>{{ d.conflict }}</span></p>
            <div class="lo-btns">
              <template v-if="b.status === 'requested'">
                <button class="btn primary sm" :disabled="!!busy || !!d.conflict" @click="act('ok', '/approve', {}, 'تأیید شد؛ مهمان بیعانه را می‌فرستد')"><Icon name="check" :size="14" />تأیید درخواست</button>
                <button class="btn ghost sm" @click="open = 'reject'">رد درخواست</button>
              </template>
              <button v-if="b.status === 'approved'" class="btn sm" :disabled="!!busy" @click="act('ok', '/confirm', {}, 'رزرو قطعی شد')">بیعانه رسید (بدون رسید)</button>
              <button v-if="['requested', 'approved', 'paid', 'confirmed'].includes(b.status) && !b.over" class="btn ghost sm" @click="open = 'cancel'">لغو</button>
              <button v-if="b.over && !b.review" class="btn sm" @click="feedback"><Icon name="heart" :size="14" />پیام نظرخواهی</button>
            </div>
            <form v-if="open === 'reject' || open === 'cancel'" class="flex flex-col gap-2" @submit.prevent="act(open, open === 'reject' ? '/reject' : '/cancel', { text }, open === 'reject' ? 'درخواست رد شد' : 'رزرو لغو شد')">
              <p v-if="open === 'cancel'" class="small">{{ fa(d.refund.rule) }} اکنون: {{ fa(d.refund.percent) }} درصد<template v-if="d.refund.amount">، {{ fa(d.refund.amount.toLocaleString()) }} تومان</template>.</p>
              <input v-model="text" class="lo-search" maxlength="300" placeholder="پیام برای مهمان (اختیاری)، مثلاً: آن شب‌ها خانه پر است" aria-label="پیام برای مهمان">
              <div class="btn-row"><button class="btn danger-soft sm" :disabled="!!busy">{{ open === 'reject' ? 'رد شود' : 'لغو شود' }}</button><button type="button" class="btn ghost sm" @click="open = ''">انصراف</button></div>
            </form>
            <template v-if="fb"><textarea :value="fb.text" rows="5" class="lo-text" readonly aria-label="پیام نظرخواهی"></textarea>
              <small class="muted">{{ fb.has_account ? 'مهمان حساب دارد و فرم نظر را در «سفرهای من» می‌بیند.' : 'مهمان هنوز حساب ندارد؛ با همین شماره می‌تواند حساب بسازد.' }}</small>
              <div class="btn-row"><button class="btn sm" @click="copy(fb.text)">کپی متن</button><button class="btn primary sm" @click="act('fb', '/feedback', {}, 'ثبت شد'); fb = null">فرستادم</button></div></template>
          </section>

          <section v-if="b.receipt" class="card flex flex-col gap-2">
            <div class="card-head">رسید بیعانه <small>{{ b.receipt.status === 'waiting' ? 'منتظر بررسی' : b.receipt.status === 'ok' ? 'تأیید شد' : 'پذیرفته نشد' }}</small></div>
            <img v-if="b.receipt_data" :src="b.receipt_data" alt="رسید" class="lo-receipt">
            <div v-if="b.status === 'paid'" class="btn-row">
              <button class="btn primary sm" :disabled="!!busy" @click="act('ok', '/confirm', {}, 'رزرو قطعی شد')"><Icon name="check" :size="14" />واریز را دیدم، قطعی شود</button>
              <button class="btn ghost sm" :disabled="!!busy" @click="act('no', '/receipt-wrong', {}, 'از مهمان رسید درست خواسته شد')">با واریزی جور نیست</button></div>
            <small class="muted">مبلغ بیعانه: {{ fa(b.deposit_text) }}. پیش از قطعی کردن، واریز را در حساب ببینید.</small>
          </section>

          <section class="card flex flex-col gap-2">
            <div class="card-head">گفت‌وگو با مهمان</div>
            <p v-if="!d.messages.length" class="muted small">پیامی نیست.</p>
            <div class="lo-thread"><p v-for="m in d.messages" :key="m.id" :class="m.side">{{ m.text }} <small class="muted">· {{ fa(m.day) }} {{ fa(m.time) }}</small></p></div>
            <form class="lo-pay" @submit.prevent="act('msg', '/message', { text }, 'پیام فرستاده شد')">
              <input v-model="text" maxlength="300" placeholder="پاسخ به مهمان؛ در «سفرهای من» می‌بیند" aria-label="پاسخ"><button class="btn primary sm" :disabled="!!busy || text.trim().length < 2">فرستادن</button></form>
          </section>

          <section v-if="b.review" class="card flex flex-col gap-1">
            <div class="card-head">نظر مهمان</div>
            <span class="lo-stars">{{ '★'.repeat(b.review.stars) }}</span><p class="small">{{ b.review.text }}</p>
          </section>

          <section v-if="d.stays.length" class="card">
            <div class="card-head">سفرهای دیگر این مهمان</div>
            <ul class="lo-mini"><li v-for="s in d.stays" :key="s.id"><span>{{ s.unit }}</span><small class="muted">{{ fa(s.stay_text) }} · {{ s.status_text }}</small></li></ul>
          </section>
          <section v-if="d.history.length" class="card">
            <div class="card-head">سابقه</div>
            <ul class="lo-mini"><li v-for="e in d.history" :key="e.id"><span>{{ fa(e.text) }}</span><small class="muted">{{ e.who }} · {{ fa(e.day) }} {{ fa(e.time) }}</small></li></ul>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>
