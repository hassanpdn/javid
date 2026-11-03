<script setup>
// The dental clinic's login: a drawing on one side, the people on the other; the shared page is components/kit/LoginPage.vue.
import { setDentalSession } from "../lib/api.js"
import { clinicInfo, ROLES } from "./lib.js"
import LoginPage from "../components/kit/LoginPage.vue"
import SlotsArt from "../components/kit/SlotsArt.vue"
const FLOATS = [
  { icon: "clock", tone: "danger", text: "نوبت فردا ساعت ۱۱ تأیید نشده", small: "پیام یادآوری آماده است", style: { top: "2%", right: 0 } },
  { icon: "users", tone: "info", text: "وقت خالی فردا ساعت ۱۷", small: "سه نفر در فهرست انتظار", style: { top: "44%", left: "-6%" } },
  { icon: "heart", tone: "success", text: "طرح درمان شروع‌نشده", small: "۳۵ روز بی‌تماس", style: { bottom: "2%", right: "8%" } },
]
</script>

<template>
  <LoginPage base="/dental" :set-session="setDentalSession" :info="clinicInfo" :business="clinicInfo.clinic" :roles="ROLES"
             kind="مطب دندان‌پزشکی" noun="مطب" letter="د" :floats="FLOATS">
    <template #art><SlotsArt /></template>
  </LoginPage>
</template>
