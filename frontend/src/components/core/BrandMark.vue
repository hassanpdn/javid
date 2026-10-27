<script setup>
// Core: the Pudineh mark. Takes the text colour (currentColor), so it is white on a coloured badge and dark on a light page.
// The same shape is the site's favicon (public/favicon.svg).
defineProps({ size: { type: Number, default: 22 } })
</script>

<template>
  <svg class="brand-mark" viewBox="-127.3 -100 254.6 254.6" :width="size" :height="size" aria-hidden="true" focusable="false">
    <path fill="currentColor" fill-rule="evenodd" d="M-100 0A100 100 0 1 1 -37.928 92.528L-100 154.600L-100 116.263L-31.561 47.825A57.3 57.3 0 1 0 -47.825 31.561L-100 83.737ZM34.0 0A34.0 34.0 0 1 1 -34.0 0A34.0 34.0 0 1 1 34.0 0ZM-15.491 -16.041A22.3 22.3 0 0 1 15.768 15.768A2.3 2.3 0 0 1 12.516 12.516A17.7 17.7 0 0 0 -12.295 -12.732A2.3 2.3 0 0 1 -15.491 -16.041Z" />
  </svg>
</template>
