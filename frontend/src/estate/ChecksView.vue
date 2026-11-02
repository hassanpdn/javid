<script setup>
// «بررسی‌ها» (owner only): what does not add up in the agency's own records, found from numbers and dates alone, each
// with the dates and sums behind it. It says what does not add up, never who did it.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["listing", "request"])
const list = ref(null), open = ref(new Set())
onMounted(() => retryable(async () => { list.value = await api("/estate/checks") }))
const toggle = (i) => { const s = new Set(open.value); s.has(i) ? s.delete(i) : s.add(i); open.value = s }
const ICON = { outside: "alert", fee: "chart", duplicate: "layers" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="muted small">این بخش سابقه‌ی فایل‌ها، بازدیدها و معامله‌ها را کنار هم می‌گذارد و هر جا عددها یا تاریخ‌ها با هم جور نباشد، همان را با جزئیات نشان می‌دهد. هر مورد ممکن است توضیح ساده‌ای داشته باشد.</p>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="3" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="shield" :size="32" /><p class="muted">همه‌چیز با هم جور است.</p></div>
    <ul v-else class="es-list">
      <li v-for="(x, i) in list" :key="i" :class="['card', 'es-check-card', 'tone-' + x.tone]">
        <div class="es-check-head"><span :class="['tint', 't-' + x.tone]"><Icon :name="ICON[x.type] || 'alert'" :size="20" /></span><b>{{ fa(x.title) }}</b></div>
        <p class="small">{{ fa(x.detail) }}</p>
        <div class="btn-row">
          <button class="btn ghost sm" :aria-expanded="open.has(i)" @click="toggle(i)">{{ open.has(i) ? 'بستن جزئیات' : 'جزئیات و تاریخ‌ها' }}</button>
          <button v-if="x.listing_id" class="btn sm" @click="emit('listing', x.listing_id)">فایل {{ fa(x.listing_id) }}</button>
          <button v-if="x.request_id" class="btn sm" @click="emit('request', x.request_id)">متقاضی</button>
        </div>
        <ol v-if="open.has(i)" class="es-how"><li v-for="l in x.how" :key="l">{{ fa(l) }}</li></ol>
      </li>
    </ul>
  </div>
</template>
