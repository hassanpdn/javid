<script setup>
// Core: a Jalali date picker. v-model is «1405/08/30» or null. Days before `min` (today when not given) can't be
// picked. The calendar opens under the field (above it when there is no room) and is moved to <body>, so a dialog
// that scrolls can't cut it off. Colours come from the theme tokens; a dark page can set the --dp-* variables.
import { ref, computed, watch, nextTick, onBeforeUnmount } from "vue"
import { MONTHS, WEEKDAYS, faDigits, today, parse, format, compare, daysInMonth, weekday, jalaliText } from "../../lib/jalali.js"
import Icon from "../Icon.vue"

const props = defineProps({
  modelValue: { type: String, default: null },
  min: { type: String, default: null },
  placeholder: { type: String, default: "انتخاب تاریخ" },
  label: { type: String, default: "تاریخ" },
})
const emit = defineEmits(["update:modelValue"])

const open = ref(false), field = ref(null), pop = ref(null), place = ref({})
const minDay = computed(() => parse(props.min) || today())
const chosen = computed(() => parse(props.modelValue))
const view = ref({ y: 0, m: 0 })   // the month on show

const cells = computed(() => {
  const { y, m } = view.value, n = daysInMonth(y, m)
  const blanks = Array.from({ length: weekday({ y, m, d: 1 }) }, () => null)
  return [...blanks, ...Array.from({ length: n }, (_, i) => ({ y, m, d: i + 1 }))]
})
const past = (j) => compare(j, minDay.value) < 0
const same = (a, b) => a && b && !compare(a, b)
const canBack = computed(() => view.value.y > minDay.value.y || (view.value.y === minDay.value.y && view.value.m > minDay.value.m))
const step = (n) => {
  let { y, m } = view.value
  m += n
  if (m < 1) { m = 12; y-- } else if (m > 12) { m = 1; y++ }
  view.value = { y, m }
}

const toggle = async () => {
  if (open.value) return close()
  const start = chosen.value && !past(chosen.value) ? chosen.value : minDay.value
  view.value = { y: start.y, m: start.m }
  open.value = true
  await nextTick()
  position()
  pop.value?.querySelector(".dp-day.sel, .dp-day.today, .dp-day:not(:disabled)")?.focus()
}
const close = () => { open.value = false }
const pick = (j) => {
  if (past(j)) return
  emit("update:modelValue", format(j))
  close()
  field.value?.focus()
}

// the calendar takes the field's colours (a page can set them on the field), since it is not inside it
const COLOURS = ["--dp-panel", "--dp-text", "--dp-muted", "--dp-accent"]
// under the field, or above it when the screen has no room below; kept inside the screen's width
const position = () => {
  if (!field.value || !pop.value) return
  const css = getComputedStyle(field.value)
  for (const v of COLOURS) pop.value.style.setProperty(v, css.getPropertyValue(v))
  const r = field.value.getBoundingClientRect(), h = pop.value.offsetHeight, w = pop.value.offsetWidth
  const below = window.innerHeight - r.bottom >= h + 12 || r.top < h + 12
  const left = Math.min(Math.max(8, r.right - w), window.innerWidth - w - 8)
  place.value = { top: (below ? r.bottom + 6 : r.top - h - 6) + "px", left: left + "px" }
}
const outside = (e) => {
  if (!pop.value?.contains(e.target) && !field.value?.contains(e.target)) close()
}
watch(open, (on) => {
  const f = on ? "addEventListener" : "removeEventListener"
  document[f]("pointerdown", outside, true)
  window[f]("resize", close); window[f]("scroll", position, true)
})
onBeforeUnmount(() => { open.value = false })
// Escape closes only the calendar, not the dialog it is in
const key = (e) => { if (e.key === "Escape") { e.stopPropagation(); close(); field.value?.focus() } }
</script>

<template>
  <button ref="field" type="button" :class="['dp-field', { open, empty: !chosen }]" :aria-expanded="open" aria-haspopup="dialog" @click="toggle">
    <Icon name="calendar" :size="18" />
    <span class="dp-value">{{ chosen ? jalaliText(chosen) : placeholder }}</span>
    <Icon name="chevron" :size="16" class="dp-chevron" />
  </button>
  <Teleport to="body">
    <div v-if="open" ref="pop" class="dp-pop" role="dialog" :aria-label="label" :style="place" @keydown="key">
      <div class="dp-head">
        <button type="button" class="dp-nav" :disabled="!canBack" aria-label="ماه قبل" @click="step(-1)"><Icon name="arrowRight" :size="17" /></button>
        <b>{{ MONTHS[view.m - 1] }} {{ faDigits(view.y) }}</b>
        <button type="button" class="dp-nav" aria-label="ماه بعد" @click="step(1)"><Icon name="arrowLeft" :size="17" /></button>
      </div>
      <div class="dp-grid">
        <span v-for="w in WEEKDAYS" :key="w" class="dp-wd">{{ w }}</span>
        <template v-for="(c, i) in cells" :key="i">
          <span v-if="!c"></span>
          <button v-else type="button" :disabled="past(c)" :aria-label="jalaliText(c)" :aria-pressed="same(c, chosen)"
                  :class="['dp-day', { sel: same(c, chosen), today: same(c, minDay) }]" @click="pick(c)">{{ faDigits(c.d) }}</button>
        </template>
      </div>
      <button type="button" class="dp-today" @click="pick(minDay)">امروز، {{ jalaliText(minDay) }}</button>
    </div>
  </Teleport>
</template>

<style scoped>
.dp-field { --dp-panel: var(--panel); --dp-field-bg: var(--panel); --dp-field-line: var(--line); --dp-text: var(--ink); --dp-muted: var(--muted); --dp-accent: var(--primary);
  display: flex; align-items: center; gap: 10px; width: 100%; height: 48px; padding: 0 14px; border-radius: 12px; cursor: pointer; text-align: right;
  font: inherit; font-size: 15px; color: var(--dp-text); background: var(--dp-field-bg); border: 1px solid var(--dp-field-line); transition: border-color .2s, box-shadow .2s; }
.dp-field > .ico:first-child { color: var(--dp-muted); }
.dp-field.empty .dp-value { color: var(--dp-muted); }
.dp-field:focus-visible, .dp-field.open { outline: none; border-color: var(--dp-accent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--dp-accent) 22%, transparent); }
.dp-value { flex: 1; min-width: 0; }
/* the chevron icon points left; turned to point down, and up while open */
.dp-chevron { color: var(--dp-muted); transform: rotate(-90deg); transition: transform .2s; }
.dp-field.open .dp-chevron { transform: rotate(90deg); }
</style>

<style>
/* the calendar lives in <body>, so its styles are not scoped */
.dp-pop { --dp-hover: color-mix(in srgb, var(--dp-accent) 12%, transparent);
  position: fixed; z-index: 90; width: 300px; max-width: calc(100vw - 16px); padding: 14px; border-radius: 18px; direction: rtl;
  color: var(--dp-text); background: var(--dp-panel); border: 1px solid color-mix(in srgb, var(--dp-text) 12%, transparent);
  box-shadow: 0 24px 60px -18px rgba(0,0,0,.55); animation: dp-in .18s ease both; }
.dp-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.dp-head b { font-size: 15px; }
.dp-nav { display: grid; place-items: center; width: 36px; height: 36px; border: 0; border-radius: 10px; cursor: pointer; color: var(--dp-text); background: transparent; }
.dp-nav:hover:not(:disabled), .dp-nav:focus-visible { background: var(--dp-hover); outline: none; }
.dp-nav:disabled { opacity: .3; cursor: default; }
.dp-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.dp-wd { display: grid; place-items: center; height: 28px; font-size: 12px; color: var(--dp-muted); }
.dp-day { display: grid; place-items: center; aspect-ratio: 1; border: 0; border-radius: 10px; cursor: pointer; font: inherit; font-size: 14px; color: var(--dp-text); background: transparent; }
.dp-day:hover:not(:disabled), .dp-day:focus-visible { background: var(--dp-hover); outline: none; }
.dp-day:disabled { opacity: .28; cursor: not-allowed; text-decoration: line-through; }
.dp-day.today { box-shadow: inset 0 0 0 1.5px var(--dp-accent); }
.dp-day.sel { color: #fff; font-weight: 700; background: var(--dp-accent); }
.dp-today { width: 100%; height: 38px; margin-top: 10px; border: 0; border-radius: 10px; cursor: pointer; font: inherit; font-size: 13px; color: var(--dp-accent); background: var(--dp-hover); }
.dp-today:hover, .dp-today:focus-visible { outline: none; filter: brightness(1.15); }
@keyframes dp-in { from { opacity: 0; transform: translateY(-6px); } }
@media (prefers-reduced-motion: reduce) { .dp-pop { animation: none; } }
</style>
