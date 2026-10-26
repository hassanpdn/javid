<script setup>
// The live site's home after the door: every assistant as a card. A click opens that assistant
// (its setup form, then its own login and panels). A new assistant is one more entry in ASSISTANTS.
import { onMounted } from "vue"
import { leaveGate } from "../lib/gate.js"
import AuroraBg from "../components/AuroraBg.vue"
import Icon from "../components/Icon.vue"

const emit = defineEmits(["open"])
const ASSISTANTS = [
  {
    key: "school", title: "دستیار مدرسه", icon: "school", hue: "violet",
    desc: "کارهای هر روز مدرسه را سبک می‌کند: نامه‌ها، حضور و غیاب، پیگیری دانش‌آموزان و خبر دادن به خانواده‌ها.",
    roles: ["مدیر", "دفتر", "مشاور", "معلم", "خانواده"],
    perks: [{ icon: "sparkles", text: "خلاصه‌ی امروز" }, { icon: "mail", text: "نامه‌ی تازه" }, { icon: "heart", text: "کمک به موقع" }],
  },
  {
    key: "fabric", title: "دستیار پارچه‌فروشی", icon: "layers", hue: "teal",
    desc: "برای عمده‌فروشی که کارش با اکسل و تلفن می‌گذرد: سفارش تلفنی، چک و طلب، انبار و خلاصه‌ی هر روز.",
    roles: ["صاحب کار", "فروشنده", "حسابدار"],
    perks: [{ icon: "message", text: "سفارش تلفنی" }, { icon: "file", text: "سه فایل اکسل" }, { icon: "alert", text: "چک برگشتی" }],
  },
]
onMounted(() => { document.title = "Pudineh Agent Center" })

// the light on the card follows the pointer, and the card leans a little toward it
const move = (e) => {
  const el = e.currentTarget, r = el.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height
  el.style.setProperty("--mx", x * 100 + "%"); el.style.setProperty("--my", y * 100 + "%")
  el.style.setProperty("--rx", (0.5 - y) * 6 + "deg"); el.style.setProperty("--ry", (x - 0.5) * 8 + "deg")
}
const leave = (e) => { e.currentTarget.style.setProperty("--rx", "0deg"); e.currentTarget.style.setProperty("--ry", "0deg") }
</script>

<template>
  <main class="hub">
    <AuroraBg />
    <header class="h-top">
      <div class="h-brand"><span class="h-mark"><Icon name="sparkles" :size="20" /></span><span dir="ltr" lang="en">Pudineh Agent Center</span></div>
      <button class="h-out" @click="leaveGate"><Icon name="logout" :size="17" />خروج</button>
    </header>

    <section class="h-hero">
      <span class="h-eyebrow"><i></i>نسخه‌ی نمایشی</span>
      <h1>انتخاب <span>دستیار</span></h1>
    </section>

    <section class="h-grid">
      <button v-for="(a, i) in ASSISTANTS" :key="a.key" :class="['h-card', 'hue-' + a.hue]" :style="{ '--i': i }"
              @pointermove="move" @pointerleave="leave" @click="emit('open', a.key)">
        <span class="h-glow" aria-hidden="true"></span>
        <span class="h-art" aria-hidden="true">
          <span class="h-rings"><i></i><i></i><i></i></span>
          <span class="h-icon"><Icon :name="a.icon" :size="46" /></span>
          <span v-for="(p, n) in a.perks" :key="p.text" :class="['h-perk', 'p' + n]"><Icon :name="p.icon" :size="14" />{{ p.text }}</span>
        </span>
        <span class="h-body">
          <span class="h-head"><b>{{ a.title }}</b><span class="h-live"><i></i>آماده</span></span>
          <span class="h-desc">{{ a.desc }}</span>
          <span class="h-roles"><span v-for="r in a.roles" :key="r">{{ r }}</span></span>
          <span class="h-go">ورود به دستیار<Icon name="arrowLeft" :size="18" /></span>
        </span>
      </button>
    </section>

    <p class="h-foot"><Icon name="shield" :size="15" />همه‌ی اطلاعات این نسخه ساختگی است.</p>
  </main>
</template>

<style scoped>
.hub { position: relative; min-height: 100vh; min-height: 100dvh; isolation: isolate; color: #eceaff; background: #07061a;
  display: flex; flex-direction: column; align-items: center; gap: 28px;
  padding: max(18px, env(safe-area-inset-top)) 16px max(28px, env(safe-area-inset-bottom)); }

.h-top { width: min(100%, 1120px); display: flex; align-items: center; justify-content: space-between; animation: h-fade .8s ease both; }
.h-brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 15px; }
.h-mark { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; color: #fff;
  background: linear-gradient(135deg, #7367f0, #00bad1); box-shadow: 0 8px 24px -6px rgba(115,103,240,.8); }
.h-out { display: inline-flex; align-items: center; gap: 6px; height: 40px; padding: 0 14px; border-radius: 12px; cursor: pointer;
  font: inherit; font-size: 13.5px; color: #cfcbf3; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); transition: background .2s, color .2s; }
.h-out:hover, .h-out:focus-visible { background: rgba(255,255,255,.12); color: #fff; outline: none; }

.h-hero { text-align: center; max-width: 640px; margin-top: 4vh; animation: h-up .9s cubic-bezier(.2,.9,.25,1) .1s both; }
.h-eyebrow { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; font-size: 12.5px; color: #d9d5ff;
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.14); }
.h-eyebrow i { width: 7px; height: 7px; border-radius: 50%; background: #3ee08f; box-shadow: 0 0 0 0 rgba(62,224,143,.6); animation: h-pulse 2s infinite; }
h1 { margin: 16px 0 10px; font-size: clamp(28px, 4.6vw, 44px); line-height: 1.45; font-weight: 700; color: #fff; }
h1 span { background: linear-gradient(90deg, #a99fff, #5fe3f3 60%, #ff9fc6); -webkit-background-clip: text; background-clip: text; color: transparent; }
.h-hero p { margin: 0; color: #b7b3d9; font-size: 15px; line-height: 2; }

.h-grid { width: min(100%, 1120px); display: grid; gap: 24px; justify-content: center;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 400px)); margin-top: 8px; perspective: 1200px; }

/* one assistant */
.h-card { --mx: 50%; --my: 0%; --rx: 0deg; --ry: 0deg; --c1: #7367f0; --c2: #00bad1;
  position: relative; display: flex; flex-direction: column; overflow: hidden; padding: 0; text-align: right; cursor: pointer;
  font: inherit; color: inherit; border-radius: 28px; border: 1px solid rgba(255,255,255,.14);
  background: linear-gradient(165deg, rgba(255,255,255,.12), rgba(255,255,255,.035));
  backdrop-filter: blur(22px) saturate(140%); -webkit-backdrop-filter: blur(22px) saturate(140%);
  box-shadow: 0 30px 80px -24px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.18);
  transform: rotateX(var(--rx)) rotateY(var(--ry)); transition: transform .25s ease, box-shadow .3s, border-color .3s;
  animation: h-up 1s cubic-bezier(.2,.9,.25,1) calc(.3s + var(--i) * .12s) backwards; }
.hue-teal { --c1: #0f8b7d; --c2: #f3b33d; }
.h-card:hover { border-color: rgba(255,255,255,.28); box-shadow: 0 40px 90px -24px rgba(115,103,240,.55), inset 0 1px 0 rgba(255,255,255,.25); }
.h-card:focus-visible { outline: 3px solid #8fefff; outline-offset: 4px; }
.h-glow { position: absolute; inset: 0; pointer-events: none; opacity: 0; transition: opacity .3s;
  background: radial-gradient(420px circle at var(--mx) var(--my), rgba(255,255,255,.14), transparent 45%); }
.h-card:hover .h-glow { opacity: 1; }

.h-art { position: relative; display: grid; place-items: center; height: 220px; overflow: hidden;
  background: radial-gradient(80% 90% at 50% 100%, color-mix(in srgb, var(--c2) 45%, transparent), transparent 70%),
              linear-gradient(140deg, color-mix(in srgb, var(--c1) 85%, #000), color-mix(in srgb, var(--c1) 40%, #0d0c24)); }
.h-rings { position: absolute; inset: 0; display: grid; place-items: center; }
.h-rings i { position: absolute; border-radius: 50%; border: 1px solid rgba(255,255,255,.18); animation: h-ring 6s ease-out infinite; }
.h-rings i:nth-child(1) { width: 120px; height: 120px; }
.h-rings i:nth-child(2) { width: 120px; height: 120px; animation-delay: 2s; }
.h-rings i:nth-child(3) { width: 120px; height: 120px; animation-delay: 4s; }
.h-icon { position: relative; display: grid; place-items: center; width: 104px; height: 104px; border-radius: 32px; color: #fff;
  background: linear-gradient(145deg, rgba(255,255,255,.3), rgba(255,255,255,.08)); border: 1px solid rgba(255,255,255,.35);
  box-shadow: 0 20px 40px -12px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.5); transition: transform .4s cubic-bezier(.2,.9,.25,1.3); }
.h-card:hover .h-icon { transform: translateY(-6px) scale(1.05) rotate(-4deg); }
.h-perk { position: absolute; display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; font-size: 12px; white-space: nowrap;
  color: #fff; background: rgba(13,12,36,.45); border: 1px solid rgba(255,255,255,.2); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  animation: h-bob 5s ease-in-out infinite alternate; }
.p0 { top: 26px; right: 22px; }
.p1 { top: 92px; left: 18px; animation-delay: 1.4s; }
.p2 { bottom: 24px; right: 40px; animation-delay: .7s; }

.h-body { position: relative; display: flex; flex-direction: column; gap: 12px; padding: 22px 24px 24px; }
.h-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.h-head b { font-size: 21px; color: #fff; }
.h-live { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 12px; color: #7ef0b0;
  background: rgba(62,224,143,.12); border: 1px solid rgba(62,224,143,.3); }
.h-live i { width: 6px; height: 6px; border-radius: 50%; background: #3ee08f; animation: h-pulse 2s infinite; }
.h-desc { color: #c3bfe6; font-size: 14px; line-height: 2; }
.h-roles { display: flex; flex-wrap: wrap; gap: 6px; }
.h-roles span { padding: 3px 11px; border-radius: 999px; font-size: 12px; color: #dcd8ff; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); }
.h-go { display: flex; align-items: center; justify-content: center; gap: 10px; height: 50px; margin-top: 6px; border-radius: 15px;
  font-weight: 700; font-size: 15px; color: #fff; background: linear-gradient(110deg, #6a5cf5, #8f6bff 45%, #1fb8d6); background-size: 180% 100%;
  box-shadow: 0 14px 30px -12px rgba(115,103,240,.9); transition: background-position .5s; }
.h-go .ico { transition: transform .3s; }
.h-card:hover .h-go { background-position: 100% 0; }
.h-card:hover .h-go .ico { transform: translateX(-5px); }

.h-foot { display: flex; align-items: center; gap: 6px; margin: auto 0 0; padding-top: 12px; font-size: 12.5px; color: #8f8bb6; animation: h-fade 1s ease .8s both; }

@media (max-width: 480px) {
  .h-hero { margin-top: 2vh; }
  .h-art { height: 190px; }
  .h-body { padding: 18px 18px 20px; }
}
@media (hover: none) { .h-card { transform: none; } }

@keyframes h-up { from { opacity: 0; transform: translateY(30px); filter: blur(6px); } to { opacity: 1; filter: none; } }
@keyframes h-fade { from { opacity: 0; } }
@keyframes h-pulse { 0% { box-shadow: 0 0 0 0 rgba(62,224,143,.6); } 70% { box-shadow: 0 0 0 8px rgba(62,224,143,0); } 100% { box-shadow: 0 0 0 0 rgba(62,224,143,0); } }
@keyframes h-ring { from { transform: scale(1); opacity: .9; } to { transform: scale(2.6); opacity: 0; } }
@keyframes h-bob { from { translate: 0 0; } to { translate: 0 -8px; } }
@media (prefers-reduced-motion: reduce) {
  .hub *, .hub *::before, .hub *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
  .h-card { transform: none; }
}
</style>
