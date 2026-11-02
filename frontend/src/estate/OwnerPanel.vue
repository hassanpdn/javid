<script setup>
// The agency owner's panel. Home: the assistant's morning summary, the main numbers (each with «از کجا؟»), today's
// work, the team this month and the live log. Then listings, buyers, visits, deals, the checks, the website and settings.
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { api, fa, estateSession, retryable } from "../lib/api.js"
import { busy, idle } from "../lib/notify.js"
import { brand, money, CHAT, useLeads } from "./lib.js"
import { ESTATE_OWNER } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"
import EventFeed from "../fabric/EventFeed.vue"
import HowTip from "../fabric/HowTip.vue"
import AlertList from "./AlertList.vue"
// shown only when opened, so their code is downloaded only then
const ListingsView = defineAsyncComponent(() => import("./ListingsView.vue"))
const RequestsView = defineAsyncComponent(() => import("./RequestsView.vue"))
const VisitsView = defineAsyncComponent(() => import("./VisitsView.vue"))
const DealsView = defineAsyncComponent(() => import("./DealsView.vue"))
const ChecksView = defineAsyncComponent(() => import("./ChecksView.vue"))
const SiteView = defineAsyncComponent(() => import("./SiteView.vue"))
const SettingsView = defineAsyncComponent(() => import("./SettingsView.vue"))
const ListingDrawer = defineAsyncComponent(() => import("./ListingDrawer.vue"))
const RequestDrawer = defineAsyncComponent(() => import("./RequestDrawer.vue"))
const VisitDialog = defineAsyncComponent(() => import("./VisitDialog.vue"))

const view = ref("home"), d = ref(null), brief = ref(""), listingId = ref(null), requestId = ref(null), visit = ref(null)
const leads = useLeads((id) => { requestId.value = id })
const nav = computed(() => [
  { header: "پیشخوان" },
  { key: "home", label: "داشبورد", icon: "dashboard", badge: d.value?.alerts.length || 0 },
  { key: "listings", label: "فایل‌ها", icon: "file" },
  { key: "requests", label: "متقاضیان", icon: "users", badge: leads.waiting },
  { key: "visits", label: "بازدیدها", icon: "calendar" },
  { key: "deals", label: "معامله‌ها", icon: "check", more: true },
  { key: "checks", label: "بررسی‌ها", icon: "shield", badge: d.value?.checks || 0, more: true },
  { header: "سایت" },
  { key: "site", label: "سایت بنگاه", icon: "message", more: true },
  { key: "settings", label: "تنظیمات", icon: "edit", more: true },
])
const TITLES = { home: "داشبورد مدیر بنگاه", listings: "فایل‌ها", requests: "متقاضیان", visits: "بازدیدها", deals: "معامله‌ها", checks: "بررسی‌ها",
                 site: "سایت بنگاه از نگاه مشتری", settings: "تنظیمات" }
const load = async () => { d.value = await api("/estate/overview") }
const changed = () => { load().catch(() => {}) }
onMounted(async () => {
  await retryable(load)
  busy("brief", "دستیار در حال نوشتن خلاصه‌ی امروز")
  try { brief.value = (await api("/estate/brief")).text } catch { brief.value = "خلاصه‌ی امروز آماده نشد." }
  finally { idle("brief") }
})
onUnmounted(() => idle("brief"))
</script>

<template>
  <AppLayout app="estate" :brand="brand()" :chat="CHAT.owner" :title="TITLES[view]" :subtitle="d ? fa(d.today) : ''" :nav="nav" v-model="view"
             :tour="{ ...ESTATE_OWNER, ready: !!d && view === 'home' }">
    <ListingsView v-if="view === 'listings'" @open="listingId = $event" />
    <RequestsView v-else-if="view === 'requests'" @open="requestId = $event" />
    <VisitsView v-else-if="view === 'visits'" @listing="listingId = $event" @request="requestId = $event" />
    <DealsView v-else-if="view === 'deals'" @listing="listingId = $event" />
    <ChecksView v-else-if="view === 'checks'" @listing="listingId = $event" @request="requestId = $event" />
    <SiteView v-else-if="view === 'site'" @request="requestId = $event" />
    <SettingsView v-else-if="view === 'settings'" />
    <div v-else class="flex flex-col gap-6">
      <section v-reveal class="card welcome brief" data-tour="eo-brief">
        <div class="welcome-text">
          <h2>روز بخیر، {{ estateSession.user.full_name }}</h2>
          <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه‌ی امروز به قلم دستیار</div>
          <p v-if="brief"><TypeText :text="fa(brief)" /></p>
          <Skeleton v-else :lines="3" />
        </div>
        <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
      </section>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6" data-tour="eo-stats">
        <Skeleton v-if="!d" kind="stat" :count="4" />
        <div v-else v-for="s in d.stats" :key="s.label" v-reveal class="card stat stat-how" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span><span class="grow"></span><HowTip :lines="s.how" /></div>
          <div><div class="stat-money">{{ fa(s.value) }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ fa(s.sub) }}</div></div>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <section v-reveal class="card col-span-12 xl:col-span-7" data-tour="eo-alerts">
          <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span>
            <span class="grow"></span><button v-if="d?.checks" class="btn ghost sm" @click="view = 'checks'"><Icon name="shield" :size="14" />{{ fa(d.checks) }} مورد در بررسی‌ها</button></div>
          <Skeleton v-if="!d" kind="row" :count="5" />
          <AlertList v-else :alerts="d.alerts" @listing="listingId = $event" @visit="visit = $event" />
        </section>
        <div class="col-span-12 xl:col-span-5 flex flex-col gap-6">
          <section v-reveal class="card" data-tour="eo-team">
            <div class="card-head">تیم در {{ d?.month }}</div>
            <Skeleton v-if="!d" kind="row" :count="3" />
            <ul v-else class="es-team">
              <li v-for="m in d.team" :key="m.id">
                <b>{{ m.name }}</b>
                <span class="es-team-nums"><span>{{ fa(m.listings) }} فایل</span><span>{{ fa(m.requests) }} متقاضی</span><span>{{ fa(m.visits) }} بازدید</span><span>{{ fa(m.deals) }} معامله</span></span>
                <small class="muted">سهم کمیسیون: {{ money(m.fee) }}</small>
              </li>
            </ul>
          </section>
          <EventFeed endpoint="/estate/events" data-tour="eo-feed" />
        </div>
      </div>
    </div>
    <ListingDrawer v-if="listingId" :id="listingId" @close="listingId = null" @changed="changed" @request="requestId = $event; listingId = null" />
    <RequestDrawer v-if="requestId" :id="requestId" @close="requestId = null" @changed="changed" @listing="listingId = $event; requestId = null" />
    <VisitDialog v-if="visit" :visit-id="visit.visit_id" :title="visit.title" @close="visit = null" @done="visit = null; changed()" />
  </AppLayout>
</template>
