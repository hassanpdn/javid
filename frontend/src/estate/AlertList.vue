<script setup>
// Today's work as a list: each line says what needs doing and its button opens the place to do it
// (the listing, the buyer, or the visit's messages). Shared by the owner's and the agents' home pages.
import { fa } from "../lib/api.js"
import Icon from "../components/Icon.vue"

defineProps({ alerts: Array })
const emit = defineEmits(["listing", "request", "visit"])
const LABEL = { missed: "پیشنهاد به متقاضی", new_match: "دیدن تطبیق", visit: "پیام‌ها و تأیید", stale: "تماس با مالک", report: "گزارش برای مالک",
                price: "دیدن قیمت", duplicate: "مقایسه‌ی دو فایل" }
const act = (a) => a.type === "visit" ? emit("visit", a) : emit("listing", a.listing_id)
</script>

<template>
  <p v-if="!alerts.length" class="muted small">کار فوری‌ای نیست.</p>
  <ul v-else class="alerts">
    <li v-for="a in alerts" :key="a.type + a.title" class="alert es-alert">
      <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
      <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
      <button class="btn sm" @click="act(a)">{{ LABEL[a.type] }}</button>
    </li>
  </ul>
</template>
