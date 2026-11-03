<script setup>
// «آژانس‌ها و سایت‌های رزرو»: each agency, booking site and company with its discount or commission and what it
// brought in the last 30 days; an agency's block of rooms with how many have a guest's name and when it is released.
// The agency's list of names can be pasted (one guest a line: name and mobile) and becomes bookings in the block.
import { ref, reactive, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["changed"])
const list = ref(null), names = reactive({ id: 0, text: "" }), busy = ref(false)
const load = async () => { list.value = await api("/hotel/agencies") }
onMounted(() => retryable(load))
async function add() {
  busy.value = true
  try {
    const r = await api(`/hotel/allotments/${names.id}/names`, { text: names.text })
    toast({ tone: r.made.length ? "success" : "warning", title: `${fa(r.made.length)} رزرو ساخته شد`, body: r.skipped.length ? `${fa(r.skipped.length)} سطر بی‌شماره یا بیش از سهمیه بود` : "" })
    names.id = 0; await load(); emit("changed")
  } catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = false }
}
</script>

<template>
  <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
  <ul v-else class="k-list">
    <li v-for="a in list" :key="a.id" class="card flex flex-col gap-2">
      <div class="k-row-top"><b>{{ a.name }}</b><span class="tag">{{ a.kind_text }}</span></div>
      <small class="muted">{{ a.discount ? `${fa(a.discount)} درصد تخفیف از قیمت هتل` : `${fa(a.commission)} درصد کمیسیون` }} · سی روز گذشته: {{ fa(a.stays) }} رزرو، {{ fa(a.amount_text) }}</small>
      <div v-for="bl in a.blocks" :key="bl.id" class="ht-block">
        <div class="k-row-top"><span>سهمیه‌ی {{ fa(bl.rooms) }} اتاق {{ bl.type_text }} · {{ fa(bl.stay) }}</span>
          <span :class="['tag', bl.named < bl.rooms ? 'k-t-warning' : 'k-t-success']">{{ fa(bl.named) }} از {{ fa(bl.rooms) }} نام دارد</span></div>
        <small class="muted">آزاد شدن سهمیه: {{ fa(bl.release_text) }}؛ پس از آن، اتاق‌های بی‌نام دوباره فروختنی است.</small>
        <button v-if="bl.named < bl.rooms && names.id !== bl.id" class="btn sm" style="align-self: flex-start" @click="Object.assign(names, { id: bl.id, text: '' })"><Icon name="users" :size="14" />افزودن نام‌ها از فهرست آژانس</button>
        <form v-if="names.id === bl.id" class="flex flex-col gap-2" @submit.prevent="add">
          <textarea v-model="names.text" rows="5" class="k-text" placeholder="هر مهمان در یک سطر: نام و شماره‌ی همراه&#10;مثلاً: رضا محمدی ۰۹۱۲۱۱۱۲۲۳۳" aria-label="فهرست نام‌ها"></textarea>
          <div class="btn-row"><button class="btn primary sm" :disabled="busy || names.text.trim().length < 3">ساختن رزروها</button><button type="button" class="btn ghost sm" @click="names.id = 0">انصراف</button></div>
        </form>
      </div>
    </li>
  </ul>
</template>
