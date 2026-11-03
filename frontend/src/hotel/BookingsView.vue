<script setup>
// «رزروها»: search by name, phone, booking number or a booking site's reference; upcoming, in the house, waiting for a
// deposit, or past. Below, the waiting list, each with whether a room has come free for it.
import { ref, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { STATUS_TONE } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const list = ref(null), q = ref(""), when = ref("upcoming"), wait = ref([])
const load = async () => { list.value = await api(`/hotel/bookings?when=${when.value}&q=${encodeURIComponent(q.value.trim())}`) }
let timer
watch(q, () => { clearTimeout(timer); timer = setTimeout(() => load().catch(() => {}), 250) })
watch(when, () => { list.value = null; load().catch(() => {}) })
onMounted(() => retryable(async () => { await load(); wait.value = await api("/hotel/waitlist") }))
const done = async (w) => { await api(`/hotel/waitlist/${w.id}/done`, {}); wait.value = wait.value.filter((x) => x.id !== w.id); toast({ tone: "success", title: "از فهرست انتظار برداشته شد" }) }
const WHEN = { upcoming: "پیش رو", house: "مقیم", tentative: "منتظر بیعانه", past: "گذشته" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="k-toolbar">
      <input v-model="q" class="k-search" placeholder="جستجو: نام، شماره‌ی همراه، شماره‌ی رزرو یا کد سایت رزرو" aria-label="جستجو">
      <div class="ht-chips" role="radiogroup" aria-label="کدام رزروها"><button v-for="(t, k) in WHEN" :key="k" type="button" role="radio" :aria-checked="when === k" :class="{ on: when === k }" @click="when = k">{{ t }}</button></div>
    </div>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="file" :size="32" /><p class="muted">رزروی با این مشخصات نیست.</p></div>
    <ul v-else class="k-list">
      <li v-for="b in list" :key="b.id">
        <button class="card k-row" @click="emit('open', b.id)">
          <span class="k-when"><b>{{ fa(b.arrive_text.split(' ').slice(1).join(' ')) }}</b><small>{{ fa(b.nights_count) }} شب</small></span>
          <span class="k-row-body">
            <b>{{ b.guest }}<template v-if="b.vip"> · ویژه</template></b>
            <span class="k-meta">{{ b.type_text }}<template v-if="b.room"> · اتاق {{ fa(b.room) }}</template> · {{ fa(b.people_text) }} · {{ b.source_text }}</span>
            <span class="k-tags"><span :class="['tag', 'k-t-' + STATUS_TONE[b.status]]">{{ b.status_text }}</span><span class="tag">{{ fa(b.total_text) }}</span>
              <span v-if="b.status === 'tentative'" class="tag k-t-warning">بیعانه تا {{ fa(b.deposit_due_text) }}</span></span>
          </span>
          <Icon name="chevron" :size="18" class="k-go" />
        </button>
      </li>
    </ul>
    <section class="card flex flex-col gap-2" data-tour="ht-wait">
      <div class="card-head">فهرست انتظار <span class="count">{{ fa(wait.length) }}</span></div>
      <p v-if="!wait.length" class="muted small">کسی در فهرست انتظار نیست.</p>
      <ul class="k-mini"><li v-for="w in wait" :key="w.id"><div class="k-row-top"><b>{{ w.guest }}</b>
        <span :class="['tag', w.free > 0 ? 'k-t-success' : 'k-t-secondary']">{{ w.free > 0 ? 'جا باز شد' : 'هنوز پر است' }}</span></div>
        <small class="muted">{{ w.type_text }} · {{ fa(w.stay) }} · <span dir="ltr">{{ fa(w.phone) }}</span><template v-if="w.note"> · {{ w.note }}</template></small>
        <button class="btn ghost sm" style="align-self: flex-start" @click="done(w)">تماس گرفته شد، برداشتن از فهرست</button></li></ul>
    </section>
  </div>
</template>
