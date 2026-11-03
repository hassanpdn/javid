<script setup>
// «جدول اتاق‌ها»: every room down, fourteen nights across, each booking a bar from its first night to its last
// (green: in the house, blue: confirmed, amber: waiting for its deposit, striped: under repair). Weekend nights are
// tinted. A bar opens its booking. Bookings without a room yet are listed below.
import { ref, computed, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { hotelInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import DatePicker from "../components/core/DatePicker.vue"

const emit = defineEmits(["open"])
const start = ref(hotelInfo.today), d = ref(null), type = ref(""), all = ref(false)
const load = async () => { d.value = await api("/hotel/grid?d=" + encodeURIComponent(start.value)) }
watch(start, () => { d.value = null; load().catch(() => {}) })
onMounted(() => retryable(load))
const rows = computed(() => (d.value?.rows || []).filter((r) => !type.value || r.type === type.value))
const pos = (b) => ({ insetInlineStart: `calc(var(--room) + ${b.from} * var(--cell) + 2px)`, width: `calc(${b.span} * var(--cell) - 4px)` })
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="ht-toolbar">
      <div class="field" style="flex: 0 1 220px"><span>از شب</span><DatePicker v-model="start" :min="'1400/01/01'" label="از شب" /></div>
      <label class="field" style="flex: 0 1 220px"><span>نوع اتاق</span><select v-model="type" class="ht-select"><option value="">همه</option><option v-for="t in hotelInfo.types" :key="t.key" :value="t.key">{{ t.name }}</option></select></label>
    </div>
    <div class="ht-legend"><span><i style="background: var(--success-strong)"></i>مقیم</span><span><i style="background: #0b7285"></i>قطعی</span><span><i style="background: #a15c00"></i>موقت</span>
      <span><i style="background: #5d596c"></i>رفته</span><span><i style="background: var(--danger-strong)"></i>تعمیر</span><span><i style="background: var(--warning-soft)"></i>آخر هفته</span></div>
    <Skeleton v-if="!d" kind="row" :count="10" />
    <div v-else class="ht-grid-wrap" data-tour="ht-grid">
      <div class="ht-grid" :style="{ '--days': d.cols.length }">
        <div class="ht-grow ht-ghead"><span>اتاق</span><span v-for="c in d.cols" :key="c.date" :class="{ we: c.weekend, td: c.today }">{{ c.weekday }}<br>{{ fa(c.day) }}</span></div>
        <div v-for="r in rows" :key="r.id" class="ht-grow">
          <div class="ht-gname"><b>{{ fa(r.number) }}</b><small>{{ r.type_text }}</small></div>
          <span v-for="c in d.cols" :key="c.date" :class="['ht-gcell', { we: c.weekend }]"></span>
          <button v-for="b in r.bars" :key="(b.id || 'o') + '-' + b.from" :class="['ht-bar', 's-' + b.status]" :style="pos(b)" :title="b.guest" :disabled="!b.id"
                  @click="b.id && emit('open', b.id)"><span v-if="b.vip" class="vip">ویژه</span>{{ b.guest }}</button>
        </div>
      </div>
    </div>
    <section v-if="d?.unassigned.length" class="card flex flex-col gap-2">
      <div class="card-head">رزروهای بی‌اتاق در این دو هفته <span class="count">{{ fa(d.unassigned.length) }}</span></div>
      <p class="muted small">اتاق این‌ها را پذیرش یک روز پیش از ورود می‌دهد؛ دستیار پیشنهادش را در هر رزرو نشان می‌دهد.</p>
      <ul class="ht-mini"><li v-for="b in all ? d.unassigned : d.unassigned.slice(0, 8)" :key="b.id"><div class="ht-row-top"><button class="ht-link" @click="emit('open', b.id)">{{ b.guest }}</button><span class="tag">{{ b.type_text }}</span></div>
        <small class="muted">{{ fa(b.stay_text) }} · {{ b.status_text }}</small></li></ul>
      <button v-if="d.unassigned.length > 8" class="btn ghost sm" style="align-self: flex-start" :aria-expanded="all" @click="all = !all">{{ all ? 'بستن' : `همه (${fa(d.unassigned.length)})` }}</button>
    </section>
  </div>
</template>
