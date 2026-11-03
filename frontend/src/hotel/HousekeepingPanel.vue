<script setup>
// Housekeeping's panel, made for a phone: the rooms in the order to do them (RoomsView) and guests' open requests.
// Nothing about prices, guests' phones or bookings.
import { ref, computed, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { brand, CHAT } from "./lib.js"
import { HOTEL_ROOMS } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Skeleton from "../components/Skeleton.vue"
import RoomsView from "./RoomsView.vue"

const view = ref("rooms"), tasks = ref(null), stamp = ref(0)
const load = async () => { tasks.value = await api("/hotel/tasks") }
onMounted(() => retryable(load))
const nav = computed(() => [{ header: "خانه‌داری" }, { key: "rooms", label: "اتاق‌ها", icon: "bed" },
                            { key: "tasks", label: "درخواست‌ها", icon: "message", badge: tasks.value?.length || 0 }])
async function done(k) {
  try { await api(`/hotel/tasks/${k.id}/done`, {}); toast({ tone: "success", title: "انجام شد" }); await load(); stamp.value++ } catch (e) { toast({ tone: "danger", title: e.message }) }
}
</script>

<template>
  <AppLayout app="hotel" :brand="brand()" :chat="CHAT" :title="view === 'rooms' ? 'اتاق‌ها' : 'درخواست‌های باز'" :nav="nav" v-model="view" :tour="{ ...HOTEL_ROOMS, ready: !!tasks }">
    <RoomsView v-if="view === 'rooms'" :key="stamp" />
    <section v-else class="card flex flex-col gap-2">
      <Skeleton v-if="!tasks" kind="row" :count="4" />
      <p v-else-if="!tasks.length" class="muted small">درخواست بازی نیست.</p>
      <ul v-else class="k-mini"><li v-for="k in tasks" :key="k.id"><div class="k-row-top"><b>اتاق {{ fa(k.room) }}</b><span :class="['tag', k.kind === 'repair' ? 'k-t-secondary' : 'k-t-warning']">{{ k.kind === 'repair' ? 'تعمیر' : 'درخواست مهمان' }}</span></div>
        <span>{{ k.text }}</span><small class="muted">{{ fa(k.day) }} ساعت {{ fa(k.time) }}</small>
        <button class="btn primary sm" style="align-self: flex-start" @click="done(k)">انجام شد</button></li></ul>
    </section>
  </AppLayout>
</template>
