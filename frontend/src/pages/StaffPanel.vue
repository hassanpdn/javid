<script setup>
// Staff: smart letter inbox. The agent reads queued letters one by one; people approve replies.
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue"
import { api, fa, lockScroll } from "../lib/api.js"
import { CATEGORY_OPTIONS, DOCS_CHAT } from "../lib/constants.js"
import AppLayout from "../components/AppLayout.vue"
import ReferDialog from "../components/ReferDialog.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import CountUp from "../components/CountUp.vue"
import AiOrb from "../components/AiOrb.vue"

const TABS = [
  { key: "mine", label: "منتظر شما", icon: "inbox", match: (l) => ["new", "processing", "awaiting_approval", "todo"].includes(l.status) },
  { key: "manager", label: "برای مدیر", icon: "forward", match: (l) => ["needs_manager", "forwarded"].includes(l.status) },
  { key: "done", label: "بسته‌شده", icon: "check", match: (l) => l.status === "done" },
  { key: "log", label: "کارهای دستیار", icon: "notebook" },
]
const letters = ref([]), log = ref([]), tab = ref("mine"), open = ref(null), reply = ref(""), view = ref("inbox")
const compose = reactive({ open: false, sender: "", subject: "", body: "", saving: false, error: "" })
const referring = ref(null)
const fresh = ref(new Set())
const agent = reactive({ running: false, processed: 0, total: 0, current: "", error: "" })
const count = (fn) => letters.value.filter(fn).length
const shown = computed(() => {
  const t = TABS.find((x) => x.key === tab.value)
  return t.match ? letters.value.filter(t.match) : []
})
const nav = computed(() => [
  { header: "نامه‌ها" },
  { key: "inbox", label: "صندوق نامه", icon: "inbox", badge: count(TABS[0].match) },
])
const stats = computed(() => [
  { label: "منتظر شما", value: count(TABS[0].match), icon: "inbox", tone: "warning" },
  { label: "فرستاده‌شده برای مدیر", value: count(TABS[1].match), icon: "forward", tone: "info" },
  { label: "بسته‌شده", value: count(TABS[2].match), icon: "check", tone: "success" },
  { label: "تأیید دریافت خودکار", value: count((l) => l.status === "done" && l.category === "ack"), icon: "sparkles", tone: "primary" },
])
const loaded = ref(false)
const load = async () => {
  letters.value = await api("/staff/letters"); loaded.value = true
  log.value = await api("/staff/log")
}
const changeCategory = async (l, category) => { await api(`/staff/letters/${l.id}/category`, { category }); await load() }
// The agent runs by itself: it takes the queued letters one at a time until none are left
const runAgent = async () => {
  agent.error = ""
  const queue = letters.value.filter((l) => l.status === "new")
  if (!queue.length) return
  Object.assign(agent, { running: true, processed: 0, total: queue.length })
  try {
    while (true) {
      agent.current = letters.value.find((l) => l.status === "new")?.subject || ""
      const r = await api("/staff/agent/next", {})
      if (r.done) break
      const i = letters.value.findIndex((l) => l.id === r.letter.id)
      letters.value[i] = r.letter
      fresh.value = new Set([...fresh.value, r.letter.id])
      agent.processed++
      log.value = await api("/staff/log")
    }
  } catch (e) {
    if (e.message !== "401") agent.error = "دستیار الان جواب نمی‌دهد. چند لحظه بعد دوباره امتحان کنید."
  } finally { agent.running = false; agent.current = "" }
}
const openLetter = (l) => { open.value = l; reply.value = l.reply || "" }
const approve = async () => { await api(`/staff/letters/${open.value.id}/approve`, { reply: reply.value }); open.value = null; await load() }
const complete = async (l) => { await api(`/staff/letters/${l.id}/complete`, {}); await load() }
// A new letter goes into the queue; the agent then picks it up exactly like the others
const addLetter = async () => {
  compose.saving = true; compose.error = ""
  try {
    await api("/staff/letters", { sender: compose.sender, subject: compose.subject, body: compose.body })
    Object.assign(compose, { open: false, sender: "", subject: "", body: "" })
    await load()
    runAgent()
  } catch (e) { compose.error = e.message } finally { compose.saving = false }
}
watch(() => !!open.value || compose.open || !!referring.value, lockScroll)
onMounted(async () => { await load(); runAgent() })
onUnmounted(() => lockScroll(false))
</script>

<template>
  <AppLayout :chat="DOCS_CHAT" title="پنل اداری" subtitle="صندوق نامه‌های اداری" :nav="nav" v-model="view">
    <div class="flex flex-col gap-6">
      <section v-reveal class="row-between">
        <div><h2>روز بخیر</h2><p class="muted">دستیار نامه‌ها را می‌خواند، دسته‌بندی می‌کند و متن پاسخ را می‌نویسد. تصمیم با شماست.</p></div>
        <button class="btn primary" @click="compose.open = true" :disabled="agent.running"><Icon name="plus" :size="18" />ثبت نامه جدید</button>
      </section>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-6">
        <Skeleton v-if="!loaded" kind="stat" :count="4" />
        <div v-else v-for="s in stats" :key="s.label" v-reveal class="card stat" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 't-' + s.tone]"><Icon :name="s.icon" :size="22" /></span><div class="stat-num"><CountUp :value="s.value" /></div></div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>

      <section v-reveal class="card agent" :class="{ running: agent.running }">
        <div class="agent-row">
          <AiOrb :size="64" :busy="agent.running" />
          <div class="agent-text">
            <Skeleton v-if="!loaded" :lines="2" />
            <b v-else-if="agent.running">دستیار در حال بررسی نامه‌ها: {{ fa(agent.processed) }} از {{ fa(agent.total) }}</b>
            <b v-else-if="agent.error">{{ agent.error }}</b>
            <b v-else>همه نامه‌ها بررسی شد</b>
            <small class="muted" v-if="loaded && agent.running && agent.current">در حال خواندن: {{ fa(agent.current) }}</small>
            <small class="muted" v-else-if="loaded && !agent.running && !agent.error">
              {{ fa(count(l => l.status === 'done' && l.category === 'ack')) }} نامه با تأیید دریافت خودکار بسته شد،
              {{ fa(count(TABS[0].match)) }} مورد منتظر شماست و {{ fa(count(TABS[1].match)) }} مورد به مدیر رفت.
            </small>
          </div>
          <button v-if="agent.error" class="btn" @click="runAgent"><Icon name="refresh" :size="18" />تلاش دوباره</button>
        </div>
        <div v-if="agent.running" class="progress"><span :style="{ width: (agent.total ? 100 * agent.processed / agent.total : 0) + '%' }"></span></div>
      </section>

      <nav v-reveal class="tabs">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">
          <Icon :name="t.icon" :size="18" />{{ t.label }}<span v-if="t.match" class="tab-count">{{ fa(count(t.match)) }}</span>
        </button>
      </nav>

      <section v-if="tab !== 'log'" class="letters">
        <Skeleton v-if="!loaded" kind="letter" :count="3" />
        <div v-else-if="!shown.length" class="card empty-state"><span class="tint lg t-success"><Icon name="check" :size="24" /></span><p>موردی نیست.</p></div>
        <article v-for="l in shown" :key="l.id" v-reveal :class="['letter-card', 'card', 'st-' + l.status, { fresh: fresh.has(l.id) }]">
          <div class="lc-top">
            <b>{{ fa(l.subject) }}</b>
            <span v-if="l.deadline_short && l.status !== 'done'" :class="['chip', { hot: l.days_left <= 3 }]">مهلت {{ fa(l.deadline_short) }}</span>
          </div>
          <div class="lc-meta"><Icon name="mail" :size="15" />{{ l.sender }} · {{ fa(l.received_short) }}</div>
          <div class="lc-tags">
            <span v-if="l.category_name" class="tag">{{ l.category_name }}</span>
            <span :class="['tag', 'st-' + l.status]">{{ l.status_name }}</span>
          </div>
          <p v-if="l.summary" class="lc-summary">{{ fa(l.summary) }}</p>
          <p v-if="l.action && l.status !== 'done'" class="lc-action"><Icon name="sparkles" :size="16" /><span>پیشنهاد دستیار: {{ fa(l.action) }}</span></p>
          <div v-if="l.referral" class="ref-line">
            <span>فرستاده‌شده برای {{ fa(l.referral.count) }} نفر</span>
            <span v-if="l.referral.needs_ack" class="sep">·</span>
            <span v-if="l.referral.needs_ack" :class="l.referral.acked === l.referral.count ? 'ok' : ''">{{ fa(l.referral.acked) }} نفر دیده‌اند</span>
            <small v-if="l.referral.pending.length" class="muted">منتظر: {{ l.referral.pending.join('، ') }}<span v-if="l.referral.more"> و {{ fa(l.referral.more) }} نفر دیگر</span></small>
          </div>
          <div class="btn-row">
            <button v-if="l.status === 'awaiting_approval'" class="btn primary sm" @click="openLetter(l)">بررسی و تأیید پاسخ</button>
            <button v-if="l.status === 'todo'" class="btn success sm" @click="complete(l)"><Icon name="check" :size="16" />انجام شد</button>
            <button v-if="l.reply && l.status === 'done'" class="btn ghost sm" @click="openLetter(l)">مشاهده پاسخ</button>
            <button v-if="!l.reply" class="btn ghost sm" @click="openLetter(l)">متن نامه</button>
            <button v-if="!['new', 'processing'].includes(l.status)" class="btn sm" @click="referring = l"><Icon name="forward" :size="16" />فرستادن به دیگران</button>
            <select v-if="l.category" class="cat-select" :value="l.category" @change="changeCategory(l, $event.target.value)" title="اصلاح دسته" aria-label="اصلاح دسته نامه">
              <option v-for="[k, v] in CATEGORY_OPTIONS" :key="k" :value="k">دسته: {{ v }}</option>
            </select>
          </div>
        </article>
      </section>

      <section v-else v-reveal class="card">
        <div class="card-head">کارهای دستیار <small>هر کاری که دستیار کرد، با دلیلش</small></div>
        <p v-if="!log.length" class="muted">هنوز کاری ثبت نشده.</p>
        <ol class="timeline">
          <li v-for="g in log" :key="g.id">
            <b>{{ fa(g.action) }}</b>
            <small>{{ fa(g.subject) }}</small>
            <small class="muted">{{ fa(g.reason) }}</small>
            <small class="muted">{{ fa(g.created_at) }}</small>
          </li>
        </ol>
      </section>
    </div>

    <div v-if="open" class="overlay" @click.self="open = null">
      <div class="dialog" v-pop>
        <h3>{{ fa(open.subject) }}</h3>
        <p class="muted small">{{ open.sender }} · {{ fa(open.received_short) }}</p>
        <div class="letter">{{ fa(open.body) }}</div>
        <template v-if="open.status === 'awaiting_approval'">
          <p class="small text-ink"><b>متنی که دستیار نوشته</b> <span class="muted">(قبل از تأیید بخوانید و در صورت نیاز ویرایش کنید)</span></p>
          <textarea v-model="reply" rows="7" class="ai-draft" aria-label="متن پاسخ"></textarea>
          <div class="dialog-actions">
            <button class="btn primary" :disabled="!reply.trim()" @click="approve"><Icon name="send" :size="18" />تأیید و ارسال پاسخ</button>
            <button class="btn ghost" @click="open = null">انصراف</button>
          </div>
        </template>
        <template v-else>
          <template v-if="open.reply"><p class="small text-ink"><b>پاسخ ثبت‌شده</b></p><div class="letter ai-draft">{{ fa(open.reply) }}</div></template>
          <div class="dialog-actions"><button class="btn ghost" @click="open = null">بستن</button></div>
        </template>
      </div>
    </div>

    <ReferDialog v-if="referring" :letter="referring" @close="referring = null" @done="referring = null; load()" />

    <div v-if="compose.open" class="overlay" @click.self="compose.open = false">
      <form class="dialog" v-pop @submit.prevent="addLetter">
        <h3>ثبت نامه جدید</h3>
        <p class="muted small">متن نامه را کپی کنید. دستیار عنوان، دسته، مهلت و کار لازم را خودش پیدا می‌کند.</p>
        <label class="field"><span>فرستنده <span class="muted">(اختیاری)</span></span><input v-model="compose.sender" placeholder="مثلا اداره آموزش و پرورش منطقه"></label>
        <label class="field"><span>موضوع <span class="muted">(اختیاری)</span></span><input v-model="compose.subject" placeholder="اگر خالی بماند، دستیار می‌نویسد"></label>
        <label class="field">متن نامه<textarea v-model="compose.body" rows="8" placeholder="متن کامل نامه را اینجا بچسبانید..."></textarea></label>
        <p v-if="compose.error" class="error-text">{{ compose.error }}</p>
        <div class="dialog-actions">
          <button class="btn primary" type="submit" :disabled="compose.body.trim().length < 15 || compose.saving"><Icon name="sparkles" :size="18" />ثبت و بررسی با دستیار</button>
          <button class="btn ghost" type="button" @click="compose.open = false">انصراف</button>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
