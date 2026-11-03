<script setup>
// The eco-lodge host's panel. Home: what waits (requests, receipts, overdue deposits, guests arriving, messages,
// reviews, stays to ask about), the main numbers, the assistant's morning summary (host) and the live log. Then the
// calendar of every unit, the bookings, the units (make, edit, photos, switch off, close nights), reviews and
// feedback, guests and the website's words. «رزرو دستی» enters a booking that came by phone or WhatsApp; «دیدن سایت»
// opens the public website.
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { api, fa, lodgeSession, retryable } from "../lib/api.js"
import { busy, idle } from "../lib/notify.js"
import { brand, CHAT, lodgeInfo } from "./lib.js"
import { LODGE } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"
import EventFeed from "../fabric/EventFeed.vue"
import HowTip from "../fabric/HowTip.vue"
import SourceTip from "../components/SourceTip.vue"
import AlertList from "./AlertList.vue"
const CalendarView = defineAsyncComponent(() => import("./CalendarView.vue"))
const BookingsView = defineAsyncComponent(() => import("./BookingsView.vue"))
const UnitsView = defineAsyncComponent(() => import("./UnitsView.vue"))
const ReviewsView = defineAsyncComponent(() => import("./ReviewsView.vue"))
const GuestsView = defineAsyncComponent(() => import("./GuestsView.vue"))
const SiteView = defineAsyncComponent(() => import("./SiteView.vue"))
const BookingDrawer = defineAsyncComponent(() => import("./BookingDrawer.vue"))
const NewBooking = defineAsyncComponent(() => import("./NewBooking.vue"))

const host = lodgeSession.user.role === "host"
const view = ref("home"), d = ref(null), brief = ref(""), bookingId = ref(null), adding = ref(false), stamp = ref(0)
const count = (t) => d.value?.alerts.filter((a) => t.includes(a.type)).length || 0
const nav = computed(() => [
  { header: "اقامتگاه" },
  { key: "home", label: "امروز", icon: "dashboard", badge: d.value?.alerts.length || 0 },
  { key: "calendar", label: "تقویم", icon: "calendar" },
  { key: "bookings", label: "رزروها", icon: "file", badge: count(["request", "receipt"]) },
  { key: "units", label: "واحدها", icon: "bed" },
  { key: "reviews", label: "نظرها", icon: "heart", badge: count(["review", "feedback"]), more: true },
  { key: "guests", label: "مهمانان", icon: "users", more: true },
  { key: "site", label: "متن سایت", icon: "edit", more: true },
])
const TITLES = { home: "کارهای امروز", calendar: "تقویم واحدها", bookings: "رزروها", units: "واحدها", reviews: "نظرها و بازخورد", guests: "مهمانان", site: "متن سایت و قاعده‌ها" }
const load = async () => { d.value = await api("/lodge/today") }
const changed = () => { stamp.value++; load().catch(() => {}) }
onMounted(async () => {
  await retryable(load)
  if (!host) return
  busy("lodge-brief", "دستیار در حال نوشتن خلاصه‌ی امروز")
  try { brief.value = (await api("/lodge/brief")).text } catch { brief.value = "خلاصه‌ی امروز آماده نشد." } finally { idle("lodge-brief") }
})
onUnmounted(() => idle("lodge-brief"))
const added = (id) => { adding.value = false; changed(); bookingId.value = id }
</script>

<template>
  <AppLayout app="lodge" :brand="brand()" :chat="CHAT" :title="TITLES[view]" :subtitle="d ? fa(d.today_long + '، ' + d.today) : ''" :nav="nav" v-model="view"
             :tour="{ ...LODGE, ready: !!d && view === 'home' }">
    <div class="lo-actions" data-tour="lo-actions">
      <button class="btn primary" @click="adding = true"><Icon name="message" :size="18" />رزرو دستی</button>
      <a class="btn" :href="lodgeInfo.site_url" target="_blank" rel="noopener"><Icon name="sparkles" :size="18" />دیدن سایت</a>
    </div>

    <CalendarView v-if="view === 'calendar'" :key="'c' + stamp" @open="bookingId = $event" />
    <BookingsView v-else-if="view === 'bookings'" :key="'b' + stamp" @open="bookingId = $event" />
    <UnitsView v-else-if="view === 'units'" :key="'u' + stamp" @changed="changed" />
    <ReviewsView v-else-if="view === 'reviews'" :key="'r' + stamp" @open="bookingId = $event" @changed="changed" />
    <GuestsView v-else-if="view === 'guests'" />
    <SiteView v-else-if="view === 'site'" />
    <div v-else class="flex flex-col gap-6">
      <section v-if="host" v-reveal class="card welcome brief" data-tour="lo-brief">
        <div class="welcome-text">
          <h2>روز بخیر، {{ lodgeSession.user.full_name }}</h2>
          <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه‌ی امروز به قلم دستیار</div>
          <p v-if="brief"><TypeText :text="fa(brief)" /></p>
          <Skeleton v-else :lines="3" />
        </div>
        <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
      </section>
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6" data-tour="lo-stats">
        <Skeleton v-if="!d" kind="stat" :count="4" />
        <div v-else v-for="(s, i) in d.stats" :key="s.key" v-reveal class="card stat stat-how" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span><span class="grow"></span><HowTip :lines="s.how" /><SourceTip app="lodge" :k="'stat.' + i" /></div>
          <div><div class="stat-money">{{ fa(s.value) }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ fa(s.sub) }}</div></div>
        </div>
      </div>
      <div class="grid grid-cols-12 gap-6">
        <section v-reveal class="card col-span-12 xl:col-span-7" data-tour="lo-alerts">
          <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span><SourceTip app="lodge" k="alerts" /></div>
          <Skeleton v-if="!d" kind="row" :count="6" />
          <AlertList v-else :alerts="d.alerts" @open="bookingId = $event" @changed="changed" />
        </section>
        <div class="col-span-12 xl:col-span-5 flex flex-col gap-6"><EventFeed endpoint="/lodge/events" data-tour="lo-feed" /></div>
      </div>
    </div>
    <BookingDrawer v-if="bookingId" :id="bookingId" @close="bookingId = null" @changed="changed" />
    <NewBooking v-if="adding" @close="adding = false" @saved="added" />
  </AppLayout>
</template>
