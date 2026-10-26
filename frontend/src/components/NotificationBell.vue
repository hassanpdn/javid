<script setup>
// Bell in the navbar: polls /notifications every 15s, opens a dropdown list and a detail dialog
import { ref, computed, watch, onMounted, onUnmounted } from "vue"
import { api, fa, lockScroll } from "../lib/api.js"
import { KINDS } from "../lib/constants.js"
import { gsap, motion } from "../lib/motion.js"
import { toast } from "../lib/notify.js"
import Icon from "./Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import KindIcon from "./KindIcon.vue"

// tab: the phone version, a button in the bottom tab bar whose list opens as a sheet
defineProps({ tab: { type: Boolean, default: false } })
const items = ref([]), unread = ref(0), open = ref(false), current = ref(null), filter = ref("all"), wrap = ref(null), icon = ref(null)
const filters = computed(() => [
  { key: "all", label: "همه" },
  { key: "unread", label: "خوانده‌نشده", n: unread.value },
  { key: "ack", label: "باید دیده شود", n: items.value.filter((n) => n.needs_ack && !n.ack_at).length },
])
const visible = computed(() => items.value.filter((n) =>
  filter.value === "unread" ? !n.read_at : filter.value === "ack" ? n.needs_ack && !n.ack_at : true))
let loaded = false
const ready = ref(false)
const seen = new Set()
const load = async () => {
  try {
    const d = await api("/notifications")
    // anything new since the last check gets a toast (not the ones already there when the page opened)
    const fresh = d.items.filter((n) => !seen.has(n.id) && !n.read_at)
    d.items.forEach((n) => seen.add(n.id))
    if (loaded) fresh.slice(0, 3).reverse().forEach((n) => toast({
      kind: n.kind, title: fa(n.title), body: n.body ? fa(n.body.split("\n")[0]) : "", action: { label: "مشاهده", run: () => show(n) },
    }))
    if (d.unread > unread.value) {
      // panels listen for this to reload their own data
      window.dispatchEvent(new Event("notifications-changed"))
      // ring the bell when something new arrives (not on the first load)
      if (loaded && motion && icon.value) gsap.fromTo(icon.value, { rotation: -18 }, { rotation: 0, duration: 1.2, ease: "elastic.out(1.2, .25)", transformOrigin: "50% 0" })
    }
    items.value = d.items; unread.value = d.unread; loaded = true; ready.value = true
  } catch {}
}
const show = async (n) => {
  open.value = false; current.value = n
  if (!n.read_at) { await api(`/notifications/${n.id}/read`, {}); load() }
}
const ack = async () => {
  await api(`/notifications/${current.value.id}/ack`, {})
  await load(); current.value = items.value.find((n) => n.id === current.value.id)
}
const readAll = async () => { await api("/notifications/read-all", {}); load() }
// close the panel when clicking anywhere outside it
const outside = (e) => { if (open.value && wrap.value && !wrap.value.contains(e.target)) open.value = false }
let timer
onMounted(() => { load(); timer = setInterval(load, 15000); document.addEventListener("click", outside) })
onUnmounted(() => { clearInterval(timer); document.removeEventListener("click", outside) })
watch(current, lockScroll)
</script>

<template>
  <div :class="['bell-wrap', { 'bell-tab': tab }]" ref="wrap">
    <button v-if="tab" :class="['tab', { on: open }]" @click="open = !open" :aria-label="'اعلان‌ها، ' + fa(unread) + ' خوانده‌نشده'" :aria-expanded="open">
      <span class="tab-ico" ref="icon"><Icon name="bell" :size="22" /><i v-if="unread" class="tab-badge">{{ fa(unread > 99 ? '99+' : unread) }}</i></span>
      <span class="tab-label">اعلان‌ها</span>
    </button>
    <button v-else class="icon-btn" :class="{ on: open }" @click="open = !open" :aria-label="'اعلان‌ها، ' + fa(unread) + ' خوانده‌نشده'">
      <span ref="icon"><Icon name="bell" :size="22" /></span>
      <span v-if="unread" class="badge-dot">{{ fa(unread > 99 ? '99+' : unread) }}</span>
    </button>

    <div v-if="open" v-pop:drop class="bell-panel">
      <header class="bp-head">
        <div class="bp-title-row"><b>اعلان‌ها</b><span v-if="unread" class="chip">{{ fa(unread) }} جدید</span></div>
        <button v-if="unread" class="link small" @click="readAll">همه خوانده شد</button>
      </header>
      <nav class="bp-filters">
        <button v-for="f in filters" :key="f.key" :class="{ on: filter === f.key }" @click="filter = f.key">
          {{ f.label }}<span v-if="f.n" class="bp-n">{{ fa(f.n) }}</span>
        </button>
      </nav>
      <div class="bp-list">
        <Skeleton v-if="!ready" kind="row" :count="3" class="bp-skel" />
        <div v-else-if="!visible.length" class="bp-empty">
          <span class="tint lg t-success"><Icon name="check" :size="24" /></span>
          <p>اعلانی در این بخش نیست.</p>
        </div>
        <button v-for="n in visible" :key="n.id" :class="['bp-item', { unread: !n.read_at }]" @click="show(n)">
          <KindIcon :kind="n.kind" />
          <span class="bp-body">
            <span class="bp-title">{{ fa(n.title) }}</span>
            <span class="bp-meta">
              <span>{{ (KINDS[n.kind] || KINDS.info).label }}</span>
              <span class="sep">·</span>
              <span>{{ fa(n.created_at) }}</span>
              <span v-if="n.needs_ack && !n.ack_at" class="bp-pill">باید دیده شود</span>
              <span v-else-if="n.ack_at" class="bp-pill ok">دیده شد</span>
            </span>
          </span>
          <span v-if="!n.read_at" class="bp-dot" aria-label="خوانده‌نشده"></span>
        </button>
      </div>
    </div>

    <div v-if="current" class="overlay" @click.self="current = null">
      <div class="dialog" v-pop>
        <div class="dlg-kind"><KindIcon :kind="current.kind" />{{ (KINDS[current.kind] || KINDS.info).label }}</div>
        <h3>{{ fa(current.title) }}</h3>
        <p class="muted small">{{ fa(current.created_at) }}</p>
        <div v-if="current.body" class="letter">{{ fa(current.body) }}</div>
        <p v-if="current.ack_at" class="check ok">✓ دیده شد: {{ fa(current.ack_at) }}</p>
        <div class="dialog-actions">
          <button v-if="current.needs_ack && !current.ack_at" class="btn primary" @click="ack"><Icon name="check" :size="18" />دیدم</button>
          <button class="btn ghost" @click="current = null">بستن</button>
        </div>
      </div>
    </div>
  </div>
</template>
