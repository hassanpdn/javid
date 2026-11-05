<script setup>
// The first step of a language institute demo: its name and two people; the shared form is components/kit/SetupPage.vue.
// The teachers and the learners are made up by the demo.
import { instInfo, loadInstitute } from "./lib.js"
import SetupPage from "../components/kit/SetupPage.vue"
const PEOPLE = [
  { role: "owner", label: "مدیر آموزشگاه", placeholder: "مثلاً مریم کاظمی" },
  { role: "secretary", label: "منشی", placeholder: "نام و نام خانوادگی منشی" },
]
const PARTS = [
  { name: "مسیر آموزشی", what: "شش سطح، دوازده ترم، کتاب و شهریه‌ی هر ترم", icon: "route" },
  { name: "کلاس‌ها", what: "سی کلاس این ترم و کلاس‌های ترم بعد، با ده استاد و شش اتاق", icon: "calendar" },
  { name: "زبان‌آموزان", what: "حدود ۳۰۰ زبان‌آموز با ترم‌های گذشته، حضور، نمره و آزمون آنلاین", icon: "users" },
]
const STEPS = ["ساخت مسیر سطح‌ها و کتاب‌ها", "استادها و ساعت‌هایشان", "جدول کلاس‌های این ترم", "زبان‌آموزان، حضور و غیاب و آزمون‌ها", "کلاس‌های ترم بعد و ثبت‌نام‌ها", "حساب‌های ورود چهار نفر"]
</script>

<template>
  <SetupPage base="/lang" payload="institute" :info="instInfo" :load="loadInstitute" noun="آموزشگاه" letter="ز"
             title="راه‌اندازی دمو برای آموزشگاه زبان" intro="یک آموزشگاه زبان انگلیسی در هفته‌ی هشتم ترم، با کلاس‌ها، استادها، زبان‌آموزان و ترم بعدی که در حال چیدن است."
             name-placeholder="مثلاً آموزشگاه زبان آوای نو" place-placeholder="مثلاً ونک، تهران" :people="PEOPLE" :parts="PARTS" :steps="STEPS" />
</template>
