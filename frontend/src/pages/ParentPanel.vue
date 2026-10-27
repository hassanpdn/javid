<script setup>
// Parent: weekly report and progress for their own child only
import { ref, computed, watch, onMounted, onUnmounted } from "vue"
import { api, fa, lockScroll } from "../lib/api.js"
import { chatUi } from "../lib/chat.js"
import AppLayout from "../components/AppLayout.vue"
import Sparkline from "../components/Sparkline.vue"
import LevelChip from "../components/LevelChip.vue"
import HealthFormDialog from "../components/HealthFormDialog.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import Avatar from "../components/Avatar.vue"
import CountUp from "../components/CountUp.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"

const f = ref(null), report = ref(""), formKind = ref(null), view = ref("child")
const load = async () => { f.value = await api("/parent/child") }
const nav = computed(() => [
  { header: "فرزند من" },
  { key: "child", label: f.value ? "گزارش " + f.value.first_name : "گزارش فرزند", icon: "user" },
])
watch(() => !!formKind.value, lockScroll)
const onNotify = () => load()
onMounted(async () => {
  window.addEventListener("notifications-changed", onNotify)
  await load()
  try { report.value = (await api("/parent/report")).text } catch { report.value = "گزارش این هفته در دسترس نیست." }
})
onUnmounted(() => { lockScroll(false); window.removeEventListener("notifications-changed", onNotify) })
// the floating assistant answers about this child only (the server takes the child from the login)
const chat = computed(() => ({
  title: "پرسش از مدرسه", subtitle: "درباره درس و حضور فرزندتان یا مقررات مدرسه", endpoint: "/parent/ask",
  loadingText: "در حال بررسی", examples: askExamples.value,
  intro: "درباره درس‌ها، غیبت و تأخیر " + (f.value ? f.value.first_name : "فرزندتون") + " یا مقررات مدرسه بپرسید:",
}))
const askExamples = computed(() => {
  const n = f.value?.first_name || "بچه‌م"
  return [`${n} در کدام درس ضعیف‌تر است؟`, "در سه هفته‌ی اخیر چند روز غیبت داشته است؟", "وضعیت درس ریاضی چطور است؟", "کلاس‌ها چه ساعتی شروع می‌شوند؟"]
})
</script>

<template>
  <AppLayout :chat="chat" title="پنل ولی" :subtitle="f ? 'گزارش ' + f.name : ''" :nav="nav" v-model="view">
    <div>
      <div v-if="!f" class="flex flex-col gap-6">
        <div class="card"><Skeleton kind="row" round /></div>
        <div class="card"><Skeleton :lines="3" /></div>
        <div class="card"><Skeleton kind="row" :count="4" /></div>
      </div>
      <div v-else class="flex flex-col gap-6">
        <section v-reveal class="card profile">
          <div class="profile-cover" ref="cover">
            <i style="width:180px;height:180px;left:-40px;top:-60px"></i><i style="width:110px;height:110px;left:30%;top:50px"></i><i style="width:70px;height:70px;right:12%;top:20px"></i>
          </div>
          <div class="profile-body">
            <Avatar :name="f.name" :size="96" tone="primary" />
            <div class="profile-meta">
              <h2>{{ f.name }}</h2>
              <div class="meta-row">
                <span><Icon name="school" :size="17" />کلاس {{ f.class }}</span>
                <span><Icon name="user" :size="17" />آموزگار: {{ f.teacher }}</span>
              </div>
            </div>
            <button class="btn primary" @click="chatUi.open = true"><Icon name="message" :size="18" />پرسش درباره {{ f.first_name }}</button>
          </div>
        </section>

        <div class="grid grid-cols-12 gap-6">
          <div class="col-span-12 xl:col-span-8 flex flex-col gap-6">
            <section v-reveal class="card welcome brief">
              <div class="welcome-text">
                <div class="card-head mb-0"><span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span> گزارش این هفته</div>
                <p v-if="report"><TypeText :text="report" /></p>
                <Skeleton v-else :lines="3" />
              </div>
              <div class="welcome-art"><AiOrb :size="110" :busy="!report" /></div>
            </section>

            <section v-for="(s, i) in f.suggestions" :key="'s' + i" v-reveal class="card counsel">
              <div class="card-head"><span class="tint sm t-success"><Icon name="message" :size="18" /></span>پیام مشاور مدرسه <small>{{ fa(s.approved_at) }}</small></div>
              <p>{{ fa(s.for_parent) }}</p>
            </section>

            <section v-reveal class="card">
              <div class="card-head">پیشرفت درسی <small>از مهر تا امروز</small></div>
              <div class="progress-list">
                <div v-for="p in f.progress" :key="p.subject" class="prog-row">
                  <span class="prog-sub">{{ p.subject }}</span>
                  <Sparkline :points="p.points" :change="p.change" />
                  <LevelChip :level="p.now" />
                </div>
                <!-- the time axis under the trend lines: oldest on the right, today on the left -->
                <div class="prog-row prog-axis" aria-hidden="true"><span></span><span class="axis"><span>مهر</span><span>امروز</span></span><span></span></div>
              </div>
              <div class="legend"><span v-for="l in [4,3,2,1]" :key="l"><LevelChip :level="l" /></span></div>
            </section>
          </div>

          <div class="col-span-12 xl:col-span-4 flex flex-col gap-6">
            <section v-reveal class="card">
              <div class="card-head">حضور <small>۳۰ روز اخیر</small></div>
              <div class="mini-stats">
                <div class="ok-tile"><b><CountUp :value="f.attendance.present" /></b><small>روز حاضر</small></div>
                <div><b><CountUp :value="f.attendance.absent" /></b><small>غیبت</small></div>
                <div><b><CountUp :value="f.attendance.late" /></b><small>تأخیر</small></div>
              </div>
              <div v-if="f.attendance.absent_days.length" class="chips">
                <span v-for="d in f.attendance.absent_days" :key="d.date" :class="['day', { ok: d.excused }]">{{ fa(d.date) }}{{ d.excused ? ' · موجه' : '' }}</span>
              </div>
            </section>

            <section v-reveal class="card">
              <div class="card-head">فرم‌های سلامت</div>
              <div class="forms-grid">
                <button v-for="k in ['physical', 'wellbeing']" :key="k" class="form-tile action" @click="formKind = k">
                  <span :class="['tint', 'sm', k === 'physical' ? 't-danger' : 't-info']"><Icon :name="k === 'physical' ? 'heart' : 'message'" :size="18" /></span>
                  <b>{{ k === 'physical' ? 'سلامت جسمی' : 'حال و احوال' }}</b>
                  <small class="muted">{{ f.forms[k] ? 'آخرین ثبت: ' + fa(f.forms[k].date) : 'هنوز تکمیل نشده' }}</small>
                  <span class="tile-cta">{{ f.forms[k] ? 'به‌روزرسانی' : 'تکمیل فرم' }}<Icon name="chevron" :size="14" /></span>
                </button>
              </div>
            </section>

            <section v-if="f.messages.length" v-reveal class="card">
              <div class="card-head">پیام‌های مدرسه</div>
              <ul class="notes"><li v-for="m in f.messages" :key="m.id"><small class="muted">{{ fa(m.created_at) }}</small><b class="small">{{ fa(m.title) }}</b><p>{{ fa(m.body) }}</p></li></ul>
            </section>
          </div>
        </div>
      </div>
    </div>

    <HealthFormDialog v-if="formKind" :kind="formKind" @close="formKind = null" @saved="formKind = null; load()" />
  </AppLayout>
</template>
