<script setup>
// One booking in a side drawer: the guest (past stays, notes), the stay and its price night by night, the room (the
// assistant's suggestions, best first, with why), the folio (charges, payments, what is left), and what can be done
// now: take a payment, check in (national ID, plate, the couple's papers), add a charge, change the dates, settle
// and check out, cancel by the hotel's rule, mark a no-show, copy the confirmation or the thank-you message. A booking
// from the public website may carry the guest's deposit receipt: a person checks the bank and accepts or turns it down.
import { ref, reactive, computed, watch } from "vue"
import { api, fa, hotelSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { hotelInfo, STATUS_TONE, ROOM_TONE, digits } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import DatePicker from "../components/core/DatePicker.vue"
import HowTip from "../fabric/HowTip.vue"

const props = defineProps({ id: Number })
const emit = defineEmits(["close", "changed"])
const role = hotelSession.user.role
const front = role === "manager" || role === "reception"
const d = ref(null), busy = ref(""), open = ref("")
const pay = reactive({ amount: "", method: "card" }), ch = reactive({ kind: "restaurant", amount: "", note: "" })
const ci = reactive({ national_id: "", plate: "", docs: false }), dates = reactive({ arrive: null, depart: null }), msg = ref("")
const load = async () => { d.value = await api(`/hotel/bookings/${props.id}`) }
watch(() => props.id, () => { d.value = null; open.value = ""; load() }, { immediate: true })
const b = computed(() => d.value?.booking)
const today = computed(() => b.value && b.value.arrive_j <= hotelInfo.today)   // its arrival day has come (the server's date)
async function act(key, path, body, title, after) {
  busy.value = key
  try { const r = await api(path, body); toast({ tone: "success", title: typeof title === "function" ? title(r) : title }); open.value = ""; after?.(r); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "خانه‌ها را درست پر کنید" : e.message }) }
  finally { busy.value = "" }
}
const room = (s) => act("room" + s.room_id, `/hotel/bookings/${props.id}/room`, { room_id: s.room_id }, (r) => `اتاق ${s.number}` + (r.upgrade ? " (ارتقا)" : ""))
const doPay = () => act("pay", `/hotel/bookings/${props.id}/pay`, { amount: digits(pay.amount), method: pay.method }, (r) => r.status === "confirmed" && b.value.status === "tentative" ? "پرداخت ثبت شد و رزرو قطعی شد" : "پرداخت ثبت شد", () => { pay.amount = "" })
const doCharge = () => act("charge", `/hotel/bookings/${props.id}/charge`, { kind: ch.kind, amount: digits(ch.amount), note: ch.note }, "هزینه ثبت شد", () => { ch.amount = ""; ch.note = "" })
const checkin = (force = false) => act("in", `/hotel/bookings/${props.id}/checkin`, { ...ci, force }, "اتاق تحویل داده شد")
const checkout = () => act("out", `/hotel/bookings/${props.id}/checkout`, {}, (r) => r.credit > 0 ? "خروج ثبت شد؛ مهمان بستانکار است" : "تسویه و خروج ثبت شد")
const cancel = () => act("cancel", `/hotel/bookings/${props.id}/cancel`, {}, (r) => r.amount ? `لغو شد؛ ${fa(r.amount.toLocaleString())} تومان برگشت داده می‌شود` : "لغو شد")
const noshow = () => act("noshow", `/hotel/bookings/${props.id}/noshow`, {}, "نیامدن ثبت شد")
const changeDates = () => act("dates", `/hotel/bookings/${props.id}/dates`, { ...dates }, "تاریخ‌ها و قیمت به‌روز شد")
const message = async (kind) => { try { msg.value = (await api(`/hotel/bookings/${props.id}/message?kind=${kind}`)).text; open.value = "msg" } catch (e) { toast({ tone: "danger", title: e.message }) } }
const copy = async () => { try { await navigator.clipboard.writeText(msg.value); toast({ tone: "success", title: "متن کپی شد" }) } catch {} }
const receipt = (ok) => act("rc", `/hotel/bookings/${props.id}/receipt`, { ok }, ok ? "بیعانه ثبت شد و رزرو قطعی شد" : "رسید پذیرفته نشد؛ مهمان در سایت می‌بیند")
const toggle = (k) => { open.value = open.value === k ? "" : k; if (k === "dates") Object.assign(dates, { arrive: b.value.arrive_j, depart: b.value.depart_j }) }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer k-drawer" v-drawer aria-label="رزرو">
      <div class="drawer-head"><b class="text-ink">رزرو {{ d ? fa(d.booking.id) : '' }}</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="6" /></div>
        <template v-else>
          <section class="card k-head">
            <div class="k-row-top"><b class="k-title">{{ b.guest }}</b><span :class="['tag', 'k-t-' + STATUS_TONE[b.status]]">{{ b.status_text }}</span></div>
            <div class="k-tags"><span v-if="b.vip" class="tag k-t-warning">مهمان ویژه</span><span class="tag" dir="ltr">{{ fa(b.phone) }}</span><span class="tag">{{ b.source_text }}</span>
              <span v-if="b.ref" class="tag" dir="ltr">{{ b.ref }}</span></div>
            <p v-if="b.notes" class="check warn small"><Icon name="alert" :size="14" /><span>{{ b.notes }}</span></p>
            <dl class="k-dl">
              <dt>اقامت</dt><dd>{{ fa(b.stay_text) }}</dd>
              <dt>اتاق</dt><dd>{{ b.type_text }}<template v-if="b.room"> · اتاق {{ fa(b.room) }} <span :class="['tag', 'k-t-' + ROOM_TONE[b.room_status]]">{{ b.room_status_text }}</span></template><template v-else> · هنوز اتاق ندارد</template></dd>
              <dt>نفرات</dt><dd>{{ fa(b.people_text) }}<template v-if="b.ages.length"> ({{ fa(b.ages.join('، ')) }} ساله)</template> · {{ b.board_text }}</dd>
              <dt>قیمت</dt><dd class="flex items-center gap-2">{{ fa(b.total_text) }}<template v-if="b.discount"> (با {{ fa(b.discount) }} درصد تخفیف)</template><HowTip :lines="d.price_how" /></dd>
              <dt v-if="b.status === 'tentative'">بیعانه</dt><dd v-if="b.status === 'tentative'" class="k-late">تا {{ fa(b.deposit_due_text) }}</dd>
              <dt v-if="b.requests">درخواست</dt><dd v-if="b.requests">{{ b.requests }}</dd>
              <dt>رسیدن</dt><dd>ساعت {{ fa(b.eta || hotelInfo.check_in) }}</dd>
            </dl>
            <div class="k-btns">
              <button v-if="['tentative', 'confirmed'].includes(b.status)" class="btn sm" @click="message('confirm')"><Icon name="message" :size="14" />پیام تأیید</button>
              <button v-if="b.status === 'out'" class="btn sm" @click="message('thanks')"><Icon name="heart" :size="14" />پیام تشکر</button>
            </div>
            <template v-if="open === 'msg'"><textarea v-model="msg" rows="7" class="k-text"></textarea>
              <div class="btn-row"><button class="btn sm" @click="copy">کپی متن</button><button class="btn ghost sm" @click="open = ''">بستن</button></div></template>
          </section>

          <section v-if="d.receipt" class="card" :class="{ 'k-receipt-wait': d.receipt.status === 'waiting' }">
            <div class="card-head">رسید بیعانه از سایت <small>{{ fa(d.receipt.at) }}</small></div>
            <img v-if="d.receipt.data" :src="d.receipt.data" alt="رسید بیعانه" class="ht-receipt">
            <p v-if="d.receipt.status === 'waiting'" class="small">بیعانه‌ی این رزرو {{ fa(d.receipt.deposit_text) }} است. اگر این مبلغ به حساب هتل آمده، تأیید کنید تا ثبت و رزرو قطعی شود.</p>
            <p v-else class="muted small">{{ d.receipt.status === 'ok' ? 'تأیید شد و بیعانه ثبت شد.' : 'پذیرفته نشد.' }}</p>
            <div v-if="d.receipt.status === 'waiting' && b.status === 'tentative'" class="btn-row">
              <button class="btn primary sm" :disabled="busy === 'rc'" @click="receipt(true)">واریز دیده شد، ثبت بیعانه</button>
              <button class="btn ghost sm" :disabled="busy === 'rc'" @click="receipt(false)">پذیرفته نیست</button></div>
          </section>

          <section v-if="d.suggest" class="card">
            <div class="card-head">{{ b.room ? 'جابه‌جایی اتاق' : 'انتخاب اتاق' }} <small>پیشنهاد دستیار، بهترین اول</small></div>
            <p v-if="!d.suggest.length" class="muted small">اتاق آزاد دیگری از این نوع برای همه‌ی این شب‌ها نیست.</p>
            <ul class="k-mini"><li v-for="s in d.suggest" :key="s.room_id">
              <div class="k-row-top"><b>اتاق {{ fa(s.number) }}</b><button class="btn sm" :disabled="busy === 'room' + s.room_id" @click="room(s)">{{ b.room ? 'ببر به این اتاق' : 'این اتاق' }}</button></div>
              <small class="muted">{{ s.why.join('، ') }}</small></li></ul>
          </section>

          <section class="card">
            <div class="card-head"><span class="grow">کارها</span></div>
            <div class="k-btns">
              <button v-if="front && ['confirmed', 'tentative'].includes(b.status) && today" class="btn primary sm" @click="toggle('in')"><Icon name="key" :size="14" />تحویل اتاق</button>
              <button v-if="front && b.status === 'in_house'" class="btn primary sm" @click="toggle('out')"><Icon name="logout" :size="14" />تسویه و خروج</button>
              <button v-if="b.status === 'in_house'" class="btn sm" @click="toggle('charge')">هزینه</button>
              <button v-if="!['cancelled', 'noshow', 'out'].includes(b.status)" class="btn sm" @click="toggle('pay')">پرداخت</button>
              <button v-if="['tentative', 'confirmed', 'in_house'].includes(b.status)" class="btn ghost sm" @click="toggle('dates')">تغییر تاریخ</button>
              <button v-if="['tentative', 'confirmed'].includes(b.status)" class="btn ghost sm" @click="toggle('cancel')">لغو</button>
              <button v-if="front && ['tentative', 'confirmed'].includes(b.status) && today" class="btn ghost sm" @click="noshow">نیامد</button>
            </div>
            <form v-if="open === 'in'" class="flex flex-col gap-2 mt-3" @submit.prevent="checkin()">
              <div class="k-grid2"><label class="field"><span>کد ملی سرپرست</span><input v-model="ci.national_id" inputmode="numeric" maxlength="12" dir="ltr"></label>
                <label class="field"><span>پلاک خودرو</span><input v-model="ci.plate" maxlength="20" placeholder="اختیاری"></label></div>
              <label class="k-check"><input v-model="ci.docs" type="checkbox">مدارک همه‌ی همراهان دیده شد (برای زوج‌ها شناسنامه یا عقدنامه)</label>
              <p v-if="b.room_status === 'dirty'" class="check warn small"><Icon name="alert" :size="14" /><span>اتاق {{ fa(b.room) }} هنوز تمیز نشده است.</span></p>
              <div class="btn-row"><button class="btn primary sm" :disabled="busy === 'in' || !b.room">ثبت ورود</button>
                <button v-if="b.room_status === 'dirty' && role === 'manager'" type="button" class="btn ghost sm" @click="checkin(true)">با همین وضع تحویل بده</button></div>
              <small v-if="!b.room" class="k-late">اول از بالا اتاق را انتخاب کنید.</small>
            </form>
            <div v-if="open === 'out'" class="flex flex-col gap-2 mt-3">
              <p class="small">مانده‌ی صورت‌حساب: <b :class="{ 'k-owe': d.folio.balance > 0 }">{{ fa(d.folio.balance_text) }}</b>. اگر مانده‌ای هست، اول پرداخت را ثبت کنید.</p>
              <div class="btn-row"><button class="btn primary sm" :disabled="busy === 'out'" @click="checkout">ثبت خروج</button></div>
            </div>
            <form v-if="open === 'charge'" class="k-pay mt-3" @submit.prevent="doCharge">
              <select v-model="ch.kind" class="k-select" aria-label="نوع هزینه"><option v-for="(t, k) in hotelInfo.charges" v-show="k !== 'room'" :key="k" :value="k">{{ t }}</option></select>
              <input v-model="ch.amount" inputmode="numeric" placeholder="مبلغ به تومان" aria-label="مبلغ"><input v-model="ch.note" maxlength="120" placeholder="شرح" aria-label="شرح">
              <button class="btn primary sm" :disabled="busy === 'charge' || !digits(ch.amount)">ثبت</button>
            </form>
            <form v-if="open === 'pay'" class="k-pay mt-3" @submit.prevent="doPay">
              <input v-model="pay.amount" inputmode="numeric" placeholder="مبلغ به تومان" aria-label="مبلغ پرداخت">
              <select v-model="pay.method" class="k-select" aria-label="روش پرداخت"><option v-for="(t, k) in hotelInfo.methods" :key="k" :value="k">{{ t }}</option></select>
              <button class="btn primary sm" :disabled="busy === 'pay' || !digits(pay.amount)">ثبت پرداخت</button>
            </form>
            <form v-if="open === 'dates'" class="flex flex-col gap-2 mt-3" @submit.prevent="changeDates">
              <div class="k-grid2"><div class="field"><span>ورود</span><DatePicker v-model="dates.arrive" :min="'1400/01/01'" label="ورود" /></div>
                <div class="field"><span>خروج</span><DatePicker v-model="dates.depart" :min="hotelInfo.today" label="خروج" /></div></div>
              <small class="muted">قیمت شب‌های جدید دوباره حساب می‌شود؛ شب‌هایی که در صورت‌حساب ثبت شده تغییر نمی‌کند.</small>
              <div class="btn-row"><button class="btn primary sm" :disabled="busy === 'dates'">ثبت تاریخ‌ها</button></div>
            </form>
            <div v-if="open === 'cancel' && d.refund" class="flex flex-col gap-2 mt-3">
              <p class="small">{{ fa(d.refund.days) }} روز تا ورود مانده. پرداخت‌شده {{ fa(d.refund.paid.toLocaleString()) }} تومان؛ طبق قانون هتل <b>{{ fa(d.refund.percent) }} درصد</b>، یعنی {{ fa(d.refund.amount.toLocaleString()) }} تومان برمی‌گردد.</p>
              <small class="muted">{{ fa(d.refund.rule) }}</small>
              <div class="btn-row"><button class="btn danger-soft sm" :disabled="busy === 'cancel'" @click="cancel">لغو رزرو</button></div>
            </div>
          </section>

          <section class="card">
            <div class="k-balance"><span>صورت‌حساب: <b :class="{ 'k-owe': d.folio.balance > 0 }">{{ d.folio.balance > 0 ? 'مانده ' : d.folio.balance < 0 ? 'پیش‌پرداخت ' : '' }}{{ fa(d.folio.balance_text.replace('منفی ', '')) }}</b></span>
              <small class="muted">هزینه‌ها {{ fa(d.folio.charged.toLocaleString()) }} · پرداخت‌ها {{ fa(d.folio.paid.toLocaleString()) }}</small></div>
            <ul class="k-mini">
              <li v-for="x in d.folio.charges" :key="'c' + x.id"><div class="k-row-top"><span>{{ x.kind_text }}<template v-if="x.note"> · {{ x.note }}</template></span><b>{{ fa(x.amount_text) }}</b></div><small class="muted">{{ fa(x.day_text) }}</small></li>
              <li v-for="x in d.folio.payments" :key="'p' + x.id"><div class="k-row-top"><span>{{ x.amount < 0 ? 'برگشت' : 'پرداخت' }} · {{ x.method_text }}</span><b class="ht-paid">{{ fa(x.amount_text) }}</b></div><small class="muted">{{ fa(x.day_text) }}</small></li>
            </ul>
          </section>

          <section v-if="d.guest && d.guest.stays.length > 1" class="card">
            <div class="card-head">سفرهای این مهمان <small>{{ fa(d.guest.visits) }} اقامت · جمع {{ fa(d.guest.spent_text) }}</small></div>
            <ul class="k-mini"><li v-for="s in d.guest.stays.filter((x) => x.id !== b.id)" :key="s.id"><span>{{ s.type_text }}<template v-if="s.room"> · اتاق {{ fa(s.room) }}</template></span><small class="muted">{{ fa(s.stay_text) }} · {{ s.status_text }}</small></li></ul>
          </section>

          <section v-if="d.history.length" class="card">
            <div class="card-head">سابقه</div>
            <ul class="k-mini"><li v-for="e in d.history" :key="e.id"><span>{{ fa(e.text) }}</span><small class="muted">{{ e.who }} · {{ fa(e.day) }} {{ fa(e.time) }}</small></li></ul>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>
