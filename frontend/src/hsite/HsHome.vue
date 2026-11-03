<script setup>
// The hotel's first page: the drawn hotel on the shore, a search for dates, people (children's ages: under 6 is free)
// and meals, then the room types. Before a search each shows the price of a night in the quiet months; after it, the
// stay's price for these people, free types first, with how it was worked out. «رزرو» asks for the hour of arrival
// and any request and makes a booking that waits for its deposit; without an account it goes to the login and back.
import { ref, reactive, computed, onMounted } from "vue"
import { call, fa, go, guest, lastSearch } from "./api.js"
import HsArt from "./HsArt.vue"
import DatePicker from "../components/core/DatePicker.vue"

const props = defineProps({ site: Object })
const f = reactive({ arrive: null, depart: null, adults: 2, kids: 0, ages: [], board: "BB" })
const found = ref(null), busy = ref(false), error = ref(""), picked = ref(""), extra = reactive({ eta: "14:00", requests: "" }), booking = ref(false)
const ETAS = ["12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
const setKids = () => { f.ages = Array.from({ length: f.kids }, (_, i) => f.ages[i] ?? 8) }
const body = () => ({ arrive: f.arrive, depart: f.depart, adults: f.adults, ages: f.ages.slice(0, f.kids), board: f.board })
async function search(scroll = true) {
  if (!f.arrive || !f.depart) { error.value = "تاریخ ورود و خروج را انتخاب کنید"; return }
  busy.value = true; error.value = ""; picked.value = ""
  try {
    found.value = await call("/search", body())
    if (scroll) setTimeout(() => document.getElementById("rooms")?.scrollIntoView({ behavior: "smooth" }), 50)
  } catch (e) { error.value = e.message; found.value = null } finally { busy.value = false }
}
function pick(o) {
  if (!guest.token) { lastSearch.set({ ...f, type: o.type }); go("/login?next=" + encodeURIComponent("/")); return }
  picked.value = picked.value === o.type ? "" : o.type
}
async function book(o) {
  booking.value = true; error.value = ""
  try {
    await call("/bookings", { ...body(), type: o.type, eta: extra.eta, requests: extra.requests })
    lastSearch.set(null); go("/account")
  } catch (e) { error.value = e.message } finally { booking.value = false }
}
onMounted(async () => {
  const s = lastSearch.get()
  if (!s || !guest.token) return
  Object.assign(f, { arrive: s.arrive, depart: s.depart, adults: s.adults, kids: s.kids, ages: s.ages, board: s.board })
  await search(false)
  if (found.value?.options.some((o) => o.type === s.type && o.fits && o.free)) {
    picked.value = s.type
    setTimeout(() => document.getElementById("opt-" + s.type)?.scrollIntoView({ behavior: "smooth", block: "center" }), 80)
  }
  lastSearch.set(null)
})
const list = computed(() => found.value ? found.value.options : props.site.types.map((t) => ({ type: t.key, name: t.name, about: t.about, fits: true, free: true, info: t })))
</script>

<template>
  <section class="eco-hero">
    <HsArt kind="hero" />
    <div class="eco-hero-text">
      <h1>{{ site.name }}</h1>
      <p>اتاق‌ها، سوئیت‌ها و ویلاهای کنار دریا؛ برای تاریخ‌های خودتان جای خالی و قیمت را ببینید و همین‌جا رزرو کنید.</p>
      <small>{{ site.place }}</small>
    </div>
  </section>
  <form class="eco-search hs-search" @submit.prevent="search()" aria-label="جستجوی اتاق خالی">
    <div class="eco-field"><span>ورود</span><DatePicker v-model="f.arrive" label="تاریخ ورود" /></div>
    <div class="eco-field"><span>خروج</span><DatePicker v-model="f.depart" :min="f.arrive" label="تاریخ خروج" /></div>
    <label class="eco-field"><span>بزرگسال</span><select v-model.number="f.adults"><option v-for="n in 8" :key="n" :value="n">{{ fa(n) }} نفر</option></select></label>
    <label class="eco-field"><span>کودک</span><select v-model.number="f.kids" @change="setKids"><option v-for="n in 5" :key="n" :value="n - 1">{{ n - 1 ? fa(n - 1) + ' کودک' : 'بدون کودک' }}</option></select></label>
    <label class="eco-field"><span>پذیرایی</span><select v-model="f.board"><option v-for="(t, k) in site.boards" :key="k" :value="k">{{ t }}</option></select></label>
    <div v-if="f.kids" class="hs-kids">
      <label v-for="(a, i) in f.ages" :key="i" class="eco-field"><span>سن کودک {{ fa(i + 1) }}</span>
        <select v-model.number="f.ages[i]"><option v-for="n in 18" :key="n" :value="n - 1">{{ n - 1 ? fa(n - 1) + ' ساله' : 'زیر یک سال' }}</option></select></label>
    </div>
    <button class="eco-btn main" :disabled="busy">{{ busy ? 'در حال جستجو…' : 'جای خالی را نشان بده' }}</button>
    <p v-if="error" class="eco-msg bad" style="grid-column: 1 / -1; margin: 0">{{ error }}</p>
  </form>

  <section id="rooms" class="eco-section">
    <div class="eco-wrap">
      <h2>{{ found ? `برای ${fa(found.stay)}` : 'اتاق‌ها، سوئیت‌ها و ویلاها' }}</h2>
      <p class="eco-sub">{{ found ? `${fa(found.people)}، ${site.boards[f.board]}. قیمت کل اقامت؛ جای خالی اول.` : `کودکان زیر ${fa(site.child_free)} سال رایگان‌اند. تاریخ‌هایتان را بالا انتخاب کنید تا قیمت دقیق را ببینید.` }}</p>
      <ul class="eco-units">
        <li v-for="o in list" :key="o.type" :id="'opt-' + o.type">
          <div class="eco-card hs-opt" :class="{ off: found && !(o.fits && o.free) }" style="cursor: default">
            <div class="eco-pic"><HsArt :kind="o.type" /><span v-if="o.last" class="eco-tag warn">فقط چند اتاق مانده</span></div>
            <div class="eco-card-body">
              <h3>{{ o.name }}</h3>
              <span v-if="o.info" class="eco-meta">{{ fa(o.info.beds) }} نفر، با تخت اضافه تا {{ fa(o.info.most) }} نفر</span>
              <span class="eco-meta">{{ o.about }}</span>
              <div v-if="!found" class="eco-price"><span class="eco-meta">هر شب از</span><b>{{ fa(o.info.price_text) }}</b></div>
              <template v-else-if="o.fits && o.free">
                <div class="eco-price"><span class="eco-meta">جمع اقامت</span><b>{{ fa(o.total_text) }}</b></div>
                <details><summary class="eco-meta" style="cursor: pointer">قیمت شب به شب</summary><ul class="eco-how"><li v-for="(l, i) in o.how" :key="i">{{ fa(l) }}</li></ul></details>
                <span class="eco-meta">بیعانه برای قطعی شدن: {{ fa(o.deposit_text) }}</span>
                <button class="eco-btn main" style="margin-top: 6px" @click="pick(o)">{{ picked === o.type ? 'بستن' : 'رزرو' }}</button>
              </template>
              <span v-else class="eco-tag bad" style="align-self: flex-start">{{ o.why }}</span>
            </div>
            <form v-if="picked === o.type" class="hs-book" @submit.prevent="book(o)">
              <label class="eco-field"><span>ساعت تقریبی رسیدن</span><select v-model="extra.eta"><option v-for="t in ETAS" :key="t" :value="t">{{ fa(t) }}</option></select></label>
              <label class="eco-field"><span>درخواست (اختیاری)</span><textarea v-model="extra.requests" rows="2" maxlength="300" placeholder="مثلاً تخت کودک، طبقه‌ی بالا"></textarea></label>
              <p class="eco-meta" style="margin: 0">رزرو تا رسیدن بیعانه موقت است. پس از ثبت، شماره‌ی کارت و مهلت پرداخت را در «رزروهای من» می‌بینید.</p>
              <button class="eco-btn main" :disabled="booking">{{ booking ? 'در حال ثبت…' : `ثبت رزرو به نام ${guest.name}` }}</button>
            </form>
          </div>
        </li>
      </ul>
    </div>
  </section>

  <section class="eco-section">
    <div class="eco-wrap">
      <h2>پیش از سفر</h2>
      <div class="hs-before"><div class="eco-pic"><HsArt kind="breakfast" /></div>
      <ul class="hs-facts">
        <li><b>ورود و خروج</b><span class="eco-meta">تحویل اتاق از ساعت {{ fa(site.check_in) }}، تخلیه تا ساعت {{ fa(site.check_out) }}. هنگام ورود کارت ملی همه‌ی همراهان لازم است.</span></li>
        <li><b>پذیرایی</b><span class="eco-meta">همه‌ی اتاق‌ها با صبحانه. نیم‌پانسیون {{ fa(site.board_prices.HB) }} و پانسیون کامل {{ fa(site.board_prices.FB) }} برای هر نفر در شب.</span></li>
        <li><b>بیعانه</b><span class="eco-meta">{{ fa(site.deposit) }} درصد قیمت کل، کارت به کارت، تا ۲۴ ساعت پس از رزرو.</span></li>
        <li><b>لغو</b><span class="eco-meta">{{ fa(site.refund_rule) }}</span></li>
      </ul></div>
    </div>
  </section>
</template>
