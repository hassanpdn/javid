<script setup>
// One unit: its photos (or drawing), what it has, six weeks of nights (free or taken, each with its price; weekend
// nights tinted), and the booking box: pick the first night and the day of leaving on the calendar, the people, and
// see the price night by night. «درخواست رزرو» needs the guest's account; the host answers it.
import { ref, reactive, computed, watch, onMounted } from "vue"
import { call, fa, go, guest } from "./api.js"
import Art from "./Art.vue"

const props = defineProps({ id: Number, site: Object })
const d = ref(null), error = ref(""), shown = ref(0), q = ref(null), busy = ref(false), sent = ref(null), note = ref("")
const params = new URLSearchParams(location.hash.split("?")[1] || "")
const f = reactive({ arrive: params.get("a"), depart: params.get("d"), people: Number(params.get("p")) || 2 })
onMounted(async () => { try { d.value = await call(`/units/${props.id}`); document.title = `${d.value.unit.name} · ${props.site.name}` } catch (e) { error.value = e.message } })
// calendar clicks: the first picks the arrival night, the second the day of leaving (the day after the last night)
const pick = (n, i) => {
  const start = () => { if (n.free) { f.arrive = n.j; f.depart = null } }
  if (!f.arrive || f.depart || n.j <= f.arrive) return start()
  const cal = d.value.calendar, from = cal.findIndex((x) => x.j === f.arrive)
  if (cal.slice(from, i).some((x) => !x.free)) return start()   // a taken night in between: start again from here
  f.depart = n.j                                                  // the day of leaving may itself be taken by the next guest
}
const state = (n) => f.arrive === n.j || f.depart === n.j ? "edge" : f.arrive && f.depart && n.j > f.arrive && n.j < f.depart ? "in" : ""
watch(() => [f.arrive, f.depart, f.people], async () => {
  q.value = null; error.value = ""
  if (!f.arrive || !f.depart) return
  try { q.value = await call("/search", { arrive: f.arrive, depart: f.depart, people: f.people, unit_id: props.id }) } catch (e) { error.value = e.message }
}, { immediate: true })
async function request() {
  if (!guest.token) { go(`/login?next=${encodeURIComponent(`/unit/${props.id}?a=${f.arrive}&d=${f.depart}&p=${f.people}`)}`); return }
  busy.value = true; error.value = ""
  try { sent.value = await call("/bookings", { unit_id: props.id, arrive: f.arrive, depart: f.depart, people: f.people, note: note.value }) }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
const pics = computed(() => d.value?.unit.photos || [])
</script>

<template>
  <div class="eco-wrap eco-page">
    <button class="eco-link eco-back" @click="go('/')">بازگشت به همه‌ی اتاق‌ها</button>
    <p v-if="error && !d" class="eco-msg bad">{{ error }}</p>
    <div v-if="d" class="eco-unit">
      <div class="flex-col" style="display: flex; flex-direction: column; gap: 18px">
        <div class="eco-gallery">
          <div class="eco-pic"><img v-if="pics.length" :src="pics[shown]" :alt="d.unit.name"><Art v-else :kind="d.unit.art" /></div>
          <div v-if="pics.length > 1" class="eco-thumbs"><button v-for="(p, i) in pics" :key="p" :class="{ on: i === shown }" :aria-label="'عکس ' + (i + 1)" @click="shown = i"><img :src="p" alt=""></button></div>
        </div>
        <div>
          <h1 style="font-size: 28px">{{ d.unit.name }}</h1>
          <p class="eco-meta" style="margin: 0">{{ d.unit.kind_text }} · {{ fa(d.unit.beds) }} تخت · تا {{ fa(d.unit.capacity) }} نفر<template v-if="d.unit.rating.avg"> · ★ {{ fa(d.unit.rating.avg) }} ({{ fa(d.unit.rating.count) }} نظر)</template></p>
          <p>{{ d.unit.description }}</p>
          <div class="eco-chips"><span v-for="a in d.unit.amenities" :key="a" class="eco-tag clay">{{ a }}</span></div>
        </div>
        <section>
          <h3>شب‌های خالی</h3>
          <p class="eco-meta" style="margin: 0 0 8px">اول شب ورود و بعد روز خروج را بزنید. شب‌های چهارشنبه و پنجشنبه رنگی‌اند.</p>
          <div class="eco-cal" role="grid" aria-label="تقویم شب‌ها">
            <button v-for="(n, i) in d.calendar" :key="n.date" :class="[state(n), { we: n.weekend }]" :disabled="!n.free && !(f.arrive && !f.depart && n.j > f.arrive)"
                    :aria-pressed="!!state(n)" :aria-label="`${n.weekday} ${n.day}، ${n.free ? n.price_text : 'پر'}`" @click="pick(n, i)">
              <b>{{ fa(n.day.split(' ')[0]) }}</b><small>{{ n.day.split(' ')[1] }}</small><small>{{ n.free ? fa((n.price / 1e6).toFixed(1).replace('.0', '')) + 'م' : 'پر' }}</small>
            </button>
          </div>
        </section>
      </div>
      <aside class="eco-box" aria-label="رزرو">
        <div class="eco-price" style="margin: 0"><span class="eco-meta">هر شب</span><b>{{ fa(d.unit.price_text) }}</b></div>
        <span class="eco-meta" style="margin-top: -10px">شب‌های چهارشنبه و پنجشنبه {{ fa(d.unit.weekend_text) }}</span>
        <div class="eco-row"><span class="eco-tag">{{ f.arrive ? 'ورود ' + fa(f.arrive) : 'ورود را روی تقویم بزنید' }}</span><span v-if="f.depart" class="eco-tag">خروج {{ fa(f.depart) }}</span></div>
        <label class="eco-field"><span>چند نفر</span><select v-model.number="f.people"><option v-for="n in d.unit.capacity" :key="n" :value="n">{{ fa(n) }} نفر</option></select></label>
        <template v-if="sent">
          <p class="eco-msg ok">درخواست شما ثبت شد. میزبان به‌زودی جواب می‌دهد؛ وضعیتش را در «سفرهای من» ببینید.</p>
          <button class="eco-btn main" @click="go('/account')">سفرهای من</button>
        </template>
        <template v-else-if="q">
          <p v-if="!q.free" class="eco-msg bad">{{ q.why }}</p>
          <template v-else>
            <ol class="eco-how"><li v-for="l in q.quote.how" :key="l">{{ fa(l) }}</li></ol>
            <label class="eco-field"><span>پیام برای میزبان (اختیاری)</span><input v-model="note" maxlength="300" placeholder="مثلاً ساعت رسیدن یا مناسبت سفر"></label>
            <button class="eco-btn main" :disabled="busy" @click="request">{{ guest.token ? 'درخواست رزرو' : 'ورود و درخواست رزرو' }}</button>
            <span class="eco-meta">پس از تأیید میزبان، بیعانه‌ی {{ fa(q.quote.deposit_text) }} را کارت به کارت واریز و عکس رسید را می‌فرستید.</span>
          </template>
        </template>
        <p v-if="error" class="eco-msg bad">{{ error }}</p>
      </aside>
    </div>
    <section v-if="d && d.reviews.length" style="margin-top: 28px">
      <h3>نظر مهمانان این اتاق</h3>
      <ul class="eco-reviews" style="margin-top: 10px"><li v-for="r in d.reviews" :key="r.id" class="eco-review"><span class="eco-stars-row">{{ '★'.repeat(r.stars) }}</span><p>{{ r.text }}</p><small>{{ r.guest }} · {{ fa(r.day) }}</small>
        <div v-if="r.reply" class="eco-reply">پاسخ میزبان: {{ r.reply }}</div></li></ul>
    </section>
  </div>
</template>
