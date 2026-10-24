<script setup>
// Attendance bars, drawn with plain SVG. points: [{ jdate, rate }]
import { ref, computed, onMounted } from "vue"
import { fa } from "../lib/api.js"
import { gsap, motion } from "../lib/motion.js"

const props = defineProps(["points"])
const W = 900, H = 210, gap = 22, svg = ref(null)
const bw = computed(() => (W - gap * (props.points.length - 1)) / props.points.length)
const x = (i) => W - (i + 1) * bw.value - i * gap          // right to left, like Persian reading
const y = (rate) => 30 + (100 - Math.max(rate, 80)) * (H - 66) / 20  // zoom on the 80..100 range
onMounted(() => {
  if (!motion) return
  gsap.from(svg.value.querySelectorAll(".bar"), { scaleY: 0, transformOrigin: "50% 100%", duration: 1, ease: "power3.out", stagger: .06, delay: .3 })
  gsap.from(svg.value.querySelectorAll(".val"), { opacity: 0, y: 8, duration: .5, stagger: .06, delay: .7 })
})
</script>

<template>
  <svg ref="svg" :viewBox="'0 0 ' + W + ' ' + H" class="bars" role="img" aria-label="نمودار درصد حضور">
    <defs>
      <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color: var(--primary)" /><stop offset="1" style="stop-color: var(--primary); stop-opacity: .35" /></linearGradient>
      <linearGradient id="barGradLow" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color: var(--warning)" /><stop offset="1" style="stop-color: var(--warning); stop-opacity: .35" /></linearGradient>
    </defs>
    <line v-for="r in [85, 90, 95, 100]" :key="r" class="gridline" x1="0" :x2="W" :y1="y(r)" :y2="y(r)" />
    <g v-for="(p, i) in points" :key="p.jdate">
      <rect :x="x(i)" :y="y(p.rate)" :width="bw" :height="H - 26 - y(p.rate)" rx="7" :class="p.rate < 95 ? 'bar low' : 'bar'" />
      <text :x="x(i) + bw / 2" :y="y(p.rate) - 7" class="val">{{ fa(p.rate) }}</text>
      <text :x="x(i) + bw / 2" :y="H - 6" class="lbl">{{ fa(p.jdate) }}</text>
    </g>
  </svg>
</template>
