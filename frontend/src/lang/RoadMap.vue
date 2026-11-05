<script setup>
// The road: the twelve terms from Starter to Advanced as stations on a winding line, first one at the right. The part
// already walked is drawn in colour (once, when it appears), the current station pulses with «شما این‌جایید», a star
// marks each station that needs a new book. Rows hold 6, 4 or 3 stations by the width it gets (a ResizeObserver).
// stations: [{key, state, level, fa, cefr, score, term}], state: done, skipped, current, next, future (or "map": the
// road itself, no learner). v-model: the selected station's key; detail: the box under the road with its book.
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue"
import { fa } from "../lib/api.js"
import { term } from "./lib.js"
import Icon from "../components/Icon.vue"
import BookCover from "./BookCover.vue"

const props = defineProps({ stations: Array, compact: { type: Boolean, default: false }, detail: { type: Boolean, default: true } })
const picked = defineModel()
const root = ref(null), width = ref(0), drawn = ref(false)
let ro
onMounted(() => {
  ro = new ResizeObserver(([e]) => { width.value = Math.round(e.contentRect.width) })
  ro.observe(root.value)
  nextTick(() => requestAnimationFrame(() => { drawn.value = true }))
})
onUnmounted(() => ro?.disconnect())

const cols = computed(() => width.value >= 860 ? 6 : width.value >= 520 ? 4 : 3)
const rowH = computed(() => props.compact ? 112 : 132)
const PAD = 50, TOP = 44, BULGE = 46
const points = computed(() => {
  const w = width.value, n = cols.value, step = (w - 2 * PAD) / (n - 1)
  return props.stations.map((s, i) => {
    const r = Math.floor(i / n), j = i % n
    return { x: r % 2 === 0 ? w - PAD - j * step : PAD + j * step, y: TOP + r * rowH.value, r }
  })
})
const height = computed(() => TOP + (Math.ceil(props.stations.length / cols.value) - 1) * rowH.value + 78)
function pathTo(k) {
  const p = points.value
  if (!p.length || k < 0) return ""
  let d = `M${p[0].x},${p[0].y}`
  for (let i = 1; i <= k && i < p.length; i++) {
    const a = p[i - 1], b = p[i]
    if (a.r === b.r) d += ` L${b.x},${b.y}`
    else {
      const out = a.r % 2 === 0 ? -BULGE : BULGE
      d += ` C${a.x + out},${a.y} ${b.x + out},${b.y} ${b.x},${b.y}`
    }
  }
  return d
}
const full = computed(() => pathTo(props.stations.length - 1))
const reached = computed(() => {
  const i = props.stations.findIndex((s) => s.state === "current")
  if (i >= 0) return i
  return props.stations.reduce((m, s, k) => (s.state === "done" || s.state === "skipped" ? k : m), -1)
})
const walked = computed(() => pathTo(reached.value))
const STATE = { done: "", skipped: "از تعیین سطح", current: "این ترم", next: "ترم بعد", future: "", map: "" }
const selected = computed(() => props.stations.find((s) => s.key === picked.value))
const info = computed(() => selected.value && term(selected.value.key))
</script>

<template>
  <div class="lg-road" ref="root">
    <div v-if="width" class="lg-stage" :style="{ height: height + 'px' }" role="list" aria-label="مسیر سطح‌ها">
      <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" aria-hidden="true">
        <defs><linearGradient id="lg-grad" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--lv-S)" /><stop offset="1" :stop-color="`var(--lv-${stations[Math.max(0, reached)]?.level || 'S'})`" /></linearGradient></defs>
        <path class="lg-track" :d="full" />
        <path v-if="walked" :class="['lg-done', { drawn }]" :d="walked" pathLength="1" />
      </svg>
      <button v-for="(s, i) in stations" :key="s.key" type="button" role="listitem"
              :class="['lg-node', 'lg-lv', 'lv-' + s.level, s.state, { sel: picked === s.key }]"
              :style="{ left: points[i].x + 'px', top: points[i].y - (s.state === 'current' ? 28 : 23) + 'px' }"
              :aria-label="`${s.fa}${STATE[s.state] ? '، ' + STATE[s.state] : ''}`" :aria-pressed="picked === s.key" @click="picked = s.key">
        <span v-if="s.state === 'current'" class="lg-here">شما این‌جایید</span>
        <span class="lg-dot">
          <Icon v-if="s.state === 'done'" name="check" :size="22" />
          <b v-else>{{ s.cefr === "Pre-A1" ? "S" : s.cefr }}</b>
          <span v-if="s.new_book && !compact && s.state !== 'done' && s.state !== 'skipped'" class="lg-badge" title="کتاب جدید"><Icon name="book" :size="12" /></span>
        </span>
        <span class="lg-name">{{ fa(s.fa) }}</span>
        <span v-if="s.state === 'done' && s.score" class="lg-state">نمره {{ fa(s.score) }}</span>
        <span v-else-if="STATE[s.state]" class="lg-state">{{ STATE[s.state] }}</span>
      </button>
    </div>

    <div v-if="detail && info" :class="['lg-info', 'lg-lv', 'lv-' + info.level]">
      <BookCover :level="info.level" :cefr="info.cefr" :units="info.units" />
      <div class="lg-info-body">
        <b>{{ fa(info.fa) }} <span class="lg-en muted small">· {{ info.en }}</span></b>
        <small class="muted">کتاب {{ info.book }}، درس‌های {{ fa(info.units[0]) }} تا {{ fa(info.units[1]) }} · ۲۰ جلسه‌ی ۹۰ دقیقه‌ای</small>
        <small class="muted">شهریه‌ی ترم {{ fa(info.fee_text) }}<template v-if="info.num === 1"> · کتاب جدید {{ fa(info.book_price_text) }}</template><template v-else> · همان کتاب ترم قبل</template></small>
        <small v-if="selected.state === 'done'" class="ok">گذرانده شد<template v-if="selected.term"> در {{ fa(selected.term) }}</template><template v-if="selected.score">، نمره‌ی {{ fa(selected.score) }}</template></small>
        <small v-else-if="selected.state === 'skipped'" class="muted">این ترم را آزمون تعیین سطح لازم ندانست.</small>
        <div class="lg-topics lg-en"><span v-for="(t, k) in info.unit_topics" :key="k">{{ info.units[0] + k }}. {{ t }}</span></div>
      </div>
    </div>
  </div>
</template>
