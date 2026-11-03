<script setup>
// Today's work as a list. Each line has the button its work needs: the booking (to take the deposit, move the room,
// settle the bill), the move that closes an empty night, the request marked done, or the page where it is handled.
import { ref } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
defineProps({ alerts: Array })
const emit = defineEmits(["open", "go", "changed"])
const busy = ref("")
async function run(key, path, body, title) {
  busy.value = key
  try { await api(path, body); toast({ tone: "success", title }); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = "" }
}
const GO = { overbooked: ["grid", "جدول اتاق‌ها"], allotment: ["agencies", "آژانس‌ها"], waitlist: ["bookings", "فهرست انتظار"] }
</script>

<template>
  <p v-if="!alerts.length" class="muted small">کار فوری‌ای نیست.</p>
  <ul v-else class="alerts">
    <li v-for="a in alerts" :key="a.type + a.title" class="alert k-alert">
      <span :class="['tint', 't-' + a.tone]"><Icon :name="a.icon" :size="20" /></span>
      <div class="alert-body"><b>{{ fa(a.title) }}</b><small class="muted">{{ fa(a.detail) }}</small></div>
      <div class="k-btns">
        <button v-if="a.type === 'gap'" class="btn sm" :disabled="busy === a.title" @click="run(a.title, `/hotel/bookings/${a.booking_id}/room`, { room_id: a.room_id }, 'رزرو جابه‌جا شد')">جابه‌جا کن</button>
        <button v-if="a.type === 'task'" class="btn sm" :disabled="busy === a.title" @click="run(a.title, `/hotel/tasks/${a.task_id}/done`, {}, 'انجام شد')">انجام شد</button>
        <button v-if="GO[a.type]" class="btn sm" @click="emit('go', GO[a.type][0])">{{ GO[a.type][1] }}</button>
        <button v-if="a.booking_id" class="btn ghost sm" @click="emit('open', a.booking_id)">رزرو</button>
      </div>
    </li>
  </ul>
</template>
