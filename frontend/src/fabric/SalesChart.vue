<script setup>
// Daily sales of the last two weeks as bars, right to left like Persian reading. points: [{ label, amount }]
// Bars are scaled to the best day; the value on each bar is in millions of toman.
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue"
import { fa } from "../lib/api.js"
import { gsap, motion } from "../lib/motion.js"

const props = defineProps(["points"])
const box = ref(null), svg = ref(null), W = ref(0), H = ref(0)
const max = computed(() => Math.max(...props.points.map((p) => p.amount), 1))
const gap = computed(() => Math.min(14, W.value / props.points.length / 4))
const bw = computed(() => (W.value - gap.value * (props.points.length - 1)) / props.points.length)
const x = (i) => W.value - (i + 1) * bw.value - i * gap.value
const h = (v) => Math.max(3, (H.value - 52) * v / max.value)
const top = (v) => H.value - 26 - h(v)
const short = (v) => fa(Math.round(v / 1e6))
let ro
onMounted(() => {
  ro = new ResizeObserver(([e]) => {
    const first = !W.value
    W.value = e.contentRect.width; H.value = e.contentRect.height
    if (first && motion) nextTick(() => gsap.from(svg.value.querySelectorAll(".bar"), { scaleY: 0, transformOrigin: "50% 100%", duration: .9, ease: "power3.out", stagger: .04, delay: .2 }))
  })
  ro.observe(box.value)
})
onBeforeUnmount(() => ro?.disconnect())
</script>

<template>
  <div ref="box" class="sales-chart" role="img" :aria-label="'فروش روزانه‌ی ' + fa(points.length) + ' روز کاری اخیر'">
    <svg v-if="W" ref="svg" :width="W" :height="H" class="bars">
      <g v-for="(p, i) in points" :key="p.date">
        <rect class="bar" :x="x(i)" :y="top(p.amount)" :width="bw" :height="h(p.amount)" rx="6"
              :style="{ fill: i === points.length - 1 ? 'var(--primary)' : 'color-mix(in srgb, var(--primary) 55%, var(--panel))' }" />
        <text v-if="bw > 22" class="val" :x="x(i) + bw / 2" :y="top(p.amount) - 6">{{ short(p.amount) }}</text>
        <text v-if="bw > 26 || i % 2 === 0" class="lbl" :x="x(i) + bw / 2" :y="H - 6">{{ fa(p.label.split(' ')[0]) }}</text>
      </g>
    </svg>
  </div>
</template>
