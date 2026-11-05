<script setup>
// «مسیر آموزشی»: the institute's road with no learner on it, every station in its level's colour. A click shows its
// book, units, fee and book price. The six levels underneath, each with its two terms.
import { ref, computed } from "vue"
import { fa } from "../lib/api.js"
import { instInfo } from "./lib.js"
import RoadMap from "./RoadMap.vue"

const picked = ref("S-1")
const stations = computed(() => instInfo.terms.map((t) => ({ key: t.key, state: "map", level: t.level, fa: t.fa, cefr: t.cefr, new_book: t.num === 1 })))
</script>

<template>
  <div class="flex flex-col gap-6">
    <section class="card" data-tour="lg-curriculum">
      <div class="card-head"><span class="grow">دوازده ترم، شش سطح</span><small class="muted">هر ترم ۲۰ جلسه، دو جلسه در هفته</small></div>
      <RoadMap :stations="stations" v-model="picked" />
    </section>
    <div class="lg-tcards">
      <div v-for="l in instInfo.levels" :key="l.key" :class="['card', 'lg-lv', 'lv-' + l.key]" style="border-top: 4px solid var(--lv)">
        <b class="text-ink">{{ l.fa }} <span class="lg-chip">{{ l.cefr }}</span></b>
        <p class="muted small lg-en" style="margin: 2px 0 8px; text-align: right">{{ l.name }}</p>
        <ul class="k-mini"><li v-for="t in instInfo.terms.filter((x) => x.level === l.key)" :key="t.key">
          <div class="k-row-top"><span>{{ fa(t.fa) }} · درس {{ fa(t.units[0]) }} تا {{ fa(t.units[1]) }}</span><span>{{ fa(t.fee_text) }}</span></div></li></ul>
        <small class="muted">کتاب {{ instInfo.terms.find((x) => x.level === l.key).book }} · {{ fa(instInfo.terms.find((x) => x.level === l.key).book_price_text) }}</small>
      </div>
    </div>
  </div>
</template>
