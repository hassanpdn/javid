<script setup>
// Cheques and debts: next week's cheques in and out against the bank balance, bounced cheques, and the
// customers who owe the most, each with a reminder text the assistant drafts and a person sends.
import { ref, reactive, computed, watch, onMounted } from "vue"
import { api, fa, lockScroll } from "../lib/api.js"
import { toast, busy, idle } from "../lib/notify.js"
import { money } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import CustomerDrawer from "./CustomerDrawer.vue"

const d = ref(null), openId = ref(null)
const draft = reactive({ open: false, who: null, text: "", loading: false, checked: undefined, saving: false })
const load = async () => { d.value = await api("/fabric/money") }
onMounted(load)
watch(() => draft.open, lockScroll)
const short = computed(() => d.value && d.value.week.left < 0)

const write = async (row) => {
  Object.assign(draft, { open: true, who: row, text: "", loading: true, checked: undefined })
  busy("remind", "دستیار در حال نوشتن پیامک یادآوری")
  try { const r = await api("/fabric/reminders/draft", { customer_id: row.id }); Object.assign(draft, r, { text: fa(r.text) }) }
  catch { draft.text = "" } finally { draft.loading = false; idle("remind") }
}
const send = async () => {
  draft.saving = true
  try {
    await api("/fabric/reminders", { customer_id: draft.who.id, text: draft.text })
    toast({ tone: "success", title: "پیامک ثبت شد", body: `یادآوری برای ${draft.who.name} ثبت شد. در این نسخه‌ی نمایشی پیامکی واقعاً فرستاده نمی‌شود.` })
    draft.open = false; await load()
  } finally { draft.saving = false }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <template v-if="!d"><div class="card"><Skeleton :lines="4" /></div><div class="card"><Skeleton kind="row" :count="4" /></div></template>
    <template v-else>
      <section v-reveal :class="['card', 'fm-week', { short }]">
        <div class="card-head"><span class="grow">چک‌های {{ fa(d.week.days) }} روز آینده</span>
          <span :class="['tag', short ? 'st-bad' : 'st-done']">{{ short ? 'کسری ' + money(-d.week.left) : 'پول کافی است' }}</span></div>
        <div class="fm-flow">
          <div><small>موجودی بانک</small><b>{{ money(d.week.bank) }}</b></div>
          <span class="fm-op">+</span>
          <div><small>چک‌هایی که می‌رسد</small><b class="t-ok">{{ money(d.week.in_total) }}</b></div>
          <span class="fm-op">−</span>
          <div><small>چک‌هایی که باید پاس شود</small><b class="t-bad">{{ money(d.week.out_total) }}</b></div>
          <span class="fm-op">=</span>
          <div class="fm-left"><small>می‌ماند</small><b :class="short ? 't-bad' : 't-ok'">{{ money(d.week.left) }}</b></div>
        </div>
        <div class="grid md:grid-cols-2 gap-4 mt-2">
          <div>
            <h4 class="fm-sub">پرداختی‌ها (چک‌های خودمان)</h4>
            <ul class="fc-list">
              <li v-for="q in d.week.outgoing" :key="q.id"><span class="grow">{{ q.who }}</span><b>{{ money(q.amount) }}</b><small class="muted">{{ fa(q.due_text) }}</small></li>
            </ul>
            <p v-if="!d.week.outgoing.length" class="muted small">چکی برای پاس شدن نیست.</p>
          </div>
          <div>
            <h4 class="fm-sub">دریافتی‌ها (چک مشتری‌ها)</h4>
            <ul class="fc-list">
              <li v-for="q in d.week.incoming" :key="q.id"><span class="grow">{{ q.who }}</span><b>{{ money(q.amount) }}</b><small class="muted">{{ fa(q.due_text) }}</small></li>
            </ul>
            <p v-if="!d.week.incoming.length" class="muted small">چکی نمی‌رسد.</p>
          </div>
        </div>
      </section>

      <section v-if="d.bounced.length" v-reveal class="card">
        <div class="card-head">چک‌های برگشتی <span class="count">{{ fa(d.bounced.length) }}</span></div>
        <ul class="alerts">
          <li v-for="q in d.bounced" :key="q.id" class="alert">
            <span class="tint t-danger"><Icon name="alert" :size="20" /></span>
            <div class="alert-body"><b>{{ q.who }} · {{ money(q.amount) }}</b>
              <small class="muted">بانک {{ q.bank }}، سررسید {{ fa(q.due_text) }}، {{ fa(q.days_ago) }} روز پیش برگشت خورد</small></div>
            <button class="btn sm" @click="openId = q.customer_id">کارت مشتری</button>
          </li>
        </ul>
      </section>

      <section v-reveal class="card">
        <div class="card-head">بیشترین طلب‌ها</div>
        <ul class="fm-debtors">
          <li v-for="r in d.debtors" :key="r.id">
            <button class="fm-who" @click="openId = r.id">
              <b>{{ r.name }}</b><small class="muted">{{ r.city }}<template v-if="r.reminded"> · پیامک: {{ fa(r.reminded) }}</template></small>
            </button>
            <span class="fm-amount"><b>{{ money(r.debt) }}</b>
              <small v-if="r.bounced" class="t-bad">چک برگشتی</small>
              <small v-else-if="r.room < 0" class="t-warn">بیش از سقف</small></span>
            <button class="btn sm" @click="write(r)"><Icon name="message" :size="16" />پیامک یادآوری</button>
          </li>
        </ul>
      </section>
    </template>

    <CustomerDrawer v-if="openId" :id="openId" @close="openId = null" />

    <div v-if="draft.open" class="overlay" @click.self="draft.open = false">
      <div class="dialog" v-pop>
        <h3>پیامک یادآوری برای {{ draft.who.name }}</h3>
        <p class="muted small">این متن را دستیار نوشته است. قبل از فرستادن بخوانید و هر جا لازم است تغییر دهید.</p>
        <Skeleton v-if="draft.loading" :lines="4" />
        <template v-else>
          <p v-if="draft.checked === true" class="check ok">✓ مبلغ‌ها با حساب این مشتری یکی است.</p>
          <p v-if="draft.checked === false" class="check bad">متن دستیار با حساب‌ها نمی‌خواند؛ این متن را خود برنامه از روی حساب نوشته است.</p>
          <p v-if="draft.checked === null" class="check warn">دستیار الان جواب نداد؛ این متن را خود برنامه از روی حساب نوشته است.</p>
          <textarea v-model="draft.text" rows="6" aria-label="متن پیامک"></textarea>
        </template>
        <div class="dialog-actions">
          <button class="btn primary" :disabled="draft.loading || !draft.text.trim() || draft.saving" @click="send"><Icon name="send" :size="18" />فرستادم</button>
          <button class="btn ghost" @click="draft.open = false">انصراف</button>
        </div>
      </div>
    </div>
  </div>
</template>
