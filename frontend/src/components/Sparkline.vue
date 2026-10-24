<script setup>
// Small trend line for one subject (levels 1..4)
import { ref, computed, onMounted } from "vue"
import { LEVEL_NAMES } from "../lib/constants.js"
import { gsap, motion } from "../lib/motion.js"

const props = defineProps(["points", "change"])
// right to left: the oldest point on the right, today on the left
const x = (i) => 116 - i * (112 / Math.max(props.points.length - 1, 1))
const y = (l) => 32 - (l - 1) * 9.3
const tone = computed(() => props.change <= -1 ? "down" : props.change >= 1 ? "up" : "flat")
const linePts = computed(() => props.points.map((p, i) => x(i) + "," + y(p)).join(" "))
const area = computed(() => `${linePts.value} ${x(props.points.length - 1)},35 ${x(0)},35`)
// the line draws itself
const lineEl = ref(null)
onMounted(() => {
  if (!motion || !lineEl.value) return
  const len = lineEl.value.getTotalLength()
  if (len) gsap.fromTo(lineEl.value, { strokeDasharray: len, strokeDashoffset: len },
    { strokeDashoffset: 0, duration: 1.3, ease: "power2.out", delay: .3, clearProps: "strokeDasharray,strokeDashoffset" })
})
</script>

<template>
  <svg viewBox="0 0 120 36" class="spark-svg" :class="tone" role="img" :aria-label="'روند: ' + points.map(p => LEVEL_NAMES[p]).join('، ')">
    <line v-for="l in [1, 2, 3, 4]" :key="l" x1="4" x2="116" :y1="y(l)" :y2="y(l)" class="grid" />
    <polygon :points="area" class="area" />
    <polyline ref="lineEl" :points="linePts" class="line" />
    <circle v-for="(p, i) in points" :key="i" :cx="x(i)" :cy="y(p)" :r="i === points.length - 1 ? 3.6 : 2.4" class="dot" />
  </svg>
</template>
