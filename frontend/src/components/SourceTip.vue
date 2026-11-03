<script setup>
// «منبع» next to a number or a list, for the permanent account only: where its data comes from in the real business
// and how it enters the program (sources.py). Nothing shows for anyone else, and nothing is asked for them.
import { computed, onMounted } from "vue"
import { access } from "../lib/access.js"
import { maps, loadMap, findItem, lines } from "../lib/sources.js"
import HowTip from "../fabric/HowTip.vue"

const props = defineProps({ app: String, k: String })
onMounted(() => loadMap(props.app))
const item = computed(() => maps[props.app] && findItem(props.app, props.k))
</script>

<template>
  <HowTip v-if="access.admin && item" class="src-tip" :lines="lines(app, item)" label="منبع" />
</template>
