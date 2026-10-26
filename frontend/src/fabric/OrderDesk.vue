<script setup>
// The phone desk. A customer calls: the seller finds them, sees their account at a glance, types the order
// as it is said, and the assistant turns it into a draft invoice (matched to the stock, priced, checked).
// Nothing is saved until the seller confirms; then it goes into the sales, stock and accounts files.
import { ref, reactive, computed, watch, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast, busy, idle } from "../lib/notify.js"
import { money, num, meters } from "./lib.js"
import Icon from "../components/Icon.vue"
import Avatar from "../components/Avatar.vue"
import CustomerCard from "./CustomerCard.vue"

const emit = defineEmits(["files"])
const q = ref(""), found = ref([]), frequent = ref([]), cid = ref(null), who = ref(null)
const note = ref(""), reading = ref(false), draft = ref(null), saving = ref(false), saved = ref(null)
const pay = reactive({ payment: "چک", days: 45, bank: "ملت", number: "" })
const stock = ref({}), cardRef = ref(null)
const BANKS = ["ملت", "ملی", "صادرات", "تجارت", "سپه", "پاسارگاد", "رسالت"]

onMounted(async () => {
  frequent.value = (await api("/fabric/customers")).slice(0, 6)
  stock.value = Object.fromEntries((await api("/fabric/stock")).map((p) => [p.code, p]))
})
let timer
watch(q, (v) => {
  clearTimeout(timer)
  if (!v.trim()) { found.value = []; return }
  timer = setTimeout(async () => { found.value = await api("/fabric/customers?q=" + encodeURIComponent(v)) }, 200)
})
const pick = (c) => { cid.value = c.id; who.value = c; q.value = ""; found.value = []; draft.value = null; saved.value = null; note.value = "" }

const read = async () => {
  if (!note.value.trim()) return
  reading.value = true; saved.value = null
  busy("order", "دستیار در حال خواندن سفارش")
  try { draft.value = await api("/fabric/order/read", { customer_id: cid.value, note: note.value }) }
  catch (e) { toast({ tone: "danger", title: "سفارش خوانده نشد", body: e.message }) }
  finally { reading.value = false; idle("order") }
}
// a line changed by hand (another product, another quantity): priced again from the stock file
const reprice = (l) => {
  const p = stock.value[l.code]
  if (!p) return
  l.title = p.title; l.price = p.sell_price
  l.meters = l.rolls ? l.rolls * p.roll_meters : Number(l.meters) || 0
  l.amount = Math.round(l.meters * p.sell_price / 1000) * 1000
  l.short = l.meters > p.meters; l.stock_meters = p.meters; l.stock_rolls = p.rolls
}
const total = computed(() => (draft.value?.lines || []).reduce((s, l) => s + l.amount, 0))
const canSave = computed(() => draft.value && draft.value.lines.length && draft.value.lines.every((l) => l.meters > 0 && !l.short))
const remove = (i) => draft.value.lines.splice(i, 1)

const confirm = async () => {
  saving.value = true
  try {
    const r = await api("/fabric/order/confirm", {
      customer_id: cid.value, payment: pay.payment, cheque_days: pay.days, cheque_bank: pay.bank, cheque_number: pay.number,
      lines: draft.value.lines.map((l) => ({ code: l.code, rolls: l.rolls, meters: l.meters })) })
    saved.value = r; draft.value = null; note.value = ""
    toast({ tone: "success", title: `فاکتور ${fa(r.invoice)} ثبت شد`, body: `${money(r.total)} · به فایل ${r.files.join(" و ")} اضافه شد.` })
    cardRef.value?.reload()
    stock.value = Object.fromEntries((await api("/fabric/stock")).map((p) => [p.code, p]))
  } catch (e) { toast({ tone: "danger", title: "فاکتور ثبت نشد", body: e.message }) }
  finally { saving.value = false }
}
</script>

<template>
  <div class="desk">
    <div class="desk-side">
      <section class="card desk-find">
        <div class="card-head"><Icon name="message" :size="18" />چه کسی زنگ زده؟</div>
        <div class="desk-search">
          <Icon name="search" :size="18" />
          <input v-model="q" class="search" placeholder="نام مشتری، فروشگاه یا شهر" aria-label="جستجوی مشتری" autocomplete="off">
          <ul v-if="found.length" class="desk-results" role="listbox">
            <li v-for="c in found" :key="c.id"><button role="option" @click="pick(c)">
              <Avatar :name="c.name" :size="32" /><span class="grow"><b>{{ c.name }}</b><small class="muted">{{ c.shop }} · {{ c.city }}</small></span>
              <span v-if="c.bounced" class="tag st-bad">چک برگشتی</span></button></li>
          </ul>
        </div>
        <div v-if="!cid" class="desk-frequent">
          <small class="muted">مشتری‌های پرخرید:</small>
          <div class="fc-chips"><button v-for="c in frequent" :key="c.id" class="chip-btn" @click="pick(c)">{{ c.name }} · {{ c.city }}</button></div>
        </div>
      </section>
      <div v-if="cid" class="desk-card"><CustomerCard ref="cardRef" :id="cid" compact /></div>
    </div>

    <div class="desk-main">
      <section v-if="!cid" class="card desk-empty">
        <Icon name="message" :size="40" />
        <b>منتظر تماس</b>
        <p class="muted">مشتری را پیدا کنید؛ کارت حسابش کنار صفحه باز می‌شود و سفارشش را همین‌جا بنویسید.</p>
      </section>
      <template v-else>
        <section class="card">
          <div class="card-head"><span class="grow">سفارش {{ who.name }}</span></div>
          <textarea v-model="note" rows="3" class="desk-note" aria-label="سفارش تلفنی"
                    placeholder="همان‌طور که مشتری می‌گوید بنویسید، مثلاً: ۳ توپ کتان کش مشکی و ۲۰ متر حریر سفید"
                    @keydown.ctrl.enter="read" @keydown.meta.enter="read"></textarea>
          <div class="btn-row">
            <button class="btn primary" :disabled="reading || !note.trim()" @click="read">
              <span v-if="reading" class="dots"><i></i><i></i><i></i></span><Icon v-else name="sparkles" :size="18" />ساخت پیش‌فاکتور</button>
          </div>
        </section>

        <section v-if="saved" v-pop class="card desk-saved">
          <div class="desk-saved-head">
            <span class="tint lg t-success"><Icon name="check" :size="26" /></span>
            <div class="grow"><b>فاکتور {{ fa(saved.invoice) }} ثبت شد · {{ money(saved.total) }}</b>
              <small class="muted">{{ saved.steps.length === 3 ? 'هر سه فایل' : 'فایل‌های ' + saved.files.join(' و ') }} با هم به‌روز شد و در دفتر رویدادها با نام شما ثبت شد.</small></div>
            <button class="btn sm ghost" @click="emit('files')">دیدن در اکسل</button>
          </div>
          <ol class="desk-flow">
            <li v-for="(st, i) in saved.steps" :key="st.file" :style="{ '--d': i * .35 + 's' }">
              <span class="df-dot"><Icon name="check" :size="14" /></span>
              <b>{{ st.file }}</b><small>{{ fa(st.text) }}</small>
            </li>
          </ol>
        </section>

        <section v-if="draft" v-reveal class="card desk-draft">
          <div class="card-head"><span class="grow">پیش‌فاکتور</span><small v-if="draft.by_model">خوانده‌شده با دستیار</small></div>
          <ul v-if="draft.warnings.length" class="fc-warnings">
            <li v-for="w in draft.warnings" :key="w.text" :class="['check', w.tone === 'danger' ? 'bad' : 'warn']"><Icon name="alert" :size="16" /><span>{{ fa(w.text) }}</span></li>
          </ul>
          <p v-for="u in draft.unmatched" :key="u.text" class="check warn">«{{ u.text }}» در انبار پیدا نشد.</p>
          <ul class="desk-lines">
            <li v-for="(l, i) in draft.lines" :key="i" :class="{ short: l.short }">
              <div class="dl-what">
                <select v-model="l.code" @change="reprice(l)" :aria-label="'جنس ردیف ' + (i + 1)">
                  <option v-for="o in l.options" :key="o.code" :value="o.code">{{ o.title }}</option>
                </select>
                <small class="muted">گفته شد: «{{ fa(l.asked) }}» · موجود {{ fa(l.stock_rolls) }} توپ</small>
              </div>
              <label class="dl-qty">
                <input v-if="l.rolls" v-model.number="l.rolls" type="number" min="1" @input="reprice(l)" :aria-label="'توپ ردیف ' + (i + 1)">
                <input v-else v-model.number="l.meters" type="number" min="1" @input="reprice(l)" :aria-label="'متر ردیف ' + (i + 1)">
                <span>{{ l.rolls ? 'توپ' : 'متر' }}</span>
              </label>
              <div class="dl-amount"><b>{{ num(l.amount) }}</b><small class="muted">{{ meters(l.meters) }} × {{ money(l.price) }}</small></div>
              <button class="icon-btn sm" @click="remove(i)" :aria-label="'حذف ردیف ' + (i + 1)"><Icon name="x" :size="16" /></button>
            </li>
          </ul>
          <div class="desk-total"><span>جمع فاکتور</span><b>{{ num(total) }} تومان</b><small class="muted">{{ money(total) }}</small></div>

          <div class="desk-pay">
            <div class="segmented" role="radiogroup" aria-label="نوع پرداخت">
              <button v-for="p in ['نقد', 'چک', 'نسیه']" :key="p" role="radio" :aria-checked="pay.payment === p" :class="{ on: pay.payment === p }" @click="pay.payment = p">{{ p }}</button>
            </div>
            <template v-if="pay.payment === 'چک'">
              <label class="field"><span>سررسید</span>
                <select v-model.number="pay.days"><option v-for="d in [30, 45, 60, 90]" :key="d" :value="d">{{ fa(d) }} روز دیگر</option></select></label>
              <label class="field"><span>بانک</span><select v-model="pay.bank"><option v-for="b in BANKS" :key="b">{{ b }}</option></select></label>
              <label class="field"><span>شماره چک</span><input v-model="pay.number" maxlength="20" inputmode="numeric" placeholder="اختیاری"></label>
            </template>
          </div>
          <div class="btn-row desk-actions">
            <button class="btn primary" :disabled="!canSave || saving" @click="confirm"><Icon name="check" :size="18" />تأیید و ثبت فاکتور</button>
            <button class="btn ghost" @click="draft = null">انصراف</button>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>
