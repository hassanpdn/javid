<script setup>
// An agent's panel. Home: today's and tomorrow's visits, today's work on their own listings and buyers (new matches,
// missed ones, owners to call or report to), and the deposit and rent tool. Then listings, buyers, visits, deals and the
// agency's website.
import { ref, computed, onMounted, defineAsyncComponent } from "vue"
import { api, fa, estateSession, retryable } from "../lib/api.js"
import { brand, CHAT, useLeads } from "./lib.js"
import { ESTATE_AGENT } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import AlertList from "./AlertList.vue"
import Converter from "./Converter.vue"
const ListingsView = defineAsyncComponent(() => import("./ListingsView.vue"))
const RequestsView = defineAsyncComponent(() => import("./RequestsView.vue"))
const VisitsView = defineAsyncComponent(() => import("./VisitsView.vue"))
const DealsView = defineAsyncComponent(() => import("./DealsView.vue"))
const SiteView = defineAsyncComponent(() => import("./SiteView.vue"))
const ListingDrawer = defineAsyncComponent(() => import("./ListingDrawer.vue"))
const RequestDrawer = defineAsyncComponent(() => import("./RequestDrawer.vue"))
const VisitDialog = defineAsyncComponent(() => import("./VisitDialog.vue"))

const view = ref("home"), d = ref(null), listingId = ref(null), requestId = ref(null), visit = ref(null)
const leads = useLeads((id) => { requestId.value = id })
const nav = computed(() => [
  { header: "کار من" },
  { key: "home", label: "امروز", icon: "dashboard", badge: d.value?.alerts.length || 0 },
  { key: "listings", label: "فایل‌ها", icon: "file" },
  { key: "requests", label: "متقاضیان", icon: "users", badge: leads.waiting },
  { key: "visits", label: "بازدیدها", icon: "calendar" },
  { key: "deals", label: "معامله‌ها", icon: "check", more: true },
  { header: "سایت" },
  { key: "site", label: "سایت بنگاه", icon: "message", more: true },
])
const TITLES = { home: "کارهای امروز", listings: "فایل‌ها", requests: "متقاضیان", visits: "بازدیدها", deals: "معامله‌ها", site: "سایت بنگاه از نگاه مشتری" }
const load = async () => { d.value = await api("/estate/today") }
const changed = () => { load().catch(() => {}) }
onMounted(() => retryable(load))
</script>

<template>
  <AppLayout app="estate" :brand="brand()" :chat="CHAT.agent" :title="TITLES[view]" :subtitle="d ? fa(d.today) : ''" :nav="nav" v-model="view"
             :tour="{ ...ESTATE_AGENT, ready: !!d && view === 'home' }">
    <ListingsView v-if="view === 'listings'" @open="listingId = $event" />
    <RequestsView v-else-if="view === 'requests'" @open="requestId = $event" />
    <VisitsView v-else-if="view === 'visits'" @listing="listingId = $event" @request="requestId = $event" />
    <DealsView v-else-if="view === 'deals'" @listing="listingId = $event" />
    <SiteView v-else-if="view === 'site'" @request="requestId = $event" />
    <div v-else class="grid grid-cols-12 gap-6">
      <section v-reveal class="card col-span-12 es-hello" data-tour="ea-hello">
        <div class="grow"><h2>روز بخیر، {{ estateSession.user.full_name }}</h2>
          <p v-if="d" class="muted">{{ fa(d.mine.listings) }} فایل فعال و {{ fa(d.mine.requests) }} متقاضی در جستجو دارید.</p></div>
        <div class="btn-row"><button class="btn" @click="view = 'listings'"><Icon name="plus" :size="16" />فایل جدید</button>
          <button class="btn" @click="view = 'requests'"><Icon name="plus" :size="16" />متقاضی جدید</button></div>
      </section>
      <section v-reveal class="card col-span-12 xl:col-span-7" data-tour="ea-alerts">
        <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span></div>
        <Skeleton v-if="!d" kind="row" :count="4" />
        <AlertList v-else :alerts="d.alerts" @listing="listingId = $event" @visit="visit = $event" />
      </section>
      <div class="col-span-12 xl:col-span-5 flex flex-col gap-6">
        <section v-reveal class="card" data-tour="ea-visits">
          <div class="card-head"><span class="grow">بازدیدهای امروز و فردا</span><button class="btn ghost sm" @click="view = 'visits'">همه</button></div>
          <Skeleton v-if="!d" kind="row" :count="2" />
          <p v-else-if="!d.visits.length" class="muted small">بازدیدی ندارید.</p>
          <ul v-else class="es-mini">
            <li v-for="v in d.visits" :key="v.id"><b>{{ fa(v.when) }}</b><span>{{ v.name }} · فایل {{ fa(v.listing_id) }}، {{ fa(v.area) }} متر {{ v.street || v.hood }}</span>
              <button v-if="v.status === 'booked'" class="link small" @click="visit = { visit_id: v.id, title: v.name }">تأیید نشده؛ پیام‌ها</button></li>
          </ul>
        </section>
        <Converter data-tour="ea-convert" />
      </div>
    </div>
    <ListingDrawer v-if="listingId" :id="listingId" @close="listingId = null" @changed="changed" @request="requestId = $event; listingId = null" />
    <RequestDrawer v-if="requestId" :id="requestId" @close="requestId = null" @changed="changed" @listing="listingId = $event; requestId = null" />
    <VisitDialog v-if="visit" :visit-id="visit.visit_id" :title="visit.title" @close="visit = null" @done="visit = null; changed()" />
  </AppLayout>
</template>
