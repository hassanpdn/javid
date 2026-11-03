<script setup>
// The first step of a hotel demo: its name and people; the shared form is components/kit/SetupPage.vue.
import { hotelInfo, loadHotel } from "./lib.js"
import SetupPage from "../components/kit/SetupPage.vue"
const PEOPLE = [
  { role: "manager", label: "مدیر هتل", placeholder: "نام و نام خانوادگی مدیر" },
  { role: "reservation", label: "کارشناس رزرو", placeholder: "نام و نام خانوادگی" },
  { role: "reception", label: "مسئول پذیرش", placeholder: "نام و نام خانوادگی" },
  { role: "housekeeping", label: "سرپرست خانه‌داری", placeholder: "نام و نام خانوادگی" },
]
const PARTS = [
  { name: "اتاق‌ها", what: "۸۰ اتاق در سه نوع، ۶ سوئیت و ۴ ویلای ساحلی", icon: "bed" },
  { name: "رزروها", what: "چهار ماه اقامت گذشته و دو ماه رزرو پیش رو", icon: "calendar" },
  { name: "آژانس‌ها و سایت‌ها", what: "سهمیه‌ی آژانس‌ها، سایت‌های رزرو و حساب شرکت‌ها", icon: "users" },
]
const STEPS = ["ساخت اتاق‌ها و قیمت‌ها", "اقامت‌ها و صورت‌حساب‌های گذشته", "رزروهای دو ماه آینده", "آژانس‌ها و سهمیه‌ها", "حساب‌های ورود چهار نفر"]
</script>

<template>
  <SetupPage base="/hotel" payload="hotel" :info="hotelInfo" :load="loadHotel" noun="هتل" letter="ه"
             title="راه‌اندازی دمو برای هتل" intro="یک هتل ساحلی با ۹۰ اتاق و سوئیت و ویلا، با رزروها و مهمانانش. همه‌چیز با همین نام‌ها ساخته می‌شود."
             name-placeholder="مثلاً هتل موج آبی" place-placeholder="مثلاً ساحل نوشهر، مازندران" :people="PEOPLE" :parts="PARTS" :steps="STEPS" />
</template>
