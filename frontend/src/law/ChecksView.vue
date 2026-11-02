<script setup>
// «بررسی‌ها» (the lawyer only): what the dates say about the office's work: deadlines that passed without action,
// actions recorded after the last day, notices entered days after they were served. Each with its dates.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const list = ref(null), open = ref(new Set())
onMounted(() => retryable(async () => { list.value = await api("/law/checks") }))
const toggle = (i) => { const s = new Set(open.value); s.has(i) ? s.delete(i) : s.add(i); open.value = s }
const ICON = { missed: "alert", late: "clock", entry: "mail" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="muted small">این بخش تاریخ ابلاغ، ثبت در دفتر، روز آخر مهلت و ثبت اقدام را کنار هم می‌گذارد و هر جا با هم جور نباشد، همان را با تاریخ‌ها نشان می‌دهد.</p>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="3" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="shield" :size="32" /><p class="muted">همه‌ی مهلت‌ها به‌موقع رسیدگی شده است.</p></div>
    <ul v-else class="lw-list">
      <li v-for="(x, i) in list" :key="i" :class="['card', 'lw-check-card', 'tone-' + x.tone]">
        <div class="lw-check-head"><span :class="['tint', 't-' + x.tone]"><Icon :name="ICON[x.type] || 'alert'" :size="20" /></span><b>{{ fa(x.title) }}</b></div>
        <p class="small">{{ fa(x.detail) }}</p>
        <div class="btn-row"><button class="btn ghost sm" :aria-expanded="open.has(i)" @click="toggle(i)">{{ open.has(i) ? 'بستن تاریخ‌ها' : 'تاریخ‌ها' }}</button>
          <button class="btn sm" @click="emit('open', x.case_id)">پرونده</button></div>
        <ol v-if="open.has(i)" class="lw-how"><li v-for="l in x.how" :key="l">{{ fa(l) }}</li></ol>
      </li>
    </ul>
  </div>
</template>
