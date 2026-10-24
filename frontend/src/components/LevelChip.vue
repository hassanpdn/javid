<script setup>
import { LEVEL_NAMES } from "../lib/constants.js"
defineProps(["level"])
</script>

<template><span :class="['level', 'l' + level]">{{ LEVEL_NAMES[level] }}</span></template>
