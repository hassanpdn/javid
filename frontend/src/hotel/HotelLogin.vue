<script setup>
// The hotel's login: a drawing on one side, the people on the other; the shared page is components/kit/LoginPage.vue.
import { setHotelSession } from "../lib/api.js"
import { hotelInfo, ROLES } from "./lib.js"
import LoginPage from "../components/kit/LoginPage.vue"
import SlotsArt from "../components/kit/SlotsArt.vue"
const FLOATS = [
  { icon: "clock", tone: "danger", text: "مهمان ویژه ساعت ۱۴ می‌رسد", small: "سوئیت ۵۰۳ اول تمیز شود", style: { top: "2%", right: 0 } },
  { icon: "users", tone: "info", text: "یک شب خالی بین دو رزرو", small: "با جابه‌جایی فروختنی می‌شود", style: { top: "44%", left: "-6%" } },
  { icon: "heart", tone: "success", text: "بیعانه‌ی دو رزرو نرسید", small: "مهلت دیروز تمام شد", style: { bottom: "2%", right: "8%" } },
]
</script>

<template>
  <LoginPage base="/hotel" :set-session="setHotelSession" :info="hotelInfo" :business="hotelInfo.hotel" :roles="ROLES"
             kind="هتل" noun="هتل" letter="ه" :floats="FLOATS">
    <template #art><SlotsArt /></template>
  </LoginPage>
</template>
