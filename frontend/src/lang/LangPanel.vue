<script setup>
// The language institute's panel, one for the four roles; each sees its own pages.
// Manager: today's work, the timetable (and fixing it), teachers, learners, the road. Secretary: today's work,
// learners, next term's registration, the timetable to look at, the road. Teacher: their classes and tests.
// Learner: their road, this week's plan and their tests. Drawers and dialogs open from any page.
import { ref, computed, defineAsyncComponent } from "vue"
import { fa, langSession } from "../lib/api.js"
import { brand, chatFor } from "./lib.js"
import { LANG_TOURS } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
const OfficeHome = defineAsyncComponent(() => import("./OfficeHome.vue"))
const BoardView = defineAsyncComponent(() => import("./BoardView.vue"))
const TeachersView = defineAsyncComponent(() => import("./TeachersView.vue"))
const StudentsView = defineAsyncComponent(() => import("./StudentsView.vue"))
const RenewalsView = defineAsyncComponent(() => import("./RenewalsView.vue"))
const CurriculumView = defineAsyncComponent(() => import("./CurriculumView.vue"))
const TeacherHome = defineAsyncComponent(() => import("./TeacherHome.vue"))
const TeacherTests = defineAsyncComponent(() => import("./TeacherTests.vue"))
const StudentHome = defineAsyncComponent(() => import("./StudentHome.vue"))
const ClassDrawer = defineAsyncComponent(() => import("./ClassDrawer.vue"))
const StudentDrawer = defineAsyncComponent(() => import("./StudentDrawer.vue"))
const MessageDialog = defineAsyncComponent(() => import("./MessageDialog.vue"))
const EnrollDialog = defineAsyncComponent(() => import("./EnrollDialog.vue"))
const NewStudentDialog = defineAsyncComponent(() => import("./NewStudentDialog.vue"))
const ExamRunner = defineAsyncComponent(() => import("./ExamRunner.vue"))

const role = langSession.user.role
const view = ref(role === "student" ? "road" : "home")
const counts = ref({ alerts: 0, problems: 0 }), stamp = ref(0), subtitle = ref("")
const classId = ref(null), studentId = ref(null), message = ref(null), enrolling = ref(null), adding = ref(false), exam = ref(null)
const board = ref({ term: "current", pick: null })   // where the timetable opens: a term, and a class to move

const NAV = {
  owner: [{ header: "آموزشگاه" }, { key: "home", label: "امروز", icon: "dashboard", badge: () => counts.value.alerts },
          { key: "board", label: "جدول کلاس‌ها", icon: "calendar" }, { key: "teachers", label: "استادها", icon: "user" },
          { key: "students", label: "زبان‌آموزان", icon: "users" }, { key: "curriculum", label: "مسیر آموزشی", icon: "route", more: true }],
  secretary: [{ header: "آموزشگاه" }, { key: "home", label: "امروز", icon: "dashboard", badge: () => counts.value.alerts },
              { key: "students", label: "زبان‌آموزان", icon: "users" }, { key: "renewals", label: "ثبت‌نام ترم بعد", icon: "refresh" },
              { key: "board", label: "جدول کلاس‌ها", icon: "calendar" }, { key: "curriculum", label: "مسیر آموزشی", icon: "route", more: true }],
  teacher: [{ header: "کلاس‌های من" }, { key: "home", label: "امروز", icon: "dashboard", badge: () => counts.value.alerts },
            { key: "tests", label: "آزمون‌های آنلاین", icon: "check" }],
  student: [{ header: "من" }, { key: "road", label: "مسیر من", icon: "route" }, { key: "plan", label: "برنامه‌ی هفته", icon: "calendar" },
            { key: "tests", label: "آزمون‌ها", icon: "check" }],
}
const nav = computed(() => NAV[role].map((i) => ({ ...i, badge: typeof i.badge === "function" ? i.badge() : i.badge })))
const TITLES = { home: "کارهای امروز", board: "جدول کلاس‌ها", teachers: "استادها", students: "زبان‌آموزان", renewals: "ثبت‌نام ترم بعد",
                 curriculum: "مسیر آموزشی", tests: "آزمون‌های آنلاین", road: "مسیر من", plan: "برنامه‌ی هفته" }
const changed = () => { stamp.value++ }

// what a line of today's work, a problem or a button asks for
function act(a) {
  if (a.act === "board") { board.value = { term: a.term || "next", pick: a.class_ids?.[a.class_ids.length - 1] || null }; view.value = "board" }
  else if (a.act === "class" || a.act === "attendance" || a.act === "results") classId.value = { id: a.class_id, open: a.act, exam_id: a.exam_id, day: a.day }
  else if (a.act === "student") studentId.value = a.student_id
  else if (a.act === "enroll") enrolling.value = { student_id: a.student_id, course: a.placed }
  else if (a.act === "renewals") view.value = "renewals"
}
const moveFromDrawer = (cl) => { classId.value = null; board.value = { term: cl.kind, pick: cl.id }; view.value = "board" }
const messageSent = () => { message.value = null; changed() }
const added = (sid) => { adding.value = false; changed(); studentId.value = sid }
const enrolled = () => { enrolling.value = null; changed() }
const examDone = () => { exam.value = null; changed() }
const placementOf = (sid) => { exam.value = { placement: sid } }
const tour = computed(() => ({ ...LANG_TOURS[role], ready: !!subtitle.value }))
</script>

<template>
  <AppLayout app="lang" :brand="brand()" :chat="chatFor(role)" :title="TITLES[view]" :subtitle="fa(subtitle)" :nav="nav" v-model="view" :tour="tour">
    <div v-if="role === 'owner' || role === 'secretary'" class="k-actions" data-tour="lg-actions">
      <button class="btn primary" @click="adding = true"><Icon name="plus" :size="18" />زبان‌آموز جدید</button>
      <button v-if="view !== 'board'" class="btn" @click="board = { term: 'next', pick: null }; view = 'board'"><Icon name="calendar" :size="18" />کلاس‌های ترم بعد</button>
    </div>

    <template v-if="role === 'owner' || role === 'secretary'">
      <BoardView v-if="view === 'board'" :key="'b' + board.term + board.pick" :start="board" :can-move="role === 'owner'" @open="classId = { id: $event }" @message="message = $event" @changed="changed" />
      <TeachersView v-else-if="view === 'teachers'" :key="'t' + stamp" @open="classId = { id: $event }" />
      <StudentsView v-else-if="view === 'students'" :key="'s' + stamp" @open="studentId = $event" />
      <RenewalsView v-else-if="view === 'renewals'" :key="'r' + stamp" @open="studentId = $event" @message="message = $event" @changed="changed" />
      <CurriculumView v-else-if="view === 'curriculum'" />
      <OfficeHome v-else :key="'h' + stamp" :role="role" @act="act" @message="message = $event" @open-class="classId = { id: $event }" @counts="counts.alerts = $event" @subtitle="subtitle = $event" />
    </template>
    <template v-else-if="role === 'teacher'">
      <TeacherTests v-if="view === 'tests'" :key="'x' + stamp" @open="classId = $event" />
      <TeacherHome v-else :key="'h' + stamp" @act="act" @open="classId = $event" @counts="counts.alerts = $event" @subtitle="subtitle = $event" />
    </template>
    <StudentHome v-else :key="'m' + stamp" :part="view" @take="exam = { exam_id: $event }" @result="exam = { result: $event }" @subtitle="subtitle = $event" @go="view = $event" />

    <ClassDrawer v-if="classId" :spec="classId" @close="classId = null" @changed="changed" @move="moveFromDrawer" @student="studentId = $event" />
    <StudentDrawer v-if="studentId" :id="studentId" @close="studentId = null" @changed="changed" @message="message = $event" @enroll="enrolling = $event" @placement="placementOf" />
    <MessageDialog v-if="message" :spec="message" @close="message = null" @done="messageSent" />
    <EnrollDialog v-if="enrolling" :spec="enrolling" @close="enrolling = null" @saved="enrolled" />
    <NewStudentDialog v-if="adding" @close="adding = false" @saved="added" @placement="(sid) => { adding = false; changed(); placementOf(sid) }"
                      @enroll="(e) => { adding = false; changed(); enrolling = e }" />
    <ExamRunner v-if="exam" :spec="exam" @close="examDone" @enroll="(e) => { exam = null; enrolling = e }" />
  </AppLayout>
</template>
