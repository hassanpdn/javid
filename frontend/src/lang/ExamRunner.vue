<script setup>
// A test on the whole screen, one question at a time: big options (A to D, or keys 1 to 4), the dots of every question,
// and the time left counting down. Each answer is saved as soon as it is picked, so a reload or a lost connection
// does not lose it; when the time runs out the test is handed in by itself. Then the mark: right answers, each
// skill, and the wrong ones with the right answer. The placement test (run by the office for a walk-in) ends with the
// level it found, the score of each level and the next term's classes of that level, each with «ثبت‌نام».
// spec: { exam_id } (a learner's online test), { placement: student_id }, or { result: attempt_id } (a mark already given).
import { ref, computed, onMounted, onUnmounted } from "vue"
import { api, fa, lockScroll } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { short } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ spec: Object })
const emit = defineEmits(["close", "enroll"])
const paper = ref(null), answers = ref({}), at = ref(0), left = ref(0), result = ref(null), sending = ref(false), confirm = ref(false)
let timer
const LETTERS = ["A", "B", "C", "D"]
onMounted(async () => {
  lockScroll(true)
  addEventListener("keydown", key)
  try {
    if (props.spec.result) { result.value = await api(`/lang/attempts/${props.spec.result}/result`); return }
    paper.value = props.spec.placement ? await api("/lang/placement/start", { student_id: props.spec.placement }) : await api(`/lang/exams/${props.spec.exam_id}/start`, {})
    answers.value = { ...paper.value.answers }
    at.value = Math.max(0, paper.value.questions.findIndex((q) => !(q.id in answers.value)))
    left.value = paper.value.seconds_left
    timer = setInterval(() => { left.value--; if (left.value <= 0) { clearInterval(timer); submit() } }, 1000)
  } catch (e) { toast({ tone: "danger", title: e.message }); emit("close") }
})
onUnmounted(() => { clearInterval(timer); removeEventListener("keydown", key); lockScroll(false) })

const q = computed(() => paper.value?.questions[at.value])
const answered = computed(() => Object.keys(answers.value).length)
const clock = computed(() => `${String(Math.floor(Math.max(0, left.value) / 60)).padStart(2, "0")}:${String(Math.max(0, left.value) % 60).padStart(2, "0")}`)
async function choose(i) {
  if (result.value || !q.value) return
  const id = q.value.id
  answers.value = { ...answers.value, [id]: i }
  try { await api(`/lang/attempts/${paper.value.attempt_id}/answer`, { question: id, choice: i }) }
  catch (e) { toast({ tone: "warning", title: e.connection ? "پاسخ ذخیره نشد؛ دوباره بزنید" : e.message }); if (!e.connection) submit() }
  if (at.value < paper.value.questions.length - 1) setTimeout(() => { at.value++ }, 260)
}
async function submit() {
  if (sending.value || result.value) return
  sending.value = true; confirm.value = false; clearInterval(timer)
  try { result.value = await api(`/lang/attempts/${paper.value.attempt_id}/submit`, {}) }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { sending.value = false }
}
function key(e) {
  if (result.value || !paper.value || e.target.closest("input, textarea")) return
  const n = "1234".indexOf(e.key) >= 0 ? "1234".indexOf(e.key) : "abcd".indexOf(e.key.toLowerCase())
  if (n >= 0 && e.key.length === 1) { e.preventDefault(); choose(n) }
  else if (e.key === "ArrowLeft" && at.value < paper.value.questions.length - 1) at.value++
  else if (e.key === "ArrowRight" && at.value > 0) at.value--
}
const R = 62, C = 2 * Math.PI * R
const ring = computed(() => C * (1 - (result.value?.score || 0) / 100))
const title = computed(() => result.value?.title || paper.value?.title || "آزمون")
const close = () => { if (paper.value && !result.value) { confirm.value = "close"; return } emit("close") }
</script>

<template>
  <div class="lg-exam" role="dialog" aria-modal="true" :aria-label="title">
    <div class="lg-exam-top">
      <Icon name="book" :size="20" class="text-primary" />
      <b>{{ fa(title) }}</b>
      <span v-if="paper && !result" :class="['lg-timer', { low: left <= 60 }]" aria-live="off"><Icon name="clock" :size="16" />{{ fa(clock) }}</span>
      <button class="icon-btn" @click="close" aria-label="بستن"><Icon name="x" /></button>
    </div>

    <template v-if="!result">
      <div v-if="!paper" class="lg-exam-body"><div class="lg-q"><Skeleton :lines="6" /></div></div>
      <template v-else>
        <nav class="lg-dots" aria-label="پرسش‌ها">
          <button v-for="(x, i) in paper.questions" :key="x.id" :class="{ ans: x.id in answers, at: i === at }" :aria-label="'پرسش ' + (i + 1) + (x.id in answers ? '، پاسخ داده شد' : '')" @click="at = i">{{ fa(i + 1) }}</button>
        </nav>
        <div class="lg-exam-body">
          <Transition name="fade" mode="out-in">
            <div class="lg-q" :key="q.id">
              <div class="lg-q-meta"><span>پرسش {{ fa(at + 1) }} از {{ fa(paper.questions.length) }}</span><span class="tag">{{ q.skill_name }}</span>
                <span v-if="paper.kind === 'placement'" :class="['lg-chip', 'lg-lv', 'lv-' + q.level]">{{ q.level === 'S' ? 'Starter' : q.level }}</span></div>
              <p v-if="q.passage" class="lg-passage">{{ q.passage }}</p>
              <p class="lg-q-text">{{ q.text }}</p>
              <div class="lg-options" role="radiogroup" :aria-label="q.text">
                <button v-for="(o, i) in q.options" :key="i" type="button" role="radio" :aria-checked="answers[q.id] === i" :class="['lg-opt', { on: answers[q.id] === i }]" @click="choose(i)">
                  <i>{{ LETTERS[i] }}</i><span>{{ o }}</span></button>
              </div>
            </div>
          </Transition>
        </div>
        <div class="lg-exam-foot">
          <button class="btn" :disabled="at === 0" @click="at--"><Icon name="arrowRight" :size="16" />قبلی</button>
          <span class="muted small">{{ fa(answered) }} از {{ fa(paper.questions.length) }} پاسخ</span>
          <button v-if="at < paper.questions.length - 1" class="btn" @click="at++">بعدی<Icon name="arrowLeft" :size="16" /></button>
          <button v-else class="btn primary" :disabled="sending" @click="answered < paper.questions.length ? (confirm = 'submit') : submit()"><Icon name="check" :size="16" />پایان آزمون</button>
        </div>
      </template>
    </template>

    <div v-else class="lg-exam-body">
      <div class="lg-result">
        <div class="lg-result-top" v-reveal>
          <div class="lg-ring"><svg width="150" height="150" viewBox="0 0 150 150"><circle class="bg" cx="75" cy="75" :r="R" /><circle class="fg" cx="75" cy="75" :r="R" :stroke-dasharray="C" :stroke-dashoffset="ring" /></svg>
            <div><b>{{ fa(result.score) }}</b><small>از ۱۰۰</small></div></div>
          <h2 v-if="result.kind === 'placement'">سطح شما: {{ result.placed_name }} <span class="lg-chip lg-lv" :class="'lv-' + result.placed.split('-')[0]">{{ short(result.placed) }}</span></h2>
          <h2 v-else>{{ fa(result.right) }} پاسخ درست از {{ fa(result.of) }}</h2>
          <p v-if="result.kind === 'placement'" class="muted" style="margin: 0">شروع از {{ fa(result.placed_fa) }}، با کتاب {{ result.book }}.</p>
        </div>

        <section v-if="result.kind === 'placement'" class="card">
          <div class="card-head">پاسخ درست در هر سطح</div>
          <div class="lg-ladder">
            <div v-for="l in result.levels" :key="l.key" :class="{ placed: result.placed.startsWith(l.key + '-') }"><b>{{ l.cefr === 'Pre-A1' ? 'S' : l.cefr }}</b>
              <span class="lg-bar lg-lv" :class="'lv-' + l.key"><i :style="{ width: (100 * l.right / l.of) + '%' }"></i></span><span>{{ fa(l.right) }} از {{ fa(l.of) }}</span></div>
          </div>
          <small class="muted">هر سطح سه پرسش دارد. اولین سطحی که کمتر از دو پاسخ درست دارد، جای شروع است.</small>
        </section>
        <section v-if="result.kind === 'placement'" class="card">
          <div class="card-head">کلاس‌های این سطح در ترم بعد</div>
          <p v-if="!result.classes.length" class="muted small">برای این سطح هنوز کلاسی تعریف نشده است.</p>
          <ul class="lg-opts">
            <li v-for="c in result.classes" :key="c.id"><span><b>{{ c.pair_text }} ساعت {{ fa(c.time) }}</b><small class="muted">{{ c.teacher }} · {{ fa(c.room_name) }} · {{ fa(c.free) }} جای خالی</small></span>
              <button class="btn primary sm" :disabled="c.free <= 0" @click="emit('enroll', { student_id: result.student_id, course: result.placed, class_id: c.id })">ثبت‌نام</button></li>
          </ul>
        </section>

        <section v-if="result.skills.length && result.kind !== 'placement'" class="card">
          <div class="card-head">هر مهارت</div>
          <div class="lg-skills"><div v-for="s in result.skills" :key="s.key" :class="['lg-skill', { weak: s.pct < 60 }]"><span>{{ s.name }}</span><span class="lg-bar"><i :style="{ width: s.pct + '%' }"></i></span><b>{{ fa(s.right) }}/{{ fa(s.of) }}</b></div></div>
        </section>
        <section v-if="result.review.length && result.kind !== 'placement'" class="card">
          <div class="card-head">پاسخ‌های نادرست</div>
          <ul class="lg-review">
            <li v-for="r in result.review" :key="r.id"><small class="muted">{{ r.skill_name }}</small><span class="lg-en">{{ r.text }}</span>
              <span class="lg-en small"><span v-if="r.yours" class="wrong">{{ r.yours }}</span><span v-else class="muted">no answer</span> → <span class="right">{{ r.answer }}</span></span></li>
          </ul>
        </section>
        <button class="btn primary" style="align-self: center" @click="emit('close')">بازگشت</button>
      </div>
    </div>

    <div v-if="confirm" class="overlay" @click.self="confirm = false">
      <div class="dialog" v-pop role="alertdialog" style="max-width: 420px">
        <h3>{{ confirm === 'close' ? 'آزمون را نیمه‌کاره ببندید؟' : 'آزمون را تمام کنید؟' }}</h3>
        <p class="muted" style="margin: 0" v-if="confirm === 'close'">پاسخ‌ها ذخیره شده‌اند و تا وقت تمام نشده، می‌توانید برگردید و ادامه دهید.</p>
        <p class="muted" style="margin: 0" v-else>{{ fa(paper.questions.length - answered) }} پرسش بی‌پاسخ مانده است. پس از پایان، پاسخ‌ها عوض نمی‌شوند.</p>
        <div class="dialog-actions"><button class="btn" @click="confirm = false">ادامه‌ی آزمون</button>
          <button class="btn primary" @click="confirm === 'close' ? emit('close') : submit()">{{ confirm === 'close' ? 'بستن' : 'پایان آزمون' }}</button></div>
      </div>
    </div>
  </div>
</template>
