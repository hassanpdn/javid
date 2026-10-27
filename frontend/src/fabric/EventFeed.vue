<script setup>
// «هم‌اکنون»: the event log as it happens. Every change in the app (an invoice, a file replaced, a reminder,
// a login) has a line with who and when. It asks the server for new lines every few seconds;
// new ones slide in and the files they touched light up in the picture above (emit "changed").
import { ref, computed, onMounted, onUnmounted } from "vue"
import { api, fa } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ limit: { default: 6 }, full: { type: Boolean, default: false } })
const emit = defineEmits(["changed"])
const items = ref(null), fresh = ref(new Set()), open = ref(null)
const LOOK = { invoice: ["file", "success"], upload: ["refresh", "warning"], reminder: ["message", "info"], login: ["user", "secondary"], import: ["sparkles", "primary"],
               web_order: ["message", "success"], customer: ["user", "info"] }
// the short feed leaves out logins; the full log keeps everything
const shown = computed(() => props.full ? items.value : items.value.filter((e) => e.kind !== "login").slice(0, props.limit))
let timer
const load = async () => {
  const after = items.value?.length ? items.value[0].id : 0
  const rows = await api("/fabric/events" + (after ? `?after=${after}` : ""))
  if (!items.value) { items.value = rows; return }
  if (!rows.length) return
  fresh.value = new Set(rows.map((r) => r.id))
  items.value = [...rows, ...items.value].slice(0, 60)
  emit("changed", [...new Set(rows.flatMap((r) => r.detail?.files || []))])
}
onMounted(async () => { await load(); timer = setInterval(() => load().catch(() => {}), 6000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <section class="card ef">
    <div class="card-head"><span class="grow">{{ full ? 'همه‌ی رویدادها' : 'هم‌اکنون' }} <small>هر تغییر با نام و ساعت</small></span>
      <span class="ef-live"><i></i>زنده</span></div>
    <Skeleton v-if="!items" kind="row" round :count="4" />
    <p v-else-if="!items.length" class="muted small">هنوز رویدادی نیست.</p>
    <TransitionGroup v-else name="ef" tag="ul" class="ef-list">
      <li v-for="e in shown" :key="e.id" :class="{ fresh: fresh.has(e.id) }">
        <span :class="['tint', 'sm', 't-' + (LOOK[e.kind] || LOOK.import)[1]]"><Icon :name="(LOOK[e.kind] || LOOK.import)[0]" :size="16" /></span>
        <div class="ef-body">
          <span>{{ fa(e.text) }}</span>
          <small class="muted">{{ e.who }}<template v-if="e.role"> · {{ e.role }}</template> · {{ e.today ? '' : fa(e.day) + ' ' }}{{ fa(e.time) }}</small>
          <button v-if="e.detail?.steps || e.detail?.changes?.length" class="link small ef-more" @click="open = open === e.id ? null : e.id">
            {{ open === e.id ? 'بستن' : 'در کدام فایل‌ها؟' }}</button>
          <ul v-if="open === e.id" class="ef-steps">
            <li v-for="s in e.detail.steps || []" :key="s.file"><b>{{ s.file }}</b> {{ fa(s.text) }}</li>
            <li v-for="c in e.detail.changes || []" :key="c">{{ fa(c) }}</li>
          </ul>
        </div>
      </li>
    </TransitionGroup>
  </section>
</template>
