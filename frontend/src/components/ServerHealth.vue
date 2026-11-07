<script setup>
// «سلامت سرور» on the assistants page, for the permanent account only (GET /access/health, health.py): how the server
// is doing now. On top one line for everything (green, yellow or red) and what the watcher is alerting about; then
// three rings (processor, memory, disk), the services, the backups, the certificates, the waiting updates and the last
// SSH logins, each with its own colour. Every number comes from the server. collapsible: only the header shows until
// it opens; then it fetches, and again every minute while open.
import { ref, watch, onMounted, onUnmounted } from "vue"
import { accessCall } from "../lib/access.js"
import { faDigits } from "../lib/jalali.js"
import Icon from "./Icon.vue"

const props = defineProps({ collapsible: { type: Boolean, default: false } })
const open = ref(false), d = ref(null), error = ref(""), loading = ref(false)
let timer
async function load() {
  loading.value = true
  try { d.value = await accessCall("/access/health"); error.value = "" }
  catch (e) { error.value = "وضعیت سرور خوانده نشد: " + e.message }
  loading.value = false
}
const start = () => { load(); clearInterval(timer); timer = setInterval(load, 60_000) }
onMounted(() => { if (!props.collapsible) start() })
watch(open, (o) => { if (o) start(); else clearInterval(timer) })
onUnmounted(() => clearInterval(timer))

const R = 34, C = 2 * Math.PI * R
const rings = (x) => [
  { key: "load", label: "پردازنده", icon: "chart", v: x.load, sub: x.load && `${faDigits(x.load.cpus)} هسته` },
  { key: "memory", label: "حافظه", icon: "layers", v: x.memory, sub: x.memory && `${faDigits(x.memory.used_gb)} از ${faDigits(x.memory.total_gb)} گیگابایت` },
  { key: "disk", label: "دیسک", icon: "inbox", v: x.disk, sub: x.disk && `${faDigits(x.disk.free_gb)} گیگابایت خالی از ${faDigits(x.disk.total_gb)}` },
]
</script>

<template>
  <section class="sh">
    <button v-if="collapsible" type="button" class="sh-fold" :aria-expanded="open" aria-controls="sh-body" @click="open = !open">
      <span class="sh-badge"><Icon name="shield" :size="18" /></span>
      <span class="sh-fold-text"><b>سلامت سرور</b>
        <small v-if="d" :class="['sh-state', d.overall.tone]"><i></i>{{ faDigits(d.overall.text) }}</small>
        <small v-else>حافظه، دیسک، سرویس‌ها، پشتیبان‌ها و گواهی‌ها</small></span>
      <Icon name="chevron" :size="18" :class="['sh-chev', { open }]" />
    </button>

    <div v-if="!collapsible || open" id="sh-body" class="sh-body">
      <p v-if="error" class="sh-error" role="alert"><Icon name="alert" :size="16" />{{ error }}</p>
      <p v-else-if="!d" class="sh-empty">در حال خواندن وضعیت سرور…</p>
      <template v-else>
        <div :class="['sh-banner', d.overall.tone]">
          <span class="sh-big-dot" aria-hidden="true"></span>
          <div class="sh-banner-text"><b>{{ faDigits(d.overall.text) }}</b>
            <small>{{ d.uptime ? faDigits(d.uptime.text) : "" }} · به‌روز شده ساعت {{ faDigits(d.at) }}</small></div>
          <button type="button" class="sh-refresh" :disabled="loading" aria-label="دوباره خواندن" @click="load"><Icon name="refresh" :size="17" :class="{ spin: loading }" /></button>
        </div>
        <ul v-if="d.problems.length || d.failed.length || d.uptime?.reboot" class="sh-alerts">
          <li v-for="p in d.problems" :key="p.key"><Icon name="alert" :size="16" />{{ p.text }}<small>از {{ faDigits(p.since) }}</small></li>
          <li v-for="f in d.failed" :key="f"><Icon name="alert" :size="16" />سرویس از کار افتاده: <span dir="ltr">{{ f }}</span></li>
          <li v-if="d.uptime?.reboot" class="warn"><Icon name="refresh" :size="16" />{{ d.uptime.note }}</li>
        </ul>

        <div class="sh-rings">
          <div v-for="r in rings(d)" :key="r.key" :class="['sh-ring', r.v?.tone || 'warn']">
            <svg viewBox="0 0 84 84" width="84" height="84" aria-hidden="true">
              <circle cx="42" cy="42" :r="R" class="bg" />
              <circle cx="42" cy="42" :r="R" class="fg" :stroke-dasharray="C" :stroke-dashoffset="C * (1 - (r.v?.pct || 0) / 100)" />
            </svg>
            <div class="sh-ring-num"><b>{{ r.v ? faDigits(r.v.pct) + "٪" : "؟" }}</b></div>
            <div class="sh-ring-text"><span><Icon :name="r.icon" :size="14" />{{ r.label }}</span><small>{{ r.sub || "خوانده نشد" }}</small></div>
          </div>
        </div>

        <div class="sh-grid">
          <div class="sh-card">
            <h3><Icon name="layers" :size="16" />سرویس‌ها</h3>
            <ul class="sh-rows"><li v-for="s in d.services" :key="s.name"><i :class="['sh-dot', s.tone]"></i><span>{{ s.label }}</span><small :class="s.tone">{{ s.text }}</small></li></ul>
          </div>
          <div class="sh-card">
            <h3><Icon name="shield" :size="16" />پشتیبان‌ها</h3>
            <ul class="sh-rows"><li v-for="b in d.backups" :key="b.label"><i :class="['sh-dot', b.tone]"></i><span>{{ b.label }}</span><small :class="b.tone">{{ faDigits(b.text) }}</small></li></ul>
          </div>
          <div class="sh-card">
            <h3><Icon name="lock" :size="16" />گواهی‌های HTTPS</h3>
            <ul class="sh-rows"><li v-for="c in d.certificates" :key="c.host"><i :class="['sh-dot', c.tone]"></i><span dir="ltr" class="sh-host">{{ c.host }}</span><small :class="c.tone">{{ faDigits(c.text) }}</small></li></ul>
          </div>
          <div class="sh-card">
            <h3><Icon name="refresh" :size="16" />به‌روزرسانی‌ها</h3>
            <p v-if="!d.updates" class="sh-muted">روی این سرور خوانده نشد.</p>
            <div v-else class="sh-updates">
              <div :class="['sh-count', d.updates.security ? (d.updates.tone === 'bad' ? 'bad' : 'warn') : 'ok']"><b>{{ faDigits(d.updates.security) }}</b><small>امنیتی</small></div>
              <div class="sh-count"><b>{{ faDigits(d.updates.all) }}</b><small>همه</small></div>
              <p class="sh-muted">{{ d.updates.security ? "به‌روزرسانی‌های امنیتی را در یک ساعت خلوت نصب کنید." : d.updates.all ? "مورد امنیتی‌ای در انتظار نیست." : "همه‌چیز به‌روز است." }}</p>
            </div>
          </div>
          <div class="sh-card sh-wide">
            <h3><Icon name="key" :size="16" />آخرین ورودها به سرور (SSH)</h3>
            <p v-if="!d.logins.length" class="sh-muted">ورودی خوانده نشد.</p>
            <ul v-else class="sh-rows"><li v-for="(l, i) in d.logins" :key="i"><i :class="['sh-dot', l.now ? 'ok' : 'none']"></i>
              <span dir="ltr" class="sh-host">{{ l.user }} · {{ l.ip }}</span><small>{{ l.now ? "اکنون وارد است" : faDigits(l.at) }}</small></li></ul>
            <p class="sh-muted">اگر نشانی یا نامی را نمی‌شناسید، همین حالا رمز سرور را عوض کنید.</p>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.sh { width: min(100%, 1120px); margin-top: 18px; padding: 24px; border-radius: 28px;
  background: linear-gradient(165deg, rgba(255,255,255,.09), rgba(255,255,255,.025)); border: 1px solid rgba(255,255,255,.12);
  backdrop-filter: blur(22px) saturate(140%); -webkit-backdrop-filter: blur(22px) saturate(140%); box-shadow: 0 30px 80px -30px rgba(0,0,0,.7); }
.sh-fold { display: flex; align-items: center; gap: 12px; width: 100%; padding: 0; border: 0; background: none; font: inherit; color: inherit; text-align: right; cursor: pointer; }
.sh-fold:focus-visible { outline: 3px solid #8fefff; outline-offset: 4px; border-radius: 14px; }
.sh-badge { flex: none; display: grid; place-items: center; width: 42px; height: 42px; border-radius: 14px; color: #fff;
  background: linear-gradient(135deg, #3ee08f, #1fb8d6); box-shadow: 0 10px 26px -8px rgba(62,224,143,.55); }
.sh-fold-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.sh-fold-text b { font-size: 16px; color: #fff; }
.sh-fold-text small { font-size: 12.5px; color: #b7b3d9; line-height: 1.7; }
.sh-chev { flex: none; color: #b7b3d9; transform: rotate(-90deg); transition: transform .25s; }
.sh-chev.open { transform: rotate(90deg); }
.sh-state { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; }
.sh-state i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.sh-fold-text .sh-state.ok { color: #7ef0b0; } .sh-fold-text .sh-state.warn { color: #ffc98a; } .sh-fold-text .sh-state.bad { color: #ffa3b0; }
.sh-body { margin-top: 16px; display: flex; flex-direction: column; gap: 14px; }

.sh-banner { display: flex; align-items: center; gap: 14px; padding: 16px 18px; border-radius: 20px; border: 1px solid; }
.sh-banner.ok { background: rgba(62,224,143,.1); border-color: rgba(62,224,143,.3); --c: #3ee08f; }
.sh-banner.warn { background: rgba(255,176,87,.1); border-color: rgba(255,176,87,.32); --c: #ffb057; }
.sh-banner.bad { background: rgba(255,111,140,.1); border-color: rgba(255,111,140,.35); --c: #ff6f8c; }
.sh-big-dot { position: relative; flex: none; width: 16px; height: 16px; border-radius: 50%; background: var(--c); box-shadow: 0 0 18px var(--c); }
.sh-big-dot::after { content: ""; position: absolute; inset: -6px; border-radius: 50%; border: 2px solid var(--c); opacity: .6; animation: sh-ping 2.2s ease-out infinite; }
@keyframes sh-ping { 0% { transform: scale(.7); opacity: .7; } 80%, 100% { transform: scale(1.5); opacity: 0; } }
.sh-banner-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.sh-banner-text b { font-size: 17px; color: #fff; }
.sh-banner-text small { font-size: 12.5px; color: #c9c5ee; }
.sh-refresh { flex: none; display: grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.07); color: #dcd8ff; cursor: pointer; }
.sh-refresh:hover, .sh-refresh:focus-visible { color: #fff; background: rgba(255,255,255,.14); outline: none; }
.sh-refresh .spin :deep(svg) { animation: sh-rot .9s linear infinite; }
@keyframes sh-rot { to { transform: rotate(360deg); } }
.sh-alerts { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
.sh-alerts li { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 10px 14px; border-radius: 14px; font-size: 13.5px; color: #ffd0d8;
  background: rgba(255,111,140,.1); border: 1px solid rgba(255,111,140,.25); }
.sh-alerts li.warn { color: #ffe0b8; background: rgba(255,176,87,.1); border-color: rgba(255,176,87,.28); }
.sh-alerts small { color: #c9c5ee; font-size: 12px; margin-inline-start: auto; }

.sh-rings { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.sh-ring { position: relative; display: flex; align-items: center; gap: 14px; padding: 14px; border-radius: 20px; background: rgba(10,9,32,.45); border: 1px solid rgba(255,255,255,.08);
  --c: #3ee08f; }
.sh-ring.warn { --c: #ffb057; } .sh-ring.bad { --c: #ff6f8c; }
.sh-ring svg { flex: none; transform: rotate(-90deg); }
.sh-ring circle { fill: none; stroke-width: 8; }
.sh-ring .bg { stroke: rgba(255,255,255,.1); }
.sh-ring .fg { stroke: var(--c); stroke-linecap: round; transition: stroke-dashoffset 1s cubic-bezier(.3,.7,.2,1); filter: drop-shadow(0 0 6px color-mix(in srgb, var(--c) 60%, transparent)); }
.sh-ring-num { position: absolute; width: 84px; height: 84px; display: grid; place-items: center; inset-inline-start: 14px; }
.sh-ring-num b { font-size: 18px; color: #fff; }
.sh-ring-text { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.sh-ring-text span { display: inline-flex; align-items: center; gap: 6px; font-size: 14.5px; font-weight: 700; color: #fff; }
.sh-ring-text small { font-size: 12px; color: #b7b3d9; line-height: 1.7; }

.sh-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.sh-card { padding: 14px 16px; border-radius: 20px; background: rgba(10,9,32,.45); border: 1px solid rgba(255,255,255,.08); min-width: 0; }
.sh-wide { grid-column: 1 / -1; }
.sh-card h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 8px; font-size: 14.5px; color: #fff; }
.sh-rows { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; }
.sh-rows li { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.06); font-size: 13.5px; color: #dcd8ff; }
.sh-rows li:last-child { border-bottom: 0; }
.sh-rows li > span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.sh-rows small { flex: none; font-size: 12.5px; color: #b7b3d9; }
.sh-rows small.ok { color: #7ef0b0; } .sh-rows small.warn { color: #ffc98a; } .sh-rows small.bad { color: #ffa3b0; }
.sh-host { font-size: 13px; text-align: right; }
.sh-dot { flex: none; width: 9px; height: 9px; border-radius: 50%; background: #6f6b8f; }
.sh-dot.ok { background: #3ee08f; box-shadow: 0 0 8px rgba(62,224,143,.7); }
.sh-dot.warn { background: #ffb057; } .sh-dot.bad { background: #ff6f8c; box-shadow: 0 0 8px rgba(255,111,140,.7); }
.sh-updates { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.sh-count { display: flex; flex-direction: column; align-items: center; min-width: 74px; padding: 8px 10px; border-radius: 14px; background: rgba(255,255,255,.06); }
.sh-count b { font-size: 22px; color: #fff; line-height: 1.3; }
.sh-count small { font-size: 11.5px; color: #b7b3d9; }
.sh-count.warn { background: rgba(255,176,87,.14); } .sh-count.warn b { color: #ffc98a; }
.sh-count.bad { background: rgba(255,111,140,.14); } .sh-count.bad b { color: #ffa3b0; }
.sh-count.ok b { color: #7ef0b0; }
.sh-muted { margin: 6px 0 0; flex-basis: 100%; font-size: 12.5px; line-height: 1.9; color: #b7b3d9; }
.sh-error { display: flex; align-items: center; gap: 8px; margin: 0; padding: 10px 14px; border-radius: 14px; font-size: 13.5px;
  color: #ffb4b6; background: rgba(255,92,97,.12); border: 1px solid rgba(255,92,97,.3); }
.sh-empty { margin: 0; padding: 22px 16px; text-align: center; border-radius: 16px; font-size: 13.5px; color: #b7b3d9; border: 1px dashed rgba(255,255,255,.18); }
@media (max-width: 860px) { .sh-rings { grid-template-columns: 1fr; } .sh-grid { grid-template-columns: 1fr; } }
@media (max-width: 480px) {
  .sh { padding: 18px 14px; border-radius: 24px; }
}
@media (prefers-reduced-motion: reduce) { .sh-big-dot::after { animation: none; } }
/* phones and touch screens: no frosted glass (iPhone Safari draws such panels wrong; see HubPage) */
@media (hover: none), (max-width: 767px) { .sh { backdrop-filter: none; -webkit-backdrop-filter: none; isolation: isolate; background: linear-gradient(165deg, rgba(40,38,82,.92), rgba(18,17,42,.94)); } }
</style>
