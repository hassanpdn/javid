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
import TapeChart from "../components/kit/TapeChart.vue"

const emit = defineEmits(["open"])
const start = ref(lodgeInfo.today), d = ref(null)
const load = async () => { d.value = await api("/lodge/calendar?d=" + encodeURIComponent(start.value)) }
watch(start, () => { d.value = null; load().catch(() => {}) })
onMounted(() => retryable(load))
const rows = computed(() => (d.value?.rows || []).map((r) => ({ ...r, label: r.name, sub: r.active ? "" : "خاموش" })))
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="k-toolbar">
      <div class="field" style="flex: 0 1 220px"><span>از شب</span><DatePicker v-model="start" :min="'1400/01/01'" label="از شب" /></div>
    </div>
    <div class="k-legend"><span><i style="background: #a15c00"></i>درخواست</span><span><i style="background: #0b7285"></i>منتظر بیعانه یا رسید</span>
      <span><i style="background: var(--success-strong)"></i>قطعی</span><span><i style="background: var(--danger-strong)"></i>بسته</span><span><i style="background: var(--warning-soft)"></i>آخر هفته</span></div>
    <Skeleton v-if="!d" kind="row" :count="10" />
    <TapeChart v-else :cols="d.cols" :rows="rows" corner="واحد" data-tour="lo-calendar" @open="emit('open', $event)" />
  </div>
</template>
