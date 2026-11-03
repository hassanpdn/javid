<script setup>
// «گزارش» (the manager): the next fourteen nights on the books against the same weekday over the last eight weeks
// (the line on each bar), with a price suggestion where a night is filling up or staying empty; income by kind and by
// channel in the last thirty days; and how far selling over the rooms is safe, from the no-show rate. Every number
// comes from the server; the decisions stay with the manager.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Skeleton from "../components/Skeleton.vue"

const d = ref(null)
onMounted(() => retryable(async () => { d.value = await api("/hotel/report") }))
const max = (rows) => Math.max(1, ...rows.map((r) => r.amount))
</script>

<template>
  <div v-if="!d" class="card"><Skeleton kind="row" :count="8" /></div>
  <div v-else class="grid grid-cols-12 gap-6">
    <section class="card col-span-12 xl:col-span-7 flex flex-col gap-3" data-tour="ht-forecast">
      <div class="card-head">چهارده شب آینده <small>پر شده تا امروز؛ خط: میانگین همان روز هفته در هشت هفته‌ی گذشته</small></div>
      <ul class="ht-bars"><li v-for="n in d.nights" :key="n.date">
        <span :class="{ 'ht-late': n.weekend }">{{ fa(n.day) }}</span>
        <span class="track"><i :style="{ width: Math.min(100, n.pct) + '%' }"></i><u :style="{ insetInlineStart: Math.min(100, n.usual) + '%' }"></u></span>
        <b>{{ fa(n.pct) }}٪</b>
        <small v-if="n.tip" class="tip">{{ n.tip }}</small></li></ul>
    </section>
    <div class="col-span-12 xl:col-span-5 flex flex-col gap-6">
      <section class="card flex flex-col gap-3">
        <div class="card-head">درآمد سی روز گذشته</div>
        <ul class="ht-bars"><li v-for="k in d.kinds" :key="k.kind"><span>{{ k.label }}</span><span class="track"><i :style="{ width: 100 * k.amount / max(d.kinds) + '%' }"></i></span><small>{{ fa(k.text) }}</small></li></ul>
      </section>
      <section class="card flex flex-col gap-3">
        <div class="card-head">سهم هر راه رزرو <small>درآمد اتاق، سی روز</small></div>
        <ul class="ht-mini"><li v-for="c in d.channels" :key="c.name"><div class="ht-row-top"><span>{{ c.name }}</span><b>{{ fa(c.pct) }}٪</b></div><small class="muted">{{ fa(c.text) }} · {{ fa(c.stays) }} اقامت</small></li></ul>
      </section>
      <section class="card flex flex-col gap-2">
        <div class="card-head">فروش بیش از ظرفیت</div>
        <p class="small">{{ fa(d.overbook_tip) }}</p>
      </section>
    </div>
  </div>
</template>
