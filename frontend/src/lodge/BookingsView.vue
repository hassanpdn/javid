<script setup>
// «رزروها»: waiting for the host (requests, deposits, receipts), confirmed and coming, past stays, and the ones that
// were turned down or cancelled; search by name, mobile or booking number.
import { ref, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { STATUS_TONE } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const list = ref(null), q = ref(""), when = ref("open")
const load = async () => { list.value = await api(`/lodge/bookings?when=${when.value}&q=${encodeURIComponent(q.value.trim())}`) }
let timer
watch(q, () => { clearTimeout(timer); timer = setTimeout(() => load().catch(() => {}), 250) })
watch(when, () => { list.value = null; load().catch(() => {}) })
onMounted(() => retryable(load))
const WHEN = { open: "منتظر کار", coming: "قطعی و پیش رو", past: "گذشته", closed: "رد و لغو" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="k-toolbar">
      <input v-model="q" class="k-search" placeholder="جستجو: نام، شماره‌ی همراه یا شماره‌ی رزرو" aria-label="جستجو">
      <div class="lo-chips" role="radiogroup" aria-label="کدام رزروها"><button v-for="(t, k) in WHEN" :key="k" type="button" role="radio" :aria-checked="when === k" :class="{ on: when === k }" @click="when = k">{{ t }}</button></div>
    </div>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="file" :size="32" /><p class="muted">رزروی در این فهرست نیست.</p></div>
    <ul v-else class="k-list">
      <li v-for="b in list" :key="b.id">
        <button class="card k-row" @click="emit('open', b.id)">
          <span class="k-when"><b>{{ fa(b.arrive_text.split(' ').slice(1).join(' ')) }}</b><small>{{ fa(b.nights_count) }} شب</small></span>
          <span class="k-row-body">
            <b>{{ b.guest }} · {{ b.unit }}</b>
            <span class="k-meta">{{ fa(b.adults) }} نفر · {{ fa(b.total_text) }} · از {{ b.source_text }}</span>
            <span class="k-tags"><span :class="['tag', 'k-t-' + STATUS_TONE[b.status]]">{{ b.status_text }}</span><span v-if="b.unread" class="tag k-t-info">پیام جدید</span></span>
          </span>
          <Icon name="chevron" :size="18" class="k-go" />
        </button>
      </li>
    </ul>
  </div>
</template>
