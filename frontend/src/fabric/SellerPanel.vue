<script setup>
// The seller's panel: the phone desk first, then the website's orders, the website itself, stock and files.
import { ref, computed, defineAsyncComponent } from "vue"
import { brand } from "./lib.js"
import { FABRIC_SELLER } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import OrderDesk from "./OrderDesk.vue"
import { CHAT } from "./chat.js"
import { useWebOrders } from "./webOrders.js"
// shown only when opened, so their code is downloaded only then
const StockView = defineAsyncComponent(() => import("./StockView.vue"))
const ExcelFiles = defineAsyncComponent(() => import("./ExcelFiles.vue"))
const ShopView = defineAsyncComponent(() => import("./ShopView.vue"))
const WebOrders = defineAsyncComponent(() => import("./WebOrders.vue"))

const view = ref("desk")
const web = useWebOrders(() => { view.value = "orders" })   // a toast and a badge when the website takes an order
const nav = computed(() => [
  { header: "فروش" },
  { key: "desk", label: "میز تلفن", icon: "message" },
  { key: "orders", label: "سفارش‌ها", icon: "inbox", badge: web.waiting },
  { key: "shop", label: "سایت", icon: "layers" },
  { key: "stock", label: "انبار", icon: "inbox", more: true },
  { key: "files", label: "اکسل‌ها", icon: "file", more: true },
])
const TITLES = { desk: "میز تلفن", orders: "سفارش‌های سایت", shop: "سایت فروشگاه از نگاه مشتری", stock: "انبار", files: "فایل‌های اکسل" }
</script>

<template>
  <AppLayout app="fabric" :brand="brand()" :chat="CHAT.seller" :title="TITLES[view]" subtitle="سفارش تلفنی، فاکتور و موجودی" :nav="nav" v-model="view" :tour="{ ...FABRIC_SELLER, ready: view === 'desk' }">
    <StockView v-if="view === 'stock'" />
    <WebOrders v-else-if="view === 'orders'" @shop="view = 'shop'" />
    <ShopView v-else-if="view === 'shop'" @orders="view = 'orders'" />
    <ExcelFiles v-else-if="view === 'files'" />
    <OrderDesk v-else @files="view = 'files'" />
  </AppLayout>
</template>
