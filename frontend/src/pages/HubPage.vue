<script setup>
// The live site's home after the door: every assistant as a card. A click opens that assistant
// (its setup form, then its own login and panels). A new assistant is one more entry in ASSISTANTS.
import { ref, computed, watch, onMounted, defineAsyncComponent } from "vue"
import { leaveGate } from "../lib/gate.js"
import { access, canOpen, forgetAccess, jalaliText, setAi } from "../lib/access.js"
import { phone } from "../lib/viewport.js"
import { ready } from "../lib/rum.js"
import AuroraBg from "../components/AuroraBg.vue"
import Icon from "../components/Icon.vue"
import BrandMark from "../components/core/BrandMark.vue"
// shown only when opened, so their code is downloaded only then
const AccessManager = defineAsyncComponent(() => import("../components/AccessManager.vue"))
const AccessDialog = defineAsyncComponent(() => import("../components/AccessDialog.vue"))
const LoginLog = defineAsyncComponent(() => import("../components/LoginLog.vue"))
const SpeedPanel = defineAsyncComponent(() => import("../components/SpeedPanel.vue"))
const ServerHealth = defineAsyncComponent(() => import("../components/ServerHealth.vue"))
const DataMap = defineAsyncComponent(() => import("../components/DataMap.vue"))

const emit = defineEmits(["open"])
const ASSISTANTS = [
  {
    key: "school", title: "دستیار مدرسه", icon: "school", hue: "violet",
    desc: "کارهای هر روز مدرسه را سبک می‌کند: نامه‌ها، حضور و غیاب، پیگیری دانش‌آموزان و خبر دادن به خانواده‌ها.",
    roles: ["مدیر", "دفتر", "مشاور", "معلم", "خانواده"],
    perks: [{ icon: "sparkles", text: "خلاصه‌ی امروز" }, { icon: "mail", text: "نامه‌ی جدید" }, { icon: "heart", text: "کمک به موقع" }],
    en: { title: "School Assistant", desc: "Takes the daily load off a school: letters, attendance, following up on pupils and keeping families informed.", roles: ["Principal", "Office", "Counselor", "Teacher", "Family"], perks: ["Today’s summary", "New letters", "Help in time"] },
  },
  {
    key: "fabric", title: "دستیار پارچه‌فروشی", icon: "layers", hue: "teal",
    desc: "برای عمده‌فروشی که کارش با اکسل و تلفن می‌گذرد: سفارش تلفنی، چک و طلب، انبار و خلاصه‌ی هر روز.",
    roles: ["صاحب کار", "فروشنده", "حسابدار", "انباردار"],
    perks: [{ icon: "message", text: "سفارش تلفنی" }, { icon: "file", text: "سه فایل اکسل" }, { icon: "alert", text: "چک برگشتی" }],
    en: { title: "Fabric Wholesale Assistant", desc: "For a wholesaler who runs on Excel and the phone: phone orders, cheques and receivables, stock and a summary of every day.", roles: ["Owner", "Seller", "Accountant", "Warehouse keeper"], perks: ["Phone orders", "Three Excel files", "Bounced cheques"] },
  },
  {
    key: "estate", title: "دستیار بنگاه املاک", icon: "mapPin", hue: "rose",
    desc: "برای بنگاهی که فایل‌هایش در دفتر و گروه‌های پیام‌رسان پخش است: ثبت فایل از هر متنی، پیدا کردن متقاضی مناسب، بازدید و گزارش به مالک.",
    roles: ["مدیر بنگاه", "مشاور املاک", "سایت بنگاه"],
    perks: [{ icon: "users", text: "متقاضی مناسب" }, { icon: "chart", text: "قیمت منطقه" }, { icon: "shield", text: "بررسی‌ها" }],
    en: { title: "Real Estate Agency Assistant", desc: "For an agency whose listings are scattered across notebooks and chat groups: a listing from any text, the right buyer, visits and reports to owners.", roles: ["Agency manager", "Agent", "Agency website"], perks: ["Matching buyers", "Area prices", "Checks"] },
  },
  {
    key: "law", title: "دستیار دفتر وکالت", icon: "book", hue: "indigo",
    desc: "برای وکیلی که ابلاغیه‌ها و مهلت‌هایش در دفترچه و ذهنش است: خواندن ابلاغیه، حساب روز آخر هر مهلت با تعطیلات، کارهای امروز و گزارش به موکل.",
    roles: ["وکیل", "همکار وکیل", "منشی"],
    perks: [{ icon: "clock", text: "روز آخر مهلت" }, { icon: "calendar", text: "جلسه‌ی فردا" }, { icon: "message", text: "گزارش به موکل" }],
    en: { title: "Law Office Assistant", desc: "For a lawyer whose notices and deadlines live in a notebook: reading court notices, the last day of every deadline with holidays, today’s work and client reports.", roles: ["Lawyer", "Associate", "Secretary"], perks: ["Last day of a deadline", "Tomorrow’s hearing", "Client reports"] },
  },
  {
    key: "dental", title: "دستیار مطب دندان‌پزشکی", icon: "tooth", hue: "sky",
    desc: "برای مطبی که نوبت‌ها و طرح‌های درمانش در دفتر منشی است: تأیید نوبت فردا، پر کردن وقت خالی از فهرست انتظار و پیگیری طرح درمانی که شروع نشده است.",
    roles: ["دندان‌پزشک", "منشی"],
    perks: [{ icon: "calendar", text: "نوبت فردا" }, { icon: "heart", text: "طرح شروع‌نشده" }, { icon: "users", text: "فهرست انتظار" }],
    en: { title: "Dental Clinic Assistant", desc: "For a clinic whose appointments and treatment plans sit in the secretary’s book: confirming tomorrow, filling empty hours from the waiting list, following up plans never started.", roles: ["Dentist", "Secretary"], perks: ["Tomorrow’s appointments", "Plans not started", "Waiting list"] },
  },
  {
    key: "lang", title: "دستیار آموزشگاه زبان", icon: "globe", hue: "cobalt",
    desc: "برای آموزشگاهی که جدول کلاس‌ها، ثبت‌نام و نمره‌هایش در دفتر و اکسل است: جدول کلاس‌ها با تداخل‌یاب، آزمون آنلاین و تعیین سطح، و مسیر هر زبان‌آموز از ترم امروز تا آخرین کتاب.",
    roles: ["مدیر", "منشی", "استاد", "زبان‌آموز"],
    perks: [{ icon: "route", text: "مسیر زبان‌آموز" }, { icon: "calendar", text: "جدول بی‌تداخل" }, { icon: "check", text: "آزمون آنلاین" }],
    en: { title: "Language Institute Assistant", desc: "For an institute whose timetable, registrations and marks live on paper and in Excel: a clash-free timetable, online and placement tests, and each learner’s road from today’s term to the last book.", roles: ["Manager", "Secretary", "Teacher", "Learner"], perks: ["Learner’s road", "Clash-free timetable", "Online tests"] },
  },
  {
    key: "hotel", title: "دستیار هتل", icon: "bed", hue: "ocean",
    desc: "رزرو تا تسویه در یک پنل: قیمت هر شب با فصل و آخر هفته، جدول اتاق‌ها، ورود و خروج، خانه‌داری، آژانس‌ها و سایت هتل؛ و در روزهای شلوغ، فهرستی که می‌گوید اول چه کاری.",
    roles: ["مدیر هتل", "رزرو", "پذیرش", "خانه‌داری", "سایت هتل"],
    perks: [{ icon: "calendar", text: "جدول اتاق‌ها" }, { icon: "users", text: "حالت شلوغی" }, { icon: "shield", text: "بررسی‌ها" }],
    en: { title: "Hotel Assistant", desc: "Reservation to check-out in one panel: nightly prices by season and weekend, the room chart, arrivals and departures, housekeeping, agencies and the hotel’s website; and on busy days, a list of what to do first.", roles: ["Manager", "Reservations", "Front desk", "Housekeeping", "Hotel website"], perks: ["Room chart", "Busy-day mode", "Checks"] },
  },
  {
    key: "lodge", title: "دستیار اقامتگاه بوم‌گردی", icon: "heart", hue: "clay",
    desc: "برای اقامتگاه ۵ تا ۲۰ واحدی، با سایت عمومی خودش: مهمان شب‌های خالی را می‌بیند، حساب می‌سازد، درخواست رزرو و رسید می‌فرستد و پس از سفر نظر می‌دهد؛ میزبان همه را از پنل می‌گرداند.",
    roles: ["میزبان", "همکار", "سایت عمومی و پنل مهمان"],
    perks: [{ icon: "sparkles", text: "سایت عمومی" }, { icon: "check", text: "تأیید رسید" }, { icon: "heart", text: "نظر مهمانان" }],
    en: { title: "Eco-lodge Assistant", desc: "For a lodge of 5 to 20 units with its own public website: guests see free nights, make an account, send a booking request and a receipt, and review after their stay; the host runs it all from one panel.", roles: ["Host", "Helper", "Public website and guest panel"], perks: ["Public website", "Receipt approval", "Guest reviews"] },
  },
  {
    key: "deed", title: "دستیار استخراج داده‌ی سند", icon: "notebook", hue: "amber",
    desc: "سند دفترچه‌ای اسکن‌شده را می‌خواند و داده‌هایش را برای بررسی و تأیید کارشناس، پیش از تبدیل به سند تک‌برگ، آماده می‌کند.",
    roles: ["کارشناس بررسی"],
    perks: [{ icon: "file", text: "تصویر یا PDF" }, { icon: "check", text: "تأیید کارشناس" }, { icon: "shield", text: "پردازش روی سرور" }],
    en: { title: "Deed Data Extraction Assistant", desc: "Reads a scanned booklet deed and prepares its data for an expert to review and confirm before it becomes a single-page deed.", roles: ["Reviewer"], perks: ["Image or PDF", "Expert approval", "Processed on the server"] },
  },
]
onMounted(() => { document.title = "Pudineh Agent Center"; ready() })

// On the live demo (access.js) the permanent account sees every card and «دسترسی‌ها» below them; anyone else sees only
// the cards they were given. Someone who passed the door without an account of their own sees a login box instead.
const visible = computed(() => ASSISTANTS.filter((a) => canOpen(a.key)))
const asking = ref(null), notice = ref("")
const opened = (key) => { asking.value = null; if (key) emit("open", key) }
// an assistant sent us back here: this person may no longer open it
watch(() => access.ask, (key) => {
  if (!key) return
  const a = ASSISTANTS.find((x) => x.key === key)
  notice.value = a ? `دسترسی شما به «${a.title}» برداشته شده است.` : ""
  access.ask = ""
}, { immediate: true })
const leave = () => { forgetAccess(); leaveGate() }

// the permanent account's AI switch under each card (nobody else sees it)
const switching = ref(""), mapOf = ref(null)   // mapOf: the assistant whose data map is open
async function flipAi(a) {
  switching.value = a.key; notice.value = ""
  try { await setAi(a.key, !access.ai[a.key]) }
  catch (e) { notice.value = e.message }
  finally { switching.value = "" }
}

// phones: each assistant is one short row; its description, roles and AI switch open under it, one at a time
const expanded = ref("")
const toggle = (key) => { expanded.value = expanded.value === key ? "" : key }

// the light on the card follows the pointer, and the card leans a little toward it
const move = (e) => {
  const el = e.currentTarget, r = el.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height
  el.style.setProperty("--mx", x * 100 + "%"); el.style.setProperty("--my", y * 100 + "%")
  el.style.setProperty("--rx", (0.5 - y) * 6 + "deg"); el.style.setProperty("--ry", (x - 0.5) * 8 + "deg")
}
const unlean = (e) => { e.currentTarget.style.setProperty("--rx", "0deg"); e.currentTarget.style.setProperty("--ry", "0deg") }
</script>

<template>
  <main class="hub">
    <AuroraBg />
    <header class="h-top">
      <div class="h-brand"><span class="h-mark"><BrandMark :size="24" /></span><span dir="ltr" lang="en">Pudineh Agent Center</span></div>
      <div class="h-tools">
        <span v-if="access.name" class="h-guest"><Icon name="user" :size="15" />{{ access.name }}<template v-if="access.expires_on">، تا {{ jalaliText(access.expires_on) }}</template></span>
        <button class="h-out" @click="leave"><Icon name="logout" :size="17" />خروج</button>
      </div>
    </header>

    <section class="h-hero">
      <span class="h-eyebrow"><i></i>نسخه‌ی نمایشی</span>
      <h1>انتخاب <span>دستیار</span></h1>
    </section>

    <p v-if="notice" class="h-notice" role="status"><Icon name="info" :size="16" />{{ notice }}</p>

    <section v-if="access.on && !visible.length" class="h-none">
      <span class="h-none-icon"><Icon name="lock" :size="26" /></span>
      <b>با حساب خودتان وارد شوید</b>
      <p>نام کاربری و رمزی را که برای دیدن دستیارها گرفته‌اید بنویسید.</p>
      <button class="h-none-btn" @click="asking = {}">ورود<Icon name="arrowLeft" :size="18" /></button>
    </section>

    <section v-else-if="phone" class="h-rows">
      <div v-for="(a, i) in visible" :key="a.key" :class="['h-row', 'hue-' + a.hue, { open: expanded === a.key }]" :style="{ '--i': i }">
        <div class="h-row-head">
          <button type="button" class="h-row-toggle" :aria-expanded="expanded === a.key" :aria-controls="'h-more-' + a.key" @click="toggle(a.key)">
            <span class="h-row-icon"><Icon :name="a.icon" :size="22" /></span>
            <span class="h-row-text"><b :title="a.title">{{ a.title }}</b>
              <small v-if="access.admin">هوش مصنوعی {{ access.ai[a.key] ? 'روشن' : 'خاموش' }}</small>
              <small v-else>{{ a.roles.join('، ') }}</small></span>
            <Icon name="chevron" :size="18" class="h-row-chev" />
          </button>
          <button type="button" class="h-row-go" @click="emit('open', a.key)">ورود<Icon name="arrowLeft" :size="16" /></button>
        </div>
        <div v-if="expanded === a.key" :id="'h-more-' + a.key" class="h-row-more">
          <p class="h-desc">{{ a.desc }}</p>
          <span class="h-roles"><span v-for="r in a.roles" :key="r">{{ r }}</span></span>
          <button v-if="access.admin" type="button" role="switch" :aria-checked="!!access.ai[a.key]"
                  :class="['h-ai', { on: access.ai[a.key] }]" :disabled="switching === a.key" @click="flipAi(a)">
            <Icon name="sparkles" :size="17" />
            <span class="h-ai-text"><b>هوش مصنوعی {{ access.ai[a.key] ? 'روشن' : 'خاموش' }}</b>
              <small>{{ access.ai[a.key] ? 'متن‌ها را مدل می‌نویسد' : 'بدون درخواست به مدل؛ متن‌ها را کد می‌نویسد' }}</small></span>
            <span class="h-ai-switch" aria-hidden="true"><i></i></span>
          </button>
          <button v-if="access.admin" type="button" class="h-ai h-map" @click="mapOf = a">
            <Icon name="layers" :size="17" /><span class="h-ai-text"><b>نقشه‌ی داده</b><small>هر داده از کجای کسب‌وکار می‌آید و هر عدد از چه ساخته شده</small></span></button>
        </div>
      </div>
    </section>

    <section v-else class="h-grid">
      <div v-for="(a, i) in visible" :key="a.key" class="h-slot" :style="{ '--i': i }">
      <button :class="['h-card', 'hue-' + a.hue]"
              @pointermove="move" @pointerleave="unlean" @click="emit('open', a.key)">
        <span class="h-glow" aria-hidden="true"></span>
        <span class="h-art" aria-hidden="true">
          <span class="h-rings"><i></i><i></i><i></i></span>
          <span class="h-icon"><Icon :name="a.icon" :size="46" /></span>
          <span v-for="(p, n) in a.perks" :key="p.text" :class="['h-perk', 'p' + n]"><Icon :name="p.icon" :size="14" />{{ p.text }}</span>
        </span>
        <span class="h-body">
          <span class="h-head"><b :title="a.title">{{ a.title }}</b><span class="h-live"><i></i>آماده</span></span>
          <span class="h-desc">{{ a.desc }}</span>
          <span class="h-roles"><span v-for="r in a.roles" :key="r">{{ r }}</span></span>
          <span class="h-go">ورود به دستیار<Icon name="arrowLeft" :size="18" /></span>
        </span>
      </button>
      <button v-if="access.admin" type="button" role="switch" :aria-checked="!!access.ai[a.key]"
              :class="['h-ai', { on: access.ai[a.key] }]" :disabled="switching === a.key" @click="flipAi(a)">
        <Icon name="sparkles" :size="17" />
        <span class="h-ai-text"><b>هوش مصنوعی {{ access.ai[a.key] ? 'روشن' : 'خاموش' }}</b>
          <small>{{ access.ai[a.key] ? 'متن‌ها را مدل می‌نویسد' : 'بدون درخواست به مدل؛ متن‌ها را کد می‌نویسد' }}</small></span>
        <span class="h-ai-switch" aria-hidden="true"><i></i></span>
      </button>
      <button v-if="access.admin" type="button" class="h-ai h-map" @click="mapOf = a">
        <Icon name="layers" :size="17" /><span class="h-ai-text"><b>نقشه‌ی داده</b><small>هر داده از کجای کسب‌وکار می‌آید و هر عدد از چه ساخته شده</small></span></button>
      </div>
    </section>

    <DataMap v-if="mapOf" :app="mapOf.key" :title="mapOf.title" @close="mapOf = null" />
    <!-- the permanent account's three panels fold to their headers, on every screen, so the cards stay first -->
    <AccessManager v-if="access.admin" :assistants="ASSISTANTS" collapsible />
    <LoginLog v-if="access.admin" collapsible />
    <SpeedPanel v-if="access.admin" collapsible />
    <ServerHealth v-if="access.admin" collapsible />
    <AccessDialog v-if="asking" @close="asking = null" @opened="opened" />
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
.h-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.h-guest { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: #c9c5ee; }
.h-notice { display: flex; align-items: center; gap: 8px; margin: -8px 0 0; padding: 10px 16px; border-radius: 14px; font-size: 13.5px;
  color: #ffd38a; background: rgba(255,176,87,.1); border: 1px solid rgba(255,176,87,.3); }
.h-none { width: min(100%, 420px); display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 32px 24px; text-align: center; border-radius: 28px;
  background: linear-gradient(165deg, rgba(255,255,255,.12), rgba(255,255,255,.035)); border: 1px solid rgba(255,255,255,.14);
  backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px); animation: h-up 1s cubic-bezier(.2,.9,.25,1) .3s backwards; }
.h-none-icon { display: grid; place-items: center; width: 64px; height: 64px; border-radius: 20px; color: #fff; background: linear-gradient(135deg, #7367f0, #00bad1); }
.h-none b { font-size: 18px; color: #fff; }
.h-none p { margin: 0; font-size: 14px; line-height: 2; color: #b7b3d9; }
.h-none-btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; height: 50px; margin-top: 6px; border: 0; border-radius: 15px; cursor: pointer;
  font: inherit; font-weight: 700; font-size: 15px; color: #fff; background: linear-gradient(110deg, #6a5cf5, #8f6bff 45%, #1fb8d6); }
.h-none-btn:focus-visible { outline: 3px solid #8fefff; outline-offset: 3px; }

.h-hero { text-align: center; max-width: 640px; margin-top: 4vh; animation: h-up .9s cubic-bezier(.2,.9,.25,1) .1s both; }
.h-eyebrow { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; font-size: 12.5px; color: #d9d5ff;
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.14); }
.h-eyebrow i { width: 7px; height: 7px; border-radius: 50%; background: #3ee08f; box-shadow: 0 0 0 0 rgba(62,224,143,.6); animation: h-pulse 2s infinite; }
h1 { margin: 16px 0 10px; font-size: clamp(28px, 4.6vw, 44px); line-height: 1.45; font-weight: 700; color: #fff; }
h1 span { background: linear-gradient(90deg, #a99fff, #5fe3f3 60%, #ff9fc6); -webkit-background-clip: text; background-clip: text; color: transparent; }
.h-hero p { margin: 0; color: #b7b3d9; font-size: 15px; line-height: 2; }

.h-grid { width: min(100%, 1120px); display: grid; gap: 24px; justify-content: center;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 400px)); grid-auto-rows: 1fr; margin-top: 8px; perspective: 1200px; }

/* one assistant, and under it the permanent account's AI switch */
.h-slot { display: flex; flex-direction: column; gap: 12px; }
.h-slot > .h-card { flex: 1; }
.h-ai { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 16px; border-radius: 18px; cursor: pointer; text-align: right;
  font: inherit; color: #d9d5ff; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.14); transition: background .2s, border-color .2s;
  animation: h-up 1s cubic-bezier(.2,.9,.25,1) calc(.45s + var(--i) * .12s) backwards; }
.h-ai:hover { background: rgba(255,255,255,.1); }
.h-ai:focus-visible { outline: 3px solid #8fefff; outline-offset: 3px; }
.h-ai:disabled { cursor: wait; }
.h-ai-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.h-ai-text b { font-size: 14px; color: #fff; }
.h-ai-text small { font-size: 12px; line-height: 1.8; color: #b7b3d9; }
.h-ai-switch { flex: none; position: relative; width: 42px; height: 24px; border-radius: 999px; background: rgba(255,255,255,.2); transition: background .25s; }
.h-ai-switch i { position: absolute; top: 3px; right: 3px; width: 18px; height: 18px; border-radius: 50%; background: #fff; transition: transform .25s; }
.h-ai.on { border-color: rgba(62,224,143,.4); }
.h-ai.on .h-ai-switch { background: #1f9d63; }
.h-ai.on .h-ai-switch i { transform: translateX(-18px); }
.h-card { --mx: 50%; --my: 0%; --rx: 0deg; --ry: 0deg; --c1: #7367f0; --c2: #00bad1;
  position: relative; display: flex; flex-direction: column; overflow: hidden; padding: 0; text-align: right; cursor: pointer;
  font: inherit; color: inherit; border-radius: 28px; border: 1px solid rgba(255,255,255,.14);
  background: linear-gradient(165deg, rgba(255,255,255,.12), rgba(255,255,255,.035));
  backdrop-filter: blur(22px) saturate(140%); -webkit-backdrop-filter: blur(22px) saturate(140%);
  box-shadow: 0 30px 80px -24px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.18);
  transform: rotateX(var(--rx)) rotateY(var(--ry)); transition: transform .25s ease, box-shadow .3s, border-color .3s;
  animation: h-up 1s cubic-bezier(.2,.9,.25,1) calc(.3s + var(--i) * .12s) backwards; }
.hue-teal { --c1: #0f8b7d; --c2: #f3b33d; }
.hue-amber { --c1: #8a5a1c; --c2: #5fb3f0; }
.hue-rose { --c1: #b23a62; --c2: #36c2a3; }
.hue-indigo { --c1: #3c4a8f; --c2: #e0a785; }
.hue-sky { --c1: #1d6fa3; --c2: #f28b82; }
.hue-ocean { --c1: #0d5c7a; --c2: #e8c27a; }
.hue-clay { --c1: #8a4320; --c2: #f2c27a; }
.hue-cobalt { --c1: #2a5bd0; --c2: #f5b82e; }
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

.h-body { flex: 1; position: relative; display: flex; flex-direction: column; gap: 12px; padding: 22px 24px 24px; }
.h-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.h-head b { min-width: 0; font-size: 21px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.h-live { flex: none; display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 12px; color: #7ef0b0;
  background: rgba(62,224,143,.12); border: 1px solid rgba(62,224,143,.3); }
.h-live i { width: 6px; height: 6px; border-radius: 50%; background: #3ee08f; animation: h-pulse 2s infinite; }
.h-desc { color: #c3bfe6; font-size: 14px; line-height: 2; }
.h-roles { display: flex; flex-wrap: wrap; gap: 6px; }
.h-roles span { padding: 3px 11px; border-radius: 999px; font-size: 12px; color: #dcd8ff; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); }
.h-go { display: flex; align-items: center; justify-content: center; gap: 10px; height: 50px; margin-top: auto; border-radius: 15px;
  font-weight: 700; font-size: 15px; color: #fff; background: linear-gradient(110deg, #6a5cf5, #8f6bff 45%, #1fb8d6); background-size: 180% 100%;
  box-shadow: 0 14px 30px -12px rgba(115,103,240,.9); transition: background-position .5s; }
.h-go .ico { transition: transform .3s; }
.h-card:hover .h-go { background-position: 100% 0; }
.h-card:hover .h-go .ico { transform: translateX(-5px); }

/* phones: one row per assistant (see the template); the chevron turns when its details are open */
.h-rows { width: 100%; display: flex; flex-direction: column; gap: 10px; margin-top: 4px; }
.h-row { --c1: #7367f0; --c2: #00bad1; border-radius: 20px; overflow: hidden; isolation: isolate;
  background: linear-gradient(165deg, rgba(48,45,96,.9), rgba(20,19,46,.92)); border: 1px solid rgba(255,255,255,.14);
  animation: h-up .7s cubic-bezier(.2,.9,.25,1) calc(.15s + var(--i) * .08s) backwards; }
.h-row.open { border-color: rgba(255,255,255,.26); }
.h-row-head { display: flex; align-items: center; gap: 8px; height: 68px; padding: 0 12px 0 10px; }
.h-row-toggle { flex: 1; min-width: 0; display: flex; align-items: center; gap: 12px; padding: 0; border: 0; background: none; font: inherit; color: inherit;
  text-align: right; cursor: pointer; border-radius: 14px; }
.h-row-toggle:focus-visible, .h-row-go:focus-visible { outline: 3px solid #8fefff; outline-offset: 3px; }
.h-row-icon { flex: none; display: grid; place-items: center; width: 44px; height: 44px; border-radius: 14px; color: #fff;
  background: linear-gradient(140deg, color-mix(in srgb, var(--c1) 90%, #fff 10%), color-mix(in srgb, var(--c2) 70%, #0d0c24)); }
.h-row-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.h-row-text b { font-size: 15.5px; color: #fff; line-height: 1.6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.h-row-text small { font-size: 12px; color: #b7b3d9; line-height: 1.7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.h-row-chev { flex: none; color: #b7b3d9; transform: rotate(-90deg); transition: transform .25s; }
.h-row.open .h-row-chev { transform: rotate(90deg); }
.h-row-go { flex: none; display: inline-flex; align-items: center; gap: 6px; height: 40px; padding: 0 14px; border: 0; border-radius: 12px; cursor: pointer;
  font: inherit; font-size: 14px; font-weight: 700; color: #fff; background: linear-gradient(110deg, #6a5cf5, #8f6bff 45%, #1fb8d6); }
.h-row-more { display: flex; flex-direction: column; gap: 12px; padding: 4px 14px 14px; animation: h-fade .3s ease both; }
.h-row-more .h-desc { margin: 0; font-size: 13.5px; }
.h-row-more .h-ai { animation: none; }

.h-foot { display: flex; align-items: center; gap: 6px; margin: auto 0 0; padding-top: 12px; font-size: 12.5px; color: #8f8bb6; animation: h-fade 1s ease .8s both; }

@media (max-width: 480px) {
  .h-top { align-items: flex-start; }
  .h-brand span:last-child { display: none; }
  .h-out { padding: 0 11px; }
  .h-hero { margin-top: 2vh; }
  .h-art { height: 190px; }
  .h-body { padding: 18px 18px 20px; }
}
@media (hover: none) { .h-card { transform: none; } }
/* Phones and touch screens: no 3D perspective (the lean follows a mouse, so it does nothing there) and no frosted
   glass. iPhone Safari draws the card's moving picture shifted and cut off when perspective, backdrop blur, rounded
   clipping and animated layers come together; the backgrounds are a little more opaque instead, so the look stays. */
@media (hover: none), (max-width: 767px) {
  .h-grid { perspective: none; }
  .h-card, .h-none { backdrop-filter: none; -webkit-backdrop-filter: none; isolation: isolate;
    background: linear-gradient(165deg, rgba(48,45,96,.9), rgba(20,19,46,.92)); }
  .h-perk { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(13,12,36,.72); }
  .h-ai { background: rgba(32,30,70,.9); }
}

@keyframes h-up { from { opacity: 0; transform: translateY(30px); } }
@keyframes h-fade { from { opacity: 0; } }
@keyframes h-pulse { 0% { box-shadow: 0 0 0 0 rgba(62,224,143,.6); } 70% { box-shadow: 0 0 0 8px rgba(62,224,143,0); } 100% { box-shadow: 0 0 0 0 rgba(62,224,143,0); } }
@keyframes h-ring { from { transform: scale(1); opacity: .9; } to { transform: scale(2.6); opacity: 0; } }
@keyframes h-bob { from { translate: 0 0; } to { translate: 0 -8px; } }
@media (prefers-reduced-motion: reduce) {
  .hub *, .hub *::before, .hub *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
  .h-card { transform: none; }
}
</style>
