<script setup>
// «بررسی‌ها» (the manager only): what the records say: discounts over the limit, a stay cancelled after check-in,
// a guest put in a dirty room, the cash short at the close of a day. Each with the lines it comes from.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const list = ref(null), open = ref(new Set())
onMounted(() => retryable(async () => { list.value = await api("/hotel/checks") }))
const toggle = (i) => { const s = new Set(open.value); s.has(i) ? s.delete(i) : s.add(i); open.value = s }
const ICON = { discount: "chart", cancel_after: "alert", dirty: "bed", cash: "key" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="muted small">این بخش تخفیف‌ها، تحویل اتاق‌ها، لغوها و صندوق هر روز را کنار هم می‌گذارد و هر جا با هم جور نباشد، همان را با جزئیاتش نشان می‌دهد.</p>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="3" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="shield" :size="32" /><p class="muted">همه‌چیز با هم جور است.</p></div>
    <ul v-else class="ht-list">
      <li v-for="(x, i) in list" :key="i" :class="['card', 'ht-check-card', 'tone-' + x.tone]">
        <div class="ht-check-head"><span :class="['tint', 't-' + x.tone]"><Icon :name="ICON[x.type] || 'alert'" :size="20" /></span><b>{{ fa(x.title) }}</b></div>
        <p class="small">{{ fa(x.detail) }}</p>
        <div class="btn-row"><button class="btn ghost sm" :aria-expanded="open.has(i)" @click="toggle(i)">{{ open.has(i) ? 'بستن جزئیات' : 'جزئیات' }}</button>
          <button v-if="x.booking_id" class="btn sm" @click="emit('open', x.booking_id)">رزرو</button></div>
        <ol v-if="open.has(i)" class="ht-how"><li v-for="l in x.how" :key="l">{{ fa(l) }}</li></ol>
      </li>
    </ul>
  </div>
</template>
