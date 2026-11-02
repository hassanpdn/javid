<script setup>
// Close a deal on a listing: the buyer or tenant, the final price, the agents on it. The commission is worked out by
// the server from the agency's settings (from each side, the total, each agent's share); the agent can write another
// amount, and an amount well under the tariff is said here and shows up in the owner's checks.
import { ref, reactive, watch, onMounted } from "vue"
import { api, fa, estateSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { toMillions, fromMillions } from "./lib.js"
import Icon from "../components/Icon.vue"
import HowTip from "../fabric/HowTip.vue"

const props = defineProps({ listing: Object, buyers: { type: Array, default: () => [] } })
const emit = defineEmits(["close", "done"])
const team = ref([]), fee = ref(null), busy = ref(false), error = ref("")
const f = reactive({ request_id: null, buyer: "", price: toMillions(props.listing.price), deposit: toMillions(props.listing.deposit), rent: toMillions(props.listing.rent),
                     agents: [...new Set([estateSession.user.id, props.listing.agent_id])], commission: "" })
const amounts = () => ({ price: fromMillions(f.price), deposit: fromMillions(f.deposit), rent: fromMillions(f.rent) })
let timer
const preview = () => {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    try {
      fee.value = await api("/estate/deals/preview", { kind: props.listing.kind, ...amounts(), agents: f.agents })
      f.commission = toMillions(fee.value.total)
    } catch {}
  }, 300)
}
watch(() => [f.price, f.deposit, f.rent, f.agents.length], preview)
onMounted(async () => { team.value = await api("/estate/agents"); preview() })
const pick = (b) => { f.request_id = b.request_id; f.buyer = b.name }
const toggle = (id) => { f.agents = f.agents.includes(id) ? f.agents.filter((x) => x !== id) : [...f.agents, id] }
const low = () => fee.value && fromMillions(f.commission) < fee.value.total * 0.9
async function save() {
  busy.value = true; error.value = ""
  try {
    const r = await api("/estate/deals", { listing_id: props.listing.id, request_id: f.request_id, buyer: f.buyer, ...amounts(), agents: f.agents,
                                          commission: fromMillions(f.commission) })
    toast({ tone: r.below_tariff ? "warning" : "success", title: "معامله ثبت شد", body: r.below_tariff ? "کمیسیون کمتر از تعرفه‌ی بنگاه است و در بررسی‌های مدیر دیده می‌شود." : "" })
    emit("done")
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "بعضی خانه‌ها درست پر نشده است" : e.message }
  finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog" v-pop role="dialog" aria-label="ثبت معامله" @submit.prevent="save">
      <div class="dialog-head"><div><h3>ثبت معامله</h3><small class="muted">فایل {{ fa(listing.id) }} · {{ fa(listing.title) }}</small></div>
        <button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div v-if="buyers.length" class="field"><span>از متقاضیان این فایل</span>
        <div class="es-chips"><button v-for="b in buyers.slice(0, 6)" :key="b.request_id" type="button" :class="['chip-btn', { on: f.request_id === b.request_id }]" @click="pick(b)">{{ b.name }}</button></div></div>
      <label class="field"><span>{{ listing.kind === 'sale' ? 'خریدار' : 'مستأجر' }}</span><input v-model="f.buyer" maxlength="60" required></label>
      <div class="es-grid2">
        <label v-if="listing.kind === 'sale'" class="field"><span>قیمت نهایی (میلیون تومان)</span><input v-model="f.price" inputmode="numeric"></label>
        <template v-else>
          <label class="field"><span>ودیعه‌ی نهایی (میلیون تومان)</span><input v-model="f.deposit" inputmode="numeric"></label>
          <label class="field"><span>اجاره‌ی نهایی (میلیون تومان)</span><input v-model="f.rent" inputmode="numeric"></label>
        </template>
      </div>
      <div class="field"><span>مشاوران این معامله</span>
        <div class="es-chips"><button v-for="a in team" :key="a.id" type="button" :class="['chip-btn', { on: f.agents.includes(a.id) }]" :aria-pressed="f.agents.includes(a.id)" @click="toggle(a.id)">{{ a.name }}</button></div></div>
      <section v-if="fee" class="es-fee">
        <div class="es-row-top"><b>کمیسیون با تعرفه‌ی بنگاه: {{ fa(fee.total_text) }}</b><HowTip :lines="fee.how" /></div>
        <small class="muted">از هر طرف {{ fa(fee.each_text) }}<template v-if="fee.split.length > 1"> · سهم هر مشاور: <template v-for="(s, i) in fee.split" :key="s.id">{{ i ? '، ' : '' }}{{ s.name }} {{ fa(s.text) }}</template></template></small>
      </section>
      <label class="field"><span>کمیسیون دریافت‌شده (میلیون تومان)</span><input v-model="f.commission" inputmode="numeric">
        <small v-if="low()" class="es-late">کمتر از تعرفه‌ی بنگاه است؛ در بررسی‌های مدیر دیده می‌شود.</small></label>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions"><button class="btn success" :disabled="busy || !f.buyer.trim() || !f.agents.length"><Icon name="check" :size="18" />ثبت معامله</button></div>
    </form>
  </div>
</template>
