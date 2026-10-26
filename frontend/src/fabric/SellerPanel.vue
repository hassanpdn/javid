<script setup>
// The seller's panel: the phone desk first, then the stock list and the Excel files.
import { ref, computed } from "vue"
import { brand } from "./lib.js"
import AppLayout from "../components/AppLayout.vue"
import OrderDesk from "./OrderDesk.vue"
import StockView from "./StockView.vue"
import ExcelFiles from "./ExcelFiles.vue"
import { CHAT } from "./chat.js"

const view = ref("desk")
const nav = computed(() => [
  { header: "فروش" },
  { key: "desk", label: "میز تلفن", icon: "message" },
  { key: "stock", label: "انبار", icon: "inbox" },
  { key: "files", label: "اکسل‌ها", icon: "file" },
])
const TITLES = { desk: "میز تلفن", stock: "انبار", files: "فایل‌های اکسل" }
</script>

<template>
  <AppLayout app="fabric" :brand="brand()" :chat="CHAT.seller" :title="TITLES[view]" subtitle="سفارش تلفنی، فاکتور و موجودی" :nav="nav" v-model="view">
    <StockView v-if="view === 'stock'" />
    <ExcelFiles v-else-if="view === 'files'" />
    <OrderDesk v-else @files="view = 'files'" />
  </AppLayout>
</template>
