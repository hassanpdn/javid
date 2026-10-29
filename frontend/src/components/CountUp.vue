<script setup>
// A number that counts up to its value (the value itself always comes from the server)
import { reactive, watch, onUnmounted } from "vue"
import { fa } from "../lib/api.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"

const props = defineProps({ value: { type: Number, default: 0 } })
const state = reactive({ n: 0 })
let tween
watch(() => props.value, (v) => {
  tween?.kill()
  if (!motion) { state.n = v; return }
  tween = gsap.to(state, { n: v, duration: 1.2, ease: "power2.out" })
}, { immediate: true })
onUnmounted(() => tween?.kill())
</script>

<template><span>{{ fa(Math.round(state.n)) }}</span></template>
