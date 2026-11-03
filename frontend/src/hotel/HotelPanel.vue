<script setup>
// The hotel's panel for the manager, reservations and the front desk. Home: today's work (most urgent first, each
// with the button its work needs), the main numbers, and for the manager the assistant's morning summary and the
// live log. Then «شلوغی امروز» (arrivals in order, the rooms to clean first, tomorrow's rooms), the tape chart, the
// bookings, the rooms, agencies, the hotel's website, the front desk's day, and for the manager the report, the
// checks and the prices. «رزرو جدید» starts from a phone call or pasted text.
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { api, fa, hotelSession, retryable } from "../lib/api.js"
import { busy, idle } from "../lib/notify.js"
import { brand, CHAT, useSiteBookings } from "./lib.js"
import { HOTEL_MANAGER, HOTEL_DESK } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"
import EventFeed from "../fabric/EventFeed.vue"
import HowTip from "../fabric/HowTip.vue"
import AlertList from "./AlertList.vue"
const PeakView = defineAsyncComponent(() => import("./PeakView.vue"))
const GridView = defineAsyncComponent(() => import("./GridView.vue"))
const BookingsView = defineAsyncComponent(() => import("./BookingsView.vue"))
const RoomsView = defineAsyncComponent(() => import("./RoomsView.vue"))
const AgenciesView = defineAsyncComponent(() => import("./AgenciesView.vue"))
const SiteView = defineAsyncComponent(() => import("./SiteView.vue"))
const DeskView = defineAsyncComponent(() => import("./DeskView.vue"))
const ReportView = defineAsyncComponent(() => import("./ReportView.vue"))
const ChecksView = defineAsyncComponent(() => import("./ChecksView.vue"))
const SettingsView = defineAsyncComponent(() => import("./SettingsView.vue"))
const BookingDrawer = defineAsyncComponent(() => import("./BookingDrawer.vue"))
const BookDialog = defineAsyncComponent(() => import("./BookDialog.vue"))

const role = hotelSession.user.role
const manager = role === "manager", front = role !== "reservation"
const view = ref("home"), d = ref(null), brief = ref(""), bookingId = ref(null), booking = ref(null), stamp = ref(0)
const site = useSiteBookings((id) => { bookingId.value = id })
const nav = computed(() => [
  { header: "هتل" },
  { key: "home", label: "امروز", icon: "dashboard", badge: d.value?.alerts.length || 0 },
  { key: "peak", label: "شلوغی", icon: "users" },
  { key: "grid", label: "جدول", icon: "calendar" },
  { key: "bookings", label: "رزروها", icon: "file", badge: site.waiting || 0 },
  { key: "rooms", label: "اتاق‌ها", icon: "bed", more: true },
  { key: "agencies", label: "آژانس‌ها", icon: "layers", more: true },
  { key: "site", label: "سایت هتل", icon: "sparkles", more: true },
  ...(front ? [{ key: "desk", label: "پایان روز", icon: "key", more: true }] : []),
  ...(manager ? [{ header: "مدیر" }, { key: "report", label: "گزارش", icon: "chart", more: true },
                 { key: "checks", label: "بررسی‌ها", icon: "shield", badge: d.value?.checks || 0, more: true },
                 { key: "settings", label: "قیمت‌ها", icon: "edit", more: true }] : []),
])
const TITLES = { home: "کارهای امروز", peak: "شلوغی امروز", grid: "جدول اتاق‌ها", bookings: "رزروها", rooms: "اتاق‌ها", agencies: "آژانس‌ها و سایت‌های رزرو",
                 site: "سایت هتل", desk: "پایان روز", report: "گزارش", checks: "بررسی‌ها", settings: "قیمت‌ها و قاعده‌ها" }
const load = async () => { d.value = await api("/hotel/today") }
const changed = () => { stamp.value++; load().catch(() => {}) }
onMounted(async () => {
  await retryable(load)
  if (!manager) return
  busy("hotel-brief", "دستیار در حال نوشتن خلاصه‌ی امروز")
  try { brief.value = (await api("/hotel/brief")).text } catch { brief.value = "خلاصه‌ی امروز آماده نشد." } finally { idle("hotel-brief") }
})
onUnmounted(() => idle("hotel-brief"))
const booked = (id) => { booking.value = null; changed(); bookingId.value = id }
</script>

<template>
  <AppLayout app="hotel" :brand="brand()" :chat="CHAT" :title="TITLES[view]" :subtitle="d ? fa(d.today_long + '، ' + d.today) : ''" :nav="nav" v-model="view"
             :tour="{ ...(manager ? HOTEL_MANAGER : HOTEL_DESK), ready: !!d && view === 'home' }">
    <div v-if="view !== 'site'" class="ht-actions" data-tour="ht-actions">
      <button class="btn primary" @click="booking = {}"><Icon name="calendar" :size="18" />رزرو جدید</button>
      <button class="btn" @click="booking = { paste: true }"><Icon name="message" :size="18" />رزرو از روی پیام</button>
    </div>

    <PeakView v-if="view === 'peak'" :key="'p' + stamp" @open="bookingId = $event" @changed="changed" />
    <GridView v-else-if="view === 'grid'" :key="'g' + stamp" @open="bookingId = $event" />
    <BookingsView v-else-if="view === 'bookings'" :key="'b' + stamp" @open="bookingId = $event" />
    <RoomsView v-else-if="view === 'rooms'" :key="'r' + stamp" @open="bookingId = $event" />
    <AgenciesView v-else-if="view === 'agencies'" :key="'a' + stamp" @changed="changed" />
    <SiteView v-else-if="view === 'site'" @open="bookingId = $event" />
    <DeskView v-else-if="view === 'desk'" :key="'d' + stamp" @changed="changed" />
    <ReportView v-else-if="view === 'report'" />
    <ChecksView v-else-if="view === 'checks'" :key="'c' + stamp" @open="bookingId = $event" />
    <SettingsView v-else-if="view === 'settings'" />
    <div v-else class="flex flex-col gap-6">
      <section v-if="manager" v-reveal class="card welcome brief" data-tour="ht-brief">
        <div class="welcome-text">
          <h2>روز بخیر، {{ hotelSession.user.full_name }}</h2>
          <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه‌ی امروز به قلم دستیار</div>
          <p v-if="brief"><TypeText :text="fa(brief)" /></p>
          <Skeleton v-else :lines="3" />
        </div>
        <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
      </section>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6" data-tour="ht-stats">
        <Skeleton v-if="!d" kind="stat" :count="4" />
        <div v-else v-for="s in d.stats" :key="s.key" v-reveal class="card stat stat-how" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span><span class="grow"></span><HowTip :lines="s.how" /></div>
          <div><div class="stat-money">{{ fa(s.value) }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ fa(s.sub) }}</div></div>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <section v-reveal :class="['card', 'col-span-12', manager ? 'xl:col-span-7' : '']" data-tour="ht-alerts">
          <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span>
            <span class="grow"></span><button v-if="d?.checks" class="btn ghost sm" @click="view = 'checks'"><Icon name="shield" :size="14" />{{ fa(d.checks) }} مورد در بررسی‌ها</button></div>
          <Skeleton v-if="!d" kind="row" :count="6" />
          <AlertList v-else :alerts="d.alerts" @open="bookingId = $event" @go="view = $event" @changed="changed" />
        </section>
        <div v-if="manager" class="col-span-12 xl:col-span-5 flex flex-col gap-6">
          <EventFeed endpoint="/hotel/events" data-tour="ht-feed" />
        </div>
      </div>
    </div>
    <BookingDrawer v-if="bookingId" :id="bookingId" @close="bookingId = null" @changed="changed" />
    <BookDialog v-if="booking" :preset="booking" @close="booking = null" @saved="booked" />
  </AppLayout>
</template>
