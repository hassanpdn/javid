<script setup>
// The owner's dashboard: the assistant's morning summary, today's and this month's sales, money owed,
// next week's cheques, what needs doing today (each item opens where it is handled), and two weeks of sales.
import { ref, computed, onMounted, onUnmounted } from "vue"
import { api, fa, fabricSession } from "../lib/api.js"
import { busy, idle } from "../lib/notify.js"
import { brand, money } from "./lib.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import TypeText from "../components/TypeText.vue"
import AiOrb from "../components/AiOrb.vue"
import SalesChart from "./SalesChart.vue"
import CustomerDrawer from "./CustomerDrawer.vue"
import MoneyView from "./MoneyView.vue"
import StockView from "./StockView.vue"
import ExcelFiles from "./ExcelFiles.vue"
import { CHAT } from "./chat.js"

const view = ref("home"), d = ref(null), brief = ref(""), openId = ref(null), stockFilter = ref("")
const nav = computed(() => [
  { header: "پیشخوان" },
  { key: "home", label: "داشبورد", icon: "dashboard", badge: d.value?.alerts.length || 0 },
  { key: "money", label: "چک و طلب", icon: "calendar" },
  { key: "stock", label: "انبار", icon: "inbox" },
  { key: "files", label: "اکسل‌ها", icon: "file" },
])
const TITLES = { home: "داشبورد صاحب کار", money: "چک و طلب", stock: "انبار", files: "فایل‌های اکسل" }
const stats = computed(() => {
  const o = d.value
  const up = o.sales_month.amount - o.sales_prev.amount
  return [
    { label: "فروش امروز", value: money(o.sales_today.amount), sub: `${fa(o.sales_today.invoices)} فاکتور`, icon: "chart", tone: "primary" },
    { label: "فروش این ماه", value: money(o.sales_month.amount), sub: `${up >= 0 ? "بیشتر" : "کمتر"} از همین روزهای ماه قبل (${money(o.sales_prev.amount)})`, icon: "sparkles", tone: up >= 0 ? "success" : "warning" },
    { label: "طلب از مشتری‌ها", value: money(o.receivable), sub: `${fa(o.debtors)} مشتری بدهکار`, icon: "users", tone: "info", go: "money" },
    { label: `چک‌های ${fa(o.week.days)} روز آینده`, value: o.week.left < 0 ? "کسری " + money(-o.week.left) : "پول کافی است",
      sub: `پرداختی ${money(o.week.out_total)}، دریافتی ${money(o.week.in_total)}`, icon: "calendar", tone: o.week.left < 0 ? "danger" : "success", go: "money" },
  ]
})
const ACTION = { bounced: "کارت مشتری", limit: "کارت مشتری", quiet: "کارت مشتری", cash: "چک‌ها", low: "انبار", dead: "انبار" }
const act = (a) => {
  if (a.customer_id) openId.value = a.customer_id
  else if (a.type === "cash") view.value = "money"
  else { stockFilter.value = ""; view.value = "stock" }
}
onMounted(async () => {
  d.value = await api("/fabric/overview")
  busy("brief", "دستیار در حال نوشتن خلاصه‌ی امروز")
  try { brief.value = (await api("/fabric/brief")).text } catch { brief.value = "خلاصه‌ی امروز آماده نشد." }
  finally { idle("brief") }
})
onUnmounted(() => idle("brief"))
</script>

<template>
  <AppLayout app="fabric" :brand="brand()" :chat="CHAT.owner" :title="TITLES[view]" :subtitle="d ? fa(d.today) : ''" :nav="nav" v-model="view">
    <MoneyView v-if="view === 'money'" />
    <StockView v-else-if="view === 'stock'" :focus="stockFilter" />
    <ExcelFiles v-else-if="view === 'files'" />
    <div v-else class="flex flex-col gap-6">
      <section v-reveal class="card welcome brief">
        <div class="welcome-text">
          <h2>روز بخیر، {{ fabricSession.user.full_name }}</h2>
          <div class="flex items-center gap-2 text-primary font-bold text-sm"><Icon name="sparkles" :size="18" /> خلاصه‌ی امروز به قلم دستیار</div>
          <p v-if="brief"><TypeText :text="fa(brief)" /></p>
          <Skeleton v-else :lines="3" />
        </div>
        <div class="welcome-art"><AiOrb :size="150" :busy="!brief" /></div>
      </section>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6">
        <Skeleton v-if="!d" kind="stat" :count="4" />
        <component v-else :is="s.go ? 'button' : 'div'" v-for="s in stats" :key="s.label" v-reveal class="card stat" :style="{ '--c': 'var(--' + s.tone + ')' }" @click="s.go && (view = s.go)">
          <div class="stat-top"><span :class="['tint', 'lg', 't-' + s.tone]"><Icon :name="s.icon" :size="24" /></span></div>
          <div><div class="stat-money">{{ s.value }}</div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ s.sub }}</div></div>
        </component>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <section v-reveal class="card col-span-12 2xl:col-span-7">
          <div class="card-head">کارهای امروز <span v-if="d" class="count">{{ fa(d.alerts.length) }}</span></div>
          <Skeleton v-if="!d" kind="row" :count="5" />
          <ul v-else class="alerts">
            <li v-for="a in d.alerts" :key="a.type + a.title" class="alert">
              <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
              <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
              <button class="btn sm" @click="act(a)">{{ ACTION[a.type] }}</button>
            </li>
          </ul>
        </section>
        <div class="col-span-12 2xl:col-span-5 flex flex-col gap-6">
          <section v-reveal class="card flex flex-col">
            <div class="card-head"><span class="grow">فروش روزانه <small>میلیون تومان، دو هفته‌ی کاری اخیر</small></span></div>
            <SalesChart v-if="d" :points="d.trend" />
            <Skeleton v-else kind="chart" />
          </section>
          <section v-if="d" v-reveal class="card">
            <div class="card-head">پرفروش‌های این ماه</div>
            <ol class="fo-top">
              <li v-for="p in d.top.products" :key="p.code"><span class="grow">{{ p.title }}</span><b>{{ money(p.amount) }}</b></li>
            </ol>
          </section>
        </div>
      </div>

      <section v-if="d && d.notes.length" v-reveal class="card">
        <div class="card-head"><span class="grow">از فایل‌های اکسل</span><button class="btn ghost sm" @click="view = 'files'">دیدن فایل‌ها</button></div>
        <ul class="xf-notes"><li v-for="n in d.notes" :key="n"><Icon name="check" :size="16" />{{ fa(n) }}</li></ul>
      </section>
    </div>
    <CustomerDrawer v-if="openId" :id="openId" @close="openId = null" />
  </AppLayout>
</template>
