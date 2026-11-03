<script setup>
// «نظرها و بازخورد»: guests' reviews, the waiting ones first; the host shows or hides each on the website and may
// reply. Below, stays that ended in the last 30 days without a review: open one to copy the message that asks.
import { ref, reactive, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open", "changed"])
const d = ref(null), reply = reactive({}), busy = ref(0)
const load = async () => { d.value = await api("/lodge/reviews"); for (const r of d.value.reviews) reply[r.id] = r.reply || "" }
onMounted(() => retryable(load))
async function decide(r, status) {
  busy.value = r.id
  try { await api(`/lodge/reviews/${r.id}`, { status, reply: reply[r.id] || "" }); toast({ tone: "success", title: status === "shown" ? "در سایت نمایش داده می‌شود" : "پنهان شد" }); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = 0 }
}
const STATUS = { waiting: ["منتظر شما", "warning"], shown: ["در سایت", "success"], hidden: ["پنهان", "secondary"] }
</script>

<template>
  <div v-if="!d" class="card"><Skeleton kind="row" :count="6" /></div>
  <div v-else class="grid grid-cols-12 gap-6">
    <section class="col-span-12 xl:col-span-8 flex flex-col gap-3">
      <p class="muted small">امتیاز در سایت: {{ fa(d.rating.avg || '-') }} از ۵، از {{ fa(d.rating.count) }} نظر. هر نظر پیش از نمایش، این‌جا دیده و تأیید می‌شود.</p>
      <ul class="lo-list">
        <li v-for="r in d.reviews" :key="r.id" class="card flex flex-col gap-2">
          <div class="lo-row-top"><span><span class="lo-stars">{{ '★'.repeat(r.stars) }}</span> <b>{{ r.guest_full }}</b> · {{ r.unit }}</span>
            <span :class="['tag', 'lo-t-' + STATUS[r.status][1]]">{{ STATUS[r.status][0] }}</span></div>
          <p class="small" style="margin: 0">{{ r.text }}</p>
          <small class="muted">{{ fa(r.date) }}</small>
          <input v-model="reply[r.id]" class="lo-search" maxlength="400" placeholder="پاسخ میزبان (اختیاری؛ زیر نظر در سایت می‌آید)" aria-label="پاسخ میزبان">
          <div class="btn-row"><button class="btn primary sm" :disabled="busy === r.id" @click="decide(r, 'shown')">{{ r.status === 'shown' ? 'ذخیره‌ی پاسخ' : 'نمایش در سایت' }}</button>
            <button v-if="r.status !== 'hidden'" class="btn ghost sm" :disabled="busy === r.id" @click="decide(r, 'hidden')">پنهان کردن</button>
            <button class="btn ghost sm" @click="emit('open', r.booking_id)">رزرو</button></div>
        </li>
      </ul>
    </section>
    <section class="card col-span-12 xl:col-span-4 flex flex-col gap-2" data-tour="lo-feedback">
      <div class="card-head">از این مهمان‌ها نظر بخواهید <span class="count">{{ fa(d.feedback.length) }}</span></div>
      <p class="muted small">سفرهایی که در سی روز گذشته تمام شده و هنوز نظری ندارند.</p>
      <ul class="lo-mini"><li v-for="b in d.feedback" :key="b.id"><div class="lo-row-top"><button class="lo-link" @click="emit('open', b.id)">{{ b.guest }}</button>
        <span :class="['tag', b.feedback_asked ? 'lo-t-secondary' : 'lo-t-warning']">{{ b.feedback_asked ? 'پرسیده شد' : 'هنوز نه' }}</span></div>
        <small class="muted">{{ b.unit }} · {{ fa(b.stay_text) }}</small></li></ul>
    </section>
  </div>
</template>
