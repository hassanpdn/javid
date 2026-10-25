<script setup>
// Runtime switches for the parent and student roles. Off for both = the system works as an internal CRM
// for the school's own staff. Each switch applies at once on the server.
import { ref, computed } from "vue"
import { schoolInfo, setFeatures } from "../lib/school.js"
import Icon from "./Icon.vue"

const busy = ref(false)
const ROLES = [
  { key: "parents", label: "نقش ولی", hint: "گزارش فرزند، پیام مشاور و پرسش از مدرسه", icon: "user" },
  { key: "students", label: "نقش دانش‌آموز", hint: "ورود دانش‌آموز", icon: "school" },
]
const internal = computed(() => !schoolInfo.features.parents && !schoolInfo.features.students)
async function toggle(key) {
  busy.value = true
  try { await setFeatures({ [key]: !schoolInfo.features[key] }) } finally { busy.value = false }
}
</script>

<template>
  <div class="toggles">
    <button v-for="r in ROLES" :key="r.key" type="button" role="switch" :aria-checked="schoolInfo.features[r.key]"
            :class="['toggle-row', { on: schoolInfo.features[r.key] }]" :disabled="busy" @click="toggle(r.key)">
      <span class="tint sm t-primary"><Icon :name="r.icon" :size="18" /></span>
      <span class="toggle-text"><b>{{ r.label }}</b><small>{{ r.hint }}</small></span>
      <span class="switch" aria-hidden="true"><i></i></span>
    </button>
    <p :class="['toggle-mode', { internal }]">
      <Icon :name="internal ? 'shield' : 'users'" :size="16" />
      {{ internal ? "حالت سی‌آر‌ام داخلی: فقط کادر مدرسه" : "حالت کامل: کادر مدرسه، اولیا و دانش‌آموزان" }}
    </p>
  </div>
</template>
