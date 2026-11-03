<script setup>
// «رزروهای من»: the guest's own bookings from this website, newest first, each with where it is (waiting for the
// deposit → receipt being checked → confirmed → at the hotel → the stay is over), what to do now (the card to pay to
// and the receipt to send, cancelling with what comes back by the hotel's rule) and the room once they are in.
import { ref, reactive, onMounted } from "vue"
import { call, fa, go, guest, signOut, readFile } from "./api.js"
import HsArt from "./HsArt.vue"

defineProps({ site: Object })
const d = ref(null), error = ref(""), busy = ref(0), note = reactive({}), cancelling = ref(0)
const load = async () => {
  if (!guest.token) { go("/login?next=" + encodeURIComponent("/account")); return }
  try { d.value = await call("/my") } catch (e) { error.value = e.message }
}
onMounted(load)
async function act(b, path, body, done) {
  busy.value = b.id; note[b.id] = ""
  try { await call(`/bookings/${b.id}${path}`, body); note[b.id] = done; await load() } catch (e) { note[b.id] = "✗ " + e.message } finally { busy.value = 0 }
}
const sendReceipt = async (b, e) => { try { await act(b, "/receipt", { data: await readFile(e.target.files[0]) }, "رسید فرستاده شد؛ همکاران رزرو واریز را می‌بینند و رزرو را قطعی می‌کنند.") } catch (x) { note[b.id] = "✗ " + x.message } }
const cancel = (b) => act(b, "/cancel", {}, "رزرو لغو شد.").then(() => { cancelling.value = 0 })
const tone = (b) => ["confirmed", "in_house"].includes(b.status) ? "leaf" : ["cancelled", "noshow"].includes(b.status) ? "bad" : b.status === "out" ? "" : "warn"
const STEPS = ["رزرو", "بیعانه", "قطعی", "اقامت"]
const step = (b) => ({ tentative: 1, confirmed: 2, in_house: 3, out: 4 })[b.status] ?? -1
const out = () => { call("/logout", {}).catch(() => {}); signOut(); go("/") }
</script>

<template>
  <div class="eco-wrap eco-page">
    <div class="eco-row" style="justify-content: space-between; margin-bottom: 18px">
      <h1 style="font-size: 24px">رزروهای من<template v-if="d">، {{ d.name }}</template></h1>
      <button class="eco-btn sm" @click="out">خروج از حساب</button>
    </div>
    <p v-if="error" class="eco-msg bad">{{ error }}</p>
    <div v-else-if="d && !d.bookings.length" class="eco-empty">هنوز رزروی ندارید. <button class="eco-link" @click="go('/')">جای خالی را ببینید</button></div>
    <ul v-else-if="d" class="eco-trips">
      <li v-for="b in d.bookings" :key="b.id" class="eco-trip">
        <div class="eco-pic"><HsArt :kind="b.type" /></div>
        <div class="eco-trip-body">
          <div class="eco-trip-top"><div><h3>{{ b.type_text }}</h3><span class="eco-meta">{{ fa(b.stay_text) }} · {{ fa(b.people_text) }} · {{ b.board_text }}</span></div>
            <span :class="['eco-tag', tone(b)]">{{ b.status_text }}</span></div>
          <span class="eco-meta">شماره‌ی رزرو {{ fa(b.id) }} · قیمت کل {{ fa(b.total_text) }}<template v-if="b.paid_text"> · پرداخت‌شده {{ fa(b.paid_text) }}</template></span>
          <div v-if="step(b) >= 0" class="eco-steps" aria-label="مرحله‌ها">
            <span v-for="(t, i) in STEPS" :key="t" :class="{ done: i < step(b), now: i === step(b) }">{{ i ? '← ' : '' }}{{ t }}</span>
          </div>

          <div v-if="b.can_pay" class="eco-msg info">
            <template v-if="b.late">مهلت بیعانه گذشته است؛ اگر هنوز می‌خواهید بیایید، زودتر واریز کنید و رسید را بفرستید.</template>
            <template v-else>برای قطعی شدن رزرو، بیعانه‌ی <b>{{ fa(b.deposit_text) }}</b> را تا {{ fa(b.deposit_due_text) }} به این کارت واریز کنید و عکس رسید را بفرستید:</template><br>
            <b dir="ltr" style="display: inline-block; margin: 4px 0">{{ fa(b.card) }}</b><br>
            <label class="eco-btn main sm" style="margin-top: 4px"><input type="file" accept="image/jpeg,image/png" hidden :disabled="busy === b.id" @change="sendReceipt(b, $event)">فرستادن عکس رسید</label>
          </div>
          <div v-if="b.receipt" class="eco-row"><img v-if="b.receipt.data" :src="b.receipt.data" alt="رسید" class="eco-receipt">
            <span class="eco-meta">{{ b.receipt.status === 'waiting' ? 'رسید در حال بررسی همکاران رزرو است' : b.receipt.status === 'ok' ? 'رسید تأیید شد' : 'رسید پذیرفته نشد؛ با هتل تماس بگیرید یا رسید درست را بفرستید' }}</span></div>
          <p v-if="b.room" class="eco-msg ok" style="margin: 0">اتاق شما: {{ fa(b.room) }}</p>
          <span v-if="['tentative', 'confirmed'].includes(b.status)" class="eco-meta">رسیدن حدود ساعت {{ fa(b.eta) }}<template v-if="b.requests"> · درخواست: {{ b.requests }}</template></span>

          <template v-if="b.can_cancel">
            <button v-if="cancelling !== b.id" class="eco-link" style="align-self: flex-start" @click="cancelling = b.id">لغو این رزرو</button>
            <div v-else class="eco-msg bad">{{ fa(b.refund.days) }} روز تا ورود مانده؛ طبق قانون هتل {{ fa(b.refund.percent) }} درصد پرداختی برمی‌گردد<template v-if="b.refund.amount"> ({{ fa(b.refund.amount.toLocaleString()) }} تومان)</template>.
              <div class="eco-row" style="margin-top: 6px"><button class="eco-btn sm" :disabled="busy === b.id" @click="cancel(b)">بله، لغو شود</button><button class="eco-btn sm soft" @click="cancelling = 0">نه</button></div></div>
          </template>
          <p v-if="note[b.id]" :class="['eco-msg', note[b.id].startsWith('✗') ? 'bad' : 'ok']">{{ note[b.id].replace('✗ ', '') }}</p>
        </div>
      </li>
    </ul>
  </div>
</template>
