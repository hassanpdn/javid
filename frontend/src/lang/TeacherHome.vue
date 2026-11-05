<script setup>
// The teacher's home: today's sessions (each with «حضور و غیاب»), what needs them (attendance not written, a learner
// who stopped coming, a weak test, a test open now), four numbers about their classes, and their classes this term.
import { ref, onMounted } from "vue"
import { api, fa, retryable, langSession } from "../lib/api.js"
import { short } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "../fabric/HowTip.vue"
import BookCover from "./BookCover.vue"

const emit = defineEmits(["act", "open", "counts", "subtitle"])
const d = ref(null)
onMounted(() => retryable(async () => {
  d.value = await api("/lang/teacher/home")
  emit("counts", d.value.alerts.length)
  emit("subtitle", `${d.value.today_long}، ${d.value.today_date} · ${d.value.term.name}`)
}))
const BUTTON = { attendance: "ثبت حضور و غیاب", class: "پرونده‌ی کلاس", results: "نتیجه‌ها" }
</script>

<template>
  <div v-if="!d" class="flex flex-col gap-6"><Skeleton kind="stat" :count="2" /><div class="card"><Skeleton kind="row" :count="4" /></div></div>
  <div v-else class="flex flex-col gap-6">
    <section class="card lg-hero" v-reveal data-tour="lg-today">
      <div class="lg-hero-text">
        <h2>روز بخیر، {{ langSession.user.full_name }}</h2>
        <span v-if="!d.today.length" class="muted">امروز کلاسی ندارید.</span>
        <span v-else class="muted">امروز {{ fa(d.today.length) }} کلاس دارید.</span>
        <div class="flex flex-col gap-2" style="margin-top: 6px">
          <div v-for="c in d.today" :key="c.id" :class="['lg-test', 'lg-lv', 'lv-' + c.level]" style="background: var(--panel)">
            <span class="k-when"><b>{{ fa(c.time) }}</b><small>{{ fa(c.room_name) }}</small></span>
            <span class="lg-test-body"><b>{{ c.course_name }} <span class="lg-chip">{{ short(c.course) }}</span></b><small class="muted">جلسه‌ی {{ fa(c.session_no) }} · {{ fa(c.seats) }} نفر</small></span>
            <span v-if="c.written" class="tag k-t-success">ثبت شد</span>
            <button v-else class="btn primary sm" @click="emit('open', { id: c.id, open: 'attendance' })"><Icon name="check" :size="14" />حضور و غیاب</button>
          </div>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6" data-tour="lg-stats">
      <div v-for="s in d.stats" :key="s.label" v-reveal class="card stat stat-how" :style="{ '--c': 'var(--' + s.tone + ')' }">
        <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span><span class="grow"></span><HowTip :lines="s.how" /></div>
        <div><div class="stat-money">{{ fa(s.value) }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ fa(s.sub) }}</div></div>
      </div>
    </div>

    <section class="card" v-reveal data-tour="lg-alerts">
      <div class="card-head">کارهای امروز <span class="count">{{ fa(d.alerts.length) }}</span></div>
      <p v-if="!d.alerts.length" class="muted small">کار فوری‌ای نیست.</p>
      <ul v-else class="alerts">
        <li v-for="a in d.alerts" :key="a.type + a.title" class="alert k-alert">
          <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
          <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
          <div class="k-btns"><button :class="['btn', 'sm', a.act === 'attendance' ? 'primary' : 'ghost']" @click="emit('act', a)">{{ BUTTON[a.act] }}</button></div>
        </li>
      </ul>
    </section>

    <section data-tour="lg-classes">
      <h3 class="text-ink" style="margin: 0 0 12px">کلاس‌های این ترم</h3>
      <div class="lg-tcards">
        <button v-for="c in d.classes" :key="c.id" :class="['card', 'lg-tcard', 'lg-lv', 'lv-' + c.level]" @click="emit('open', { id: c.id })">
          <div class="lg-tcard-top"><BookCover :level="c.level" :cefr="c.cefr" :units="c.units" size="sm" />
            <span><b>{{ c.course_name }}</b><small class="muted">{{ c.pair_text }} · {{ fa(c.time_text) }}</small><small class="muted">{{ fa(c.room_name) }} · {{ fa(c.seats) }} نفر</small></span></div>
          <div class="lg-bar"><i :style="{ width: (100 * c.held / 20) + '%' }"></i></div>
          <small class="muted">{{ fa(c.held) }} جلسه از ۲۰ · جلسه‌ی بعد {{ fa(c.next_text) }}</small>
        </button>
      </div>
    </section>
  </div>
</template>
