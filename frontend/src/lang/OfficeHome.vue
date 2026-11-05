<script setup>
// The manager's and the secretary's home: the assistant's morning summary (manager), the four main numbers with
// «از کجا؟», today's work (each line with the button its work needs), today's classes and, for the manager, the live log.
import { ref, onMounted, onUnmounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { busy, idle } from "../lib/notify.js"
import { langSession } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"
import EventFeed from "../fabric/EventFeed.vue"
import HowTip from "../fabric/HowTip.vue"
import SourceTip from "../components/SourceTip.vue"
import { short } from "./lib.js"

const props = defineProps({ role: String })
const emit = defineEmits(["act", "message", "open-class", "counts", "subtitle"])
const d = ref(null), brief = ref("")
const load = async () => {
  d.value = await api("/lang/today")
  emit("counts", d.value.alerts.length)
  emit("subtitle", `${d.value.today_long}، ${d.value.today} · ${d.value.term.name}، ${d.value.term.days_left} روز تا پایان`)
}
onMounted(async () => {
  await retryable(load)
  if (props.role !== "owner") return
  busy("lang-brief", "دستیار در حال نوشتن خلاصه‌ی امروز")
  try { brief.value = (await api("/lang/brief")).text } catch { brief.value = "خلاصه‌ی امروز آماده نشد." } finally { idle("lang-brief") }
})
onUnmounted(() => idle("lang-brief"))
const BUTTON = { board: "در جدول کلاس‌ها", class: "پرونده‌ی کلاس", student: "پرونده", enroll: "ثبت‌نام در کلاس", renewals: "فهرست" }
</script>

<template>
  <div class="flex flex-col gap-6">
    <section v-if="role === 'owner'" v-reveal class="card welcome brief" data-tour="lg-brief">
      <div class="welcome-text">
        <h2>روز بخیر، {{ langSession.user.full_name }}</h2>
        <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه‌ی امروز به قلم دستیار</div>
        <p v-if="brief"><TypeText :text="fa(brief)" /></p>
        <Skeleton v-else :lines="3" />
      </div>
      <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
    </section>

    <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6" data-tour="lg-stats">
      <Skeleton v-if="!d" kind="stat" :count="4" />
      <div v-else v-for="(s, i) in d.stats" :key="s.label" v-reveal class="card stat stat-how" :style="{ '--c': 'var(--' + s.tone + ')' }">
        <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span><span class="grow"></span><HowTip :lines="s.how" /><SourceTip app="lang" :k="'stat.' + i" /></div>
        <div><div class="stat-money">{{ fa(s.value) }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ fa(s.sub) }}</div></div>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-6">
      <section v-reveal class="card col-span-12 xl:col-span-7" data-tour="lg-alerts">
        <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span><SourceTip app="lang" k="alerts" /></div>
        <Skeleton v-if="!d" kind="row" :count="5" />
        <p v-else-if="!d.alerts.length" class="muted small">کار فوری‌ای نیست.</p>
        <ul v-else class="alerts">
          <li v-for="a in d.alerts" :key="a.type + a.title" class="alert k-alert">
            <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
            <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
            <div class="k-btns">
              <button v-if="a.message" class="btn sm" @click="emit('message', { student_id: a.student_id, kind: a.message })"><Icon name="message" :size="14" />پیام</button>
              <button v-if="a.act === 'board' && role !== 'owner'" class="btn ghost sm" @click="emit('act', a)">{{ BUTTON.board }}</button>
              <button v-else-if="a.act" :class="['btn', 'sm', a.act === 'board' || a.act === 'enroll' ? 'primary' : 'ghost']" @click="emit('act', a)">{{ a.act === 'board' ? 'درست کردن در جدول' : BUTTON[a.act] }}</button>
            </div>
          </li>
        </ul>
      </section>
      <div class="col-span-12 xl:col-span-5 flex flex-col gap-6">
        <section v-reveal class="card" data-tour="lg-today">
          <div class="card-head">کلاس‌های امروز <span v-if="d" class="count">{{ fa(d.classes_today.length) }}</span></div>
          <Skeleton v-if="!d" kind="row" :count="4" />
          <p v-else-if="!d.classes_today.length" class="muted small">امروز کلاسی نیست.</p>
          <ul v-else class="k-list">
            <li v-for="c in d.classes_today" :key="c.id">
              <button :class="['card', 'k-row', 'lg-lv', 'lv-' + c.level]" @click="emit('open-class', c.id)">
                <span class="k-when"><b>{{ fa(c.time) }}</b><small>{{ fa(c.room_name) }}</small></span>
                <span class="k-row-body"><b>{{ c.course_name }} <span class="lg-chip">{{ short(c.course) }}</span></b>
                  <span class="k-meta">{{ c.teacher }} · {{ fa(c.seats) }} نفر · جلسه‌ی {{ fa(c.session_no) }}</span></span>
                <span v-if="c.written" class="tag k-t-success">حضور ثبت شد</span>
              </button>
            </li>
          </ul>
        </section>
        <EventFeed v-if="role === 'owner'" endpoint="/lang/events" data-tour="lg-feed" />
      </div>
    </div>
  </div>
</template>
