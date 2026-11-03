<script setup>
// «تقویم»: every unit down, three weeks across, each booking a bar from its first night to its last (amber: a request
// waiting for the host, blue: waiting for or checking the deposit, green: confirmed, striped: closed). Weekend nights
// are tinted. A bar opens its booking.
import { ref, computed, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { lodgeInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import DatePicker from "../components/core/DatePicker.vue"

const emit = defineEmits(["open"])
const start = ref(lodgeInfo.today), d = ref(null)
const load = async () => { d.value = await api("/lodge/calendar?d=" + encodeURIComponent(start.value)) }
watch(start, () => { d.value = null; load().catch(() => {}) })
onMounted(() => retryable(load))
const rows = computed(() => d.value?.rows || [])
const pos = (b) => ({ insetInlineStart: `calc(var(--room) + ${b.from} * var(--cell) + 2px)`, width: `calc(${b.span} * var(--cell) - 4px)` })
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="lo-toolbar">
      <div class="field" style="flex: 0 1 220px"><span>از شب</span><DatePicker v-model="start" :min="'1400/01/01'" label="از شب" /></div>
    </div>
    <div class="lo-legend"><span><i style="background: #a15c00"></i>درخواست</span><span><i style="background: #0b7285"></i>منتظر بیعانه یا رسید</span>
      <span><i style="background: var(--success-strong)"></i>قطعی</span><span><i style="background: var(--danger-strong)"></i>بسته</span><span><i style="background: var(--warning-soft)"></i>آخر هفته</span></div>
    <Skeleton v-if="!d" kind="row" :count="10" />
    <div v-else class="lo-grid-wrap" data-tour="lo-calendar">
      <div class="lo-grid" :style="{ '--days': d.cols.length }">
        <div class="lo-grow lo-ghead"><span>واحد</span><span v-for="c in d.cols" :key="c.date" :class="{ we: c.weekend, td: c.today }">{{ c.weekday }}<br>{{ fa(c.day) }}</span></div>
        <div v-for="r in rows" :key="r.id" class="lo-grow">
          <div class="lo-gname"><b>{{ r.name }}</b><small>{{ r.active ? "" : "خاموش" }}</small></div>
          <span v-for="c in d.cols" :key="c.date" :class="['lo-gcell', { we: c.weekend }]"></span>
          <button v-for="b in r.bars" :key="(b.id || 'o') + '-' + b.from" :class="['lo-bar', 's-' + b.status]" :style="pos(b)" :title="b.guest" :disabled="!b.id"
                  @click="b.id && emit('open', b.id)"><span v-if="b.vip" class="vip">ویژه</span>{{ b.guest }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
