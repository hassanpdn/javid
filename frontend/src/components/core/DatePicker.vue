<script setup>
// Core: a Jalali date picker that looks like any other input. v-model is «1405/08/30» or null (empty, shown as the
// placeholder). Days before `min` (today when not given) can't be picked. clearable: a × empties it.
// The calendar opens under the field (above it when there is no room) and lives in <body> (lib/popover.js).
import { ref, computed } from "vue"
import { MONTHS, WEEKDAYS, faDigits, today, parse, format, compare, daysInMonth, weekday, jalaliText } from "../../lib/jalali.js"
import { usePopover } from "../../lib/popover.js"
import Icon from "../Icon.vue"
import "./picker.css"

const props = defineProps({
  modelValue: { type: String, default: null },
  min: { type: String, default: null },
  placeholder: { type: String, default: "انتخاب تاریخ" },
  label: { type: String, default: "تاریخ" },
  clearable: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue"])
const { open, field, pop, place, show, close, key } = usePopover()

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

const toggle = () => {
  if (open.value) return close()
  const start = chosen.value && !past(chosen.value) ? chosen.value : minDay.value
  view.value = { y: start.y, m: start.m }
  show(".dp-day.sel, .dp-day.today, .dp-day:not(:disabled)")
}
const pick = (j) => {
  if (past(j)) return
  emit("update:modelValue", format(j))
  close(true)
}
</script>

<template>
  <div ref="field" :class="['dp-field', { 'dp-on': open, 'dp-empty': !chosen }]">
    <button type="button" class="dp-open" :aria-label="label" :aria-expanded="open" aria-haspopup="dialog" @click="toggle">
      <Icon name="calendar" :size="19" />
      <span class="dp-value">{{ chosen ? jalaliText(chosen) : placeholder }}</span>
    </button>
    <button v-if="clearable && chosen" type="button" class="dp-clear" :aria-label="`پاک کردن ${label}`" @click="emit('update:modelValue', null)"><Icon name="x" :size="16" /></button>
  </div>
  <Teleport to="body">
    <div v-if="open" ref="pop" class="dp-pop dp-cal" role="dialog" :aria-label="label" :style="place" @keydown="key">
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

<style>
/* the calendar lives in <body>, so its styles are not scoped */
.dp-cal { width: 300px; }
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
</style>
