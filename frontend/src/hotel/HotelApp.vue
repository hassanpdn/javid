<script setup>
// The hotel's root: its setup form (first run, or when asked for), its login, or the panel.
import { onMounted, watch, defineAsyncComponent } from "vue"
import { api, hotelSession, clearHotelSession, lockScroll } from "../lib/api.js"
import { hotelInfo, loadHotel } from "./lib.js"
const HotelSetup = defineAsyncComponent(() => import("./HotelSetup.vue"))
const HotelLogin = defineAsyncComponent(() => import("./HotelLogin.vue"))
const HotelPanel = defineAsyncComponent(() => import("./HotelPanel.vue"))
const HousekeepingPanel = defineAsyncComponent(() => import("./HousekeepingPanel.vue"))

onMounted(async () => {
  try { await loadHotel() } catch { hotelInfo.loaded = true }
  if (hotelInfo.set_up && hotelSession.token && !hotelSession.user) {
    try { hotelSession.user = await api("/hotel/me") } catch { clearHotelSession() }
  }
})
watch(() => hotelSession.user, () => lockScroll(false))
</script>

<template>
  <template v-if="!hotelInfo.loaded"></template>
  <HotelSetup v-else-if="!hotelSession.user && (!hotelInfo.set_up || hotelInfo.setupOpen)" />
  <HotelLogin v-else-if="!hotelSession.user" />
  <HousekeepingPanel v-else-if="hotelSession.user.role === 'housekeeping'" :key="'h' + hotelSession.user.id" />
  <HotelPanel v-else :key="hotelSession.user.id" />
</template>
