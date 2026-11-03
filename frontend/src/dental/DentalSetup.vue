<script setup>
// The first step of a dental clinic demo: its name and people; the shared form is components/kit/SetupPage.vue.
import { clinicInfo, loadClinic } from "./lib.js"
import SetupPage from "../components/kit/SetupPage.vue"
const PEOPLE = [
  { role: "owner", label: "دندان‌پزشک (صاحب مطب)", placeholder: "مثلاً دکتر شیرین رستگار" },
  { role: "secretary", label: "منشی", placeholder: "نام و نام خانوادگی منشی" },
]
const PARTS = [
  { name: "بیماران", what: "۱۵۰ بیمار با نوبت‌ها و پرداخت‌های چهار ماه گذشته", icon: "file" },
  { name: "طرح‌های درمان", what: "طرح‌های تمام‌شده، در حال انجام و شروع‌نشده", icon: "users" },
  { name: "نوبت‌ها", what: "نوبت‌های امروز و روزهای آینده و فهرست انتظار", icon: "check" },
]
const STEPS = ["ساخت پرونده‌ی بیماران", "نوبت‌ها و پرداخت‌های گذشته", "طرح‌های درمان", "نوبت‌های پیش رو و فهرست انتظار", "حساب‌های ورود دو نفر"]
</script>

<template>
  <SetupPage base="/dental" payload="clinic" :info="clinicInfo" :load="loadClinic" noun="مطب" letter="د"
             title="راه‌اندازی دمو برای مطب دندان‌پزشکی" intro="یک مطب دندان‌پزشکی در تهران با بیماران، نوبت‌ها و طرح‌های درمان. همه‌چیز با همین نام‌ها ساخته می‌شود."
             name-placeholder="مثلاً مطب دندان‌پزشکی لبخند" place-placeholder="مثلاً سعادت‌آباد، تهران" :people="PEOPLE" :parts="PARTS" :steps="STEPS" />
</template>
