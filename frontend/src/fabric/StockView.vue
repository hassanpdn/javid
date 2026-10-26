<script setup>
// The stock file as a searchable list: rolls and meters, days of stock left at the current pace,
// and two flags: running out, and nothing sold for three months.
import { ref, computed, watch, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { money, meters, swatch } from "./lib.js"
import Skeleton from "../components/Skeleton.vue"
import Icon from "../components/Icon.vue"

const props = defineProps({ focus: { default: "" } })
const rows = ref(null), q = ref(props.focus), filter = ref("all")
let timer
const load = async () => { rows.value = await api("/fabric/stock?q=" + encodeURIComponent(q.value)) }
watch(q, () => { clearTimeout(timer); timer = setTimeout(load, 250) })
onMounted(load)
const shown = computed(() => (rows.value || []).filter((p) => filter.value === "all" || (filter.value === "low" ? p.low : p.dead)))
const count = (k) => (rows.value || []).filter((p) => p[k]).length
</script>

<template>
  <section class="card">
    <div class="fs-tools">
      <label class="fs-search"><Icon name="search" :size="18" />
        <input v-model="q" class="search" placeholder="جستجو: جنس، رنگ، عرض یا کد" aria-label="جستجو در انبار"></label>
      <div class="segmented" role="tablist" aria-label="فیلتر انبار">
        <button role="tab" :aria-selected="filter === 'all'" :class="{ on: filter === 'all' }" @click="filter = 'all'">همه</button>
        <button role="tab" :aria-selected="filter === 'low'" :class="{ on: filter === 'low' }" @click="filter = 'low'">رو به تمام شدن {{ fa(count('low')) }}</button>
        <button role="tab" :aria-selected="filter === 'dead'" :class="{ on: filter === 'dead' }" @click="filter = 'dead'">خوابیده {{ fa(count('dead')) }}</button>
      </div>
    </div>
    <Skeleton v-if="!rows" kind="row" :count="6" />
    <p v-else-if="!shown.length" class="muted small">جنسی پیدا نشد.</p>
    <ul v-else class="fs-list">
      <li v-for="p in shown" :key="p.code" :class="{ low: p.low, dead: p.dead }">
        <span class="fs-swatch" :style="{ background: swatch(p.color) }" aria-hidden="true"></span>
        <div class="fs-main">
          <b>{{ p.title }}</b>
          <small class="muted">{{ fa(p.code) }} · عرض {{ fa(p.width) }} · {{ money(p.sell_price) }} هر متر · {{ p.supplier }}</small>
        </div>
        <div class="fs-qty"><b>{{ fa(p.rolls) }} توپ</b><small class="muted">{{ meters(p.meters) }}</small></div>
        <span v-if="p.low" class="tag st-bad">حدود {{ fa(p.days_left) }} روز</span>
        <span v-else-if="p.dead" class="tag st-todo">بی‌فروش · {{ money(p.value) }}</span>
        <span v-else-if="p.days_left !== null" class="tag">{{ fa(p.days_left) }} روز</span>
      </li>
    </ul>
  </section>
</template>
