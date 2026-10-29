<script setup>
// The accountant's panel: cheques and debts first, then customers' cards and the Excel files.
import { ref, computed, watch, defineAsyncComponent } from "vue"
import { api, fa } from "../lib/api.js"
import { brand, money } from "./lib.js"
import { FABRIC_ACCOUNTANT } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Avatar from "../components/Avatar.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import MoneyView from "./MoneyView.vue"
import { CHAT } from "./chat.js"
// shown only when opened, so their code is downloaded only then
const ExcelFiles = defineAsyncComponent(() => import("./ExcelFiles.vue"))
const ReconcileView = defineAsyncComponent(() => import("./ReconcileView.vue"))
const ReportView = defineAsyncComponent(() => import("./ReportView.vue"))
const CustomerDrawer = defineAsyncComponent(() => import("./CustomerDrawer.vue"))

const view = ref("money"), q = ref(""), list = ref(null), openId = ref(null)
const nav = computed(() => [
  { header: "حساب‌ها" },
  { key: "money", label: "چک و طلب", icon: "calendar" },
  { key: "check", label: "تطبیق", icon: "shield" },
  { key: "report", label: "گزارش", icon: "chart" },
  { key: "customers", label: "مشتری‌ها", icon: "users", more: true },
  { key: "files", label: "اکسل‌ها", icon: "file", more: true },
])
const TITLES = { money: "چک و طلب", check: "تطبیق سه فایل", report: "گزارش", customers: "مشتری‌ها", files: "فایل‌های اکسل" }
const load = async () => { list.value = await api("/fabric/customers?q=" + encodeURIComponent(q.value)) }
let timer
watch(q, () => { clearTimeout(timer); timer = setTimeout(load, 250) })
watch(view, (v) => { if (v === "customers" && !list.value) load() })
</script>

<template>
  <AppLayout app="fabric" :brand="brand()" :chat="CHAT.accountant" :title="TITLES[view]" subtitle="چک‌ها، طلب‌ها و یادآوری" :nav="nav" v-model="view" :tour="{ ...FABRIC_ACCOUNTANT, ready: view === 'money' }">
    <ExcelFiles v-if="view === 'files'" />
    <ReconcileView v-else-if="view === 'check'" />
    <ReportView v-else-if="view === 'report'" />
    <section v-else-if="view === 'customers'" class="card">
      <label class="fs-search"><Icon name="search" :size="18" />
        <input v-model="q" class="search" placeholder="نام، فروشگاه یا شهر" aria-label="جستجوی مشتری"></label>
      <Skeleton v-if="!list" kind="row" round :count="6" />
      <ul v-else class="fm-debtors">
        <li v-for="c in list" :key="c.id">
          <button class="fm-who fm-who-row" @click="openId = c.id"><Avatar :name="c.name" :size="36" />
            <span><b>{{ c.name }}</b><small class="muted">{{ c.shop }} · {{ c.city }}</small></span></button>
          <span class="fm-amount"><b>{{ money(c.debt) }}</b>
            <small v-if="c.bounced" class="t-bad">چک برگشتی</small>
            <small v-else-if="c.room < 0" class="t-warn">بیش از سقف</small>
            <small v-else class="muted">بدهی</small></span>
        </li>
      </ul>
    </section>
    <MoneyView v-else />
    <CustomerDrawer v-if="openId" :id="openId" @close="openId = null" />
  </AppLayout>
</template>
