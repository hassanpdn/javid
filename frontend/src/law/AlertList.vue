<script setup>
// Today's work as a list; each line's button opens its case.
import { fa } from "../lib/api.js"
import Icon from "../components/Icon.vue"
defineProps({ alerts: Array })
const emit = defineEmits(["open"])
const LABEL = { overdue: "پرونده", deadline: "پرونده", hearing: "پرونده", idle: "پرونده", report: "گزارش به موکل" }
</script>

<template>
  <p v-if="!alerts.length" class="muted small">کار فوری‌ای نیست.</p>
  <ul v-else class="alerts">
    <li v-for="a in alerts" :key="a.type + a.title" class="alert lw-alert">
      <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
      <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
      <button class="btn sm" @click="emit('open', a.case_id)">{{ LABEL[a.type] }}</button>
    </li>
  </ul>
</template>
