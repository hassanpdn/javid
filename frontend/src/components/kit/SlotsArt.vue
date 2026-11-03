<script setup>
// Kit: the login drawing of a booking business (dental, hotel, lodge): a calendar of slots, one left empty for the
// assistant to fill. Its pieces rise in on the login page (class es-house).
const SLOTS = [[30, 40, "#7367f0"], [140, 40, "#00bad1"], [250, 40, "#28c76f"], [30, 120, "#00bad1"], [140, 120, ""], [250, 120, "#7367f0"],
               [30, 200, "#28c76f"], [140, 200, "#7367f0"], [250, 200, "#00bad1"]]
</script>

<template>
  <svg viewBox="0 0 400 330" aria-hidden="true" class="shelves">
    <ellipse cx="200" cy="312" rx="180" ry="12" style="fill: var(--primary-soft)" />
    <g v-for="h in SLOTS" :key="h[0] + '-' + h[1]" class="es-house">
      <rect :x="h[0]" :y="h[1]" width="100" height="62" rx="12" :style="h[2] ? { fill: h[2] } : { fill: 'none', stroke: 'var(--primary)', strokeDasharray: '6 5', strokeWidth: 2 }" :opacity="h[2] ? .88 : 1" />
      <template v-if="h[2]"><rect :x="h[0] + 14" :y="h[1] + 16" width="50" height="7" rx="3" fill="#fff" opacity=".8" /><rect :x="h[0] + 14" :y="h[1] + 32" width="34" height="6" rx="3" fill="#fff" opacity=".5" /></template>
      <text v-else :x="h[0] + 50" :y="h[1] + 38" text-anchor="middle" style="fill: var(--primary); font-size: 26px; font-weight: 700">+</text>
    </g>
  </svg>
</template>
