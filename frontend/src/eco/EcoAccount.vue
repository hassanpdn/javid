<script setup>
// «سفرهای من»: the guest's own bookings, newest first, each with where it is (request → the host's yes → deposit →
// confirmed → the stay → a review), what to do now (the card to pay to and the receipt to send, cancelling with what
// comes back by the lodge's rule, a word to the host) and, after the stay, the review form. Nothing of anyone else.
import { ref, reactive, onMounted } from "vue"
import { call, fa, go, guest, signOut, readFile } from "./api.js"
import Art from "./Art.vue"

defineProps({ site: Object })
const d = ref(null), error = ref(""), busy = ref(0), note = reactive({}), msg = reactive({}), review = reactive({}), cancelling = ref(0)
const load = async () => {
  if (!guest.token) { go("/login?next=" + encodeURIComponent("/account")); return }
  try { d.value = await call("/my") } catch (e) { error.value = e.message }
}
onMounted(load)
async function act(b, path, body, done) {
  busy.value = b.id; note[b.id] = ""
  try { await call(`/bookings/${b.id}${path}`, body); note[b.id] = done; await load() } catch (e) { note[b.id] = "✗ " + e.message } finally { busy.value = 0 }
}
const sendReceipt = async (b, e) => { try { await act(b, "/receipt", { data: await readFile(e.target.files[0]) }, "رسید فرستاده شد؛ میزبان واریز را می‌بیند و رزرو را قطعی می‌کند.") } catch (x) { note[b.id] = "✗ " + x.message } }
const send = (b) => act(b, "/message", { text: msg[b.id] || "" }, "پیام فرستاده شد.").then(() => { msg[b.id] = "" })
const rate = (b) => act(b, "/review", { stars: review[b.id]?.stars || 0, text: review[b.id]?.text || "" }, "ممنون! نظر شما پس از دیدن میزبان در سایت نمایش داده می‌شود.")
const cancel = (b) => act(b, "/cancel", {}, "رزرو لغو شد.").then(() => { cancelling.value = 0 })
const STEPS = [["requested", "درخواست"], ["approved", "تأیید میزبان"], ["paid", "رسید بیعانه"], ["confirmed", "قطعی"]]
const step = (b) => ["requested", "approved", "paid", "confirmed"].indexOf(b.status)
const out = () => { call("/logout", {}).catch(() => {}); signOut(); go("/") }
</script>

<template>
  <div class="eco-wrap eco-page">
    <div class="eco-row" style="justify-content: space-between; margin-bottom: 18px">
      <h1 style="font-size: 24px">سفرهای من<template v-if="d">، {{ d.name }}</template></h1>
      <button class="eco-btn sm" @click="out">خروج از حساب</button>
    </div>
    <p v-if="error" class="eco-msg bad">{{ error }}</p>
    <div v-else-if="d && !d.bookings.length" class="eco-empty">هنوز رزروی ندارید. <button class="eco-link" @click="go('/')">اتاق‌ها را ببینید</button></div>
    <ul v-else-if="d" class="eco-trips">
      <li v-for="b in d.bookings" :key="b.id" class="eco-trip">
        <div class="eco-pic"><Art :kind="b.art" /></div>
        <div class="eco-trip-body">
          <div class="eco-trip-top"><div><h3>{{ b.unit }}</h3><span class="eco-meta">{{ fa(b.stay_text) }} · {{ fa(b.adults) }} نفر · {{ fa(b.total_text) }}</span></div>
            <span :class="['eco-tag', b.status === 'confirmed' ? 'leaf' : ['cancelled', 'rejected'].includes(b.status) ? 'bad' : 'warn']">{{ b.status_text }}</span></div>
          <div v-if="step(b) >= 0" class="eco-steps" aria-label="مرحله‌ها">
            <span v-for="([k, t], i) in STEPS" :key="k" :class="{ done: i < step(b) || b.status === 'confirmed', now: i === step(b) && b.status !== 'confirmed' }">{{ i ? '← ' : '' }}{{ t }}</span>
            <span :class="{ done: b.over }">← سفر</span><span :class="{ done: b.review }">← نظر</span>
          </div>

          <div v-if="b.can_pay" class="eco-msg info">
            میزبان رزرو را تأیید کرد. بیعانه‌ی <b>{{ fa(b.deposit_text) }}</b> را تا {{ fa(b.deposit_due_text) }} به این کارت واریز کنید و عکس رسید را بفرستید:<br>
            <b dir="ltr" style="display: inline-block; margin: 4px 0">{{ fa(b.card) }}</b>
            <label class="eco-btn main sm" style="margin-top: 4px"><input type="file" accept="image/jpeg,image/png" hidden @change="sendReceipt(b, $event)">فرستادن عکس رسید</label>
          </div>
          <div v-if="b.receipt" class="eco-row"><img :src="b.receipt.data" alt="رسید" class="eco-receipt">
            <span class="eco-meta">{{ b.receipt.status === 'waiting' ? 'رسید در انتظار بررسی میزبان' : b.receipt.status === 'ok' ? 'رسید تأیید شد' : 'رسید پذیرفته نشد؛ پیام میزبان را ببینید' }}</span></div>

          <div v-if="b.messages.length" class="eco-thread"><p v-for="(m, i) in b.messages" :key="i" :class="m.side">{{ m.text }} <small class="eco-meta">· {{ fa(m.day) }} {{ fa(m.time) }}</small></p></div>
          <form v-if="!['cancelled', 'rejected'].includes(b.status)" class="eco-row" @submit.prevent="send(b)">
            <input v-model="msg[b.id]" maxlength="500" placeholder="پیام برای میزبان" aria-label="پیام برای میزبان"><button class="eco-btn sm" :disabled="busy === b.id || (msg[b.id] || '').trim().length < 2">فرستادن</button>
          </form>

          <form v-if="b.can_review" class="eco-panel" style="box-shadow: none; padding: 14px" @submit.prevent="rate(b)">
            <b>سفرتان چطور بود؟</b>
            <div class="eco-pick-stars" role="radiogroup" aria-label="امتیاز"><button v-for="n in 5" :key="n" type="button" role="radio" :aria-checked="review[b.id]?.stars === n"
              :class="{ on: (review[b.id]?.stars || 0) >= n }" :aria-label="fa(n) + ' ستاره'" @click="review[b.id] = { ...(review[b.id] || {}), stars: n }">★</button></div>
            <textarea :value="review[b.id]?.text" rows="3" maxlength="800" placeholder="از اقامتتان بنویسید" aria-label="نظر" style="padding: 10px 14px; border-radius: 12px; border: 1px solid var(--line)"
                      @input="review[b.id] = { ...(review[b.id] || {}), text: $event.target.value }"></textarea>
            <button class="eco-btn main sm" :disabled="busy === b.id || !review[b.id]?.stars || (review[b.id]?.text || '').trim().length < 10">ثبت نظر</button>
          </form>
          <div v-if="b.review" class="eco-review" style="padding: 12px"><span class="eco-stars-row">{{ '★'.repeat(b.review.stars) }}</span><p>{{ b.review.text }}</p>
            <small>{{ b.review.status === 'waiting' ? 'منتظر دیدن میزبان' : b.review.status === 'shown' ? 'در سایت نمایش داده می‌شود' : 'در سایت نمایش داده نمی‌شود' }}</small>
            <div v-if="b.review.reply" class="eco-reply">پاسخ میزبان: {{ b.review.reply }}</div></div>

          <template v-if="b.can_cancel">
            <button v-if="cancelling !== b.id" class="eco-link" style="align-self: flex-start" @click="cancelling = b.id">لغو این رزرو</button>
            <div v-else class="eco-msg bad">{{ fa(b.refund.days) }} روز تا ورود مانده؛ طبق قانون اقامتگاه {{ fa(b.refund.percent) }} درصد بیعانه‌ی پرداخت‌شده برمی‌گردد<template v-if="b.refund.amount"> ({{ fa(b.refund.amount.toLocaleString()) }} تومان)</template>.
              <div class="eco-row" style="margin-top: 6px"><button class="eco-btn sm" :disabled="busy === b.id" @click="cancel(b)">بله، لغو شود</button><button class="eco-btn sm soft" @click="cancelling = 0">نه</button></div></div>
          </template>
          <p v-if="note[b.id]" :class="['eco-msg', note[b.id].startsWith('✗') ? 'bad' : 'ok']">{{ note[b.id].replace('✗ ', '') }}</p>
        </div>
      </li>
    </ul>
  </div>
</template>
