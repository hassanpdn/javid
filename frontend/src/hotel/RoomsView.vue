<script setup>
// «اتاق‌ها»: every room as a tile, in the order housekeeping should do them: rooms a guest arrives in today and that
// are still dirty first, then departures, then arrivals, then stayovers. Housekeeping marks a room clean or
// inspected, reports a repair (the room leaves the sale until the date given) and closes guests' requests. Made to
// be used on a phone (HousekeepingPanel), and by the desk on a computer.
import { ref, reactive, computed, onMounted } from "vue"
import { api, fa, hotelSession, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { hotelInfo, ROOM_TONE } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import DatePicker from "../components/core/DatePicker.vue"

const emit = defineEmits(["open"])
const role = hotelSession.user.role
const list = ref(null), filter = ref("todo"), busy = ref(0), repair = reactive({ id: 0, until: null, note: "" }), ask = reactive({ id: 0, text: "" })
const load = async () => { list.value = await api("/hotel/rooms") }
onMounted(() => retryable(load))
const shown = computed(() => (list.value || []).filter((r) => filter.value === "all" || (filter.value === "todo" ? r.status === "dirty" && !r.ooo : filter.value === "ooo" ? r.ooo : r.tasks.length)))
async function act(r, path, body, title) {
  busy.value = r.id
  try { await api(path, body); toast({ tone: "success", title }); repair.id = 0; ask.id = 0; await load() }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = 0 }
}
const set = (r, status) => act(r, `/hotel/rooms/${r.id}/status`, { status }, `اتاق ${r.number}: ${{ clean: "تمیز", dirty: "کثیف", inspected: "بازرسی‌شده" }[status]}`)
const FILTERS = { todo: "برای نظافت", tasks: "درخواست‌ها", ooo: "در تعمیر", all: "همه" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="ht-chips" role="radiogroup" aria-label="کدام اتاق‌ها"><button v-for="(t, k) in FILTERS" :key="k" type="button" role="radio" :aria-checked="filter === k" :class="{ on: filter === k }" @click="filter = k">{{ t }}</button></div>
    <Skeleton v-if="!list" kind="row" :count="8" />
    <p v-else-if="!shown.length" class="muted small">اتاقی در این فهرست نیست.</p>
    <ul v-else class="ht-tiles" data-tour="ht-tiles">
      <li v-for="r in shown" :key="r.id" :class="['ht-tile', 'st-' + r.status, { ooo: r.ooo }]">
        <div class="ht-tile-top"><b>{{ fa(r.number) }}</b><span :class="['tag', r.ooo ? 'k-t-secondary' : 'k-t-' + ROOM_TONE[r.status]]">{{ r.ooo ? 'در تعمیر' : r.status_text }}</span></div>
        <small>{{ r.type_text }}</small>
        <small v-if="r.guest">{{ r.leaving ? 'امروز می‌رود: ' : 'مقیم: ' }}{{ r.guest }}</small>
        <small v-if="r.arriving" :class="{ 'k-late': r.status === 'dirty' }">{{ r.vip ? 'مهمان ویژه' : 'ورود امروز' }}: {{ fa(r.arriving) }}</small>
        <small v-if="r.ooo">{{ fa(r.ooo_note) }} · تا {{ fa(r.ooo_to_text) }}</small>
        <div v-for="k in r.tasks" :key="k.id" class="k-row-top"><small class="k-late">{{ k.kind === 'repair' ? 'تعمیر' : 'درخواست' }}: {{ fa(k.text) }}</small>
          <button class="btn ghost sm" :disabled="busy === r.id" @click="act(r, `/hotel/tasks/${k.id}/done`, {}, 'انجام شد')">انجام شد</button></div>
        <div class="k-btns">
          <button v-if="r.status === 'dirty'" class="btn primary sm" :disabled="busy === r.id" @click="set(r, 'clean')">تمیز شد</button>
          <button v-if="r.status === 'clean' && role !== 'reception'" class="btn sm" :disabled="busy === r.id" @click="set(r, 'inspected')">بازرسی شد</button>
          <button v-if="r.status !== 'dirty'" class="btn ghost sm" :disabled="busy === r.id" @click="set(r, 'dirty')">کثیف</button>
          <button v-if="r.booking_id && role !== 'housekeeping'" class="btn ghost sm" @click="emit('open', r.booking_id)">رزرو</button>
        </div>
        <div class="k-btns">
          <button v-if="!r.ooo" class="btn ghost sm" @click="Object.assign(repair, { id: r.id, until: hotelInfo.today, note: '' })"><Icon name="edit" :size="14" />تعمیر</button>
          <button v-else class="btn ghost sm" :disabled="busy === r.id" @click="act(r, `/hotel/rooms/${r.id}/ooo`, { until: null }, 'تعمیر تمام شد')">تعمیر تمام شد</button>
          <button class="btn ghost sm" @click="Object.assign(ask, { id: r.id, text: '' })"><Icon name="message" :size="14" />درخواست</button>
        </div>
        <form v-if="repair.id === r.id" class="flex flex-col gap-2" @submit.prevent="act(r, `/hotel/rooms/${r.id}/ooo`, { until: repair.until, note: repair.note }, 'اتاق از فروش بیرون رفت')">
          <input v-model="repair.note" maxlength="120" placeholder="چه خرابی؟ مثلاً نشتی حمام" aria-label="خرابی" class="k-search">
          <div class="field"><span>تا (اتاق تا این روز فروخته نمی‌شود)</span><DatePicker v-model="repair.until" :min="hotelInfo.today" label="پایان تعمیر" /></div>
          <div class="btn-row"><button class="btn primary sm" :disabled="busy === r.id">ثبت</button><button type="button" class="btn ghost sm" @click="repair.id = 0">انصراف</button></div>
        </form>
        <form v-if="ask.id === r.id" class="k-pay" @submit.prevent="act(r, '/hotel/tasks', { room_id: r.id, kind: 'request', text: ask.text }, 'درخواست ثبت شد')">
          <input v-model="ask.text" maxlength="200" placeholder="مثلاً حوله‌ی اضافه" aria-label="درخواست"><button class="btn primary sm" :disabled="ask.text.trim().length < 2">ثبت</button>
        </form>
      </li>
    </ul>
  </div>
</template>
