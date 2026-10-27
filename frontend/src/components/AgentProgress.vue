<script setup>
// The assistant's progress while it reads letters one by one (office panel and the manager's letters page).
// The percentage is always the real one: letters finished out of all of them. Only the bar moves smoothly: between
// two letters it creeps toward the next one (never past 90% of the way), then jumps to the true place when that
// letter is done, so the bar never sits still for the seconds one letter takes.
import { ref, computed, watch, onMounted, onUnmounted } from "vue"
import { fa } from "../lib/api.js"

const props = defineProps({ processed: { type: Number, default: 0 }, total: { type: Number, default: 0 } })
const creep = ref(0)                      // 0..0.9 of the way to the next letter
let started = performance.now(), took = [], frame = 0

const percent = computed(() => props.total ? Math.round(100 * props.processed / props.total) : 0)
const width = computed(() => props.total ? Math.min(100, 100 * (props.processed + creep.value) / props.total) : 0)

// how long a letter takes: the average of the ones done so far (6 seconds before the first is done)
const expected = () => took.length ? took.reduce((a, b) => a + b, 0) / took.length : 6000
const tick = () => {
  const t = performance.now() - started
  creep.value = props.processed < props.total ? 0.9 * (1 - Math.exp(-t / expected())) : 0
  frame = requestAnimationFrame(tick)
}
watch(() => props.processed, (n, old) => {
  const now = performance.now()
  if (n > old) took.push((now - started) / (n - old))
  started = now; creep.value = 0
})
onMounted(() => { frame = requestAnimationFrame(tick) })
onUnmounted(() => cancelAnimationFrame(frame))
</script>

<template>
  <div class="agent-progress" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100" :aria-label="`پیشرفت دستیار: ${percent} درصد`">
    <div class="progress"><span :style="{ width: width + '%' }"></span></div>
    <b class="ap-percent">{{ fa(percent) }}٪</b>
  </div>
</template>

<style scoped>
.agent-progress { display: flex; align-items: center; gap: 12px; }
.agent-progress .progress { flex: 1; }
/* the bar is moved by the creep every frame, so its own width animation would only lag behind */
.agent-progress .progress span { transition: width .3s linear; }
.ap-percent { min-width: 3.2em; text-align: left; font-size: 14px; color: var(--primary-ink, var(--primary)); font-variant-numeric: tabular-nums; }
</style>
