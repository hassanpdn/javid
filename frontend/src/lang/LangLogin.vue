<script setup>
// The language institute's login: the road up the hill on one side, the four people on the other; the shared page is
// components/kit/LoginPage.vue.
import { setLangSession } from "../lib/api.js"
import { instInfo, ROLES } from "./lib.js"
import LoginPage from "../components/kit/LoginPage.vue"
import RoadArt from "./RoadArt.vue"
const FLOATS = [
  { icon: "alert", tone: "danger", text: "استاد در یک ساعت دو کلاس دارد", small: "ترم بعد، شنبه و دوشنبه", style: { top: "2%", right: 0 } },
  { icon: "route", tone: "info", text: "شما این‌جایید: B1 · ۲", small: "ترم بعد کتاب جدید", style: { top: "44%", left: "-6%" } },
  { icon: "check", tone: "success", text: "آزمون آنلاین باز است", small: "۸ پرسش، ۱۵ دقیقه", style: { bottom: "2%", right: "8%" } },
]
</script>

<template>
  <LoginPage base="/lang" :set-session="setLangSession" :info="instInfo" :business="instInfo.institute" :roles="ROLES"
             kind="آموزشگاه زبان" noun="آموزشگاه" letter="ز" :floats="FLOATS">
    <template #art><RoadArt /></template>
  </LoginPage>
</template>
