<script setup>
// The dental clinic's panel, one for both roles. Home: today's work (the next working day's unconfirmed appointments
// and empty hours, patients who often do not come, plans not started), the main numbers, today's schedule, and for the
// dentist the assistant's morning summary and the live log. Then the schedule, the patients, the treatment plans and,
// for the dentist, the checks. «نوبت جدید» books; «بیمار جدید» opens a patient's file.
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { api, fa, dentalSession, retryable } from "../lib/api.js"
import { busy, idle } from "../lib/notify.js"
import { brand, CHAT } from "./lib.js"
import { DENTAL_OWNER, DENTAL_STAFF } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"
import EventFeed from "../fabric/EventFeed.vue"
import HowTip from "../fabric/HowTip.vue"
import SourceTip from "../components/SourceTip.vue"
import AlertList from "./AlertList.vue"
import DayList from "./DayList.vue"
const ScheduleView = defineAsyncComponent(() => import("./ScheduleView.vue"))
const PatientsView = defineAsyncComponent(() => import("./PatientsView.vue"))
const PlansView = defineAsyncComponent(() => import("./PlansView.vue"))
const ChecksList = defineAsyncComponent(() => import("../components/kit/ChecksList.vue"))
const PatientDrawer = defineAsyncComponent(() => import("./PatientDrawer.vue"))
const BookDialog = defineAsyncComponent(() => import("./BookDialog.vue"))
const PatientDialog = defineAsyncComponent(() => import("./PatientDialog.vue"))
const MessageDialog = defineAsyncComponent(() => import("./MessageDialog.vue"))

const owner = dentalSession.user.role === "owner"
const view = ref("home"), d = ref(null), brief = ref(""), patientId = ref(null), booking = ref(null), adding = ref(false), message = ref(null), stamp = ref(0)
const nav = computed(() => [
  { header: "مطب" },
  { key: "home", label: "امروز", icon: "dashboard", badge: d.value?.alerts.length || 0 },
  { key: "schedule", label: "نوبت‌ها", icon: "calendar" },
  { key: "patients", label: "بیماران", icon: "users" },
  { key: "plans", label: "طرح‌های درمان", icon: "heart" },
  ...(owner ? [{ key: "checks", label: "بررسی‌ها", icon: "shield", badge: d.value?.checks || 0, more: true }] : []),
])
const TITLES = { home: "کارهای امروز", schedule: "نوبت‌ها", patients: "بیماران", plans: "طرح‌های درمان", checks: "بررسی‌ها" }
const load = async () => { d.value = await api("/dental/today") }
const changed = () => { stamp.value++; load().catch(() => {}) }
onMounted(async () => {
  await retryable(load)
  if (!owner) return
  busy("dental-brief", "دستیار در حال نوشتن خلاصه‌ی امروز")
  try { brief.value = (await api("/dental/brief")).text } catch { brief.value = "خلاصه‌ی امروز آماده نشد." } finally { idle("dental-brief") }
})
onUnmounted(() => idle("dental-brief"))
const booked = () => { booking.value = null; changed() }
const added = (pid) => { adding.value = false; changed(); patientId.value = pid }
const sent = () => { message.value = null; changed() }
</script>

<template>
  <AppLayout app="dental" :brand="brand()" :chat="CHAT" :title="TITLES[view]" :subtitle="d ? fa(d.today_long + '، ' + d.today) : ''" :nav="nav" v-model="view"
             :tour="{ ...(owner ? DENTAL_OWNER : DENTAL_STAFF), ready: !!d && view === 'home' }">
    <div class="k-actions" data-tour="dt-actions">
      <button class="btn primary" @click="booking = {}"><Icon name="calendar" :size="18" />نوبت جدید</button>
      <button class="btn" @click="adding = true"><Icon name="plus" :size="18" />بیمار جدید</button>
    </div>

    <ScheduleView v-if="view === 'schedule'" :key="stamp" @open="patientId = $event" @book="booking = $event" @message="message = $event" @changed="changed" />
    <PatientsView v-else-if="view === 'patients'" :key="stamp" @open="patientId = $event" />
    <PlansView v-else-if="view === 'plans'" :key="stamp" @open="patientId = $event" @message="message = $event" />
    <ChecksList v-else-if="view === 'checks'" :key="stamp" @open="patientId = $event" endpoint="/dental/checks" intro="این بخش درمان‌های انجام‌شده، پرداخت‌ها و مراحل طرح‌های درمان را کنار هم می‌گذارد و هر جا با هم جور نباشد، همان را با جزئیاتش نشان می‌دهد." empty="همه‌چیز با هم جور است." :icons='{ unpaid: "chart", halfway: "tooth" }' :record="{ key: 'patient_id', label: 'بیمار' }" how-label="جزئیات" />
    <div v-else class="flex flex-col gap-6">
      <section v-if="owner" v-reveal class="card welcome brief" data-tour="dt-brief">
        <div class="welcome-text">
          <h2>روز بخیر، {{ dentalSession.user.full_name }}</h2>
          <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه‌ی امروز به قلم دستیار</div>
          <p v-if="brief"><TypeText :text="fa(brief)" /></p>
          <Skeleton v-else :lines="3" />
        </div>
        <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
      </section>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6" data-tour="dt-stats">
        <Skeleton v-if="!d" kind="stat" :count="4" />
        <div v-else v-for="(s, i) in d.stats" :key="s.label" v-reveal class="card stat stat-how" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span><span class="grow"></span><HowTip :lines="s.how" /><SourceTip app="dental" :k="'stat.' + i" /></div>
          <div><div class="stat-money">{{ fa(s.value) }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ fa(s.sub) }}</div></div>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <section v-reveal class="card col-span-12 xl:col-span-7" data-tour="dt-alerts">
          <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span><SourceTip app="dental" k="alerts" />
            <span class="grow"></span><button v-if="d?.checks" class="btn ghost sm" @click="view = 'checks'"><Icon name="shield" :size="14" />{{ fa(d.checks) }} مورد در بررسی‌ها</button></div>
          <Skeleton v-if="!d" kind="row" :count="5" />
          <AlertList v-else :alerts="d.alerts" @open="patientId = $event" @book="booking = $event" @message="message = $event" @changed="changed" />
        </section>
        <div class="col-span-12 xl:col-span-5 flex flex-col gap-6">
          <section v-reveal class="card" data-tour="dt-today">
            <div class="card-head">نوبت‌های امروز</div>
            <Skeleton v-if="!d" kind="row" :count="4" />
            <p v-else-if="d.schedule.closed" class="muted small">امروز مطب تعطیل است.</p>
            <DayList v-else :rows="d.schedule.rows.filter((r) => r.appt)" compact @open="patientId = $event" @changed="changed" />
          </section>
          <EventFeed v-if="owner" endpoint="/dental/events" data-tour="dt-feed" />
        </div>
      </div>
    </div>
    <PatientDrawer v-if="patientId" :id="patientId" @close="patientId = null" @changed="changed" @book="booking = $event" @message="message = $event" />
    <BookDialog v-if="booking" :preset="booking" @close="booking = null" @saved="booked" />
    <PatientDialog v-if="adding" @close="adding = false" @saved="added" />
    <MessageDialog v-if="message" :spec="message" @close="message = null" @done="sent" />
  </AppLayout>
</template>
