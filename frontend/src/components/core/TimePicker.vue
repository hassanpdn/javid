<script setup>
// Core: a time picker that looks like any other input. v-model is «18:30» (24-hour). Hours and minutes are picked
// from two columns; minutes go in 5-minute steps. Times before `min` («14:20», e.g. now when the date is today)
// can't be picked. disabled: greyed out (e.g. until a date is chosen).
import { computed } from "vue"
import { faDigits } from "../../lib/jalali.js"
import { usePopover } from "../../lib/popover.js"
import Icon from "../Icon.vue"
import "./picker.css"

const props = defineProps({
  modelValue: { type: String, default: null },
  min: { type: String, default: null },
  placeholder: { type: String, default: "ساعت" },
  label: { type: String, default: "ساعت" },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue"])
const { open, field, pop, place, show, close, key } = usePopover()

const HOURS = Array.from({ length: 24 }, (_, i) => i)
const MINUTES = Array.from({ length: 12 }, (_, i) => i * 5)
const pad = (n) => String(n).padStart(2, "0")
const split = (s) => s ? s.split(":").map(Number) : [null, null]
const chosen = computed(() => split(props.modelValue))
const minT = computed(() => split(props.min))

// an hour is out when its last minute (:55) is still before min; a minute is out when hour:minute is before min
const hourOff = (h) => minT.value[0] !== null && h < minT.value[0]
const minuteOff = (h, m) => minT.value[0] !== null && h * 60 + m < minT.value[0] * 60 + minT.value[1]
const firstMinute = (h) => MINUTES.find((m) => !minuteOff(h, m)) ?? 0

const setHour = (h) => {
  const m = chosen.value[1] ?? 0
  emit("update:modelValue", `${pad(h)}:${pad(minuteOff(h, m) ? firstMinute(h) : m)}`)
}
const setMinute = (m) => {
  const h = chosen.value[0] ?? (minT.value[0] ?? 0)
  if (minuteOff(h, m)) return
  emit("update:modelValue", `${pad(h)}:${pad(m)}`)
  close(true)
}
const toggle = async () => {
  if (props.disabled) return
  if (open.value) return close()
  await show(".tp-cell.sel, .tp-cell:not(:disabled)")
  // bring the chosen hour and minute into view in their columns
  for (const el of pop.value?.querySelectorAll(".tp-cell.sel") || []) el.scrollIntoView({ block: "center" })
}
</script>

<template>
  <div ref="field" :class="['dp-field', { 'dp-on': open, 'dp-empty': !modelValue, 'dp-off': disabled }]">
    <button type="button" class="dp-open" :disabled="disabled" :aria-label="label" :aria-expanded="open" aria-haspopup="dialog" @click="toggle">
      <Icon name="clock" :size="19" />
      <span class="dp-value">{{ modelValue ? faDigits(modelValue) : placeholder }}</span>
    </button>
  </div>
  <Teleport to="body">
    <div v-if="open" ref="pop" class="dp-pop tp" role="dialog" :aria-label="label" :style="place" @keydown="key">
      <div class="tp-cols">
        <div class="tp-col">
          <span class="tp-title">ساعت</span>
          <div class="tp-list">
            <button v-for="h in HOURS" :key="h" type="button" :disabled="hourOff(h)" :class="['tp-cell', { sel: chosen[0] === h }]" @click="setHour(h)">{{ faDigits(pad(h)) }}</button>
          </div>
        </div>
        <div class="tp-col">
          <span class="tp-title">دقیقه</span>
          <div class="tp-list">
            <button v-for="m in MINUTES" :key="m" type="button" :disabled="minuteOff(chosen[0] ?? (minT[0] ?? 0), m)"
                    :class="['tp-cell', { sel: chosen[1] === m }]" @click="setMinute(m)">{{ faDigits(pad(m)) }}</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style>
/* the box lives in <body>, so its styles are not scoped */
.tp { width: 200px; padding: 10px; }
.tp-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.tp-col { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.tp-title { text-align: center; font-size: 12px; color: var(--dp-muted); }
.tp-list { display: flex; flex-direction: column; gap: 2px; height: 220px; overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; }
.tp-cell { flex: none; height: 36px; border: 0; border-radius: 9px; cursor: pointer; font: inherit; font-size: 14px; color: var(--dp-text); background: transparent; }
.tp-cell:hover:not(:disabled), .tp-cell:focus-visible { background: var(--dp-hover); outline: none; }
.tp-cell:disabled { opacity: .28; cursor: not-allowed; }
.tp-cell.sel { color: #fff; font-weight: 700; background: var(--dp-accent); }
</style>
