<script setup>
// Kit: «بررسی‌ها», the owner's checks of a business assistant (law, dental, hotel). The server finds what does not add
// up and sends each with its tone, title, detail and the lines it comes from (how); this shows them, each with its
// lines one click away and a button to the record. It never names who is to blame: the server never sends that.
// endpoint: GET for the list; intro: one line on what is compared; empty: the text when all is well; icons: an icon
// per kind; record: {key: the field with the record's id, label: the button's word}; howLabel: the lines' button.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../../lib/api.js"
import Icon from "../Icon.vue"
import Skeleton from "../Skeleton.vue"

const props = defineProps({ endpoint: String, intro: String, empty: String, icons: { type: Object, default: () => ({}) },
                            record: { type: Object, default: () => ({ key: "id", label: "باز کردن" }) }, howLabel: { type: String, default: "جزئیات" } })
const emit = defineEmits(["open"])
const list = ref(null), open = ref(new Set())
onMounted(() => retryable(async () => { list.value = await api(props.endpoint) }))
const toggle = (i) => { const s = new Set(open.value); s.has(i) ? s.delete(i) : s.add(i); open.value = s }
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="muted small">{{ intro }}</p>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="3" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="shield" :size="32" /><p class="muted">{{ empty }}</p></div>
    <ul v-else class="k-list">
      <li v-for="(x, i) in list" :key="i" :class="['card', 'k-check-card', 'tone-' + x.tone]">
        <div class="k-check-head"><span :class="['tint', 't-' + x.tone]"><Icon :name="icons[x.type] || 'alert'" :size="20" /></span><b>{{ fa(x.title) }}</b></div>
        <p class="small">{{ fa(x.detail) }}</p>
        <div class="btn-row"><button class="btn ghost sm" :aria-expanded="open.has(i)" @click="toggle(i)">{{ open.has(i) ? 'بستن ' + howLabel : howLabel }}</button>
          <button v-if="x[record.key]" class="btn sm" @click="emit('open', x[record.key])">{{ record.label }}</button></div>
        <ol v-if="open.has(i)" class="k-how"><li v-for="l in x.how" :key="l">{{ fa(l) }}</li></ol>
      </li>
    </ul>
  </div>
</template>
