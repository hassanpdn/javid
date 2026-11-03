<script setup>
// «رزرو جدید»: one form for a phone call or a pasted message. The dates and people bring up every room type with how
// many are left on the fullest night and the price («از کجا؟» shows it night by night); the mobile number brings up
// the guest's past stays and notes. Saved as tentative (waiting for its deposit) or confirmed with the payment
// taken now; then the confirmation message to send. No rooms left: the guest goes on the waiting list.
// preset.paste: start from pasted text.
import { ref, reactive, computed, watch } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { hotelInfo, digits } from "./lib.js"
import Icon from "../components/Icon.vue"
import DatePicker from "../components/core/DatePicker.vue"
import HowTip from "../fabric/HowTip.vue"

const props = defineProps({ preset: { type: Object, default: () => ({}) } })
const emit = defineEmits(["close", "saved"])
const pasting = ref(!!props.preset.paste), text = ref(""), found = ref({}), method = ref("")
const f = reactive({ arrive: hotelInfo.today, depart: null, adults: 2, ages: [], board: "BB", agency_id: null, source: "phone", discount: 0,
                     type: "", name: "", phone: "", eta: "14:00", requests: "", pay: "", method: "card" })
const q = ref(null), guest = ref(null), busy = ref(false), error = ref(""), done = ref(null), msg = ref("")
const agencies = computed(() => hotelInfo.agencies)
const source = computed(() => { const a = agencies.value.find((x) => x.id === f.agency_id); return a ? (a.kind === "ota" ? "ota" : a.kind) : f.source })

async function readText() {
  busy.value = true; error.value = ""
  try {
    const r = await api("/hotel/read", { text: text.value })
    const x = r.fields
    if (x.arrive) f.arrive = x.arrive
    if (x.depart) f.depart = x.depart
    if (x.adults) f.adults = x.adults
    if (x.ages) f.ages = [...x.ages]
    if (x.board) f.board = x.board
    if (x.type) f.type = x.type
    if (x.name) f.name = x.name
    if (x.phone) f.phone = x.phone
    if (/واتس|whatsapp/i.test(text.value)) f.source = "whatsapp"
    found.value = r.found; method.value = r.method; guest.value = r.guest; pasting.value = false
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function quote() {
  if (!f.arrive || !f.depart) { q.value = null; return }
  try { q.value = await api("/hotel/quote", { arrive: f.arrive, depart: f.depart, adults: f.adults, ages: f.ages, board: f.board, discount: Number(f.discount) || 0, agency_id: f.agency_id }); error.value = "" }
  catch (e) { q.value = null; error.value = e.message }
}
watch(() => [f.arrive, f.depart, f.adults, f.ages.length, f.ages.join(), f.board, f.agency_id, f.discount], quote, { immediate: true })
let timer
watch(() => f.phone, (p) => {
  clearTimeout(timer)
  const n = String(p).replace(/[۰-۹]/g, (x) => "۰۱۲۳۴۵۶۷۸۹".indexOf(x)).replace(/\D/g, "")
  if (n.length !== 11) return
  timer = setTimeout(async () => { try { const r = await api("/hotel/guests?q=" + n); guest.value = r[0] || null; if (guest.value && !f.name) f.name = guest.value.name } catch {} }, 250)
})
const chosen = computed(() => q.value?.options.find((o) => o.type === f.type))
watch(chosen, (o) => { if (o && !f.pay) f.pay = "" })
const overLimit = computed(() => !f.agency_id && Number(f.discount) > hotelInfo.max_discount)

async function save(status) {
  busy.value = true; error.value = ""
  try {
    const paid = status === "confirmed" ? digits(f.pay) || chosen.value.deposit : 0
    const b = await api("/hotel/bookings", { arrive: f.arrive, depart: f.depart, adults: f.adults, ages: f.ages, board: f.board, discount: Number(f.discount) || 0,
      agency_id: f.agency_id, type: f.type, guest_id: guest.value?.id || null, name: f.name, phone: f.phone, source: source.value, status, paid, method: f.method,
      eta: f.eta, requests: f.requests })
    done.value = b
    msg.value = (await api(`/hotel/bookings/${b.id}/message`)).text
    toast({ tone: "success", title: `رزرو ${b.id} ثبت شد` })
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "خانه‌های لازم را درست پر کنید" : e.message } finally { busy.value = false }
}
async function wait() {
  busy.value = true; error.value = ""
  try { await api("/hotel/waitlist", { name: f.name, phone: f.phone, type: f.type || "dbl_sea", arrive: f.arrive, depart: f.depart, adults: f.adults, note: f.requests })
        toast({ tone: "success", title: "به فهرست انتظار اضافه شد" }); emit("close") }
  catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "نام، شماره و تاریخ‌ها را بنویسید" : e.message } finally { busy.value = false }
}
const copy = async () => { try { await navigator.clipboard.writeText(msg.value); toast({ tone: "success", title: "متن کپی شد" }) } catch {} }
const ETAS = ["12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog wide" v-pop role="dialog" aria-label="رزرو جدید">
      <div class="dialog-head"><h3>{{ done ? `رزرو ${fa(done.id)} ثبت شد` : 'رزرو جدید' }}</h3><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>

      <template v-if="done">
        <p class="check ok small"><Icon name="check" :size="14" /><span>{{ done.guest }} · {{ done.type_text }} · {{ fa(done.stay_text) }} · {{ fa(done.total_text) }} · {{ done.status_text }}</span></p>
        <label class="field"><span>پیام تأیید برای مهمان (از تلفن هتل بفرستید)</span><textarea v-model="msg" rows="8" class="ht-text"></textarea></label>
        <div class="dialog-actions"><button class="btn" @click="copy"><Icon name="file" :size="16" />کپی متن</button>
          <button class="btn primary" @click="emit('saved', done.id)">دیدن رزرو</button></div>
      </template>

      <template v-else-if="pasting">
        <p class="muted small">پیام مهمان یا آژانس را همان‌طور که هست بگذارید. دستیار تاریخ‌ها، تعداد نفر، نوع اتاق، پذیرایی، نام و شماره را درمی‌آورد؛ هر چه در متن نباشد خالی می‌ماند.</p>
        <textarea v-model="text" rows="7" maxlength="3000" placeholder="مثلاً: سلام، ۱۵ تا ۱۸ آذر یک اتاق رو به دریا برای دو نفر با صبحانه می‌خواستم. مریم کاظمی ۰۹۱۲…" aria-label="متن پیام"></textarea>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions"><button class="btn primary" :disabled="busy || text.trim().length < 5" @click="readText"><Icon name="sparkles" :size="18" />{{ busy ? 'در حال خواندن…' : 'خواندن پیام' }}</button>
          <button class="btn ghost" @click="pasting = false">پر کردن دستی</button></div>
      </template>

      <form v-else class="flex flex-col gap-3" @submit.prevent>
        <p v-if="method" class="check info small"><Icon name="info" :size="14" /><span>{{ method === 'model' ? 'دستیار پیام را خواند' : 'پیام با قاعده‌های ثابت خوانده شد' }}. زیر هر مقدار، جایی از پیام که از آن آمده نوشته شده است.</span></p>
        <div class="ht-grid2">
          <div class="field"><span>ورود</span><DatePicker v-model="f.arrive" :min="hotelInfo.today" label="تاریخ ورود" /><small v-if="found.arrive" class="ht-from">«{{ fa(found.arrive) }}»</small></div>
          <div class="field"><span>خروج</span><DatePicker v-model="f.depart" :min="f.arrive || hotelInfo.today" label="تاریخ خروج" /><small v-if="found.depart && found.depart !== found.arrive" class="ht-from">«{{ fa(found.depart) }}»</small></div>
        </div>
        <div class="ht-grid2">
          <label class="field"><span>بزرگسال</span><select v-model.number="f.adults" class="ht-select"><option v-for="n in 8" :key="n" :value="n">{{ fa(n) }} نفر</option></select>
            <small v-if="found.adults" class="ht-from">«{{ fa(found.adults) }}»</small></label>
          <label class="field"><span>پذیرایی</span><select v-model="f.board" class="ht-select"><option v-for="(t, k) in hotelInfo.boards" :key="k" :value="k">{{ t }}</option></select>
            <small v-if="found.board" class="ht-from">«{{ fa(found.board) }}»</small></label>
        </div>
        <div class="field"><span>کودکان (سن هر کدام؛ زیر ۶ سال رایگان)</span>
          <div class="ht-chips">
            <span v-for="(a, i) in f.ages" :key="i" class="flex items-center gap-1"><select v-model.number="f.ages[i]" class="ht-select" :aria-label="'سن کودک ' + (i + 1)"><option v-for="n in 13" :key="n" :value="n - 1">{{ fa(n - 1) }} ساله</option></select>
              <button type="button" class="icon-btn" aria-label="حذف کودک" @click="f.ages.splice(i, 1)"><Icon name="x" :size="14" /></button></span>
            <button type="button" @click="f.ages.push(6)"><Icon name="plus" :size="14" /> کودک</button>
          </div><small v-if="found.ages" class="ht-from">«{{ fa(found.ages) }}»</small></div>
        <div class="ht-grid2">
          <label class="field"><span>از طریق</span>
            <select v-model="f.agency_id" class="ht-select"><option :value="null">مستقیم</option><option v-for="a in agencies" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
          <label v-if="!f.agency_id" class="field"><span>راه تماس</span>
            <select v-model="f.source" class="ht-select"><option value="phone">تلفن</option><option value="whatsapp">واتس‌اپ</option><option value="walkin">حضوری</option></select></label>
          <label v-else class="field"><span>تخفیف آژانس</span><input :value="fa(q?.discount ?? 0) + ' درصد'" disabled></label>
        </div>
        <label v-if="!f.agency_id" class="field"><span>تخفیف (درصد)</span><input v-model="f.discount" inputmode="numeric" maxlength="3">
          <small v-if="overLimit" class="ht-late">بیش از سقف {{ fa(hotelInfo.max_discount) }} درصد است؛ فقط مدیر می‌تواند ثبت کند و در بررسی‌ها دیده می‌شود.</small></label>

        <div class="field"><span>اتاق‌های خالی در همه‌ی شب‌ها <small v-if="found.type" class="ht-from">پیام: «{{ fa(found.type) }}»</small></span>
          <p v-if="!f.depart" class="muted small">تاریخ خروج را انتخاب کنید.</p>
          <ul v-else-if="q" class="ht-quote">
            <li v-for="o in q.options" :key="o.type">
              <button type="button" :class="{ on: f.type === o.type }" :disabled="!o.fits" :aria-pressed="f.type === o.type" @click="f.type = o.type">
                <span class="flex flex-col"><b>{{ o.name }}</b><small>{{ o.fits ? (o.free > 0 ? fa(o.free) + ' اتاق مانده' : 'پر است' + (o.tight ? '، ' + fa(o.tight) : '')) : o.why }}</small></span>
                <span v-if="o.fits" class="ht-q-right"><b>{{ fa(o.total_text) }}</b><HowTip :lines="o.how" /></span>
              </button>
            </li>
          </ul>
          <small v-if="q?.waiting" class="muted">{{ fa(q.waiting) }} نفر برای این شب‌ها در فهرست انتظارند.</small>
        </div>

        <div class="ht-grid2">
          <label class="field"><span>شماره‌ی همراه</span><input v-model="f.phone" dir="ltr" inputmode="tel" maxlength="20" placeholder="09121234567">
            <small v-if="found.phone" class="ht-from">«{{ fa(found.phone) }}»</small></label>
          <label class="field"><span>نام مهمان</span><input v-model="f.name" maxlength="60"><small v-if="found.name" class="ht-from">«{{ fa(found.name) }}»</small></label>
        </div>
        <div v-if="guest" class="ht-guest">
          <b>{{ guest.vip ? 'مهمان ویژه · ' : '' }}{{ fa(guest.visits) }} بار مهمان ما بوده<template v-if="guest.noshows"> · {{ fa(guest.noshows) }} بار نیامده</template></b>
          <small v-if="guest.notes">یادداشت: {{ guest.notes }}</small>
          <small v-if="guest.stays.length">آخرین: {{ guest.stays[0].type_text }}، {{ fa(guest.stays[0].stay_text) }}<template v-if="guest.stays[0].room">، اتاق {{ fa(guest.stays[0].room) }}</template></small>
        </div>
        <div class="ht-grid2">
          <label class="field"><span>ساعت رسیدن</span><select v-model="f.eta" class="ht-select"><option v-for="t in ETAS" :key="t" :value="t">{{ fa(t) }}</option></select></label>
          <label class="field"><span>درخواست‌ها</span><input v-model="f.requests" maxlength="300" placeholder="مثلاً تخت بچه، طبقه‌ی بالا"></label>
        </div>
        <div v-if="chosen" class="ht-grid2">
          <label class="field"><span>پرداخت اکنون (تومان)</span><input v-model="f.pay" inputmode="numeric" :placeholder="'بیعانه ' + fa(chosen.deposit.toLocaleString())"></label>
          <label class="field"><span>روش پرداخت</span><select v-model="f.method" class="ht-select"><option v-for="(t, k) in hotelInfo.methods" :key="k" :value="k">{{ t }}</option></select></label>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions">
          <template v-if="chosen && chosen.free > 0">
            <button type="button" class="btn primary" :disabled="busy || !f.phone" @click="save('confirmed')"><Icon name="check" :size="18" />قطعی، با پرداخت</button>
            <button type="button" class="btn" :disabled="busy || !f.phone" @click="save('tentative')">موقت، منتظر بیعانه</button>
          </template>
          <button v-else-if="f.depart && f.phone" type="button" class="btn" :disabled="busy" @click="wait"><Icon name="users" :size="16" />فهرست انتظار</button>
          <button type="button" class="btn ghost" @click="pasting = true">از روی پیام</button>
        </div>
      </form>
    </div>
  </div>
</template>
