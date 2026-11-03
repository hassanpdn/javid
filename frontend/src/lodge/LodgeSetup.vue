<script setup>
// The first step of a eco-lodge demo: its name and people; the shared form is components/kit/SetupPage.vue.
import { lodgeInfo, loadLodge } from "./lib.js"
import SetupPage from "../components/kit/SetupPage.vue"
const PEOPLE = [
  { role: "host", label: "میزبان (صاحب اقامتگاه)", placeholder: "نام و نام خانوادگی میزبان" },
  { role: "helper", label: "همکار", placeholder: "نام و نام خانوادگی همکار" },
]
const PARTS = [
  { name: "واحدها", what: "۱۲ اتاق و خانه‌ی خشتی، با قیمت عادی و آخر هفته", icon: "bed" },
  { name: "رزروها و نظرها", what: "چهار ماه اقامت گذشته با نظر مهمانان و دو ماه رزرو پیش رو", icon: "heart" },
  { name: "سایت عمومی", what: "سایت اقامتگاه با حساب مهمانان و رزرو آنلاین", icon: "sparkles" },
]
const STEPS = ["ساخت واحدها و قیمت‌ها", "اقامت‌های گذشته و نظر مهمانان", "رزروهای پیش رو", "سایت عمومی و مهمان نمونه", "حساب‌های ورود دو نفر"]
</script>

<template>
  <SetupPage base="/lodge" payload="lodge" :info="lodgeInfo" :load="loadLodge" noun="اقامتگاه" letter="ب" warning="داده‌های فعلی پاک و از نو ساخته می‌شوند؛ حساب‌ها و نظرهایی که مهمانان در سایت ثبت کرده‌اند هم پاک می‌شود."
             title="راه‌اندازی دمو برای اقامتگاه بوم‌گردی" intro="یک اقامتگاه بوم‌گردی با ۱۲ واحد، سایت عمومی، رزروها و نظر مهمانان. همه‌چیز با همین نام‌ها ساخته می‌شود؛ حساب‌ها و نظرهایی که مهمانان در سایت ثبت کرده‌اند پاک می‌شود."
             name-placeholder="مثلاً اقامتگاه بوم‌گردی خانه‌ی گلین" place-placeholder="مثلاً روستای خرانق، یزد" :people="PEOPLE" :parts="PARTS" :steps="STEPS" />
</template>
