<script setup>
// Round gauge for a percentage, drawn with plain SVG
import { ref, onMounted } from "vue"
import { fa } from "../lib/api.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"

defineProps(["value", "label"])
const C = 2 * Math.PI * 56, arc = ref(null)
onMounted(() => { if (motion) gsap.from(arc.value, { attr: { "stroke-dashoffset": C }, duration: 1.6, ease: "power3.out", delay: .2 }) })
</script>

<template>
  <svg class="gauge" viewBox="0 0 140 140" width="180" height="180" role="img" :aria-label="label + ' ' + fa(value) + ' درصد'">
    <circle class="track" cx="70" cy="70" r="56" fill="none" stroke-width="12" />
    <circle ref="arc" class="val" cx="70" cy="70" r="56" fill="none" stroke-width="12"
            :stroke-dasharray="C" :stroke-dashoffset="C * (1 - value / 100)" transform="rotate(-90 70 70)" />
    <text x="70" y="74" text-anchor="middle" font-size="28">{{ fa(value) }}٪</text>
    <text class="sub" x="70" y="98" text-anchor="middle" font-size="12">{{ label }}</text>
  </svg>
</template>
