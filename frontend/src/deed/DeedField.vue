<script setup>
// One field of the review form: the value to correct, how surely it was read, the line of the deed it came from,
// what is wrong with it, and, when pages disagree, the other values to pick from.
import { computed } from "vue"
import { fa } from "../lib/api.js"
import { CONFIDENCE } from "./lib.js"

const props = defineProps({ label: String, field: Object, wide: Boolean, disabled: Boolean })
const model = defineModel({ type: String, default: "" })
defineEmits(["look"])
const conf = computed(() => CONFIDENCE[props.field?.confidence || "none"])
const unsure = computed(() => ["low", "medium"].includes(props.field?.confidence) && !props.field?.edited)
</script>

<template>
  <div :class="['dv-field', { 'dv-wide': wide, 'dv-unsure': unsure, 'dv-low': field?.confidence === 'low' && !field?.edited }]">
    <div class="dv-head">
      <span class="dv-label">{{ label }}</span>
      <span :class="['dv-conf', 'tone-' + conf.tone]">{{ field?.edited ? "اصلاح شد" : conf.text }}</span>
    </div>
    <input v-model="model" :disabled="disabled" :aria-invalid="!!field?.issues?.length" :aria-label="label" @focus="$emit('look', field?.page)" />
    <button v-if="field?.source" type="button" class="dv-source" @click="$emit('look', field.page)">
      از صفحه‌ی {{ fa(field.page || 1) }}: «{{ fa(field.source) }}»
    </button>
    <p v-for="i in field?.issues || []" :key="i" class="dv-issue">{{ fa(i) }}</p>
    <div v-if="field?.conflicts?.length" class="dv-conflicts">
      <span>مقدارهای دیگر:</span>
      <button v-for="c in field.conflicts" :key="c.page + '-' + c.value" type="button" class="chip-btn" :disabled="disabled"
              @click="model = fa(c.value); $emit('look', c.page)">{{ fa(c.value) }} (صفحه‌ی {{ fa(c.page) }})</button>
    </div>
  </div>
</template>

<style scoped>
.dv-field { display: flex; flex-direction: column; gap: 6px; min-width: 0; padding: 10px 12px; border-radius: var(--radius-sm); border: 1px solid transparent; }
.dv-wide { grid-column: 1 / -1; }
.dv-unsure { background: var(--warning-soft); }
.dv-low { background: var(--danger-soft); border-color: color-mix(in srgb, var(--danger) 35%, transparent); }
.dv-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.dv-label { font-size: 13.5px; font-weight: 700; color: var(--ink); }
.dv-conf { flex: none; font-size: 11.5px; padding: 1px 9px; border-radius: 999px; }
.tone-success { background: var(--success-soft); color: var(--success-ink); }
.tone-warning { background: var(--warning-soft); color: var(--warning-ink); }
.tone-danger { background: var(--danger-soft); color: var(--danger-ink); }
.tone-secondary { background: var(--secondary-soft); color: var(--secondary-ink); }
input { width: 100%; font: inherit; font-size: 15px; padding: 8px 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--panel); color: var(--ink); outline: none; }
input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-soft); }
input[aria-invalid="true"] { border-color: var(--danger); }
input:disabled { opacity: .75; }
.dv-source { align-self: flex-start; max-width: 100%; padding: 0; border: 0; background: none; cursor: pointer; text-align: right; font: inherit; font-size: 12px; line-height: 1.8; color: var(--muted); overflow-wrap: anywhere; }
.dv-source:hover { color: var(--primary-ink); }
.dv-issue { margin: 0; font-size: 12.5px; line-height: 1.8; color: var(--danger-ink); }
.dv-conflicts { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ink); }
</style>
