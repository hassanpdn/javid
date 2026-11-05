<script setup>
// One class in a side drawer: its book, teacher, days, room and seats, its 20 sessions (held, today, the midterm and
// the final), the learners with absences and marks, its online tests. The manager can give it another teacher (only
// the ones who can: right level, free, coming at that hour) or move it in the timetable; the teacher writes
// attendance and marks, and opens an online test. spec: { id, open: "attendance" | "results", exam_id, day }.
import { ref, reactive, computed, watch, onMounted, defineAsyncComponent } from "vue"
import { api, fa, langSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { short } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import BookCover from "./BookCover.vue"
const AttendanceSheet = defineAsyncComponent(() => import("./AttendanceSheet.vue"))
const ExamDialog = defineAsyncComponent(() => import("./ExamDialog.vue"))
const ResultsDialog = defineAsyncComponent(() => import("./ResultsDialog.vue"))

const props = defineProps({ spec: Object })
const emit = defineEmits(["close", "changed", "move", "student"])
const role = langSession.user.role
const d = ref(null), sheet = ref(null), making = ref(false), results = ref(null), busy = ref(""), marks = reactive({})
const load = async () => {
  d.value = await api(`/lang/classes/${props.spec.id}`)
  for (const r of d.value.roster) marks[r.student_id] = { midterm: r.midterm ?? "", final: r.final ?? "" }
}
watch(() => props.spec.id, () => { d.value = null; load() })
onMounted(async () => {
  await load()
  if (props.spec.open === "attendance") sheet.value = props.spec.day || true
  if (props.spec.open === "results" && props.spec.exam_id) results.value = props.spec.exam_id
})
const num = (v) => { const s = String(v).replace(/[۰-۹]/g, (x) => "۰۱۲۳۴۵۶۷۸۹".indexOf(x)).trim(); return s === "" ? null : Number(s) }
async function saveMark(r) {
  const m = marks[r.student_id], mid = num(m.midterm), fin = num(m.final)
  if (mid === r.midterm && fin === r.final) return
  if ([mid, fin].some((x) => x !== null && (!Number.isInteger(x) || x < 0 || x > 100))) { toast({ tone: "warning", title: "نمره باید عددی از ۰ تا ۱۰۰ باشد" }); return }
  try { const res = await api(`/lang/classes/${props.spec.id}/scores`, { student_id: r.student_id, midterm: mid, final: fin }); Object.assign(r, { midterm: mid, final: fin, so_far: res.so_far }) }
  catch (e) { toast({ tone: "danger", title: e.message }) }
}
async function giveTo(t) {
  busy.value = "teacher"
  try { await api(`/lang/classes/${props.spec.id}/teacher`, { teacher_id: t.id }); toast({ tone: "success", title: "استاد کلاس عوض شد", body: t.name }); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
async function remove() {
  busy.value = "remove"
  try { await api(`/lang/classes/${props.spec.id}/remove`, {}); toast({ tone: "success", title: "کلاس حذف شد" }); emit("changed"); emit("close") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
const written = () => { sheet.value = null; load(); emit("changed") }
const made = () => { making.value = false; load(); emit("changed") }
const todayIso = computed(() => d.value?.class.today ? d.value.class.next_day : null)
const open = (sid) => { if (role !== "teacher") emit("student", sid) }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer k-drawer" v-drawer aria-label="پرونده‌ی کلاس">
      <div class="drawer-head"><b class="text-ink">پرونده‌ی کلاس</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><Skeleton :lines="6" /></div>
        <template v-else>
          <section :class="['card', 'lg-class-head', 'lg-lv', 'lv-' + d.class.level]">
            <BookCover :level="d.class.level" :cefr="d.class.cefr" :units="d.class.units" size="sm" />
            <div class="k-head grow" style="min-width: 0">
              <b class="k-title">{{ d.class.course_name }} <span class="lg-chip">{{ short(d.class.course) }}</span></b>
              <span class="k-meta">{{ d.term.name }} · {{ d.class.teacher }}</span>
              <span class="k-meta">{{ d.class.pair_text }} ساعت {{ fa(d.class.time_text) }} · {{ fa(d.class.room_name) }}</span>
              <span :class="['lg-seats', { over: d.class.seats > d.class.capacity }]" style="max-width: 260px"><span class="lg-bar"><i :style="{ width: Math.min(100, 100 * d.class.seats / d.class.capacity) + '%' }"></i></span>{{ fa(d.class.seats) }} از {{ fa(d.class.capacity) }} جا</span>
              <div class="btn-row" style="margin-top: 6px">
                <button v-if="role !== 'secretary' && d.class.kind === 'current'" class="btn primary sm" @click="sheet = true"><Icon name="check" :size="14" />حضور و غیاب</button>
                <button v-if="role !== 'secretary' && d.class.kind === 'current'" class="btn sm" @click="making = true"><Icon name="sparkles" :size="14" />آزمون آنلاین جدید</button>
                <button v-if="role === 'owner'" class="btn sm" @click="emit('move', d.class)"><Icon name="calendar" :size="14" />جابه‌جا در جدول</button>
              </div>
            </div>
          </section>

          <section v-if="d.class.kind === 'current'" :class="['card', 'lg-lv', 'lv-' + d.class.level]">
            <div class="card-head">جلسه‌ها <span class="count">{{ fa(d.class.held) }} از ۲۰</span></div>
            <div class="lg-sessions" role="list">
              <i v-for="s in d.sessions" :key="s.n" role="listitem" :title="s.day_text + (s.exam ? '، ' + s.exam : s.unit ? '، درس ' + s.unit : '')"
                 :class="{ held: s.past && s.written, miss: s.past && !s.written && s.day !== todayIso, today: s.day === todayIso, exam: !!s.exam }">{{ fa(s.n) }}</i>
            </div>
            <small class="muted">دایره‌ها آزمون میان‌ترم و پایان ترم‌اند. قرمز: جلسه‌ای که حضور و غیابش ثبت نشده است.</small>
          </section>

          <section class="card">
            <div class="card-head">زبان‌آموزان <span class="count">{{ fa(d.roster.length) }}</span></div>
            <p v-if="!d.roster.length" class="muted small">هنوز کسی ثبت‌نام نکرده است.</p>
            <div v-else style="overflow-x: auto">
              <table class="lg-roster">
                <thead><tr><th>نام</th><th v-if="d.class.kind === 'current'">غیبت</th><th v-if="d.class.kind === 'current'">میان‌ترم</th><th v-if="d.class.kind === 'current'">آنلاین</th><th v-if="d.class.kind === 'current'">تا این‌جا</th><th v-if="role !== 'teacher'">شهریه</th></tr></thead>
                <tbody>
                  <tr v-for="r in d.roster" :key="r.student_id">
                    <td><button v-if="role !== 'teacher'" class="link" @click="open(r.student_id)">{{ r.name }}</button><template v-else>{{ r.name }}</template></td>
                    <template v-if="d.class.kind === 'current'">
                      <td :class="{ warn: r.absent >= 3 }">{{ fa(r.absent) }}</td>
                      <td><input v-if="role !== 'secretary'" v-model="marks[r.student_id].midterm" inputmode="numeric" :aria-label="'میان‌ترم ' + r.name" @change="saveMark(r)"><template v-else>{{ fa(r.midterm ?? "—") }}</template></td>
                      <td>{{ fa(r.quiz ?? "—") }}</td>
                      <td :class="{ warn: r.so_far !== null && r.so_far < 70 }"><b>{{ fa(r.so_far ?? "—") }}</b></td>
                    </template>
                    <td v-if="role !== 'teacher'"><span v-if="r.left > 0" class="tag k-t-warning">مانده دارد</span><span v-else class="tag k-t-success">پرداخت شد</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <small v-if="d.class.kind === 'current'" class="muted">«تا این‌جا» میانگین نمره‌ی میان‌ترم و آزمون‌های آنلاین است؛ قبولی ۷۰.</small>
          </section>

          <section v-if="d.exams.length" class="card">
            <div class="card-head">آزمون‌های آنلاین</div>
            <ul class="k-mini"><li v-for="e in d.exams" :key="e.id">
              <div class="k-row-top"><span>{{ fa(e.title) }}</span><span :class="['tag', e.open ? 'k-t-success' : 'k-t-secondary']">{{ e.open ? 'باز تا ' + fa(e.closes_word) : 'بسته شد' }}</span></div>
              <small class="muted">{{ fa(e.count) }} پرسش · {{ fa(e.taken) }} از {{ fa(e.of) }} نفر داده‌اند<template v-if="e.average !== null"> · میانگین {{ fa(e.average) }}</template></small>
              <button v-if="role !== 'secretary'" class="link small" style="align-self: flex-start" @click="results = e.id">نتیجه‌ها</button></li></ul>
          </section>

          <section v-if="role === 'owner' && d.teachers" class="card">
            <div class="card-head">استاد دیگری بدهید</div>
            <ul class="lg-teachers">
              <li v-for="t in d.teachers.slice(0, 6)" :key="t.id"><span><b class="text-ink">{{ t.name }}</b><small>{{ t.ok ? 'سطح را درس می‌دهد، این ساعت آزاد است و می‌آید' : t.why.join('، ') }}</small></span>
                <button class="btn sm" :disabled="!t.ok || busy === 'teacher'" @click="giveTo(t)">بدهید</button></li>
            </ul>
            <button v-if="!d.roster.length" class="btn ghost sm" style="margin-top: 10px" :disabled="busy === 'remove'" @click="remove"><Icon name="x" :size="14" />حذف این کلاس</button>
          </section>
        </template>
      </div>
    </aside>
    <AttendanceSheet v-if="sheet" :class-id="spec.id" :day="typeof sheet === 'string' ? sheet : null" @close="sheet = null" @saved="written" />
    <ExamDialog v-if="making && d" :cls="d.class" @close="making = false" @saved="made" />
    <ResultsDialog v-if="results" :id="results" @close="results = null" />
  </div>
</template>
