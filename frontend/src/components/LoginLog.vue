<script setup>
// «ورودها» on the assistants page, for the permanent account only (GET /access/logins): every login try at the site's
// door or an assistant's login box, newest first, 50 at a time, with a filter for one person. Failed tries are
// marked in red. The server keeps 90 days and gives Tehran's date and time.
import { ref, onMounted } from "vue"
import { access, accessCall, jalaliText } from "../lib/access.js"
import { faDigits } from "../lib/jalali.js"
import Icon from "./Icon.vue"

const items = ref([]), people = ref([]), more = ref(false), who = ref("")
const loading = ref(true), loadingMore = ref(false), error = ref("")

const RESULTS = { ok: "وارد شد", wrong: "رمز نادرست", expired: "دسترسی تمام شده", unknown: "نام کاربری ناشناس" }
const VIA = { door: "ورودی سایت", card: "کارت دستیار" }

async function load(next = false) {
  const before = next && items.value.length ? items.value[items.value.length - 1].id : null
  const q = new URLSearchParams()
  if (before) q.set("before", before)
  if (who.value) q.set("username", who.value)
  next ? (loadingMore.value = true) : (loading.value = true)
  try {
    const data = await accessCall("/access/logins?" + q)
    items.value = next ? items.value.concat(data.items) : data.items
    more.value = data.more; people.value = data.people; error.value = ""
  } catch (e) { error.value = "فهرست ورودها بارگیری نشد: " + e.message }
  loading.value = loadingMore.value = false
}
onMounted(() => load())

// «1405/08/10 18:30» → «امروز، ساعت ۱۸:۳۰» or «۱۰ آبان ۱۴۰۵، ساعت ۱۸:۳۰» (today from the server's clock)
const at = (s) => s.split(" ")[0] === access.today ? faDigits("امروز، ساعت " + s.split(" ")[1]) : jalaliText(s)
</script>

<template>
  <section class="ll">
    <header class="ll-head">
      <div class="ll-title">
        <span class="ll-badge"><Icon name="lock" :size="20" /></span>
        <div><h2>ورودها</h2><p>چه کسی، چه زمانی و با چه دستگاهی وارد شد. ورودهای ناموفق قرمزند.</p></div>
      </div>
      <select v-model="who" class="ll-filter" aria-label="نمایش ورودهای یک نفر" @change="load()">
        <option value="">همه</option>
        <option v-for="p in people" :key="p.username" :value="p.username">{{ p.name }}</option>
      </select>
    </header>

    <p v-if="error" class="ll-error" role="alert"><Icon name="alert" :size="16" />{{ error }}</p>
    <ul v-if="loading" class="ll-list">
      <li v-for="n in 3" :key="n" class="ll-row ll-skel"><i></i><span><b></b><em></em></span></li>
    </ul>
    <p v-else-if="!items.length && !error" class="ll-empty">هنوز ورودی ثبت نشده است.</p>
    <ul v-else class="ll-list">
      <li v-for="r in items" :key="r.id" :class="['ll-row', { bad: r.result !== 'ok' }]">
        <span class="ll-icon"><Icon :name="r.result === 'ok' ? 'check' : 'alert'" :size="16" /></span>
        <div class="ll-body">
          <div class="ll-top">
            <b class="ll-name">{{ r.name || "ناشناس" }}</b>
            <span :class="['ll-tag', r.result === 'ok' ? 'on' : 'off']">{{ RESULTS[r.result] || r.result }}</span>
          </div>
          <span class="ll-user" dir="ltr">{{ r.username }}</span>
          <div class="ll-meta">
            <span><Icon name="clock" :size="13" />{{ at(r.at) }}</span>
            <span dir="ltr">{{ r.device }}</span>
            <span>{{ VIA[r.via] || r.via }}</span>
          </div>
        </div>
      </li>
    </ul>
    <button v-if="more && !loading" class="ll-more" :disabled="loadingMore" @click="load(true)">
      {{ loadingMore ? "در حال بارگیری…" : "ورودهای قبلی" }}
    </button>
  </section>
</template>

<style scoped>
.ll { width: min(100%, 1120px); margin-top: 18px; padding: 24px; border-radius: 28px;
  background: linear-gradient(165deg, rgba(255,255,255,.09), rgba(255,255,255,.025)); border: 1px solid rgba(255,255,255,.12);
  backdrop-filter: blur(22px) saturate(140%); -webkit-backdrop-filter: blur(22px) saturate(140%); box-shadow: 0 30px 80px -30px rgba(0,0,0,.7); }
.ll-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin-bottom: 16px; }
.ll-title { display: flex; align-items: center; gap: 14px; min-width: 0; }
.ll-badge { flex: none; display: grid; place-items: center; width: 48px; height: 48px; border-radius: 16px; color: #fff;
  background: linear-gradient(135deg, #1fb8d6, #7367f0); box-shadow: 0 10px 26px -8px rgba(31,184,214,.6); }
.ll-title h2 { margin: 0; font-size: 20px; color: #fff; }
.ll-title p { margin: 2px 0 0; font-size: 13.5px; line-height: 1.8; color: #b7b3d9; }
.ll-filter { height: 42px; min-width: 180px; padding-inline-start: 14px; border-radius: 12px; font: inherit; font-size: 14px; color: #fff;
  background-color: rgba(10,9,32,.55); border: 1px solid rgba(255,255,255,.16); }
.ll-filter option { color: #111; background: #fff; }
.ll-filter:focus-visible { outline: 3px solid #8fefff; outline-offset: 2px; }

.ll-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
.ll-row { display: flex; gap: 12px; align-items: flex-start; padding: 12px 14px; border-radius: 16px;
  background: rgba(10,9,32,.45); border: 1px solid rgba(255,255,255,.08); }
.ll-row.bad { border-color: rgba(255,111,140,.35); background: rgba(80,14,32,.35); }
.ll-icon { flex: none; display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; color: #7ef0b0; background: rgba(62,224,143,.14); }
.ll-row.bad .ll-icon { color: #ffa3b0; background: rgba(255,111,140,.16); }
.ll-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.ll-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.ll-name { min-width: 0; color: #fff; font-size: 14.5px; line-height: 1.7; overflow-wrap: anywhere; }
.ll-user { align-self: flex-start; font-size: 12.5px; color: #c9c5ee; overflow-wrap: anywhere; }
.ll-tag { flex: none; padding: 2px 10px; border-radius: 999px; font-size: 12px; white-space: nowrap; }
.ll-tag.on { color: #7ef0b0; background: rgba(62,224,143,.14); }
.ll-tag.off { color: #ffa3b0; background: rgba(255,111,140,.16); }
.ll-meta { display: flex; flex-wrap: wrap; gap: 2px 14px; font-size: 12.5px; color: #b7b3d9; }
.ll-meta span { display: inline-flex; align-items: center; gap: 5px; }
.ll-more { display: block; margin: 14px auto 0; height: 40px; padding: 0 18px; border-radius: 12px; cursor: pointer; font: inherit; font-size: 13.5px;
  color: #dcd8ff; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.14); }
.ll-more:hover:not(:disabled), .ll-more:focus-visible { color: #fff; background: rgba(255,255,255,.14); outline: none; }
.ll-more:disabled { cursor: wait; opacity: .7; }
.ll-error { display: flex; align-items: center; gap: 8px; margin: 0 0 12px; padding: 10px 14px; border-radius: 14px; font-size: 13.5px;
  color: #ffb4b6; background: rgba(255,92,97,.12); border: 1px solid rgba(255,92,97,.3); }
.ll-empty { margin: 0; padding: 22px 16px; text-align: center; border-radius: 16px; font-size: 13.5px; color: #b7b3d9; border: 1px dashed rgba(255,255,255,.18); }
.ll-skel i { flex: none; width: 30px; height: 30px; border-radius: 50%; background: rgba(255,255,255,.08); }
.ll-skel span { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.ll-skel b, .ll-skel em { display: block; height: 12px; border-radius: 6px; background: rgba(255,255,255,.08); }
.ll-skel b { width: 40%; } .ll-skel em { width: 70%; }

@media (max-width: 480px) {
  .ll { padding: 18px 14px; border-radius: 24px; }
  .ll-filter { width: 100%; }
}
/* phones and touch screens: no frosted glass (iPhone Safari draws such panels wrong; see HubPage) */
@media (hover: none), (max-width: 767px) { .ll { backdrop-filter: none; -webkit-backdrop-filter: none; isolation: isolate; background: linear-gradient(165deg, rgba(40,38,82,.92), rgba(18,17,42,.94)); } }
</style>
