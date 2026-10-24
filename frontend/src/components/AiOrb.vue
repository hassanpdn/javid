<script setup>
// The assistant's animated "orb". busy makes it spin faster while the model is working.
import { ref, watch, onMounted, onUnmounted } from "vue"
import { gsap, motion } from "../lib/motion.js"

const props = defineProps({ size: { default: 120 }, busy: { default: false } })
const el = ref(null)
let ctx, spin
onMounted(() => {
  if (!motion) return
  // gsap.context limits the selectors to this svg and lets us undo every tween on unmount
  ctx = gsap.context(() => {
    spin = gsap.timeline({ repeat: -1 })
    spin.to(".ring", { rotation: 360, svgOrigin: "60 60", duration: 18, ease: "none" }, 0)
    gsap.to(".sat.a", { rotation: 360, svgOrigin: "60 60", duration: 9, repeat: -1, ease: "none" })
    gsap.to(".sat.b", { rotation: -360, svgOrigin: "60 60", duration: 13, repeat: -1, ease: "none" })
    gsap.to(".core", { scale: 1.06, svgOrigin: "60 60", duration: 1.8, yoyo: true, repeat: -1, ease: "sine.inOut" })
    gsap.to(".halo", { scale: 1.1, opacity: .18, svgOrigin: "60 60", duration: 2.2, yoyo: true, repeat: -1, ease: "sine.inOut" })
    spin.timeScale(props.busy ? 8 : 1)
  }, el.value)
})
watch(() => props.busy, (b) => spin && gsap.to(spin, { timeScale: b ? 8 : 1, duration: .6 }))
onUnmounted(() => ctx?.revert())
</script>

<template>
  <svg ref="el" class="orb" :width="size" :height="size" viewBox="0 0 120 120" aria-hidden="true">
    <defs><linearGradient id="orbGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color: var(--primary)" /><stop offset="1" style="stop-color: var(--info)" /></linearGradient></defs>
    <circle class="halo" cx="60" cy="60" r="56" style="fill: var(--primary)" opacity=".08" />
    <circle class="ring" cx="60" cy="60" r="50" fill="none" style="stroke: var(--primary)" stroke-opacity=".4" stroke-width="1.5" stroke-dasharray="4 7" />
    <g class="core">
      <circle cx="60" cy="60" r="34" fill="url(#orbGrad)" />
      <path d="M60 42c1.6 8.8 5.2 12.4 14 14-8.8 1.6-12.4 5.2-14 14-1.6-8.8-5.2-12.4-14-14 8.8-1.6 12.4-5.2 14-14Z" fill="#fff" />
      <path d="M74 38c.6 3.4 2 4.8 5.4 5.4-3.4.6-4.8 2-5.4 5.4-.6-3.4-2-4.8-5.4-5.4 3.4-.6 4.8-2 5.4-5.4Z" fill="#fff" opacity=".8" />
    </g>
    <circle class="sat a" cx="60" cy="10" r="4" style="fill: var(--warning)" />
    <circle class="sat b" cx="110" cy="60" r="3" style="fill: var(--success)" />
  </svg>
</template>
