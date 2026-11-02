<script setup>
// «سرعت برای بازدیدکنندگان» on the assistants page, for the permanent account only (GET /speed, speed.py): how fast each
// screen behind the door really was for the people who opened it, measured in their own browsers (lib/rum.js).
// Per screen the median, the slowest tenth, and visits that had a failed request; then the latest visits. Every
// number comes from the server. collapsible (phones): only the header shows, and nothing is fetched until it opens.
import { ref, watch, onMounted } from "vue"
import { accessCall } from "../lib/access.js"
import { faDigits } from "../lib/jalali.js"
import Icon from "./Icon.vue"

const props = defineProps({ collapsible: { type: Boolean, default: false } })
const open = ref(false), d = ref(null), days = ref(7), device = ref(""), error = ref(""), loading = ref(true)
async function load() {
  loading.value = true
  try { d.value = await accessCall(`/speed?days=${days.value}&device=${device.value}`); error.value = "" }
  catch (e) { error.value = "گزارش سرعت بارگیری نشد: " + e.message }
  loading.value = false
}
onMounted(() => { if (!props.collapsible) load() })
watch(open, (o) => { if (o && !d.value) load() })
watch([days, device], load)

// 2350 → «۲٫۴ ثانیه», 640 → «۰٫۶ ثانیه»
const sec = (ms) => faDigits((ms / 1000).toFixed(1).replace(".", "٫")) + " ثانیه"
const tone = (ms) => ms <= 3000 ? "good" : ms <= 8000 ? "mid" : "bad"
const DEVICE = { phone: "گوشی", desktop: "رایانه" }
</script>

<template>
  <section class="sp">
    <button v-if="collapsible" type="button" class="sp-fold" :aria-expanded="open" aria-controls="sp-body" @click="open = !open">
      <span class="sp-badge"><Icon name="clock" :size="18" /></span>
      <span class="sp-fold-text"><b>سرعت برای بازدیدکنندگان</b><small>چند ثانیه تا آماده شدن هر صفحه</small></span>
      <Icon name="chevron" :size="18" :class="['sp-chev', { open }]" />
    </button>
    <div v-if="!collapsible || open" id="sp-body">
      <header :class="['sp-head', { 'sp-head-in': collapsible }]">
        <div v-if="!collapsible" class="sp-title">
          <span class="sp-badge"><Icon name="clock" :size="20" /></span>
          <div><h2>سرعت برای بازدیدکنندگان</h2><p>هر بار که کسی صفحه‌ای را باز می‌کند، مرورگر خودش می‌سنجد چند ثانیه طول کشید تا صفحه آماده شد.</p></div>
        </div>
        <div class="sp-filters">
          <select v-model="days" aria-label="بازه"><option :value="1">امروز</option><option :value="7">هفت روز</option><option :value="30">سی روز</option><option :value="90">نود روز</option></select>
          <select v-model="device" aria-label="دستگاه"><option value="">همه</option><option value="phone">گوشی</option><option value="desktop">رایانه</option></select>
        </div>
      </header>

      <p v-if="error" class="sp-error" role="alert"><Icon name="alert" :size="16" />{{ error }}</p>
      <p v-else-if="loading && !d" class="sp-empty">در حال بارگیری…</p>
      <p v-else-if="d && !d.count" class="sp-empty">در این بازه هنوز کسی صفحه‌ای باز نکرده است.</p>
      <template v-else-if="d">
        <p class="sp-note">{{ faDigits(d.count) }} بار باز شدن صفحه. «میانه»: نیمی از بازدیدها زودتر از این آماده شد. «کندترین‌ها»: نه بازدید از هر ده زودتر از این آماده شد.</p>
        <ul class="sp-list">
          <li v-for="s in d.screens" :key="s.screen" class="sp-row">
            <div class="sp-row-top"><b>{{ s.label }}</b><span class="sp-count">{{ faDigits(s.count) }} بار</span></div>
            <div class="sp-nums">
              <span :class="['sp-num', tone(s.median)]"><small>میانه</small>{{ sec(s.median) }}</span>
              <span :class="['sp-num', tone(s.p90)]"><small>کندترین‌ها</small>{{ sec(s.p90) }}</span>
              <span class="sp-num"><small>بدترین</small>{{ sec(s.worst) }}</span>
            </div>
            <small class="sp-meta"><template v-if="s.kb !== null">حجم دریافتی {{ faDigits(s.kb) }} کیلوبایت · </template>
              <span :class="{ 'sp-bad': s.failed }">{{ s.failed ? faDigits(s.failed) + ' بار درخواستی بی‌پاسخ ماند' : 'بدون درخواست بی‌پاسخ' }}</span></small>
          </li>
        </ul>
        <h3 class="sp-sub">آخرین بازدیدها</h3>
        <ul class="sp-latest">
          <li v-for="r in d.latest" :key="r.id">
            <span :class="['sp-dot', tone(r.ms)]" aria-hidden="true"></span>
            <span class="sp-latest-body"><b>{{ r.label }} · {{ sec(r.ms) }}</b>
              <small>{{ faDigits(r.at.replace(' ', '، ساعت ')) }} · {{ DEVICE[r.device] }}<template v-if="r.net"> · <span dir="ltr">{{ r.net }}</span></template> · {{ r.kind }}<template v-if="r.who"> · {{ r.who }}</template><template v-if="r.failed"> · <span class="sp-bad">{{ faDigits(r.failed) }} درخواست بی‌پاسخ</span></template></small></span>
          </li>
        </ul>
      </template>
    </div>
  </section>
</template>

<style scoped>
.sp { width: min(100%, 1120px); margin-top: 18px; padding: 24px; border-radius: 28px;
  background: linear-gradient(165deg, rgba(255,255,255,.09), rgba(255,255,255,.025)); border: 1px solid rgba(255,255,255,.12);
  backdrop-filter: blur(22px) saturate(140%); -webkit-backdrop-filter: blur(22px) saturate(140%); box-shadow: 0 30px 80px -30px rgba(0,0,0,.7); }
.sp-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin-bottom: 14px; }
.sp-head-in { margin-top: 14px; }
.sp-title { display: flex; align-items: center; gap: 14px; min-width: 0; flex: 1 1 360px; }
.sp-badge { flex: none; display: grid; place-items: center; width: 48px; height: 48px; border-radius: 16px; color: #fff;
  background: linear-gradient(135deg, #28c76f, #00bad1); box-shadow: 0 10px 26px -8px rgba(40,199,111,.6); }
.sp-title h2 { margin: 0; font-size: 20px; color: #fff; }
.sp-title p { margin: 2px 0 0; font-size: 13.5px; line-height: 1.8; color: #b7b3d9; }
.sp-filters { display: flex; gap: 8px; flex-wrap: wrap; }
.sp-filters select { height: 40px; min-width: 130px; padding-inline-start: 12px; border-radius: 12px; font: inherit; font-size: 14px; color: #fff;
  background-color: rgba(10,9,32,.55); border: 1px solid rgba(255,255,255,.16); }
.sp-filters select option { color: #111; background: #fff; }
.sp-filters select:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }
.sp-note { margin: 0 0 12px; font-size: 13px; line-height: 1.9; color: #b7b3d9; }
.sp-list { margin: 0; padding: 0; list-style: none; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); }
.sp-row { display: flex; flex-direction: column; gap: 8px; padding: 14px; border-radius: 16px; background: rgba(10,9,32,.45); border: 1px solid rgba(255,255,255,.08); }
.sp-row-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.sp-row-top b { min-width: 0; color: #fff; font-size: 14.5px; overflow-wrap: anywhere; }
.sp-count { flex: none; font-size: 12px; color: #b7b3d9; }
.sp-nums { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
.sp-num { display: flex; flex-direction: column; gap: 1px; padding: 6px 8px; border-radius: 10px; font-size: 13.5px; font-weight: 700; color: #fff; background: rgba(255,255,255,.06); }
.sp-num small { font-size: 11px; font-weight: 400; color: #b7b3d9; }
.sp-num.good { background: rgba(62,224,143,.14); color: #7ef0b0; }
.sp-num.mid { background: rgba(255,176,87,.16); color: #ffc98a; }
.sp-num.bad { background: rgba(255,111,140,.16); color: #ffa3b0; }
.sp-meta { font-size: 12px; color: #b7b3d9; line-height: 1.8; }
.sp-bad { color: #ffa3b0; }
.sp-sub { margin: 18px 0 8px; font-size: 15px; color: #fff; }
.sp-latest { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
.sp-latest li { display: flex; align-items: flex-start; gap: 10px; padding: 8px 10px; border-radius: 12px; background: rgba(10,9,32,.35); }
.sp-dot { flex: none; width: 9px; height: 9px; margin-top: 8px; border-radius: 50%; background: #b7b3d9; }
.sp-dot.good { background: #3ee08f; } .sp-dot.mid { background: #ffb057; } .sp-dot.bad { background: #ff6f8c; }
.sp-latest-body { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.sp-latest-body b { color: #fff; font-size: 13.5px; }
.sp-latest-body small { color: #b7b3d9; font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }
.sp-error { display: flex; align-items: center; gap: 8px; margin: 0; padding: 10px 14px; border-radius: 14px; font-size: 13.5px;
  color: #ffb4b6; background: rgba(255,92,97,.12); border: 1px solid rgba(255,92,97,.3); }
.sp-empty { margin: 0; padding: 22px 16px; text-align: center; border-radius: 16px; font-size: 13.5px; color: #b7b3d9; border: 1px dashed rgba(255,255,255,.18); }
.sp-fold { display: flex; align-items: center; gap: 12px; width: 100%; padding: 0; border: 0; background: none; font: inherit; color: inherit; text-align: right; cursor: pointer; }
.sp-fold:focus-visible { outline: 3px solid #8fefff; outline-offset: 4px; border-radius: 14px; }
.sp-fold .sp-badge { width: 42px; height: 42px; border-radius: 14px; }
.sp-fold-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.sp-fold-text b { font-size: 16px; color: #fff; }
.sp-fold-text small { font-size: 12.5px; color: #b7b3d9; line-height: 1.7; }
.sp-chev { flex: none; color: #b7b3d9; transform: rotate(-90deg); transition: transform .25s; }
.sp-chev.open { transform: rotate(90deg); }
@media (max-width: 480px) {
  .sp { padding: 18px 14px; border-radius: 24px; }
  .sp-filters, .sp-filters select { width: 100%; }
  .sp-filters select { flex: 1; min-width: 0; }
}
/* phones and touch screens: no frosted glass (iPhone Safari draws such panels wrong; see HubPage) */
@media (hover: none), (max-width: 767px) { .sp { backdrop-filter: none; -webkit-backdrop-filter: none; isolation: isolate; background: linear-gradient(165deg, rgba(40,38,82,.92), rgba(18,17,42,.94)); } }
</style>
