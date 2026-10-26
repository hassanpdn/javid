<script setup>
// What a customer's account looks like right now: debt, cheques, credit room, warnings, usual fabrics and
// the last invoices. The seller has it open while the customer is on the phone; owner and accountant open it from lists.
import { ref, computed, watch } from "vue"
import { api, fa } from "../lib/api.js"
import { money, meters } from "./lib.js"
import Icon from "../components/Icon.vue"
import Avatar from "../components/Avatar.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ id: Number, compact: { type: Boolean, default: false } })
const emit = defineEmits(["loaded"])
const k = ref(null), allCheques = ref(false)
const load = async () => { k.value = null; allCheques.value = false; if (props.id) { k.value = await api(`/fabric/customers/${props.id}`); emit("loaded", k.value) } }
watch(() => props.id, load, { immediate: true })
defineExpose({ reload: load })
// bounced cheques always show; of the rest only the next few, unless asked for all
const shownCheques = computed(() => allCheques.value ? k.value.cheques
  : [...k.value.cheques.filter((q) => q.status === "برگشتی"), ...k.value.cheques.filter((q) => q.status !== "برگشتی").slice(0, 4)])
const pct = (k) => k.credit_limit ? Math.min(100, Math.round(100 * k.exposure / k.credit_limit)) : 0
</script>

<template>
  <div v-if="!k" class="card"><Skeleton kind="row" round /><Skeleton :lines="3" /></div>
  <div v-else class="fc-card">
    <section class="card fc-head">
      <Avatar :name="k.name" :size="52" />
      <div class="grow">
        <b class="fc-name">{{ k.name }}</b>
        <small class="muted">{{ k.shop }} · {{ k.city }} · <span dir="ltr">{{ fa(k.phone) }}</span></small>
      </div>
    </section>

    <ul v-if="k.warnings.length" class="fc-warnings">
      <li v-for="w in k.warnings" :key="w.text" :class="['check', w.tone === 'danger' ? 'bad' : w.tone === 'info' ? 'info' : 'warn']">
        <Icon :name="w.tone === 'info' ? 'clock' : 'alert'" :size="16" /><span>{{ fa(w.text) }}</span></li>
    </ul>

    <section class="card">
      <div class="fc-nums">
        <div><small>بدهی</small><b :class="{ 't-bad': k.debt > 0 }">{{ money(k.debt) }}</b></div>
        <div><small>چک در جریان</small><b>{{ money(k.open_cheques) }}</b></div>
        <div><small>سقف اعتبار</small><b>{{ money(k.credit_limit) }}</b></div>
      </div>
      <div class="fc-limit" :class="{ over: k.room < 0 }"><span :style="{ width: pct(k) + '%' }"></span></div>
      <small class="muted">{{ k.room < 0 ? `${money(-k.room)} بیشتر از سقف` : `${money(k.room)} تا سقف اعتبار` }}</small>
    </section>

    <section v-if="k.cheques.length" class="card">
      <div class="card-head">چک‌ها</div>
      <ul class="fc-list">
        <li v-for="q in shownCheques" :key="q.number + q.due">
          <span :class="['tag', q.status === 'برگشتی' ? 'st-bad' : 'st-todo']">{{ q.status }}</span>
          <span class="grow">{{ money(q.amount) }} · {{ q.bank }}</span>
          <small class="muted">{{ fa(q.due_text) }}</small>
        </li>
      </ul>
      <button v-if="k.cheques.length > shownCheques.length" class="link small" @click="allCheques = true">{{ fa(k.cheques.length - shownCheques.length) }} چک دیگر</button>
    </section>

    <section v-if="!compact && k.usual.length" class="card">
      <div class="card-head">معمولاً می‌خرد</div>
      <div class="fc-chips"><span v-for="u in k.usual" :key="u.code" class="chip">{{ u.title }} · {{ meters(u.meters) }}</span></div>
    </section>

    <section class="card">
      <div class="card-head">آخرین فاکتورها</div>
      <p v-if="!k.recent.length" class="muted small">فاکتوری ندارد.</p>
      <ul class="fc-list">
        <li v-for="r in k.recent" :key="r.id" class="fc-inv">
          <div class="grow"><b>{{ fa(r.date) }} · {{ money(r.total) }}</b><small class="muted">{{ fa(r.items) }}</small></div>
          <span class="tag">{{ r.payment }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>
