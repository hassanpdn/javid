<script setup>
// A term's book drawn in CSS, in its level's colour: «English Path», the level, the units. size "sm" for lists.
defineProps({ level: String, cefr: String, units: Array, size: { default: "" } })
</script>

<template>
  <span :class="['lg-book', 'lg-lv', 'lv-' + level, size]" aria-hidden="true">
    <small>English Path</small>
    <b :style="cefr === 'Pre-A1' ? { fontSize: size ? '11px' : '15px' } : null">{{ cefr === "Pre-A1" ? "Starter" : cefr }}</b>
    <span v-if="units">Units {{ units[0] }}–{{ units[1] }}</span>
  </span>
</template>
