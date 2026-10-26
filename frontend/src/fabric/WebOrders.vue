<script setup>
// «سفارش‌های سایت»: what the website's assistant took. Not paid yet: once the customer pays (or a cheque or
// credit is agreed) the seller turns it into an invoice, which goes into all three files like a phone sale.
import { ref, reactive, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { money, meters, num } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["shop"])
const list = ref(null), pay = reactive({}), busy = ref(0), done = reactive({})
const load = async () => { list.value = await api("/fabric/web-orders") }
onMounted(load)
defineExpose({ load })
const invoice = async (o) => {
  busy.value = o.id
  try {
    const r = await api(`/fabric/web-orders/${o.id}/invoice`, { payment: pay[o.id] || "نقد" })
    done[o.id] = r
    toast({ tone: "success", title: `فاکتور ${fa(r.invoice)} ثبت شد`, body: `سفارش سایت ${fa(o.id)} · به فایل‌های ${r.files.join(" و ")} اضافه شد.` })
    await load()
  } catch (e) { toast({ tone: "danger", title: "فاکتور ثبت نشد", body: e.message }) }
  finally { busy.value = 0 }
}
const cancel = async (o) => { await api(`/fabric/web-orders/${o.id}/cancel`, {}); await load() }
const TONE = { "پرداخت نشده": "st-todo", "فاکتور شد": "st-done", "لغو شد": "" }
</script>

<template>
  <div class="flex flex-col gap-6">
    <section v-reveal class="rp-head">
      <div class="grow"><h2>سفارش‌های سایت</h2>
        <p class="muted">سفارش‌هایی که دستیار سایت از مشتری‌ها گرفته. پرداخت نشده‌اند؛ بعد از پرداخت، فاکتور بزنید.</p></div>
      <button class="btn ghost" @click="emit('shop')"><Icon name="message" :size="18" />دیدن سایت از نگاه مشتری</button>
    </section>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="3" /></div>
    <section v-else-if="!list.length" class="card desk-empty">
      <Icon name="message" :size="40" /><b>هنوز سفارشی از سایت نیامده</b>
      <p class="muted">در «سایت فروشگاه» جای مشتری سفارش بدهید تا ببینید اینجا چه می‌آید.</p>
      <button class="btn primary sm" @click="emit('shop')">رفتن به سایت فروشگاه</button>
    </section>
    <article v-for="o in list || []" :key="o.id" v-reveal :class="['card', 'wo', { wait: o.status === 'پرداخت نشده' }]">
      <div class="wo-top">
        <span class="wo-no"><small>سفارش</small><b>{{ fa(o.id) }}</b></span>
        <div class="grow">
          <b>{{ o.name }} <span :class="['tag', o.known ? 'st-done' : '']">{{ o.known ? 'مشتری قدیمی' : 'مشتری تازه' }}</span></b>
          <small class="muted"><span dir="ltr">{{ fa(o.phone) }}</span><template v-if="o.city"> · {{ o.city }}</template> · ساعت {{ fa(o.time) }}</small>
        </div>
        <span :class="['tag', TONE[o.status]]">{{ o.status }}<template v-if="o.invoice_id"> · فاکتور {{ fa(o.invoice_id) }}</template></span>
      </div>
      <ul v-if="o.warnings.length" class="fc-warnings">
        <li v-for="w in o.warnings" :key="w.text" :class="['check', w.tone === 'danger' ? 'bad' : 'warn']"><Icon name="alert" :size="16" /><span>{{ fa(w.text) }}</span></li>
      </ul>
      <ul class="fc-list">
        <li v-for="i in o.items" :key="i.code"><span class="grow">{{ i.title }}</span>
          <small class="muted">{{ i.rolls ? fa(i.rolls) + ' توپ · ' : '' }}{{ meters(i.meters) }}</small><b>{{ num(i.amount) }}</b></li>
      </ul>
      <div class="desk-total"><span>جمع</span><b>{{ num(o.total) }} تومان</b><small class="muted">{{ money(o.total) }}</small></div>
      <div v-if="o.status === 'پرداخت نشده'" class="wo-actions">
        <div class="segmented" role="radiogroup" aria-label="نوع پرداخت">
          <button v-for="p in ['نقد', 'چک', 'نسیه']" :key="p" role="radio" :aria-checked="(pay[o.id] || 'نقد') === p" :class="{ on: (pay[o.id] || 'نقد') === p }" @click="pay[o.id] = p">{{ p }}</button>
        </div>
        <button class="btn primary sm" :disabled="busy === o.id" @click="invoice(o)"><Icon name="check" :size="16" />پرداخت شد، فاکتور بزن</button>
        <button class="btn ghost sm" :disabled="busy === o.id" @click="cancel(o)">لغو</button>
      </div>
      <ol v-if="done[o.id]" class="desk-flow">
        <li v-for="(st, i) in done[o.id].steps" :key="st.file" :style="{ '--d': i * .35 + 's' }">
          <span class="df-dot"><Icon name="check" :size="14" /></span><b>{{ st.file }}</b><small>{{ fa(st.text) }}</small></li>
      </ol>
    </article>
  </div>
</template>
