<script setup>
// Kit: the tape chart (hotel rooms, lodge units). Rows down, nights across; each booking a bar from its first night to
// its last, coloured by its status (s-… classes in styles/kit.css), weekend nights tinted, today marked. A bar with an
// id opens it. cols: [{date, day, weekday, weekend, today}]; rows: [{id, label, sub, bars: [{id, from, span, guest,
// status, vip}]}]; corner: the first header cell's word.
import { fa } from "../../lib/api.js"
defineProps({ cols: Array, rows: Array, corner: { type: String, default: "" } })
const emit = defineEmits(["open"])
const pos = (b) => ({ insetInlineStart: `calc(var(--room) + ${b.from} * var(--cell) + 2px)`, width: `calc(${b.span} * var(--cell) - 4px)` })
</script>

<template>
  <div class="k-grid-wrap">
    <div class="k-grid" :style="{ '--days': cols.length }">
      <div class="k-grow k-ghead"><span>{{ corner }}</span><span v-for="c in cols" :key="c.date" :class="{ we: c.weekend, td: c.today }">{{ c.weekday }}<br>{{ fa(c.day) }}</span></div>
      <div v-for="r in rows" :key="r.id" class="k-grow">
        <div class="k-gname"><b>{{ fa(r.label) }}</b><small>{{ r.sub }}</small></div>
        <span v-for="c in cols" :key="c.date" :class="['k-gcell', { we: c.weekend }]"></span>
        <button v-for="b in r.bars" :key="(b.id || 'o') + '-' + b.from" :class="['k-bar', 's-' + b.status]" :style="pos(b)" :title="b.guest" :disabled="!b.id"
                @click="b.id && emit('open', b.id)"><span v-if="b.vip" class="vip">ویژه</span>{{ b.guest }}</button>
      </div>
    </div>
  </div>
</template>
