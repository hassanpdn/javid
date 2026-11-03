<script setup>
// The law office's login: a drawing on one side, the people on the other; the shared page is components/kit/LoginPage.vue.
import { setLawSession } from "../lib/api.js"
import { officeInfo, ROLES } from "./lib.js"
import LoginPage from "../components/kit/LoginPage.vue"
// case folders on a shelf: [x, height, colour]
const HOUSES = [[40, 150, "#3c4a8f"], [96, 190, "#7367f0"], [152, 130, "#e0a785"], [208, 200, "#00bad1"], [264, 160, "#28c76f"], [320, 140, "#ea5455"]]
const FLOATS = [
  { icon: "clock", tone: "danger", text: "دو روز به آخر مهلت تجدیدنظر", small: "با جمعه‌ها و تعطیلات", style: { top: "2%", right: 0 } },
  { icon: "mail", tone: "info", text: "ابلاغیه‌ی جدید خوانده شد", small: "شماره‌ی پرونده و شعبه پیدا شد", style: { top: "44%", left: "-6%" } },
  { icon: "calendar", tone: "success", text: "جلسه‌ی فردا ساعت ۱۰:۳۰", small: "شعبه‌ی ۷ دادگاه خانواده", style: { bottom: "2%", right: "8%" } },
]
</script>

<template>
  <LoginPage base="/law" :set-session="setLawSession" :info="officeInfo" :business="officeInfo.office" :roles="ROLES"
             kind="دفتر وکالت" noun="دفتر" letter="و" :floats="FLOATS">
    <template #art>
      <svg viewBox="0 0 400 330" aria-hidden="true" class="shelves">
          <ellipse cx="200" cy="312" rx="180" ry="12" style="fill: var(--primary-soft)" />
          <rect x="10" y="296" width="380" height="8" rx="4" style="fill: var(--line)" />
          <g v-for="h in HOUSES" :key="h[0]" class="es-house">
            <rect :x="h[0]" :y="296 - h[1]" width="46" :height="h[1]" rx="5" :style="{ fill: h[2] }" opacity=".9" />
            <rect :x="h[0] + 9" :y="296 - h[1] + 18" width="28" height="22" rx="3" fill="#fff" opacity=".7" />
            <rect :x="h[0] + 9" :y="296 - 30" width="28" height="4" rx="2" fill="#fff" opacity=".4" />
          </g>
        </svg>
    </template>
  </LoginPage>
</template>
