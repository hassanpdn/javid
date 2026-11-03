<script setup>
// «شلوغی امروز»: one calm page for a busy morning. Today's arrivals in the order they come, each with its room and
// whether it is ready; the rooms housekeeping should do first (a guest is waiting for them, VIPs first); today's
// departures with what is left on each bill; and tomorrow's arrivals without a room, each with the room the assistant
// suggests, given all at once with one button.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { ROOM_TONE, STATUS_TONE } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open", "changed"])
const d = ref(null), busy = ref(false)
const load = async () => { d.value = await api("/hotel/peak") }
onMounted(() => retryable(load))
async function assign() {
  busy.value = true
  try { const r = await api("/hotel/assign/tomorrow", {}); toast({ tone: "success", title: `${fa(r.assigned.length)} اتاق برای ورودی‌های فردا انتخاب شد` }); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div v-if="!d" class="card"><Skeleton kind="row" :count="8" /></div>
  <div v-else class="grid grid-cols-12 gap-6">
    <section class="card col-span-12 xl:col-span-7 flex flex-col gap-3" data-tour="ht-arrivals">
      <div class="card-head">ورودی‌های امروز <span class="count">{{ fa(d.arrivals.length) }}</span></div>
      <p v-if="!d.arrivals.length" class="muted small">امروز ورودی نداریم.</p>
      <ul class="ht-list">
        <li v-for="a in d.arrivals" :key="a.id">
          <button :class="['card', 'ht-row', a.status !== 'in_house' && a.room_status === 'dirty' ? 'tone-warning' : '']" @click="emit('open', a.id)">
            <span class="ht-when"><b>{{ fa(a.eta || '14:00') }}</b><small>{{ a.status === 'in_house' ? 'رسید' : 'منتظر' }}</small></span>
            <span class="ht-row-body">
              <b>{{ a.guest }}<template v-if="a.vip"> · ویژه</template></b>
              <span class="ht-meta">{{ a.type_text }} · {{ fa(a.people_text) }} · {{ fa(a.nights_count) }} شب</span>
              <span class="ht-tags">
                <span v-if="!a.room" class="tag ht-t-danger">بی‌اتاق</span>
                <span v-else :class="['tag', 'ht-t-' + ROOM_TONE[a.room_status]]">اتاق {{ fa(a.room) }} · {{ a.room_status_text }}</span>
                <span :class="['tag', 'ht-t-' + STATUS_TONE[a.status]]">{{ a.status_text }}</span>
              </span>
            </span>
            <Icon name="chevron" :size="18" class="ht-go" />
          </button>
        </li>
      </ul>
    </section>
    <div class="col-span-12 xl:col-span-5 flex flex-col gap-6">
      <section class="card flex flex-col gap-2" data-tour="ht-first">
        <div class="card-head">اول این اتاق‌ها تمیز شود <span class="count">{{ fa(d.first.length) }}</span></div>
        <p class="muted small">اتاق‌هایی که مهمان امروزشان در راه است، به ترتیب ساعت رسیدن؛ مهمان ویژه اول.</p>
        <p v-if="!d.first.length" class="muted small">همه‌ی اتاق‌های ورودی‌ها آماده است.</p>
        <ol class="ht-mini"><li v-for="r in d.first" :key="r.room_id"><div class="ht-row-top"><b>اتاق {{ fa(r.room) }}<template v-if="r.vip"> · ویژه</template></b><span class="tag ht-t-warning">ساعت {{ fa(r.eta) }}</span></div>
          <small class="muted">{{ r.guest }} · {{ r.leaving }}</small></li></ol>
      </section>
      <section class="card flex flex-col gap-2" data-tour="ht-tomorrow">
        <div class="card-head"><span class="grow">ورودی‌های فردا بی‌اتاق</span><span class="count">{{ fa(d.tomorrow.length) }}</span></div>
        <p v-if="!d.tomorrow.length" class="muted small">همه‌ی ورودی‌های فردا اتاق دارند.</p>
        <template v-else>
          <ul class="ht-mini"><li v-for="b in d.tomorrow" :key="b.id"><div class="ht-row-top"><button class="ht-link" @click="emit('open', b.id)">{{ b.guest }}</button>
            <span v-if="b.suggest.length" class="tag ht-t-info">اتاق {{ fa(b.suggest[0].number) }}</span><span v-else class="tag ht-t-danger">اتاقی نیست</span></div>
            <small class="muted">{{ b.type_text }} · {{ fa(b.nights_count) }} شب<template v-if="b.suggest.length"> · {{ b.suggest[0].why[0] }}</template></small></li></ul>
          <button class="btn primary sm" style="align-self: flex-start" :disabled="busy" @click="assign"><Icon name="check" :size="14" />پذیرفتن همه‌ی پیشنهادها</button>
        </template>
      </section>
      <section class="card flex flex-col gap-2">
        <div class="card-head">خروجی‌های امروز <span class="count">{{ fa(d.departures.length) }}</span></div>
        <ul class="ht-mini"><li v-for="b in d.departures" :key="b.id"><div class="ht-row-top"><button class="ht-link" @click="emit('open', b.id)">اتاق {{ fa(b.room) }} · {{ b.guest }}</button>
          <span v-if="b.status === 'out'" class="tag ht-t-secondary">رفت</span><span v-else-if="b.balance > 0" class="tag ht-t-danger">مانده {{ fa(b.balance_text) }}</span><span v-else class="tag ht-t-success">تسویه</span></div></li></ul>
      </section>
    </div>
  </div>
</template>
