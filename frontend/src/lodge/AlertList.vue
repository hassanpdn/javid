<script setup>
// What waits for the host, most urgent first. A request and a receipt can be answered right here; everything else
// opens its booking.
import { ref } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
defineProps({ alerts: Array })
const emit = defineEmits(["open", "changed"])
const busy = ref(0)
async function run(a, path, title) {
  busy.value = a.booking_id
  try { await api(path, {}); toast({ tone: "success", title }); emit("changed") } catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = 0 }
}
</script>

<template>
  <p v-if="!alerts.length" class="muted small">کار فوری‌ای نیست.</p>
  <ul v-else class="alerts">
    <li v-for="a in alerts" :key="a.type + a.title" class="alert lo-alert">
      <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
      <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
      <div class="lo-btns">
        <button v-if="a.type === 'request'" class="btn sm" :disabled="busy === a.booking_id" @click="run(a, `/lodge/bookings/${a.booking_id}/approve`, 'تأیید شد؛ مهمان بیعانه را می‌فرستد')">تأیید</button>
        <button class="btn ghost sm" @click="emit('open', a.booking_id)">{{ a.type === 'receipt' ? 'دیدن رسید' : a.type === 'feedback' ? 'پیام نظرخواهی' : 'رزرو' }}</button>
      </div>
    </li>
  </ul>
</template>
