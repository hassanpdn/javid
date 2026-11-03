<script setup>
// The eco-lodge's login: a drawing on one side, the people on the other; the shared page is components/kit/LoginPage.vue.
import { setLodgeSession } from "../lib/api.js"
import { lodgeInfo, ROLES } from "./lib.js"
import LoginPage from "../components/kit/LoginPage.vue"
import SlotsArt from "../components/kit/SlotsArt.vue"
const FLOATS = [
  { icon: "clock", tone: "danger", text: "درخواست رزرو از سایت", small: "گنبد آبی، دو شب", style: { top: "2%", right: 0 } },
  { icon: "users", tone: "info", text: "رسید بیعانه رسید", small: "یک کلیک تا قطعی شدن", style: { top: "44%", left: "-6%" } },
  { icon: "heart", tone: "success", text: "نظر جدید: ۵ ستاره", small: "پیش از نمایش در سایت", style: { bottom: "2%", right: "8%" } },
]
</script>

<template>
  <LoginPage base="/lodge" :set-session="setLodgeSession" :info="lodgeInfo" :business="lodgeInfo.lodge" :roles="ROLES"
             kind="اقامتگاه بوم‌گردی" noun="اقامتگاه" letter="ب" :floats="FLOATS">
    <template #art><SlotsArt /></template>
  </LoginPage>
</template>
