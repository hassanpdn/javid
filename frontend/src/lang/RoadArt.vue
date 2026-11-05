<script setup>
// The login drawing: a winding road up a hill with a station for each level, from Starter at the foot to Advanced
// at the flag on top. Its pieces rise in on the login page (class es-house).
const STOPS = [[64, 268, "var(--lv-S)"], [172, 248, "var(--lv-A1)"], [292, 214, "var(--lv-A2)"], [214, 160, "var(--lv-B1)"], [110, 118, "var(--lv-B2)"], [214, 70, "var(--lv-C1)"]]
const LABELS = ["S", "A1", "A2", "B1", "B2", "C1"]
</script>

<template>
  <svg viewBox="0 0 400 330" aria-hidden="true" class="shelves">
    <ellipse cx="200" cy="312" rx="180" ry="12" style="fill: var(--primary-soft)" />
    <path class="es-house" d="M20 300 C120 300 360 280 330 220 C300 170 120 190 110 140 C100 90 200 96 214 70" fill="none" style="stroke: var(--line)" stroke-width="16" stroke-linecap="round" />
    <path class="es-house" d="M20 300 C120 300 360 280 330 220 C300 170 120 190 110 140 C100 90 200 96 214 70" fill="none" style="stroke: var(--panel)" stroke-width="3" stroke-dasharray="8 10" stroke-linecap="round" />
    <g v-for="(s, i) in STOPS" :key="i" class="es-house">
      <circle :cx="s[0]" :cy="s[1]" r="19" :style="{ fill: s[2] }" />
      <circle :cx="s[0]" :cy="s[1]" r="19" fill="none" stroke="#fff" stroke-width="3" opacity=".7" />
      <text :x="s[0]" :y="s[1] + 5" text-anchor="middle" fill="#fff" style="font-size: 13px; font-weight: 800; font-family: Vazirmatn, sans-serif">{{ LABELS[i] }}</text>
    </g>
    <g class="es-house">
      <line x1="214" y1="51" x2="214" y2="14" style="stroke: var(--ink)" stroke-width="3" stroke-linecap="round" />
      <path d="M214 14 h34 l-8 9 l8 9 h-34 z" style="fill: var(--sun)" />
    </g>
  </svg>
</template>
