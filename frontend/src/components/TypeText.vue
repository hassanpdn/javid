<script setup>
// Text written by the assistant appears letter by letter, like it is being typed
import { reactive, ref, computed, watch, onUnmounted } from "vue"
import { fa } from "../lib/api.js"
import gsap from "gsap"
import { motion } from "../lib/motion.js"

const props = defineProps(["text"])
const state = reactive({ n: 0 }), typing = ref(false)
const shown = computed(() => (props.text || "").slice(0, Math.round(state.n)))
let tween
watch(() => props.text, (t) => {
  tween?.kill()
  if (!motion || !t) { state.n = (t || "").length; return }
  state.n = 0; typing.value = true
  tween = gsap.to(state, { n: t.length, duration: Math.min(3, t.length / 90), ease: "none", onComplete: () => { typing.value = false } })
}, { immediate: true })
onUnmounted(() => tween?.kill())
</script>

<template><span :class="{ 'typing-caret': typing }">{{ fa(shown) }}</span></template>
