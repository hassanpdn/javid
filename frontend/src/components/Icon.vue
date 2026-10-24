<script setup>
import { ICONS } from "../lib/icons.js"
defineProps({ name: String, size: { default: 20 } })
</script>

<template>
  <span class="ico">
    <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="ICONS[name] || ICONS.sparkles" /></svg>
  </span>
</template>
