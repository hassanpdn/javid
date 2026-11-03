<script setup>
// The law office's panel, one for all three roles. Home: today's work (deadlines passed or near, hearings, idle cases,
// clients waiting for news), the main numbers, and for the lawyer the assistant's morning summary, the team and the
// live log. Then the deadlines, the cases, and for the lawyer the checks and the settings. «ثبت ابلاغیه» reads a
// pasted notice; «پرونده‌ی جدید» opens a case. The associate's home shows only their own cases.
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { api, fa, lawSession, retryable } from "../lib/api.js"
import { busy, idle } from "../lib/notify.js"
import { brand, CHAT } from "./lib.js"
import { LAW_OWNER, LAW_STAFF } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"
import EventFeed from "../fabric/EventFeed.vue"
import HowTip from "../fabric/HowTip.vue"
import SourceTip from "../components/SourceTip.vue"
import AlertList from "./AlertList.vue"
const DeadlinesView = defineAsyncComponent(() => import("./DeadlinesView.vue"))
const CasesView = defineAsyncComponent(() => import("./CasesView.vue"))
const ChecksView = defineAsyncComponent(() => import("./ChecksView.vue"))
const SettingsView = defineAsyncComponent(() => import("./SettingsView.vue"))
const CaseDrawer = defineAsyncComponent(() => import("./CaseDrawer.vue"))
const NoticeDialog = defineAsyncComponent(() => import("./NoticeDialog.vue"))
const CaseDialog = defineAsyncComponent(() => import("./CaseDialog.vue"))

const owner = lawSession.user.role === "owner"
const view = ref("home"), d = ref(null), o = ref(null), brief = ref(""), caseId = ref(null), adding = ref(false), opening = ref(false), stamp = ref(0)
const nav = computed(() => [
  { header: "دفتر" },
  { key: "home", label: "امروز", icon: "dashboard", badge: d.value?.alerts.length || 0 },
  { key: "deadlines", label: "مهلت‌ها", icon: "clock" },
  { key: "cases", label: "پرونده‌ها", icon: "file" },
  ...(owner ? [{ key: "checks", label: "بررسی‌ها", icon: "shield", badge: o.value?.checks || 0, more: true }, { key: "settings", label: "تنظیمات", icon: "edit", more: true }] : []),
])
const TITLES = { home: "کارهای امروز", deadlines: "مهلت‌ها و جلسه‌ها", cases: "پرونده‌ها", checks: "بررسی‌ها", settings: "مهلت‌ها و تعطیلات" }
const load = async () => {
  d.value = await api("/law/today")
  if (owner) o.value = await api("/law/overview")
}
const changed = () => { stamp.value++; load().catch(() => {}) }
onMounted(async () => {
  await retryable(load)
  if (!owner) return
  busy("law-brief", "دستیار در حال نوشتن خلاصه‌ی امروز")
  try { brief.value = (await api("/law/brief")).text } catch { brief.value = "خلاصه‌ی امروز آماده نشد." } finally { idle("law-brief") }
})
onUnmounted(() => idle("law-brief"))
const saved = (cid) => { adding.value = false; opening.value = false; changed(); caseId.value = cid }
</script>

<template>
  <AppLayout app="law" :brand="brand()" :chat="CHAT" :title="TITLES[view]" :subtitle="d ? fa(d.today_long + '، ' + d.today) : ''" :nav="nav" v-model="view"
             :tour="{ ...(owner ? LAW_OWNER : LAW_STAFF), ready: !!d && view === 'home' }">
    <div class="lw-actions" data-tour="lw-actions">
      <button class="btn primary" @click="adding = true"><Icon name="mail" :size="18" />ثبت ابلاغیه</button>
      <button class="btn" @click="opening = true"><Icon name="plus" :size="18" />پرونده‌ی جدید</button>
    </div>

    <DeadlinesView v-if="view === 'deadlines'" :key="stamp" @open="caseId = $event" />
    <CasesView v-else-if="view === 'cases'" :key="stamp" @open="caseId = $event" />
    <ChecksView v-else-if="view === 'checks'" :key="stamp" @open="caseId = $event" />
    <SettingsView v-else-if="view === 'settings'" />
    <div v-else class="flex flex-col gap-6">
      <section v-if="owner" v-reveal class="card welcome brief" data-tour="lw-brief">
        <div class="welcome-text">
          <h2>روز بخیر، {{ lawSession.user.full_name }}</h2>
          <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه‌ی امروز به قلم دستیار</div>
          <p v-if="brief"><TypeText :text="fa(brief)" /></p>
          <Skeleton v-else :lines="3" />
        </div>
        <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
      </section>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6" data-tour="lw-stats">
        <Skeleton v-if="!d" kind="stat" :count="4" />
        <div v-else v-for="(s, i) in d.stats" :key="s.label" v-reveal class="card stat stat-how" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span><span class="grow"></span><HowTip :lines="s.how" /><SourceTip app="law" :k="'stat.' + i" /></div>
          <div><div class="stat-money">{{ fa(s.value) }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ fa(s.sub) }}</div></div>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <section v-reveal :class="['card', 'col-span-12', owner ? 'xl:col-span-7' : '']" data-tour="lw-alerts">
          <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span><SourceTip app="law" k="alerts" />
            <span class="grow"></span><button v-if="o?.checks" class="btn ghost sm" @click="view = 'checks'"><Icon name="shield" :size="14" />{{ fa(o.checks) }} مورد در بررسی‌ها</button></div>
          <Skeleton v-if="!d" kind="row" :count="5" />
          <AlertList v-else :alerts="d.alerts" @open="caseId = $event" />
        </section>
        <div v-if="owner" class="col-span-12 xl:col-span-5 flex flex-col gap-6">
          <section v-reveal class="card" data-tour="lw-team">
            <div class="card-head">وکلای دفتر</div>
            <Skeleton v-if="!o" kind="row" :count="2" />
            <ul v-else class="lw-team">
              <li v-for="m in o.team" :key="m.id"><b>{{ m.name }}</b><span>{{ fa(m.cases) }} پرونده‌ی باز · {{ fa(m.due) }} مهلت در این هفته</span></li>
            </ul>
          </section>
          <EventFeed endpoint="/law/events" data-tour="lw-feed" />
        </div>
      </div>
    </div>
    <CaseDrawer v-if="caseId" :id="caseId" @close="caseId = null" @changed="changed" />
    <NoticeDialog v-if="adding" @close="adding = false" @saved="saved" />
    <CaseDialog v-if="opening" @close="opening = false" @saved="saved" />
  </AppLayout>
</template>
