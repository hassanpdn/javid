<script setup>
// The lodge's first page: the drawn village under a night sky with the lodge's words, a search for dates and people,
// the units (or, after a search, the ones free for every night, cheapest first, with the stay's price), the
// lodge's story, what guests said (only the reviews the host chose to show) and the house rules.
import { ref, reactive } from "vue"
import { call, fa, go } from "./api.js"
import Art from "./Art.vue"
import DatePicker from "../components/core/DatePicker.vue"

const props = defineProps({ site: Object })
const f = reactive({ arrive: null, depart: null, people: 2 }), found = ref(null), busy = ref(false), error = ref("")
async function search() {
  if (!f.arrive || !f.depart) { error.value = "تاریخ ورود و خروج را انتخاب کنید"; return }
  busy.value = true; error.value = ""
  try { found.value = await call("/search", { ...f }); setTimeout(() => document.getElementById("units")?.scrollIntoView({ behavior: "smooth" }), 50) }
  catch (e) { error.value = e.message; found.value = null } finally { busy.value = false }
}
const open = (u) => go(`/unit/${u.id}` + (found.value && f.arrive ? `?a=${f.arrive}&d=${f.depart}&p=${f.people}` : ""))
const stars = (n) => "★".repeat(n) + "☆".repeat(5 - n)
</script>

<template>
  <section class="eco-hero">
    <Art kind="hero" />
    <div class="eco-hero-text">
      <h1>{{ site.name }}</h1>
      <p>{{ site.words.tagline }}</p>
      <small v-if="site.rating.avg">★ {{ fa(site.rating.avg) }} از ۵ · {{ fa(site.rating.count) }} نظر مهمانان · {{ site.place }}</small>
    </div>
  </section>
  <form class="eco-search" @submit.prevent="search" aria-label="جستجوی شب‌های خالی">
    <div class="eco-field"><span>ورود</span><DatePicker v-model="f.arrive" label="تاریخ ورود" /></div>
    <div class="eco-field"><span>خروج</span><DatePicker v-model="f.depart" :min="f.arrive" label="تاریخ خروج" /></div>
    <label class="eco-field"><span>چند نفر</span><select v-model.number="f.people"><option v-for="n in 8" :key="n" :value="n">{{ fa(n) }} نفر</option></select></label>
    <button class="eco-btn main" :disabled="busy">{{ busy ? 'در حال جستجو…' : 'جای خالی' }}</button>
    <p v-if="error" class="eco-msg bad" style="grid-column: 1 / -1; margin: 0">{{ error }}</p>
  </form>

  <section id="units" class="eco-section">
    <div class="eco-wrap">
      <h2>{{ found ? `برای ${fa(found.stay)}` : 'اتاق‌ها و خانه‌ها' }}</h2>
      <p class="eco-sub">{{ found ? (found.units.length ? `${fa(found.units.length)} جای خالی برای ${fa(f.people)} نفر، ارزان‌ترین اول` : 'برای این شب‌ها جای خالی نداریم؛ تاریخ دیگری را امتحان کنید.') : 'هر کدام خشت و نور و حال خودش را دارد.' }}</p>
      <ul class="eco-units">
        <li v-for="u in (found ? found.units : site.units)" :key="u.id">
          <button class="eco-card" @click="open(u)">
            <div class="eco-pic"><img v-if="u.photos.length" :src="u.photos[0]" :alt="u.name" loading="lazy"><Art v-else :kind="u.art" />
              <span v-if="u.rating.avg" class="eco-tag">★ {{ fa(u.rating.avg) }}</span></div>
            <div class="eco-card-body">
              <h3>{{ u.name }}</h3>
              <span class="eco-meta">{{ u.kind_text }} · تا {{ fa(u.capacity) }} نفر</span>
              <span class="eco-meta">{{ u.description }}</span>
              <div class="eco-price"><span class="eco-meta">{{ found ? 'جمع اقامت' : 'هر شب از' }}</span><b>{{ fa(found ? u.quote.total_text : u.price_text) }}</b></div>
            </div>
          </button>
        </li>
      </ul>
    </div>
  </section>

  <section class="eco-section">
    <div class="eco-wrap eco-story">
      <div><h2>داستان این خانه</h2><p>{{ site.words.story }}</p><p class="eco-meta">میزبان شما: {{ site.host }}</p></div>
      <div class="eco-pic"><Art kind="yard" /></div>
    </div>
  </section>

  <section v-if="site.reviews.length" class="eco-section">
    <div class="eco-wrap">
      <h2>مهمانان می‌گویند</h2>
      <p class="eco-sub">نظر کسانی که این‌جا مانده‌اند؛ هر نظر پس از پایان سفر نوشته شده است.</p>
      <ul class="eco-reviews">
        <li v-for="r in site.reviews" :key="r.id" class="eco-review">
          <span class="eco-stars-row" :aria-label="fa(r.stars) + ' ستاره'">{{ stars(r.stars) }}</span>
          <p>{{ r.text }}</p>
          <small>{{ r.guest }} · {{ r.unit }} · {{ fa(r.day) }}</small>
          <div v-if="r.reply" class="eco-reply">پاسخ میزبان: {{ r.reply }}</div>
        </li>
      </ul>
    </div>
  </section>

  <section class="eco-section">
    <div class="eco-wrap"><div class="eco-rules"><h3>قاعده‌های خانه</h3><p style="margin: 6px 0 0">{{ fa(site.words.rules) }}</p>
      <p class="eco-meta" style="margin: 6px 0 0">بیعانه: {{ fa(site.rules.deposit) }} درصد، پس از تأیید میزبان. لغو بیش از ۷ روز پیش از ورود: ۹۰ درصد بیعانه برمی‌گردد؛ ۳ تا ۷ روز: ۵۰ درصد.</p></div></div>
  </section>
</template>
