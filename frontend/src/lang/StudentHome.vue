<script setup>
// The learner's own pages. part "road": where they are on the road (a ring with the share walked, the assistant's
// short note, the road itself), this term (the book, the unit now, sessions, attendance, the mark so far, the next
// session, the fee) and the next term (its book, new or the same, when it starts, and keeping a seat in one of its
// classes). part "plan": this week's plan, built from the book, the week's sessions, weak skills and open tests, with
// ticks that last the week. part "tests": the open test to start, past marks and each skill.
import { ref, computed, onMounted } from "vue"
import { api, fa, retryable, langSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { short } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import RoadMap from "./RoadMap.vue"
import BookCover from "./BookCover.vue"

const props = defineProps({ part: { default: "road" } })
const emit = defineEmits(["take", "result", "subtitle", "go"])
const d = ref(null), note = ref(""), picked = ref(null), busy = ref(0)
const load = async () => {
  d.value = await api("/lang/me/home")
  picked.value = picked.value || d.value.road.stations.find((s) => s.state === "current")?.key || d.value.road.stations.find((s) => s.state === "next")?.key
  emit("subtitle", `${d.value.today_long}، ${d.value.today_date}`)
}
onMounted(async () => {
  await retryable(load)
  try { note.value = (await api("/lang/me/note")).text } catch { note.value = "" }
})
const cu = computed(() => d.value?.road.current), nx = computed(() => d.value?.road.next)
const open = computed(() => (d.value?.exams || []).filter((e) => e.open && !(e.mine && e.mine.submitted)))
const past = computed(() => (d.value?.exams || []).filter((e) => e.mine && e.mine.submitted))
const R = 48, C = 2 * Math.PI * R
const firstName = computed(() => (langSession.user.full_name || "").split(" ")[0])
async function tick(i) {
  i.done = !i.done
  try { await api("/lang/me/tick", { item: i.key, done: i.done }); d.value.plan.done += i.done ? 1 : -1 }
  catch (e) { i.done = !i.done; toast({ tone: "danger", title: e.message }) }
}
async function reserve(c) {
  busy.value = c.id
  try { await api("/lang/me/reserve", { class_id: c.id }); toast({ tone: "success", title: "جای شما نگه داشته شد", body: `${c.course_name}، ${c.pair_text} ساعت ${fa(c.time)}. شهریه را در دفتر بپردازید.` }); await load() }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = 0 }
}
const KIND = { book: "book", workbook: "notebook", skill: "sparkles", absent: "user", test: "check", exam: "flag" }
</script>

<template>
  <div v-if="!d" class="flex flex-col gap-6"><div class="card"><Skeleton :lines="4" /></div><div class="card"><Skeleton :lines="6" /></div></div>

  <div v-else-if="part === 'road'" class="flex flex-col gap-6">
    <section class="card lg-hero" v-reveal data-tour="lg-hero">
      <div class="lg-ring" role="img" :aria-label="`${d.road.pct} درصد مسیر`">
        <svg width="116" height="116" viewBox="0 0 116 116" style="width: 100%; height: 100%"><circle class="bg" cx="58" cy="58" :r="R" /><circle class="fg" cx="58" cy="58" :r="R" :stroke-dasharray="C" :stroke-dashoffset="C * (1 - d.road.pct / 100)" /></svg>
        <div><b>{{ fa(d.road.pct) }}٪</b><small>از کل مسیر</small></div>
      </div>
      <div class="lg-hero-text">
        <h2>سلام {{ firstName }}</h2>
        <span v-if="cu" class="muted">این ترم: <b class="text-ink">{{ cu.class.course_name }}</b> <span :class="['lg-chip', 'lg-lv', 'lv-' + cu.class.level]">{{ short(cu.class.course) }}</span></span>
        <span v-if="d.road.finish" class="muted small">اگر بی‌وقفه ادامه دهید، {{ fa(d.road.finish.terms) }} ترم دیگر، در {{ fa(d.road.finish.month) }}، به پایان مسیر می‌رسید.</span>
        <p v-if="note" class="small" style="margin: 4px 0 0; line-height: 2"><Icon name="sparkles" :size="14" class="text-primary" /> <TypeText :text="fa(note)" /></p>
      </div>
    </section>

    <button v-if="open.length" class="lg-test open" v-reveal @click="emit('take', open[0].id)" style="cursor: pointer; text-align: right; font: inherit">
      <span class="tint" style="background: rgba(255,255,255,.18); color: #fff"><Icon name="check" :size="22" /></span>
      <span class="lg-test-body"><b>آزمون آنلاین «{{ fa(open[0].title) }}» باز است</b><small>{{ fa(open[0].count) }} پرسش در {{ fa(open[0].minutes) }} دقیقه · تا {{ fa(open[0].closes_word) }}</small></span>
      <span class="btn light sm">شروع آزمون<Icon name="arrowLeft" :size="16" /></span>
    </button>

    <section class="card" v-reveal data-tour="lg-road">
      <div class="card-head"><span class="grow">مسیر من</span><small class="muted">روی هر ایستگاه بزنید</small></div>
      <RoadMap :stations="d.road.stations" v-model="picked" />
    </section>

    <div class="grid grid-cols-12 gap-6">
      <section v-if="cu" :class="['card', 'col-span-12', 'lg:col-span-7', 'lg-lv', 'lv-' + cu.class.level]" v-reveal data-tour="lg-now">
        <div class="card-head">این ترم <span class="count">{{ fa(cu.term.name) }}</span></div>
        <div class="lg-term">
          <BookCover :level="cu.class.level" :cefr="cu.class.cefr" :units="cu.class.units" />
          <div class="lg-term-body">
            <b>{{ cu.class.book }}</b>
            <span class="muted small">درس‌های {{ fa(cu.class.units[0]) }} تا {{ fa(cu.class.units[1]) }}<template v-if="cu.unit"> · اکنون درس {{ fa(cu.unit) }}، <span class="lg-en">«{{ cu.topic }}»</span></template></span>
            <div class="lg-bar" role="progressbar" :aria-valuenow="cu.sessions" aria-valuemin="0" :aria-valuemax="cu.of"><i :style="{ width: cu.pct + '%' }"></i></div>
            <small class="muted">جلسه‌ی {{ fa(cu.sessions) }} از {{ fa(cu.of) }} · پایان ترم {{ fa(cu.term.end_text) }}</small>
          </div>
        </div>
        <div class="lg-facts">
          <div><b>{{ fa(cu.so_far ?? "—") }}</b><small>نمره تا این‌جا (قبولی ۷۰)</small></div>
          <div><b>{{ fa(cu.attendance.counts.absent) }}</b><small>غیبت در این ترم</small></div>
          <div><b>{{ fa(cu.midterm ?? "—") }}</b><small>میان‌ترم</small></div>
        </div>
        <div class="lg-next" style="margin-top: 12px"><Icon name="clock" :size="20" />
          <span>جلسه‌ی بعد: <b>{{ fa(cu.class.next_text) }} ساعت {{ fa(cu.class.time) }}</b> · {{ fa(cu.class.room_name) }} · {{ cu.class.teacher }}</span></div>
        <small v-if="cu.left > 0" class="k-late" style="margin-top: 8px">از شهریه‌ی این ترم {{ fa(cu.left_text) }} مانده است.</small>
      </section>

      <section v-if="nx" :class="['card', 'col-span-12', cu ? 'lg:col-span-5' : '', 'lg-lv', 'lv-' + nx.key.split('-')[0]]" v-reveal data-tour="lg-next">
        <div class="card-head">ترم بعد <span v-if="nx.term" class="count">از {{ fa(nx.term.start_long) }}</span></div>
        <div class="lg-term">
          <BookCover :level="nx.key.split('-')[0]" :cefr="nx.key.split('-')[0] === 'S' ? 'Pre-A1' : nx.key.split('-')[0]" :units="nx.units" />
          <div class="lg-term-body">
            <b>{{ nx.name }}</b>
            <span class="muted small">{{ nx.book }}، درس‌های {{ fa(nx.units[0]) }} تا {{ fa(nx.units[1]) }}</span>
            <span v-if="nx.same_book" class="tag k-t-success" style="align-self: flex-start">همین کتاب این ترم</span>
            <span v-else class="tag k-t-warning" style="align-self: flex-start">کتاب جدید لازم است · {{ fa(nx.book_price_text) }}</span>
            <small class="muted">شهریه {{ fa(nx.fee_text) }}</small>
          </div>
        </div>
        <div v-if="nx.registered" class="lg-next" style="margin-top: 12px"><Icon name="check" :size="20" />
          <span>جای شما نگه داشته شده: <b>{{ nx.registered.pair_text }} ساعت {{ fa(nx.registered.time) }}</b> · {{ nx.registered.teacher }}<template v-if="nx.registered.left > 0"> · شهریه را در دفتر بپردازید</template></span></div>
        <template v-else>
          <p class="muted small" style="margin: 12px 0 0">هنوز برای ترم بعد جا نگرفته‌اید. یکی از این کلاس‌ها را انتخاب کنید:</p>
          <ul class="lg-opts">
            <li v-for="c in nx.options" :key="c.id"><span><b>{{ c.pair_text }} ساعت {{ fa(c.time) }}</b><small class="muted">{{ c.teacher }} · {{ fa(c.free) }} جای خالی</small></span>
              <button class="btn primary sm" :disabled="c.free <= 0 || busy === c.id" @click="reserve(c)">نگه داشتن جا</button></li>
          </ul>
        </template>
      </section>
    </div>

    <section class="card" v-reveal>
      <div class="card-head"><span class="grow">این هفته</span><span class="count">{{ fa(d.plan.done) }} از {{ fa(d.plan.items.length) }}</span>
        <button class="btn ghost sm" @click="emit('go', 'plan')">همه‌ی برنامه<Icon name="arrowLeft" :size="14" /></button></div>
      <ul class="lg-plan"><li v-for="i in d.plan.items.slice(0, 3)" :key="i.key" :class="{ done: i.done }">
        <button class="lg-tick" :class="{ on: i.done }" :aria-pressed="i.done" :aria-label="i.text" @click="tick(i)"><Icon name="check" :size="16" /></button>
        <span class="lg-plan-body"><span>{{ fa(i.text) }}</span></span><span :class="['lg-when', { now: i.when === 'امروز' }]">{{ fa(i.when) }}</span></li></ul>
    </section>
  </div>

  <div v-else-if="part === 'plan'" class="grid grid-cols-12 gap-6">
    <section class="card col-span-12 xl:col-span-8" v-reveal data-tour="lg-plan">
      <div class="card-head"><span class="grow">برنامه‌ی {{ fa(d.plan.week_text) }}</span><span class="count">{{ fa(d.plan.done) }} از {{ fa(d.plan.items.length) }}</span></div>
      <p class="muted small" style="margin: 0 0 6px">این برنامه از روی درس‌های کتاب، جلسه‌های همین هفته، نتیجه‌ی آزمون‌های آنلاین و غیبت‌هایتان ساخته شده است.</p>
      <p v-if="!d.plan.items.length" class="muted small">این هفته کاری نیست.</p>
      <ul class="lg-plan"><li v-for="i in d.plan.items" :key="i.key" :class="{ done: i.done }">
        <button class="lg-tick" :class="{ on: i.done }" :aria-pressed="i.done" :aria-label="i.text" @click="tick(i)"><Icon name="check" :size="16" /></button>
        <span class="lg-plan-body"><span><Icon :name="KIND[i.kind]" :size="14" class="muted" /> {{ fa(i.text) }}</span><small v-if="i.why">{{ fa(i.why) }}</small>
          <button v-if="i.exam_id && !i.done" class="btn primary sm" style="align-self: flex-start; margin-top: 4px" @click="emit('take', i.exam_id)">شروع آزمون</button></span>
        <span :class="['lg-when', { now: i.when === 'امروز' }]">{{ fa(i.when) }}</span></li></ul>
    </section>
    <section class="card col-span-12 xl:col-span-4" v-reveal>
      <div class="card-head">مهارت‌ها در آزمون‌های این ترم</div>
      <p v-if="!d.skills.length" class="muted small">هنوز آزمون آنلاینی نداده‌اید.</p>
      <div class="lg-skills"><div v-for="s in d.skills" :key="s.name" :class="['lg-skill', { weak: s.pct < 60 }]"><span>{{ s.name }}</span><span class="lg-bar"><i :style="{ width: s.pct + '%' }"></i></span><b>{{ fa(s.right) }}/{{ fa(s.of) }}</b></div></div>
      <small class="muted" style="display: block; margin-top: 10px">مهارتی که کمتر از ۶۰ درصد پاسخ درست دارد، تمرینش در برنامه‌ی هفته می‌آید.</small>
    </section>
  </div>

  <div v-else class="flex flex-col gap-6">
    <section class="card" v-reveal data-tour="lg-tests">
      <div class="card-head">آزمون‌های باز</div>
      <p v-if="!open.length" class="muted small">اکنون آزمون بازی نیست. وقتی استاد آزمونی باز کند، این‌جا می‌آید.</p>
      <div class="flex flex-col gap-3">
        <div v-for="e in open" :key="e.id" class="lg-test open">
          <span class="lg-test-body"><b>{{ fa(e.title) }}</b><small>{{ fa(e.count) }} پرسش در {{ fa(e.minutes) }} دقیقه · تا {{ fa(e.closes_word) }}<template v-if="e.mine"> · نیمه‌کاره، ادامه دهید</template></small></span>
          <button class="btn light sm" @click="emit('take', e.id)">{{ e.mine ? 'ادامه' : 'شروع' }}<Icon name="arrowLeft" :size="16" /></button>
        </div>
      </div>
    </section>
    <section class="card" v-reveal>
      <div class="card-head">نمره‌های من</div>
      <p v-if="!past.length" class="muted small">هنوز نمره‌ای نیست.</p>
      <div class="flex flex-col gap-3">
        <div v-for="e in past" :key="e.id" class="lg-test">
          <span class="lg-score">{{ fa(e.mine.score) }}<small>از ۱۰۰</small></span>
          <span class="lg-test-body"><b>{{ fa(e.title) }}</b><small class="muted">{{ fa(e.closes_text) }}</small></span>
          <button class="btn ghost sm" @click="emit('result', e.mine.id)">پاسخ‌ها</button>
        </div>
      </div>
    </section>
  </div>
</template>
