<script setup>
// «بررسی‌ها» (the dentist only): what the records say: balances left unpaid after treatment, plans begun and left
// halfway. Each with the lines its sum comes from.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const list = ref(null), open = ref(new Set())
onMounted(() => retryable(async () => { list.value = await api("/dental/checks") }))
const toggle = (i) => { const s = new Set(open.value); s.has(i) ? s.delete(i) : s.add(i); open.value = s }
const ICON = { unpaid: "chart", halfway: "tooth" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="muted small">این بخش درمان‌های انجام‌شده، پرداخت‌ها و مراحل طرح‌های درمان را کنار هم می‌گذارد و هر جا با هم جور نباشد، همان را با جزئیاتش نشان می‌دهد.</p>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="3" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="shield" :size="32" /><p class="muted">همه‌چیز با هم جور است.</p></div>
    <ul v-else class="dt-list">
      <li v-for="(x, i) in list" :key="i" :class="['card', 'dt-check-card', 'tone-' + x.tone]">
        <div class="dt-check-head"><span :class="['tint', 't-' + x.tone]"><Icon :name="ICON[x.type] || 'alert'" :size="20" /></span><b>{{ fa(x.title) }}</b></div>
        <p class="small">{{ fa(x.detail) }}</p>
        <div class="btn-row"><button class="btn ghost sm" :aria-expanded="open.has(i)" @click="toggle(i)">{{ open.has(i) ? 'بستن جزئیات' : 'جزئیات' }}</button>
          <button class="btn sm" @click="emit('open', x.patient_id)">بیمار</button></div>
        <ol v-if="open.has(i)" class="dt-how"><li v-for="l in x.how" :key="l">{{ fa(l) }}</li></ol>
      </li>
    </ul>
  </div>
</template>
