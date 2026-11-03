<script setup>
// «نقشه‌ی داده» of one assistant (the permanent account, from its card on the assistants page): every piece of data
// it uses, grouped by how it enters the program, with where it lives in the real business and who enters it; then
// every number it computes, with what it is made of. For explaining the assistant to a business and training its
// staff; it prints on its own (the rest of the page is hidden when printing).
import { computed, onMounted } from "vue"
import { maps, loadMap } from "../lib/sources.js"
import Icon from "./Icon.vue"

const props = defineProps({ app: String, title: String })
const emit = defineEmits(["close"])
onMounted(() => loadMap(props.app))
const m = computed(() => maps[props.app])
const ways = computed(() => {
  if (!m.value) return []
  const raw = m.value.items.filter((i) => i.kind === "raw")
  return Object.entries(m.value.ways).filter(([k]) => k !== "computed").map(([k, t]) => ({ key: k, text: t, items: raw.filter((i) => i.way === k) })).filter((w) => w.items.length)
})
const computedItems = computed(() => m.value?.items.filter((i) => i.kind === "computed") || [])
// print only this map: everything else in <body> is hidden while printing (main.css, body.dm-printing)
const print = () => { document.body.classList.add("dm-printing"); window.print(); document.body.classList.remove("dm-printing") }
</script>

<template>
  <Teleport to="body"><div class="overlay dm-overlay" @click.self="emit('close')">
    <article class="dm" role="dialog" :aria-label="'نقشه‌ی داده‌ی ' + title">
      <header class="dm-head"><div><small>نقشه‌ی داده</small><h2>{{ title }}</h2></div>
        <span class="grow"></span><button class="dm-btn" @click="print"><Icon name="file" :size="16" />چاپ</button>
        <button class="dm-x" aria-label="بستن" @click="emit('close')"><Icon name="x" /></button></header>
      <p v-if="!m" class="dm-muted">در حال بارگیری…</p>
      <template v-else>
        <p class="dm-muted">هر داده در کسب‌وکار واقعی کجاست و از چه راهی وارد برنامه می‌شود؛ و هر عددی که برنامه نشان می‌دهد از کدام داده‌ها ساخته شده است.</p>
        <h3>داده‌هایی که وارد برنامه می‌شوند</h3>
        <section v-for="w in ways" :key="w.key" class="dm-way">
          <h4>{{ w.text }}</h4>
          <ul><li v-for="i in w.items" :key="i.key"><b>{{ i.name }}</b><span>در کسب‌وکار واقعی: {{ i.real }}</span><span>چه کسی: {{ i.who }}</span><small v-if="i.note">{{ i.note }}</small></li></ul>
        </section>
        <h3>عددهایی که برنامه حساب می‌کند</h3>
        <ul class="dm-calc"><li v-for="i in computedItems" :key="i.key"><b>{{ i.name }}</b><span>{{ i.rule }}</span><small>ساخته از: {{ i.made_of_text.join('، ') }}</small></li></ul>
      </template>
    </article>
  </div></Teleport>
</template>

<style scoped>
.dm-overlay { align-items: flex-start; overflow-y: auto; padding: 24px 12px; }
.dm { width: min(860px, 100%); margin: 0 auto; background: #fff; color: #2f2b3d; border-radius: 22px; padding: 24px; line-height: 1.9; text-align: right; }
.dm-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.dm-head small { color: #6d6b77; }
.dm-head h2 { margin: 0; font-size: 22px; color: #2f2b3d; }
.dm-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 12px; border: 1px solid #dbdade; background: #fff; font: inherit; cursor: pointer; }
.dm-x { border: 0; background: none; cursor: pointer; color: #6d6b77; padding: 6px; }
.dm-btn:focus-visible, .dm-x:focus-visible { outline: 3px solid #7367f0; outline-offset: 2px; }
.dm-muted { color: #6d6b77; font-size: 14px; }
.dm h3 { margin: 22px 0 8px; font-size: 17px; color: #2f2b3d; }
.dm h4 { margin: 0 0 6px; font-size: 14.5px; color: #5a4fcf; }
.dm-way { padding: 12px 14px; border-radius: 14px; background: #f6f6f8; margin-bottom: 10px; }
.dm ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
.dm li { display: flex; flex-direction: column; gap: 1px; font-size: 13.5px; }
.dm li b { color: #2f2b3d; font-size: 14.5px; }
.dm li small { color: #6d6b77; font-size: 12.5px; }
.dm-calc li { padding: 10px 14px; border-radius: 14px; border: 1px solid #ececf0; }
@media print {
  .dm-overlay { position: static; background: none; padding: 0; }
  .dm { border-radius: 0; padding: 0; }
  .dm-btn, .dm-x { display: none; }
}
</style>
