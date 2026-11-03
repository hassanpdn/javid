<script setup>
// Today's work as a list. Each line has the button its work needs: the reminder message for an unconfirmed
// appointment, booking the empty hour for someone on the waiting list, the follow-up message for a plan not started.
import { fa } from "../lib/api.js"
import Icon from "../components/Icon.vue"
defineProps({ alerts: Array })
const emit = defineEmits(["open", "book", "message", "changed"])
</script>

<template>
  <p v-if="!alerts.length" class="muted small">کار فوری‌ای نیست.</p>
  <ul v-else class="alerts">
    <li v-for="a in alerts" :key="a.type + a.title" class="alert k-alert">
      <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
      <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
      <div class="k-btns">
        <button v-if="a.type === 'unconfirmed' || a.type === 'noshow'" class="btn sm" @click="emit('message', { kind: 'reminder', appt_id: a.appt_id })">پیام یادآوری</button>
        <button v-if="a.type === 'slot'" class="btn sm" @click="emit('book', { date: a.date, time: a.time, fromWaitlist: true })">دادن به فهرست انتظار</button>
        <button v-if="a.type === 'plan'" class="btn sm" @click="emit('message', { kind: 'followup', plan_id: a.plan_id })">پیام پیگیری</button>
        <button v-if="a.patient_id" class="btn ghost sm" @click="emit('open', a.patient_id)">بیمار</button>
      </div>
    </li>
  </ul>
</template>
