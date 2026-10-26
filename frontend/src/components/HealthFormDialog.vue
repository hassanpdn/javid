<script setup>
// Parent fills the physical or wellbeing form; questions come from the server
import { ref, reactive, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import Icon from "./Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const SCALE_ENDS = { mood: ["خیلی کم", "خیلی خوب"], sleep_quality: ["بد", "عالی"], school_worry: ["اصلا", "خیلی زیاد"], friends: ["سخت", "خیلی خوب"] }
const props = defineProps(["kind"])
const emit = defineEmits(["close", "saved"])
const fields = ref([]), data = reactive({}), date = ref(null), saving = ref(false)
onMounted(async () => {
  const r = await api(`/parent/forms/${props.kind}`)
  fields.value = r.fields; Object.assign(data, r.data); date.value = r.date
})
const save = async () => {
  saving.value = true
  try { await api(`/parent/forms/${props.kind}`, { data: { ...data } }); emit("saved") } finally { saving.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <form class="dialog" v-pop @submit.prevent="save">
      <div class="dialog-head">
        <div><h3>{{ kind === 'physical' ? 'فرم سلامت جسمی' : 'فرم حال و احوال' }}</h3>
          <p class="muted small">{{ date ? 'آخرین ثبت: ' + fa(date) + '. پاسخ‌های قبلی را ببینید و اگر چیزی تغییر کرده اصلاح کنید.' : 'چند سؤال کوتاه. پاسخ‌ها فقط برای مشاور مدرسه است.' }}</p></div>
        <button type="button" class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <Skeleton v-if="!fields.length" kind="field" :count="4" />
      <div v-for="[key, label, type] in fields" :key="key" class="q">
        <span class="q-label">{{ label }}</span>
        <input v-if="type === 'number'" type="number" inputmode="decimal" v-model="data[key]" class="q-input" min="0">
        <input v-else-if="type === 'text'" v-model="data[key]" class="q-input" placeholder="اگر چیزی هست بنویسید">
        <div v-else-if="type === 'scale'" class="scale">
          <small class="muted">{{ SCALE_ENDS[key]?.[0] }}</small>
          <button v-for="n in 5" :key="n" type="button" :class="['dot-btn', { on: Number(data[key]) === n }]" @click="data[key] = n" :aria-label="fa(n)">{{ fa(n) }}</button>
          <small class="muted">{{ SCALE_ENDS[key]?.[1] }}</small>
        </div>
        <div v-else class="options">
          <button v-for="o in type" :key="o" type="button" :class="{ on: data[key] === o }" @click="data[key] = o">{{ o }}</button>
        </div>
      </div>
      <div class="dialog-actions">
        <button class="btn primary" :disabled="saving">{{ saving ? 'در حال ثبت...' : 'ثبت فرم' }}</button>
        <button type="button" class="btn ghost" @click="$emit('close')">انصراف</button>
      </div>
    </form>
  </div>
</template>
