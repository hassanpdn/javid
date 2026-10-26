<script setup>
// The toast stack: top of the screen on phones, top-left corner on wide screens.
// Each toast closes itself after its timeout; hovering or focusing it pauses the countdown.
import { watch, onUnmounted } from "vue"
import { toasts, dismiss } from "../lib/notify.js"
import { KINDS } from "../lib/constants.js"
import Icon from "./Icon.vue"

const TONE_ICON = { success: "check", info: "bell", primary: "sparkles", warning: "clock", danger: "alert" }
const look = (t) => t.kind ? (KINDS[t.kind] || KINDS.info) : { icon: TONE_ICON[t.tone] || "bell", tone: t.tone }

// one timer per toast, paused while the pointer or keyboard focus is on it
const timers = new Map()
const start = (t) => {
  if (!t.timeout || timers.has(t.id)) return
  const left = t._left ?? t.timeout
  t._started = Date.now()
  timers.set(t.id, setTimeout(() => { timers.delete(t.id); dismiss(t.id) }, left))
}
const pause = (t) => {
  if (!timers.has(t.id)) return
  clearTimeout(timers.get(t.id)); timers.delete(t.id)
  t._left = (t._left ?? t.timeout) - (Date.now() - t._started)
  t.paused = true
}
const resume = (t) => { t.paused = false; start(t) }
// every new toast starts its countdown as soon as it is shown
watch(() => toasts.map((t) => t.id), () => toasts.forEach(start), { immediate: true })
const act = (t) => { t.action.run(); dismiss(t.id) }
onUnmounted(() => timers.forEach(clearTimeout))
</script>

<template>
  <div class="toasts" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" :class="['toast', 't-line-' + look(t).tone]"
           @mouseenter="pause(t)" @mouseleave="resume(t)" @focusin="pause(t)" @focusout="resume(t)">
        <span :class="['tint', 'sm', 't-' + look(t).tone]"><Icon :name="look(t).icon" :size="18" /></span>
        <div class="toast-body">
          <b>{{ t.title }}</b>
          <small v-if="t.body">{{ t.body }}</small>
          <button v-if="t.action" class="toast-action" @click="act(t)">{{ t.action.label }}</button>
        </div>
        <button class="icon-btn sm" @click="dismiss(t.id)" aria-label="بستن"><Icon name="x" :size="16" /></button>
        <span v-if="t.timeout" class="toast-time" :style="{ animationDuration: t.timeout + 'ms', animationPlayState: t.paused ? 'paused' : 'running' }"></span>
      </div>
    </TransitionGroup>
  </div>
</template>
