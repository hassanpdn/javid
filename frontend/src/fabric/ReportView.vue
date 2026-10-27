<script setup>
// «گزارش»: a period's sales, stock and money in a few lines, each with where it comes from,
// and the same report as an Excel file to hand on.
import { ref, watch, onMounted } from "vue"
import { api, fa, fabricSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { num } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "./HowTip.vue"

const PERIODS = [["today", "امروز"], ["week", "این هفته"], ["month", "این ماه"], ["last_month", "ماه قبل"], ["last_30", "سی روز اخیر"]]
const period = ref("last_30"), d = ref(null), saving = ref(false)
const load = async () => { d.value = null; d.value = await api("/fabric/report?period=" + period.value) }
watch(period, load)
onMounted(load)
const download = async () => {
  saving.value = true
  try {
    const res = await fetch("/fabric/report/download?period=" + period.value, { headers: { Authorization: `Bearer ${fabricSession.token}` } })
    if (!res.ok) throw new Error()
    const url = URL.createObjectURL(await res.blob())
    const a = document.createElement("a"); a.href = url; a.download = `گزارش ${d.value.label}.xlsx`; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  } catch { toast({ tone: "danger", title: "گزارش دانلود نشد" }) } finally { saving.value = false }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <section v-reveal class="rp-head">
      <div class="grow"><h2>گزارش</h2><p class="muted">{{ d ? fa(d.span) : '' }} · روی «از کجا؟» کنار هر عدد کلیک کنید تا حسابش را ببینید.</p></div>
      <button class="btn primary" :disabled="!d || saving" @click="download"><Icon name="file" :size="18" />دانلود اکسل گزارش</button>
    </section>
    <div class="segmented rp-periods" role="tablist" aria-label="دوره‌ی گزارش">
      <button v-for="[k, t] in PERIODS" :key="k" role="tab" :aria-selected="period === k" :class="{ on: period === k }" @click="period = k">{{ t }}</button>
    </div>
    <div v-if="!d" class="grid md:grid-cols-2 gap-4"><div v-for="n in 4" :key="n" class="card"><Skeleton :lines="4" /></div></div>
    <div v-else class="grid md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6">
      <section v-for="sec in d.sections" :key="sec.title" v-reveal class="card">
        <div class="card-head">{{ sec.title }}</div>
        <p v-if="!sec.rows.length" class="muted small">در این دوره چیزی ثبت نشده.</p>
        <ul class="rp-rows">
          <li v-for="r in sec.rows" :key="r.label">
            <span class="grow">{{ r.label }}</span>
            <b>{{ fa(r.value) }}</b>
            <HowTip :lines="[r.how]" label="" />
          </li>
        </ul>
      </section>
      <section v-reveal class="card md:col-span-2 xl:col-span-3">
        <div class="card-head">فاکتورهای این دوره <span class="count">{{ fa(d.invoices.length) }}</span></div>
        <div class="xf-table-wrap rp-table" tabindex="0">
          <table class="xf-table">
            <thead><tr><th>شماره</th><th>مشتری</th><th>شهر</th><th>پرداخت</th><th>مبلغ (تومان)</th></tr></thead>
            <tbody><tr v-for="i in d.invoices.slice(-80).reverse()" :key="i.id"><td>{{ fa(i.id) }}</td><td>{{ i.customer }}</td><td>{{ i.city }}</td><td>{{ i.payment }}</td><td>{{ num(i.total) }}</td></tr></tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>
