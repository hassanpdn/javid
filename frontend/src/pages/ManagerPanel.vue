<script setup>
// Manager dashboard: today's brief, attendance, alerts that need a decision, 10-day trend
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue"
import { api, fa, session, lockScroll } from "../lib/api.js"
import AppLayout from "../components/AppLayout.vue"
import ChatBox from "../components/ChatBox.vue"
import BarChart from "../components/BarChart.vue"
import RadialGauge from "../components/RadialGauge.vue"
import Icon from "../components/Icon.vue"
import CountUp from "../components/CountUp.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"

const ALERT_LOOK = {
  teacher_late: { icon: "clock", tone: "danger" },
  letter_decision: { icon: "file", tone: "primary" },
  letter_deadline: { icon: "calendar", tone: "warning" },
}
const user = computed(() => session.user)
const data = ref(null), brief = ref(""), view = ref("home")
const draft = reactive({ open: false, alert: null, text: "", loading: false, saving: false, verified: null, missing: [] })
const open = computed(() => data.value ? data.value.alerts.filter((a) => !a.done).length : 0)
const nav = computed(() => [
  { header: "پیشخوان" },
  { key: "home", label: "داشبورد", icon: "dashboard", badge: open.value },
  { header: "دستیار" },
  { key: "chat", label: "پرسش از اسناد", icon: "message" },
])
const presentPct = computed(() => {
  const s = data.value?.students
  return s && s.total ? Math.round(100 * s.present / s.total) : 0
})
const stats = computed(() => {
  const d = data.value
  return [
    { label: "دانش‌آموزان حاضر", value: d.students.present, of: d.students.total, sub: `${fa(d.students.absent)} غایب، ${fa(d.students.late)} تأخیر`, icon: "userCheck", tone: "success" },
    { label: "غیبت امروز", value: d.students.absent, sub: "دانش‌آموزان غایب امروز", icon: "calendar", tone: "danger" },
    { label: "تأخیر معلمان امروز", value: d.late_teachers.length, sub: d.late_teachers.map((t) => t.full_name + " " + fa(t.check_in)).join("، ") || "همه به موقع", icon: "clock", tone: "warning" },
    { label: "نامه‌های منتظر رسیدگی", value: d.open_letters, sub: "در صندوق پرسنل اداری", icon: "mail", tone: "primary" },
  ]
})
const look = (a) => ALERT_LOOK[a.type] || { icon: "alert", tone: "warning" }
const load = async () => { data.value = await api("/manager/overview") }
watch(() => draft.open, lockScroll)
// the bell fires this when a new notification arrives, so alerts stay current
const onNotify = () => load()
onMounted(async () => {
  window.addEventListener("notifications-changed", onNotify)
  await load()
  try { brief.value = (await api("/manager/briefing")).text } catch { brief.value = "خلاصه امروز در دسترس نیست." }
})
onUnmounted(() => { lockScroll(false); window.removeEventListener("notifications-changed", onNotify) })
const openDraft = async (alert) => {
  Object.assign(draft, { open: true, alert, text: "", loading: true, verified: null, missing: [] })
  try {
    const r = await api("/manager/warnings/draft", { teacher_id: alert.teacher_id })
    Object.assign(draft, { text: r.text, verified: r.verified, missing: r.missing })
  }
  catch { draft.text = "" } finally { draft.loading = false }
}
const issue = async () => {
  draft.saving = true
  try { await api("/manager/warnings", { teacher_id: draft.alert.teacher_id, text: draft.text }); draft.open = false; await load() }
  finally { draft.saving = false }
}
const decide = async (alert, approve) => {
  await api(`/manager/letters/${alert.letter_id}/decide`, { approve }); await load()
}
</script>

<template>
  <AppLayout title="داشبورد مدیر" :subtitle="data ? fa(data.today) : ''" :nav="nav" v-model="view">
    <div v-show="view === 'home'" class="flex flex-col gap-6">
      <div class="grid grid-cols-12 gap-6">
        <section v-reveal class="card welcome brief col-span-12 xl:col-span-8">
          <div class="welcome-text">
            <h2>روز بخیر، {{ user.full_name }}</h2>
            <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه امروز به قلم دستیار</div>
            <p v-if="brief"><TypeText :text="brief" /></p>
            <div v-else class="shimmer"><span></span><span></span><span style="width:60%"></span></div>
          </div>
          <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
        </section>
        <section v-reveal class="card col-span-12 xl:col-span-4 flex flex-col">
          <div class="card-head">حضور امروز <small>دانش‌آموزان</small></div>
          <template v-if="data">
            <RadialGauge :value="presentPct" label="حاضر" />
            <div class="grid grid-cols-3 text-center mt-2">
              <div><b class="text-ink text-lg"><CountUp :value="data.students.present" /></b><small class="block muted">حاضر</small></div>
              <div><b class="text-danger text-lg"><CountUp :value="data.students.absent" /></b><small class="block muted">غایب</small></div>
              <div><b class="text-warning text-lg"><CountUp :value="data.students.late" /></b><small class="block muted">تأخیر</small></div>
            </div>
          </template>
          <div v-else class="shimmer"><span></span><span></span><span></span></div>
        </section>
      </div>

      <div v-if="data" class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6">
        <div v-for="s in stats" :key="s.label" v-reveal class="card stat" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span>
            <div class="stat-num"><CountUp :value="s.value" /> <span v-if="s.of" class="of">از {{ fa(s.of) }}</span></div></div>
          <div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ s.sub }}</div></div>
        </div>
      </div>

      <div v-if="data" class="grid grid-cols-12 gap-6">
        <section v-reveal class="card col-span-12 2xl:col-span-6">
          <div class="card-head">نیاز به توجه شما <span class="count">{{ fa(open) }}</span></div>
          <p v-if="!data.alerts.length" class="muted">موردی نیست.</p>
          <ul class="alerts">
            <li v-for="(a, i) in data.alerts" :key="i" :class="['alert', a.type, { done: a.done }]">
              <span :class="['tint', 't-' + (a.done ? 'success' : look(a).tone)]"><Icon :name="a.done ? 'check' : look(a).icon" :size="20" /></span>
              <div class="alert-body">
                <b>{{ fa(a.title) }}</b>
                <small class="muted">{{ fa(a.detail) }}</small>
                <small v-if="a.done" class="ok">✓ {{ fa(a.done_text) }}</small>
              </div>
              <button v-if="a.type === 'teacher_late' && !a.done" class="btn sm" @click="openDraft(a)"><Icon name="edit" :size="16" />پیش‌نویس تذکر</button>
              <div v-if="a.type === 'letter_decision'" class="btn-row">
                <button class="btn sm success" @click="decide(a, true)">موافقم</button>
                <button class="btn sm danger-soft" @click="decide(a, false)">مخالفم</button>
              </div>
            </li>
          </ul>
        </section>

        <section v-reveal class="card col-span-12 2xl:col-span-6">
          <div class="card-head"><span class="grow">درصد حضور دانش‌آموزان در ده روز اخیر</span>
            <span class="legend-dot" style="--c: var(--primary)">۹۵٪ و بیشتر</span><span class="legend-dot" style="--c: var(--warning)">کمتر از ۹۵٪</span></div>
          <BarChart :points="data.trend" />
        </section>
      </div>
    </div>

    <div v-show="view === 'chat'">
      <ChatBox class="card chat-card" title="دستیار اسناد" subtitle="پاسخ فقط از روی آیین‌نامه‌ها و دستورالعمل‌های مدرسه" />
    </div>

    <!-- written warning dialog -->
    <div v-if="draft.open" class="overlay" @click.self="draft.open = false">
      <div class="dialog" v-pop>
        <h3>تذکر کتبی به {{ draft.alert.name }}</h3>
        <p class="muted small">این متن را دستیار نوشته است. قبل از صدور بخوانید و هر جا لازم است ویرایش کنید.</p>
        <div v-if="draft.loading" class="shimmer tall"><span></span><span></span><span></span><span style="width:50%"></span></div>
        <p v-if="!draft.loading && draft.verified === true" class="check ok">✓ تاریخ‌ها و ساعت‌های این متن با ثبت ورود سامانه تطبیق داده شد.</p>
        <p v-if="!draft.loading && draft.verified === false" class="check bad">این موارد ثبت‌شده در متن نیامده یا متفاوت آمده: {{ fa(draft.missing.join('، ')) }}. قبل از صدور اصلاح کنید.</p>
        <textarea v-if="!draft.loading" v-model="draft.text" rows="10"></textarea>
        <div class="dialog-actions">
          <button class="btn primary" :disabled="draft.loading || !draft.text.trim() || draft.saving" @click="issue">تأیید و صدور</button>
          <button class="btn ghost" @click="draft.open = false">انصراف</button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
