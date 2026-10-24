<script setup>
// tinted icon for a notification kind
import { computed } from "vue"
import { KINDS } from "../lib/constants.js"
import Icon from "./Icon.vue"

const props = defineProps(["kind"])
const k = computed(() => KINDS[props.kind] || KINDS.info)
</script>

<template><span :class="['tint', 'sm', 't-' + k.tone]"><Icon :name="k.icon" :size="18" /></span></template>
