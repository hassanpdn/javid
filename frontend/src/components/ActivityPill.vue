<script setup>
// Navbar pill that says the assistant is working in the background, so results never appear out of nowhere
import { computed } from "vue"
import { activity } from "../lib/notify.js"
import { fa } from "../lib/api.js"

const labels = computed(() => [...activity.values()])
</script>

<template>
  <Transition name="pill">
    <div v-if="labels.length" class="activity-pill" role="status" aria-live="polite">
      <span class="ap-dot"><i></i></span>
      <span class="ap-text">{{ fa(labels[labels.length - 1]) }}</span>
      <span v-if="labels.length > 1" class="ap-more">+{{ fa(labels.length - 1) }}</span>
    </div>
  </Transition>
</template>
