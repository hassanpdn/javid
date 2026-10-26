<script setup>
// «از کجا؟» next to a number: opens the sum behind it, each part with the file and sheet it comes from,
// so anyone can check the number against the Excel files by hand.
// The box is placed under the button but kept inside the window, wherever the button sits.
import { ref, reactive, nextTick, onMounted, onUnmounted } from "vue"
import { fa } from "../lib/api.js"
import Icon from "../components/Icon.vue"

defineProps({ lines: { type: Array, default: () => [] }, label: { default: "از کجا؟" } })
const open = ref(false), root = ref(null), btn = ref(null), pos = reactive({ top: 0, left: 0 })
const WIDTH = 340
const toggle = async () => {
  open.value = !open.value
  if (!open.value) return
  const r = btn.value.getBoundingClientRect(), w = Math.min(WIDTH, window.innerWidth - 24)
  pos.top = r.bottom + 8
  pos.left = Math.max(12, Math.min(r.right - w, window.innerWidth - w - 12))
  pos.width = w
}
const close = (e) => { if (open.value && root.value && !root.value.contains(e.target)) open.value = false }
const away = () => { open.value = false }
onMounted(() => { document.addEventListener("click", close); window.addEventListener("scroll", away, true) })
onUnmounted(() => { document.removeEventListener("click", close); window.removeEventListener("scroll", away, true) })
</script>

<template>
  <span ref="root" class="how">
    <button ref="btn" type="button" class="how-btn" :aria-expanded="open" :aria-label="label || 'از کجا آمده؟'" @click.stop="toggle">
      <Icon name="info" :size="14" />{{ label }}</button>
    <Teleport to="body">
      <span v-if="open" class="how-pop" role="note" :style="{ top: pos.top + 'px', left: pos.left + 'px', width: pos.width + 'px' }" @click.stop>
        <span v-for="l in lines" :key="l" :class="['how-line', { sum: /^[=+−]/.test(l) }]">{{ fa(l) }}</span>
      </span>
    </Teleport>
  </span>
</template>
