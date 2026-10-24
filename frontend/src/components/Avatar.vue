<script setup>
import { toneOf } from "../lib/constants.js"
defineProps(["name", "size", "tone"])
</script>

<template>
  <span :class="['avatar', 't-' + (tone || toneOf(name))]"
        :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px', fontSize: (size || 40) * 0.42 + 'px' }">{{ (name || '?')[0] }}</span>
</template>
