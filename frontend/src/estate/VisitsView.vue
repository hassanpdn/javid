<script setup>
// «بازدیدها»: the coming visits by day (send the messages and confirm the ones not confirmed yet), and the past ones.
// After a visit the agent writes one line of how it went; the assistant turns it into a short note and a next step.
import { ref, reactive, watch, onMounted, defineAsyncComponent } from "vue"
import { api, fa, estateSession, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
const VisitDialog = defineAsyncComponent(() => import("./VisitDialog.vue"))

const emit = defineEmits(["listing", "request"])
const list = ref(null), open = ref(null), writing = reactive({}), busy = ref(null)
const f = reactive({ when: "upcoming", mine: estateSession.user.role === "agent" })
const load = async () => { list.value = await api("/estate/visits?" + new URLSearchParams({ when: f.when, mine: f.mine ? "true" : "false" })) }
watch(f, () => { list.value = null; load().catch(() => { list.value = [] }) })
onMounted(() => retryable(load))
const STATUS = { booked: ["تأیید نشده", "warning"], confirmed: ["تأیید شده", "success"], done: ["انجام شد", "secondary"], cancelled: ["لغو شد", "secondary"] }
async function outcome(v) {
  busy.value = v.id
  try { const r = await api(`/estate/visits/${v.id}/outcome`, { text: writing[v.id] }); Object.assign(v, { status: "done", note: r.note, next_step: r.next_step, outcome: writing[v.id] }); delete writing[v.id] }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = null }
}
async function cancel(v) {
  try { await api(`/estate/visits/${v.id}/cancel`, {}); await load() } catch (e) { toast({ tone: "danger", title: e.message }) }
}
const past = (v) => f.when === "past"
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="es-toolbar">
      <div class="tabs" role="tablist"><button v-for="(t, k) in { upcoming: 'پیش رو', past: 'گذشته' }" :key="k" role="tab" :aria-selected="f.when === k" :class="{ on: f.when === k }" @click="f.when = k">{{ t }}</button></div>
      <label class="es-check"><input v-model="f.mine" type="checkbox">فقط بازدیدهای من</label>
    </div>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="5" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="calendar" :size="32" /><p class="muted">بازدیدی نیست. از فایل یا متقاضی، «بازدید» را بزنید.</p></div>
    <ul v-else class="es-list">
      <li v-for="v in list" :key="v.id" class="card es-visit">
        <div class="es-row-top"><b>{{ fa(v.when) }}</b><span :class="['tag', 'es-t-' + STATUS[v.status][1]]">{{ STATUS[v.status][0] }}</span></div>
        <div class="es-meta"><button class="link" @click="emit('request', v.request_id)">{{ v.name }}</button> · <span dir="ltr">{{ fa(v.phone) }}</span></div>
        <div class="es-meta"><button class="link" @click="emit('listing', v.listing_id)">فایل {{ fa(v.listing_id) }}</button>: {{ fa(v.area) }} متر، {{ fa(v.rooms) }} خواب، {{ v.street || v.hood }} · {{ v.agent }}</div>
        <p v-if="v.note || v.outcome" class="es-note"><b>یادداشت:</b> {{ fa(v.note || v.outcome) }}<template v-if="v.next_step"><br><b>گام بعد:</b> {{ fa(v.next_step) }}</template></p>
        <div v-if="v.status === 'booked'" class="btn-row"><button class="btn sm" @click="open = v"><Icon name="message" :size="14" />پیام‌ها و تأیید</button><button class="btn ghost sm" @click="cancel(v)">لغو</button></div>
        <form v-else-if="v.status === 'confirmed' || (past(v) && v.status !== 'done' && v.status !== 'cancelled')" class="es-outcome" @submit.prevent="outcome(v)">
          <input v-model="writing[v.id]" maxlength="500" placeholder="بازدید چطور بود؟ مثلاً پسندیدند، پنجشنبه با همسرش دوباره می‌آید" aria-label="نتیجه‌ی بازدید">
          <button class="btn sm" :disabled="!writing[v.id]?.trim() || busy === v.id">{{ busy === v.id ? '…' : 'ثبت نتیجه' }}</button>
        </form>
      </li>
    </ul>
    <VisitDialog v-if="open" :visit-id="open.id" :title="`${open.name} · فایل ${open.listing_id}`" @close="open = null" @done="open = null; load()" />
  </div>
</template>
