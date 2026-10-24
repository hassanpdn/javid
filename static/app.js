const { createApp, ref, reactive, computed, nextTick, onMounted, onUnmounted, watch } = Vue

// ---------- shared helpers ----------
const store = {
  get: (k) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k, v) => { try { localStorage.setItem(k, v) } catch {} },
  del: (k) => { try { localStorage.removeItem(k) } catch {} },
}
// Persian digits for everything we show
const fa = (v) => String(v ?? "").replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d])

// One shared session object; every component reads the token from here
const session = reactive({ token: store.get("token"), user: null })
const clearSession = () => { session.token = null; session.user = null; store.del("token") }

async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token || ""}` },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401 && path !== "/login") { clearSession(); throw new Error("401") }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || res.status)
  return data
}

// ---------- login ----------
const DEMO_USERS = [
  { u: "modir", role: "مدیر", name: "آقای دکتر انوشه‌پور", desc: "خلاصه روز، هشدارها و تصمیم‌ها", color: "#1f5f5b" },
  { u: "edari", role: "پرسنل اداری", name: "کارمند اداری", desc: "صندوق نامه هوشمند و دستیار پیگیری", color: "#7a5c2e" },
  { u: "moalem", role: "آموزگار", name: "سارا احمدی، پایه چهارم", desc: "کلاس و دانش‌آموزان", color: "#3d5a80", soon: true },
  { u: "karimi", role: "معلم ورزش", name: "نرگس کریمی", desc: "اعلان‌ها و تذکرها", color: "#8a4f7d", soon: true },
  { u: "moshaver", role: "مشاور", name: "مریم کاظمی", desc: "دانش‌آموزان نیازمند توجه و پیام به اولیا", color: "#4f7a5a" },
  { u: "vali", role: "ولی", name: "رضا محمدی، پدر آوا", desc: "گزارش هفتگی، پیشرفت و فرم‌های سلامت", color: "#a0442c" },
  { u: "daneshamooz", role: "دانش‌آموز", name: "آوا محمدی", desc: "نمره‌ها و پیشرفت من", color: "#c27c0e", soon: true },
]
const LoginPage = {
  template: `
  <div class="login-wrap">
    <div class="login-card fade-in">
      <span class="logo big">ج</span>
      <h1>دستیار هوشمند دبستان جاوید</h1>
      <p class="muted">نسخه آزمایشی برای نمایش امکانات سامانه</p>
      <p v-if="error" class="error-text">{{ error }}</p>
      <button type="button" class="demo-btn" :disabled="busy" @click="picker = true">ورود به نسخه آزمایشی</button>
    </div>

    <div v-if="picker" class="overlay" @click.self="picker = false">
      <div class="dialog wide pop-in">
        <div class="dialog-head">
          <div><h3>با کدام نقش وارد می‌شوید؟</h3><p class="muted small">هر نقش پنل و دسترسی‌های خودش را می‌بیند.</p></div>
          <button class="link" @click="picker = false">بستن</button>
        </div>
        <div class="role-grid">
          <button v-for="(d, i) in demo" :key="d.u" class="role-card" :style="{ '--c': d.color, animationDelay: i * 40 + 'ms' }"
                  :disabled="busy" @click="login(d.u, '1234')">
            <span class="role-icon">{{ d.role[0] }}</span>
            <span class="role-text">
              <b>{{ d.role }}</b>
              <span>{{ d.name }}</span>
              <small>{{ d.desc }}</small>
            </span>
            <span v-if="d.soon" class="soon">فعلا: چت اسناد</span>
          </button>
        </div>
      </div>
    </div>
  </div>`,
  setup() {
    const form = ref({ username: "", password: "" })
    const error = ref(""), busy = ref(false), picker = ref(false)
    const login = async (username, password) => {
      error.value = ""; busy.value = true
      try {
        const data = await api("/login", { username, password })
        picker.value = false
        session.token = data.token; session.user = data.user; store.set("token", data.token)
      } catch (e) {
        error.value = e.message === "Failed to fetch" ? "ارتباط با سرور برقرار نشد." : e.message
        picker.value = false
      } finally { busy.value = false }
    }
    watch(picker, (v) => document.body.classList.toggle("no-scroll", v))
    onUnmounted(() => document.body.classList.remove("no-scroll"))
    return { form, error, busy, picker, demo: DEMO_USERS, login, fa }
  },
}

// ---------- chat (used as a full page and inside the manager drawer) ----------
const EXAMPLES = {
  manager: ["ساعت کار کارکنان اداری چقدره؟", "مدرسه غیرانتفاعی مالیات میده؟", "ساعت شروع کلاس‌ها چنده؟"],
  staff: ["سال مالی مدرسه از کی شروع میشه؟", "مدرسه باید حساب بانکی جدا داشته باشه؟", "غیبت بیماری رو تا کی باید اطلاع داد؟"],
  default: ["ساعت شروع کلاس‌ها چنده؟", "اگه بچه‌م مریض بشه غیبتش چطور موجه میشه؟", "استفاده از موبایل توی مدرسه مجازه؟"],
}
const ChatBox = {
  // endpoint/examples/intro let other panels reuse the same chat (e.g. the parent's questions about their child)
  props: { endpoint: { default: "/chat" }, examples: { default: null }, intro: { default: null }, loadingText: { default: "در حال جستجو در اسناد" } },
  template: `
  <div class="chatbox">
    <main class="chat" ref="box">
      <div v-if="messages.length === 0" class="empty">
        <p>{{ intro || 'سؤالتون رو از آیین‌نامه‌ها و دستورالعمل‌ها بپرسید، یا یکی از این‌ها رو امتحان کنید:' }}</p>
        <button v-for="ex in shownExamples" :key="ex" class="example" @click="send(ex)">{{ ex }}</button>
      </div>
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.from]">
        <div class="bubble">{{ fa(m.text) }}</div>
        <div v-if="m.sources && m.sources.length" class="sources">
          <span>منبع:</span>
          <span v-for="s in m.sources" :key="s.doc + s.article" class="chip">{{ s.doc }}{{ s.article ? '، ' + fa(s.article) : '' }}</span>
          <span v-if="m.checked" class="muted small">· عددها مستقیم از سامانه مدرسه</span>
        </div>
      </div>
      <div v-if="loading" class="msg bot"><div class="bubble loading">{{ loadingText }}<span class="dots"></span></div></div>
    </main>
    <form class="composer" @submit.prevent="send(input)">
      <input v-model="input" :disabled="loading" placeholder="سؤالتون رو اینجا بنویسید...">
      <button type="submit" :disabled="loading || !input.trim()">ارسال</button>
    </form>
  </div>`,
  setup(props) {
    const messages = ref([]), input = ref(""), loading = ref(false), box = ref(null)
    const shownExamples = computed(() => props.examples || EXAMPLES[session.user?.role] || EXAMPLES.default)
    const scrollDown = async () => { await nextTick(); if (box.value) box.value.scrollTop = box.value.scrollHeight }
    const send = async (text) => {
      const question = text.trim()
      if (!question || loading.value) return
      messages.value.push({ from: "user", text: question }); input.value = ""; loading.value = true; scrollDown()
      try {
        const data = await api(props.endpoint, { question })
        messages.value.push({ from: "bot", text: data.answer, sources: data.sources, checked: data.checked })
      } catch (e) {
        if (e.message !== "401") messages.value.push({ from: "bot error", text: "ارتباط با سرور برقرار نشد. چند لحظه بعد دوباره امتحان کنید." })
      } finally { loading.value = false; scrollDown() }
    }
    return { messages, input, loading, box, shownExamples, send, fa }
  },
}

// ---------- notification bell (in every top bar) ----------
const KINDS = {
  warning: { label: "تذکر", path: "M12 8v5M12 16.5v.5M10.3 3.9 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" },
  letter: { label: "نامه", path: "M4 6h16v12H4zM4 7l8 6 8-6" },
  reminder: { label: "یادآوری", path: "M12 7v5l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" },
  info: { label: "اطلاع", path: "M5 12.5 10 17l9-10" },
  referral: { label: "ارجاع", path: "M19 12H5M11 6l-6 6 6 6" },
  suggestion: { label: "پیام مشاور", path: "M4 5h16v11H8l-4 4V5Z" },
}
// small line icon used in the notification list
const KindIcon = {
  props: ["kind"],
  template: `<span class="bp-icon"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path :d="(KINDS[kind] || KINDS.info).path"/></svg></span>`,
  setup() { return { KINDS } },
}
const NotificationBell = {
  components: { KindIcon },
  template: `
  <div class="bell-wrap" ref="wrap">
    <button class="bell" :class="{ on: open }" @click="open = !open" :aria-label="'اعلان‌ها، ' + fa(unread) + ' خوانده‌نشده'">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
      <span v-if="unread" class="badge-dot">{{ fa(unread > 99 ? '99+' : unread) }}</span>
    </button>

    <div v-if="open" class="bell-panel pop-in">
      <header class="bp-head">
        <div class="bp-title-row"><b>اعلان‌ها</b><small v-if="unread" class="muted">{{ fa(unread) }} خوانده‌نشده</small></div>
        <button v-if="unread" class="link small" @click="readAll">همه خوانده شد</button>
      </header>
      <nav class="bp-filters">
        <button v-for="f in filters" :key="f.key" :class="{ on: filter === f.key }" @click="filter = f.key">
          {{ f.label }}<span v-if="f.n" class="bp-n">{{ fa(f.n) }}</span>
        </button>
      </nav>
      <div class="bp-list">
        <div v-if="!visible.length" class="bp-empty">
          <span class="bp-empty-icon">✓</span>
          <p>اعلانی در این بخش نیست.</p>
        </div>
        <button v-for="n in visible" :key="n.id" :class="['bp-item', 'k-' + n.kind, { unread: !n.read_at }]" @click="show(n)">
          <KindIcon :kind="n.kind" />
          <span class="bp-body">
            <span class="bp-title">{{ fa(n.title) }}</span>
            <span class="bp-meta">
              <span>{{ (KINDS[n.kind] || KINDS.info).label }}</span>
              <span class="sep">·</span>
              <span>{{ fa(n.created_at) }}</span>
              <span v-if="n.needs_ack && !n.ack_at" class="bp-pill">نیاز به رؤیت</span>
              <span v-else-if="n.ack_at" class="bp-pill ok">رؤیت شد</span>
            </span>
          </span>
          <span v-if="!n.read_at" class="bp-dot" aria-label="خوانده‌نشده"></span>
        </button>
      </div>
    </div>

    <div v-if="current" class="overlay" @click.self="current = null">
      <div class="dialog pop-in">
        <div class="dlg-kind" :class="'k-' + current.kind"><KindIcon :kind="current.kind" />{{ (KINDS[current.kind] || KINDS.info).label }}</div>
        <h3>{{ fa(current.title) }}</h3>
        <p class="muted small">{{ fa(current.created_at) }}</p>
        <div v-if="current.body" class="letter">{{ fa(current.body) }}</div>
        <p v-if="current.ack_at" class="ok small">✓ رؤیت شد: {{ fa(current.ack_at) }}</p>
        <div class="dialog-actions">
          <button v-if="current.needs_ack && !current.ack_at" class="btn primary" @click="ack">رؤیت شد</button>
          <button class="btn ghost" @click="current = null">بستن</button>
        </div>
      </div>
    </div>
  </div>`,
  setup() {
    const items = ref([]), unread = ref(0), open = ref(false), current = ref(null), filter = ref("all"), wrap = ref(null)
    const filters = computed(() => [
      { key: "all", label: "همه" },
      { key: "unread", label: "خوانده‌نشده", n: unread.value },
      { key: "ack", label: "نیاز به رؤیت", n: items.value.filter((n) => n.needs_ack && !n.ack_at).length },
    ])
    const visible = computed(() => items.value.filter((n) =>
      filter.value === "unread" ? !n.read_at : filter.value === "ack" ? n.needs_ack && !n.ack_at : true))
    const load = async () => {
      try {
        const d = await api("/notifications")
        if (d.unread > unread.value) window.dispatchEvent(new Event("notifications-changed"))
        items.value = d.items; unread.value = d.unread
      } catch {}
    }
    const show = async (n) => {
      open.value = false; current.value = n
      if (!n.read_at) { await api(`/notifications/${n.id}/read`, {}); load() }
    }
    const ack = async () => {
      await api(`/notifications/${current.value.id}/ack`, {})
      await load(); current.value = items.value.find((n) => n.id === current.value.id)
    }
    const readAll = async () => { await api("/notifications/read-all", {}); load() }
    // close the panel when clicking anywhere outside it
    const outside = (e) => { if (open.value && wrap.value && !wrap.value.contains(e.target)) open.value = false }
    let timer
    onMounted(() => { load(); timer = setInterval(load, 15000); document.addEventListener("click", outside) })
    onUnmounted(() => { clearInterval(timer); document.removeEventListener("click", outside) })
    watch(current, (v) => document.body.classList.toggle("no-scroll", !!v))
    return { KINDS, items, unread, open, current, filter, filters, visible, wrap, show, ack, readAll, fa }
  },
}

const TopBar = {
  components: { NotificationBell },
  props: ["title"],
  template: `
  <header class="topbar">
    <div class="brand"><span class="logo">ج</span><div><b>دبستان جاوید</b><small>{{ title }}</small></div></div>
    <div class="who"><NotificationBell /><span class="name">{{ user.full_name }}</span><button class="link" @click="logout">خروج</button></div>
  </header>`,
  setup() {
    const logout = async () => { try { await api("/logout", {}) } catch {} clearSession() }
    return { user: computed(() => session.user), logout }
  },
}

const ChatPage = {
  components: { TopBar, ChatBox },
  template: `<div class="shell"><TopBar :title="'دستیار اسناد · ' + user.role_name" /><ChatBox /></div>`,
  setup() { return { user: computed(() => session.user) } },
}

// ---------- small bar chart, drawn with plain SVG ----------
const BarChart = {
  props: ["points"],  // [{ jdate, rate }]
  template: `
  <svg :viewBox="'0 0 ' + W + ' ' + H" class="bars" role="img" aria-label="نمودار درصد حضور">
    <g v-for="(p, i) in points" :key="p.jdate">
      <rect :x="x(i)" :y="y(p.rate)" :width="bw" :height="H - 26 - y(p.rate)" rx="5"
            :class="p.rate < 95 ? 'bar low' : 'bar'" :style="{ animationDelay: i * 50 + 'ms' }" />
      <text :x="x(i) + bw / 2" :y="y(p.rate) - 6" class="val">{{ fa(p.rate) }}</text>
      <text :x="x(i) + bw / 2" :y="H - 8" class="lbl">{{ fa(p.jdate) }}</text>
    </g>
  </svg>`,
  setup(props) {
    const W = 900, H = 200, gap = 18
    const bw = computed(() => (W - gap * (props.points.length - 1)) / props.points.length)
    const x = (i) => W - (i + 1) * bw.value - i * gap          // right to left, like Persian reading
    const y = (rate) => 26 + (100 - Math.max(rate, 80)) * (H - 60) / 20  // zoom on the 80..100 range
    return { W, H, bw, x, y, fa }
  },
}

// ---------- manager panel ----------
const ManagerPanel = {
  components: { TopBar, ChatBox, BarChart },
  template: `
  <div class="page">
    <TopBar title="پنل مدیر" />
    <div class="content">
      <section class="hello fade-in">
        <h2>روز بخیر</h2>
        <p class="muted">{{ data ? fa(data.today) : '' }}</p>
      </section>

      <section class="card brief fade-in" style="animation-delay:60ms">
        <div class="card-head"><span class="spark">✦</span> خلاصه امروز</div>
        <p v-if="brief">{{ fa(brief) }}</p>
        <div v-else class="shimmer"><span></span><span></span><span style="width:60%"></span></div>
      </section>

      <section v-if="data" class="stats">
        <div class="card stat fade-in" style="animation-delay:120ms">
          <small>حضور دانش‌آموزان</small>
          <b>{{ fa(data.students.present) }} <span>از {{ fa(data.students.total) }}</span></b>
          <small class="muted">{{ fa(data.students.absent) }} غایب، {{ fa(data.students.late) }} تأخیر</small>
        </div>
        <div class="card stat fade-in" style="animation-delay:170ms">
          <small>تأخیر معلمان امروز</small>
          <b>{{ fa(data.late_teachers.length) }}</b>
          <small class="muted">{{ data.late_teachers.map(t => t.full_name + ' ' + fa(t.check_in)).join('، ') || 'همه به موقع' }}</small>
        </div>
        <div class="card stat fade-in" style="animation-delay:220ms">
          <small>نامه‌های منتظر رسیدگی</small>
          <b>{{ fa(data.open_letters) }}</b>
          <small class="muted">در صندوق پرسنل اداری</small>
        </div>
      </section>

      <section v-if="data" class="card fade-in" style="animation-delay:270ms">
        <div class="card-head">نیاز به توجه شما <span class="count">{{ fa(data.alerts.filter(a => !a.done).length) }}</span></div>
        <ul class="alerts">
          <li v-for="(a, i) in data.alerts" :key="i" :class="['alert', a.type, { done: a.done }]">
            <span class="dot"></span>
            <div class="alert-body">
              <b>{{ fa(a.title) }}</b>
              <small class="muted">{{ fa(a.detail) }}</small>
              <small v-if="a.done" class="ok">✓ {{ fa(a.done_text) }}</small>
            </div>
            <button v-if="a.type === 'teacher_late' && !a.done" class="btn" @click="openDraft(a)">پیش‌نویس تذکر</button>
            <div v-if="a.type === 'letter_decision'" class="btn-row">
              <button class="btn" @click="decide(a, true)">موافقم</button>
              <button class="btn ghost" @click="decide(a, false)">مخالفم</button>
            </div>
          </li>
        </ul>
      </section>

      <section v-if="data" class="card fade-in" style="animation-delay:320ms">
        <div class="card-head">درصد حضور دانش‌آموزان در ده روز اخیر</div>
        <BarChart :points="data.trend" />
      </section>
    </div>

    <!-- written warning dialog -->
    <div v-if="draft.open" class="overlay" @click.self="draft.open = false">
      <div class="dialog pop-in">
        <h3>تذکر کتبی به {{ draft.alert.name }}</h3>
        <p class="muted small">این متن را دستیار نوشته است. قبل از صدور بخوانید و هر جا لازم است ویرایش کنید.</p>
        <div v-if="draft.loading" class="shimmer tall"><span></span><span></span><span></span><span style="width:50%"></span></div>
        <p v-if="!draft.loading && draft.verified === true" class="check ok">✓ تاریخ‌ها و ساعت‌های این متن با ثبت ورود سامانه تطبیق داده شد.</p>
        <p v-if="!draft.loading && draft.verified === false" class="check bad">این موارد ثبت‌شده در متن نیامده یا متفاوت آمده: {{ fa(draft.missing.join('، ')) }}. قبل از صدور اصلاح کنید.</p>
        <textarea v-if="!draft.loading" v-model="draft.text" rows="10"></textarea>
        <div class="dialog-actions">
          <button class="btn primary" :disabled="draft.loading || !draft.text.trim() || draft.saving" @click="issue">تأیید و صدور</button>
          <button class="btn ghost" @click="draft.open = false">انصراف</button>
        </div>
      </div>
    </div>

    <!-- docs chat drawer -->
    <button class="fab" @click="chatOpen = true">پرسش از اسناد</button>
    <div v-if="chatOpen" class="overlay" @click.self="chatOpen = false">
      <aside class="drawer slide-in">
        <div class="drawer-head"><b>پرسش از آیین‌نامه‌ها</b><button class="link" @click="chatOpen = false">بستن</button></div>
        <ChatBox />
      </aside>
    </div>
  </div>`,
  setup() {
    const data = ref(null), brief = ref(""), chatOpen = ref(false)
    const draft = reactive({ open: false, alert: null, text: "", loading: false, saving: false, verified: null, missing: [] })
    const load = async () => { data.value = await api("/manager/overview") }
    // While a dialog or the chat drawer is open, freeze the page behind it
    watch(() => draft.open || chatOpen.value, (open) => document.body.classList.toggle("no-scroll", open))
    const onNotify = () => load()
    window.addEventListener("notifications-changed", onNotify)
    onUnmounted(() => { document.body.classList.remove("no-scroll"); window.removeEventListener("notifications-changed", onNotify) })
    onMounted(async () => {
      await load()
      try { brief.value = (await api("/manager/briefing")).text } catch { brief.value = "خلاصه امروز در دسترس نیست." }
    })
    const openDraft = async (alert) => {
      Object.assign(draft, { open: true, alert, text: "", loading: true, verified: null, missing: [] })
      try {
        const r = await api("/manager/warnings/draft", { teacher_id: alert.teacher_id })
        Object.assign(draft, { text: r.text, verified: r.verified, missing: r.missing })
      }
      catch { draft.text = "" } finally { draft.loading = false }
    }
    const issue = async () => {
      draft.saving = true
      try { await api("/manager/warnings", { teacher_id: draft.alert.teacher_id, text: draft.text }); draft.open = false; await load() }
      finally { draft.saving = false }
    }
    const decide = async (alert, approve) => {
      await api(`/manager/letters/${alert.letter_id}/decide`, { approve }); await load()
    }
    return { data, brief, chatOpen, draft, openDraft, issue, decide, fa }
  },
}

// ---------- refer a letter to people (staff panel) ----------
const CATEGORY_OPTIONS = [
  ["ack", "اعلام وصول"], ["stats", "درخواست آمار"], ["meeting", "دعوت به جلسه"],
  ["info", "برای اطلاع"], ["decision", "نیازمند تصمیم مدیر"], ["request", "نیازمند اقدام"],
]
const ReferDialog = {
  props: ["letter"],
  emits: ["close", "done"],
  template: `
  <div class="overlay" @click.self="$emit('close')">
    <form class="dialog wide pop-in" @submit.prevent="send">
      <div class="dialog-head">
        <div><h3>ارجاع نامه</h3><p class="muted small">{{ fa(letter.subject) }}</p></div>
        <button type="button" class="link" @click="$emit('close')">بستن</button>
      </div>

      <div class="suggest">
        <span class="spark">✦</span>
        <div v-if="suggestion.loading" class="muted small">دستیار در حال پیشنهاد گیرنده...</div>
        <div v-else-if="suggestion.keys.length" class="suggest-body">
          <span class="small">پیشنهاد دستیار: <b>{{ suggestion.keys.map(label).join('، ') }}</b></span>
          <small class="muted" v-if="suggestion.reason">{{ fa(suggestion.reason) }}</small>
        </div>
        <div v-else class="muted small">دستیار پیشنهادی نداشت. گیرنده را خودتان انتخاب کنید.</div>
        <button v-if="suggestion.keys.length" type="button" class="btn" @click="applySuggestion">اعمال پیشنهاد</button>
      </div>

      <div class="picked">
        <span v-if="!picked.length" class="muted small">هنوز گیرنده‌ای انتخاب نشده.</span>
        <span v-for="k in picked" :key="k" :class="['pick', kindOf(k)]">{{ label(k) }}<button type="button" @click="toggle(k)" aria-label="حذف">×</button></span>
      </div>

      <input class="search" v-model="q" placeholder="جستجوی نام، درس یا نام دانش‌آموز...">
      <div class="people">
        <template v-for="sec in sections" :key="sec.title">
          <div v-if="sec.items.length" class="people-sec">{{ sec.title }}</div>
          <button v-for="p in sec.items" :key="p.key" type="button" :class="['person', { on: picked.includes(p.key) }]" @click="toggle(p.key)">
            <span class="check-box">{{ picked.includes(p.key) ? '✓' : '' }}</span>
            <span class="person-text"><b>{{ p.label }}</b><small v-if="p.sub" class="muted">{{ p.sub }}</small></span>
          </button>
        </template>
      </div>

      <label class="field"><span>یادداشت برای گیرندگان <span class="muted">(اختیاری)</span></span>
        <textarea v-model="note" rows="2" placeholder="مثلا: لطفا تا ۳ دی دو دانش‌آموز معرفی کنید."></textarea></label>

      <div v-if="hasParents" class="parent-box">
        <div class="row-between"><b class="small">پیام برای اولیا</b>
          <button type="button" class="link small" @click="draftParent" :disabled="parent.loading">{{ parent.loading ? 'در حال نوشتن...' : 'نوشتن دوباره با دستیار' }}</button></div>
        <p class="muted small">اولیا متن اداری نامه را نمی‌بینند؛ فقط این پیام ساده را دریافت می‌کنند.</p>
        <div v-if="parent.loading && !parent.text" class="shimmer"><span></span><span></span><span style="width:60%"></span></div>
        <textarea v-else v-model="parent.text" rows="5"></textarea>
      </div>

      <label class="ack-row"><input type="checkbox" v-model="needsAck"> گیرندگان باید «رؤیت شد» را بزنند</label>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions">
        <button class="btn primary" type="submit" :disabled="!picked.length || sending || (hasParents && !parent.text.trim())">
          ارجاع به {{ fa(estimate) }} نفر</button>
        <button class="btn ghost" type="button" @click="$emit('close')">انصراف</button>
      </div>
    </form>
  </div>`,
  setup(props, { emit }) {
    const options = ref({ groups: [], people: [] })
    const picked = ref([]), q = ref(""), note = ref(""), needsAck = ref(true), sending = ref(false), error = ref("")
    const suggestion = reactive({ loading: true, keys: [], reason: "" })
    const parent = reactive({ loading: false, text: "" })
    const all = computed(() => [...options.value.groups, ...options.value.people])
    const find = (k) => all.value.find((p) => p.key === k)
    const label = (k) => find(k)?.label || k
    const kindOf = (k) => find(k)?.kind || "staff"
    const match = (p) => !q.value.trim() || (p.label + " " + (p.sub || "")).includes(q.value.trim())
    const sections = computed(() => [
      { title: "گروه‌ها", items: options.value.groups.filter(match) },
      { title: "کارکنان و معلمان", items: options.value.people.filter((p) => p.kind !== "parent" && match(p)) },
      { title: "اولیا", items: options.value.people.filter((p) => p.kind === "parent" && match(p)) },
    ])
    const hasParents = computed(() => picked.value.some((k) => kindOf(k) === "parent"))
    // rough head count for the button label
    const estimate = computed(() => picked.value.reduce((n, k) => n + (
      k === "group:parents" ? options.value.people.filter((p) => p.kind === "parent").length :
      k === "group:teachers" ? options.value.people.filter((p) => p.kind === "teacher").length :
      k.startsWith("group:class:") ? 15 : 1), 0))
    const toggle = (k) => { picked.value = picked.value.includes(k) ? picked.value.filter((x) => x !== k) : [...picked.value, k] }
    const applySuggestion = () => { picked.value = [...new Set([...picked.value, ...suggestion.keys])] }
    const draftParent = async () => {
      parent.loading = true
      try { parent.text = (await api(`/staff/letters/${props.letter.id}/parent-draft`, {})).text } catch {}
      finally { parent.loading = false }
    }
    // the first time a parent group is picked, the agent writes the parent message automatically
    watch(hasParents, (v) => { if (v && !parent.text) draftParent() })
    const send = async () => {
      sending.value = true; error.value = ""
      try {
        await api(`/staff/letters/${props.letter.id}/refer`,
          { recipients: picked.value, note: note.value, needs_ack: needsAck.value, parent_text: parent.text })
        emit("done")
      } catch (e) { error.value = e.message } finally { sending.value = false }
    }
    onMounted(async () => {
      options.value = await api("/staff/recipients")
      try { Object.assign(suggestion, await api(`/staff/letters/${props.letter.id}/suggest`, {})) } catch {}
      suggestion.loading = false
    })
    return { picked, q, note, needsAck, sending, error, suggestion, parent, sections, hasParents, estimate,
             label, kindOf, toggle, applySuggestion, draftParent, send, fa }
  },
}

// ---------- staff panel: smart letter inbox ----------
const TABS = [
  { key: "mine", label: "منتظر شما", match: (l) => ["new", "processing", "awaiting_approval", "todo"].includes(l.status) },
  { key: "manager", label: "ارجاع به مدیر", match: (l) => ["needs_manager", "forwarded"].includes(l.status) },
  { key: "done", label: "بسته‌شده", match: (l) => l.status === "done" },
  { key: "log", label: "دفترچه دستیار" },
]
const StaffPanel = {
  components: { TopBar, ChatBox, ReferDialog },
  template: `
  <div class="page">
    <TopBar title="پنل اداری" />
    <div class="content">
      <section class="hello fade-in row-between">
        <div><h2>روز بخیر</h2><p class="muted">صندوق نامه‌های اداری</p></div>
        <button class="btn primary" @click="compose.open = true" :disabled="agent.running">+ ثبت نامه جدید</button>
      </section>

      <section class="card agent fade-in" :class="{ running: agent.running }">
        <div class="agent-row">
          <span class="agent-icon" :class="{ spin: agent.running }">✦</span>
          <div class="agent-text">
            <b v-if="agent.running">دستیار در حال بررسی نامه‌ها: {{ fa(agent.processed) }} از {{ fa(agent.total) }}</b>
            <b v-else-if="agent.error">{{ agent.error }}</b>
            <b v-else>همه نامه‌ها بررسی شد</b>
            <small class="muted" v-if="agent.running && agent.current">در حال خواندن: {{ fa(agent.current) }}</small>
            <small class="muted" v-else-if="!agent.running && !agent.error">
              {{ fa(count(l => l.status === 'done' && l.category === 'ack')) }} اعلام وصول خودکار بسته شد،
              {{ fa(count(TABS[0].match)) }} مورد منتظر شماست و {{ fa(count(TABS[1].match)) }} مورد به مدیر رفت.
            </small>
          </div>
          <button v-if="agent.error" class="btn" @click="runAgent">تلاش دوباره</button>
        </div>
        <div v-if="agent.running" class="progress"><span :style="{ width: (agent.total ? 100 * agent.processed / agent.total : 0) + '%' }"></span></div>
      </section>

      <nav class="tabs">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">
          {{ t.label }}<span v-if="t.match" class="tab-count">{{ fa(count(t.match)) }}</span>
        </button>
      </nav>

      <section v-if="tab !== 'log'" class="letters">
        <p v-if="!shown.length" class="muted empty-note">موردی نیست.</p>
        <article v-for="l in shown" :key="l.id" :class="['letter-card', 'card', { fresh: fresh.has(l.id) }]">
          <div class="lc-top">
            <b>{{ fa(l.subject) }}</b>
            <span v-if="l.deadline_short && l.status !== 'done'" :class="['chip', { hot: l.days_left <= 3 }]">مهلت {{ fa(l.deadline_short) }}</span>
          </div>
          <small class="muted">{{ l.sender }} · {{ fa(l.received_short) }}</small>
          <div class="lc-tags">
            <span v-if="l.category_name" class="tag">{{ l.category_name }}</span>
            <span :class="['tag', 'st-' + l.status]">{{ l.status_name }}</span>
          </div>
          <p v-if="l.summary" class="lc-summary">{{ fa(l.summary) }}</p>
          <p v-if="l.action && l.status !== 'done'" class="lc-action">پیشنهاد دستیار: {{ fa(l.action) }}</p>
          <div v-if="l.referral" class="ref-line">
            <span>ارجاع به {{ fa(l.referral.count) }} نفر</span>
            <span v-if="l.referral.needs_ack" class="sep">·</span>
            <span v-if="l.referral.needs_ack" :class="l.referral.acked === l.referral.count ? 'ok' : ''">{{ fa(l.referral.acked) }} رؤیت</span>
            <small v-if="l.referral.pending.length" class="muted">منتظر: {{ l.referral.pending.join('، ') }}<span v-if="l.referral.more"> و {{ fa(l.referral.more) }} نفر دیگر</span></small>
          </div>
          <div class="btn-row">
            <button v-if="l.status === 'awaiting_approval'" class="btn primary" @click="openLetter(l)">بررسی و تأیید پاسخ</button>
            <button v-if="l.status === 'todo'" class="btn" @click="complete(l)">انجام شد</button>
            <button v-if="l.reply && l.status === 'done'" class="btn ghost" @click="openLetter(l)">مشاهده پاسخ</button>
            <button v-if="!l.reply" class="btn ghost" @click="openLetter(l)">متن نامه</button>
            <button v-if="!['new', 'processing'].includes(l.status)" class="btn ghost" @click="referring = l">ارجاع</button>
            <select v-if="l.category" class="cat-select" :value="l.category" @change="changeCategory(l, $event.target.value)" title="اصلاح دسته">
              <option v-for="[k, v] in CATEGORY_OPTIONS" :key="k" :value="k">دسته: {{ v }}</option>
            </select>
          </div>
        </article>
      </section>

      <section v-else class="card">
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
      <div class="dialog pop-in">
        <h3>{{ fa(open.subject) }}</h3>
        <p class="muted small">{{ open.sender }} · {{ fa(open.received_short) }}</p>
        <div class="letter">{{ fa(open.body) }}</div>
        <template v-if="open.status === 'awaiting_approval'">
          <p class="small"><b>پیش‌نویس پاسخ دستیار</b> <span class="muted">(قبل از تأیید بخوانید و در صورت نیاز ویرایش کنید)</span></p>
          <textarea v-model="reply" rows="7"></textarea>
          <div class="dialog-actions">
            <button class="btn primary" :disabled="!reply.trim()" @click="approve">تأیید و ارسال پاسخ</button>
            <button class="btn ghost" @click="open = null">انصراف</button>
          </div>
        </template>
        <template v-else>
          <template v-if="open.reply"><p class="small"><b>پاسخ ثبت‌شده</b></p><div class="letter">{{ fa(open.reply) }}</div></template>
          <div class="dialog-actions"><button class="btn ghost" @click="open = null">بستن</button></div>
        </template>
      </div>
    </div>

    <ReferDialog v-if="referring" :letter="referring" @close="referring = null" @done="referring = null; load()" />

    <div v-if="compose.open" class="overlay" @click.self="compose.open = false">
      <form class="dialog pop-in" @submit.prevent="addLetter">
        <h3>ثبت نامه جدید</h3>
        <p class="muted small">متن نامه را کپی کنید. دستیار عنوان، دسته، مهلت و کار لازم را خودش پیدا می‌کند.</p>
        <label class="field"><span>فرستنده <span class="muted">(اختیاری)</span></span><input v-model="compose.sender" placeholder="مثلا اداره آموزش و پرورش منطقه"></label>
        <label class="field"><span>موضوع <span class="muted">(اختیاری)</span></span><input v-model="compose.subject" placeholder="اگر خالی بماند، دستیار می‌نویسد"></label>
        <label class="field">متن نامه<textarea v-model="compose.body" rows="8" placeholder="متن کامل نامه را اینجا بچسبانید..."></textarea></label>
        <p v-if="compose.error" class="error-text">{{ compose.error }}</p>
        <div class="dialog-actions">
          <button class="btn primary" type="submit" :disabled="compose.body.trim().length < 15 || compose.saving">ثبت و بررسی با دستیار</button>
          <button class="btn ghost" type="button" @click="compose.open = false">انصراف</button>
        </div>
      </form>
    </div>

    <button class="fab" @click="chatOpen = true">پرسش از اسناد</button>
    <div v-if="chatOpen" class="overlay" @click.self="chatOpen = false">
      <aside class="drawer slide-in">
        <div class="drawer-head"><b>پرسش از آیین‌نامه‌ها</b><button class="link" @click="chatOpen = false">بستن</button></div>
        <ChatBox />
      </aside>
    </div>
  </div>`,
  setup() {
    const letters = ref([]), log = ref([]), tab = ref("mine"), open = ref(null), reply = ref(""), chatOpen = ref(false)
    const compose = reactive({ open: false, sender: "", subject: "", body: "", saving: false, error: "" })
    const referring = ref(null)
    const changeCategory = async (l, category) => { await api(`/staff/letters/${l.id}/category`, { category }); await load() }
    const fresh = ref(new Set())
    const agent = reactive({ running: false, processed: 0, total: 0, current: "", error: "" })
    const count = (fn) => letters.value.filter(fn).length
    const shown = computed(() => {
      const t = TABS.find((x) => x.key === tab.value)
      return t.match ? letters.value.filter(t.match) : []
    })
    const load = async () => {
      letters.value = await api("/staff/letters")
      log.value = await api("/staff/log")
    }
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
        if (e.message !== "401") agent.error = "دستیار در دسترس نیست. مدل محلی روشن است؟"
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
    watch(() => !!open.value || chatOpen.value || compose.open || !!referring.value, (v) => document.body.classList.toggle("no-scroll", v))
    onMounted(async () => { await load(); runAgent() })
    onUnmounted(() => document.body.classList.remove("no-scroll"))
    return { TABS, CATEGORY_OPTIONS, letters, log, tab, open, reply, chatOpen, compose, referring, fresh, agent, count, shown,
             runAgent, load, openLetter, approve, complete, addLetter, changeCategory, fa }
  },
}

// ---------- shared pieces for student data ----------
const LEVEL_NAMES = { 4: "خیلی خوب", 3: "خوب", 2: "قابل قبول", 1: "نیاز به تلاش بیشتر" }
const Sparkline = {
  props: ["points", "change"],
  template: `
  <svg viewBox="0 0 120 36" class="spark-svg" :class="tone" role="img" :aria-label="'روند: ' + points.map(p => LEVEL_NAMES[p]).join('، ')">
    <line v-for="l in [1,2,3,4]" :key="l" x1="4" x2="116" :y1="y(l)" :y2="y(l)" class="grid" />
    <polyline :points="points.map((p, i) => x(i) + ',' + y(p)).join(' ')" class="line" />
    <circle v-for="(p, i) in points" :key="i" :cx="x(i)" :cy="y(p)" :r="i === points.length - 1 ? 3.6 : 2.4" class="dot" />
  </svg>`,
  setup(props) {
    // right to left: the oldest point on the right, today on the left
    const x = (i) => 116 - i * (112 / Math.max(props.points.length - 1, 1))
    const y = (l) => 32 - (l - 1) * 9.3
    const tone = computed(() => props.change <= -1 ? "down" : props.change >= 1 ? "up" : "flat")
    return { x, y, tone, LEVEL_NAMES }
  },
}
const LevelChip = {
  props: ["level"],
  template: `<span :class="['level', 'l' + level]">{{ LEVEL_NAMES[level] }}</span>`,
  setup() { return { LEVEL_NAMES } },
}
const SIGNAL_ICON = { grade: "↘", absence: "○", health: "♡" }
// health flags are grouped into one chip so the list stays calm
const groupSignals = (signals) => {
  const health = signals.filter((s) => s.type === "health")
  const rest = signals.filter((s) => s.type !== "health")
  return health.length ? [...rest, { type: "health", text: `فرم سلامت: ${fa(health.length)} مورد` }] : rest
}
const Avatar = {
  props: ["name", "size"],
  template: `<span class="avatar" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px', fontSize: (size || 40) * 0.42 + 'px' }">{{ (name || '?')[0] }}</span>`,
}

// ---------- counselor: one student's file, opened in a side drawer ----------
const StudentProfile = {
  components: { Sparkline, LevelChip, Avatar },
  props: ["sid"],
  emits: ["close", "changed"],
  template: `
  <div class="overlay" @click.self="$emit('close')">
    <aside class="drawer wide-drawer slide-in">
      <div class="drawer-head">
        <div class="head-person" v-if="f"><Avatar :name="f.name" :size="44" /><div><b>{{ f.name }}</b><small class="muted">کلاس {{ f.class }} · آموزگار: {{ f.teacher }}</small></div></div>
        <span v-else></span>
        <button class="link" @click="$emit('close')">بستن</button>
      </div>
      <div v-if="!f" class="drawer-body"><div class="shimmer"><span></span><span></span><span style="width:60%"></span></div></div>
      <div v-else class="drawer-body">

        <section class="card brief">
          <div class="card-head"><span class="spark">✦</span> جمع‌بندی دستیار</div>
          <p v-if="insight">{{ fa(insight) }}</p>
          <div v-else class="shimmer"><span></span><span style="width:70%"></span></div>
          <div v-if="f.signals.length" class="chips">
            <span v-for="s in f.signals" :key="s.text" :class="['sig', s.type]">{{ fa(s.text) }}</span>
          </div>
        </section>

        <section class="card">
          <div class="card-head">پیام به ولی</div>
          <template v-if="draft">
            <p class="muted small">این متن را دستیار نوشته است. بخوانید، در صورت نیاز ویرایش کنید و بعد بفرستید.</p>
            <label class="field"><span>گام بعدی برای شما</span><textarea v-model="draft.for_counselor" rows="2"></textarea></label>
            <label class="field"><span>پیام برای ولی</span><textarea v-model="draft.for_parent" rows="5"></textarea></label>
            <div class="dialog-actions">
              <button class="btn primary" :disabled="!draft.for_parent.trim()" @click="approve">تأیید و ارسال به ولی</button>
              <button class="btn ghost" @click="dismiss">کنار گذاشتن</button>
            </div>
          </template>
          <template v-else>
            <p class="muted small" v-if="!sent.length">هنوز پیامی برای ولیِ {{ f.first_name }} فرستاده نشده.</p>
            <div v-for="s in sent" :key="s.id" class="sent-msg">
              <small class="ok">✓ ارسال شد · {{ fa(s.approved_at) }}</small>
              <p>{{ fa(s.for_parent) }}</p>
              <small v-if="s.for_counselor" class="muted">گام شما: {{ fa(s.for_counselor) }}</small>
            </div>
            <button class="btn" :disabled="drafting" @click="suggest">{{ drafting ? 'دستیار در حال نوشتن...' : 'نوشتن پیام با دستیار' }}</button>
            <p v-if="error" class="error-text">{{ error }}</p>
          </template>
        </section>

        <section class="card">
          <div class="card-head">پیشرفت درسی <small class="muted">از مهر تا امروز</small></div>
          <div class="progress-list">
            <div v-for="p in f.progress" :key="p.subject" class="prog-row">
              <span class="prog-sub">{{ p.subject }}</span>
              <Sparkline :points="p.points" :change="p.change" />
              <LevelChip :level="p.now" />
            </div>
          </div>
          <p v-for="p in f.progress.filter(p => p.note)" :key="'n' + p.subject" class="teacher-note">یادداشت آموزگار ({{ p.subject }}): {{ p.note }}</p>
        </section>

        <section class="card">
          <div class="card-head">حضور <small class="muted">۳۰ روز اخیر</small></div>
          <div class="mini-stats">
            <div><b>{{ fa(f.attendance.present) }}</b><small>روز حاضر</small></div>
            <div :class="{ warn: f.attendance.unexcused >= 3 }"><b>{{ fa(f.attendance.absent) }}</b><small>غیبت ({{ fa(f.attendance.unexcused) }} غیرموجه)</small></div>
            <div><b>{{ fa(f.attendance.late) }}</b><small>تأخیر</small></div>
          </div>
          <div v-if="f.attendance.absent_days.length" class="chips">
            <span v-for="d in f.attendance.absent_days" :key="d.date" :class="['day', { ok: d.excused }]">{{ fa(d.date) }}{{ d.excused ? ' · موجه' : '' }}</span>
          </div>
        </section>

        <section class="card">
          <div class="card-head">فرم‌های سلامت <small class="muted">تکمیل‌شده توسط ولی</small></div>
          <div class="forms-grid">
            <div v-for="k in ['physical', 'wellbeing']" :key="k" class="form-tile">
              <b>{{ k === 'physical' ? 'سلامت جسمی' : 'حال و احوال' }}</b>
              <template v-if="f.forms[k]">
                <small class="muted">{{ fa(f.forms[k].date) }}</small>
                <div class="chips"><span v-for="fl in f.forms[k].flags" :key="fl" class="sig health">{{ fa(fl) }}</span>
                  <span v-if="!f.forms[k].flags.length" class="sig ok">مورد قابل توجهی ندارد</span></div>
                <details><summary class="small">پاسخ‌ها</summary>
                  <dl class="answers"><template v-for="[key, label] in f.fields[k]" :key="key"><dt>{{ label }}</dt><dd>{{ fa(f.forms[k].data[key] ?? '-') }}</dd></template></dl>
                </details>
              </template>
              <small v-else class="muted">هنوز تکمیل نشده</small>
            </div>
          </div>
        </section>

        <section class="card">
          <div class="card-head">یادداشت‌های مشاور <small class="muted">فقط برای شما، ولی این‌ها را نمی‌بیند</small></div>
          <form class="note-add" @submit.prevent="addNote">
            <textarea v-model="newNote" rows="2" placeholder="یادداشت جدید..."></textarea>
            <button class="btn" :disabled="!newNote.trim()">ثبت</button>
          </form>
          <ul class="notes"><li v-for="(n, i) in f.notes" :key="i"><small class="muted">{{ fa(n.date) }}</small><p>{{ fa(n.note) }}</p></li></ul>
        </section>
      </div>
    </aside>
  </div>`,
  setup(props, { emit }) {
    const f = ref(null), insight = ref(""), draft = ref(null), drafting = ref(false), newNote = ref(""), error = ref("")
    const sent = computed(() => (f.value?.suggestions || []).filter((s) => s.status === "approved"))
    const load = async () => {
      f.value = await api(`/counselor/students/${props.sid}`)
      draft.value = f.value.suggestions.find((s) => s.status === "draft") || null
    }
    const suggest = async () => {
      drafting.value = true; error.value = ""
      try { draft.value = await api(`/counselor/students/${props.sid}/suggest`, {}) }
      catch (e) { error.value = e.message } finally { drafting.value = false }
    }
    const approve = async () => {
      await api(`/counselor/suggestions/${draft.value.id}/approve`, { for_counselor: draft.value.for_counselor, for_parent: draft.value.for_parent })
      await load(); emit("changed")
    }
    const dismiss = async () => { await api(`/counselor/suggestions/${draft.value.id}/dismiss`, {}); draft.value = null }
    const addNote = async () => { await api(`/counselor/students/${props.sid}/notes`, { note: newNote.value }); newNote.value = ""; await load() }
    onMounted(async () => {
      await load()
      try { insight.value = (await api(`/counselor/students/${props.sid}/insight`)).text } catch { insight.value = "جمع‌بندی در دسترس نیست." }
    })
    return { f, insight, draft, drafting, newNote, error, sent, suggest, approve, dismiss, addNote, fa }
  },
}

// ---------- counselor panel ----------
const CounselorPanel = {
  components: { TopBar, ChatBox, StudentProfile, Avatar },
  template: `
  <div class="page">
    <TopBar title="پنل مشاور" />
    <div class="content">
      <section class="hello fade-in"><h2>روز بخیر</h2><p class="muted">دانش‌آموزانی که این روزها به توجه شما نیاز دارند</p></section>

      <div class="toolbar">
        <div class="segmented">
          <button :class="{ on: view === 'flagged' }" @click="view = 'flagged'">نیاز به توجه <span>{{ fa(flagged.length) }}</span></button>
          <button :class="{ on: view === 'all' }" @click="view = 'all'">همه <span>{{ fa(list.length) }}</span></button>
        </div>
        <input v-if="view === 'all'" class="search small-search" v-model="q" placeholder="جستجوی نام یا کلاس...">
      </div>

      <div v-if="!loaded" class="card"><div class="shimmer"><span></span><span></span><span></span></div></div>
      <div v-else-if="!shown.length" class="card empty-state"><span class="bp-empty-icon">✓</span><p>موردی نیست.</p></div>
      <div v-else class="student-list">
        <button v-for="(s, i) in shown" :key="s.id" class="student-row card fade-in" :style="{ animationDelay: i * 30 + 'ms' }" @click="openId = s.id">
          <Avatar :name="s.name" />
          <span class="sr-main">
            <b>{{ s.name }}</b>
            <small class="muted">کلاس {{ s.class }}</small>
          </span>
          <span class="chips">
            <span v-for="g in groupSignals(s.signals)" :key="g.text" :class="['sig', g.type]">{{ fa(g.text) }}</span>
            <span v-if="s.has_suggestion" class="sig ok">پیام فرستاده شد</span>
          </span>
          <span class="chev">‹</span>
        </button>
      </div>
    </div>

    <StudentProfile v-if="openId" :sid="openId" @close="openId = null" @changed="load" />

    <button class="fab" @click="chatOpen = true">پرسش از اسناد</button>
    <div v-if="chatOpen" class="overlay" @click.self="chatOpen = false">
      <aside class="drawer slide-in"><div class="drawer-head"><b>پرسش از آیین‌نامه‌ها</b><button class="link" @click="chatOpen = false">بستن</button></div><ChatBox /></aside>
    </div>
  </div>`,
  setup() {
    const list = ref([]), loaded = ref(false), view = ref("flagged"), q = ref(""), openId = ref(null), chatOpen = ref(false)
    const flagged = computed(() => list.value.filter((s) => s.signals.length))
    const shown = computed(() => view.value === "flagged" ? flagged.value
      : list.value.filter((s) => !q.value.trim() || (s.name + s.class).includes(q.value.trim())))
    const load = async () => { list.value = await api("/counselor/students"); loaded.value = true }
    watch(() => !!openId.value || chatOpen.value, (v) => document.body.classList.toggle("no-scroll", v))
    onMounted(load)
    onUnmounted(() => document.body.classList.remove("no-scroll"))
    return { list, loaded, view, q, openId, chatOpen, flagged, shown, load, groupSignals, fa }
  },
}

// ---------- parent: health and wellbeing form ----------
const SCALE_ENDS = { mood: ["خیلی کم", "خیلی خوب"], sleep_quality: ["بد", "عالی"], school_worry: ["اصلا", "خیلی زیاد"], friends: ["سخت", "خیلی خوب"] }
const HealthFormDialog = {
  props: ["kind"],
  emits: ["close", "saved"],
  template: `
  <div class="overlay" @click.self="$emit('close')">
    <form class="dialog pop-in" @submit.prevent="save">
      <div class="dialog-head">
        <div><h3>{{ kind === 'physical' ? 'فرم سلامت جسمی' : 'فرم حال و احوال' }}</h3>
          <p class="muted small">{{ date ? 'آخرین ثبت: ' + fa(date) + '. پاسخ‌های قبلی را ببینید و اگر چیزی تغییر کرده اصلاح کنید.' : 'چند سؤال کوتاه. پاسخ‌ها فقط برای مشاور مدرسه است.' }}</p></div>
        <button type="button" class="link" @click="$emit('close')">بستن</button>
      </div>
      <div v-if="!fields.length" class="shimmer"><span></span><span></span></div>
      <div v-for="[key, label, type] in fields" :key="key" class="q">
        <span class="q-label">{{ label }}</span>
        <input v-if="type === 'number'" type="number" inputmode="decimal" v-model="data[key]" class="q-input" min="0">
        <input v-else-if="type === 'text'" v-model="data[key]" class="q-input" placeholder="اگر چیزی هست بنویسید">
        <div v-else-if="type === 'scale'" class="scale">
          <small class="muted">{{ SCALE_ENDS[key]?.[0] }}</small>
          <button v-for="n in 5" :key="n" type="button" :class="['dot-btn', { on: Number(data[key]) === n }]" @click="data[key] = n" :aria-label="fa(n)">{{ fa(n) }}</button>
          <small class="muted">{{ SCALE_ENDS[key]?.[1] }}</small>
        </div>
        <div v-else class="options">
          <button v-for="o in type" :key="o" type="button" :class="{ on: data[key] === o }" @click="data[key] = o">{{ o }}</button>
        </div>
      </div>
      <div class="dialog-actions">
        <button class="btn primary" :disabled="saving">{{ saving ? 'در حال ثبت...' : 'ثبت فرم' }}</button>
        <button type="button" class="btn ghost" @click="$emit('close')">انصراف</button>
      </div>
    </form>
  </div>`,
  setup(props, { emit }) {
    const fields = ref([]), data = reactive({}), date = ref(null), saving = ref(false)
    onMounted(async () => {
      const r = await api(`/parent/forms/${props.kind}`)
      fields.value = r.fields; Object.assign(data, r.data); date.value = r.date
    })
    const save = async () => {
      saving.value = true
      try { await api(`/parent/forms/${props.kind}`, { data: { ...data } }); emit("saved") } finally { saving.value = false }
    }
    return { fields, data, date, saving, save, SCALE_ENDS, fa }
  },
}

// ---------- parent panel ----------
const ParentPanel = {
  components: { TopBar, ChatBox, Sparkline, LevelChip, Avatar, HealthFormDialog },
  template: `
  <div class="page">
    <TopBar title="پنل ولی" />
    <div class="content narrow">
      <div v-if="!f" class="card"><div class="shimmer"><span></span><span></span><span></span></div></div>
      <template v-else>
        <section class="child-card card fade-in">
          <Avatar :name="f.name" :size="56" />
          <div><h2>{{ f.name }}</h2><p class="muted">کلاس {{ f.class }} · آموزگار: {{ f.teacher }}</p></div>
        </section>

        <section class="card brief fade-in" style="animation-delay:60ms">
          <div class="card-head"><span class="spark">✦</span> گزارش این هفته</div>
          <p v-if="report">{{ fa(report) }}</p>
          <div v-else class="shimmer"><span></span><span></span><span style="width:55%"></span></div>
        </section>

        <section v-for="(s, i) in f.suggestions" :key="'s' + i" class="card counsel fade-in">
          <div class="card-head">پیام مشاور مدرسه <small class="muted">{{ fa(s.approved_at) }}</small></div>
          <p>{{ fa(s.for_parent) }}</p>
        </section>

        <section class="card fade-in" style="animation-delay:120ms">
          <div class="card-head">پیشرفت درسی <small class="muted">از مهر تا امروز</small></div>
          <div class="progress-list">
            <div v-for="p in f.progress" :key="p.subject" class="prog-row">
              <span class="prog-sub">{{ p.subject }}</span>
              <Sparkline :points="p.points" :change="p.change" />
              <LevelChip :level="p.now" />
            </div>
          </div>
          <div class="legend"><span v-for="l in [4,3,2,1]" :key="l"><LevelChip :level="l" /></span></div>
        </section>

        <section class="card fade-in" style="animation-delay:170ms">
          <div class="card-head">حضور <small class="muted">۳۰ روز اخیر</small></div>
          <div class="mini-stats">
            <div><b>{{ fa(f.attendance.present) }}</b><small>روز حاضر</small></div>
            <div><b>{{ fa(f.attendance.absent) }}</b><small>غیبت</small></div>
            <div><b>{{ fa(f.attendance.late) }}</b><small>تأخیر</small></div>
          </div>
          <div v-if="f.attendance.absent_days.length" class="chips">
            <span v-for="d in f.attendance.absent_days" :key="d.date" :class="['day', { ok: d.excused }]">{{ fa(d.date) }}{{ d.excused ? ' · موجه' : '' }}</span>
          </div>
        </section>

        <section class="card fade-in" style="animation-delay:220ms">
          <div class="card-head">فرم‌های سلامت</div>
          <div class="forms-grid">
            <button v-for="k in ['physical', 'wellbeing']" :key="k" class="form-tile action" @click="formKind = k">
              <b>{{ k === 'physical' ? 'سلامت جسمی' : 'حال و احوال' }}</b>
              <small class="muted">{{ f.forms[k] ? 'آخرین ثبت: ' + fa(f.forms[k].date) : 'هنوز تکمیل نشده' }}</small>
              <span class="tile-cta">{{ f.forms[k] ? 'به‌روزرسانی' : 'تکمیل فرم' }}</span>
            </button>
          </div>
        </section>

        <section v-if="f.messages.length" class="card fade-in" style="animation-delay:270ms">
          <div class="card-head">پیام‌های مدرسه</div>
          <ul class="notes"><li v-for="m in f.messages" :key="m.id"><small class="muted">{{ fa(m.created_at) }}</small><b class="small">{{ fa(m.title) }}</b><p>{{ fa(m.body) }}</p></li></ul>
        </section>
      </template>
    </div>

    <HealthFormDialog v-if="formKind" :kind="formKind" @close="formKind = null" @saved="formKind = null; load()" />
    <button class="fab" @click="chatOpen = true">پرسش از مدرسه</button>
    <div v-if="chatOpen" class="overlay" @click.self="chatOpen = false">
      <aside class="drawer slide-in"><div class="drawer-head"><b>پرسش از مدرسه</b><button class="link" @click="chatOpen = false">بستن</button></div>
        <ChatBox endpoint="/parent/ask" loading-text="در حال بررسی" :examples="askExamples"
          :intro="'درباره درس‌ها، غیبت و تأخیر ' + (f ? f.first_name : 'فرزندتون') + ' یا مقررات مدرسه بپرسید:'" /></aside>
    </div>
  </div>`,
  setup() {
    const f = ref(null), report = ref(""), formKind = ref(null), chatOpen = ref(false)
    const load = async () => { f.value = await api("/parent/child") }
    watch(() => !!formKind.value || chatOpen.value, (v) => document.body.classList.toggle("no-scroll", v))
    const onNotify = () => load()
    onMounted(async () => {
      window.addEventListener("notifications-changed", onNotify)
      await load()
      try { report.value = (await api("/parent/report")).text } catch { report.value = "گزارش این هفته در دسترس نیست." }
    })
    onUnmounted(() => { document.body.classList.remove("no-scroll"); window.removeEventListener("notifications-changed", onNotify) })
    const askExamples = computed(() => {
      const n = f.value?.first_name || "بچه‌م"
      return [`${n} توی چه درسی ضعیف‌تره؟`, "توی سه هفته اخیر چند روز غیبت داشته؟", "وضعیت ریاضیش چطوره؟", "ساعت شروع کلاس‌ها چنده؟"]
    })
    return { f, report, formKind, chatOpen, load, askExamples, fa }
  },
}

// ---------- root: decides which screen to show ----------
createApp({
  components: { LoginPage, ManagerPanel, StaffPanel, CounselorPanel, ParentPanel, ChatPage },
  template: `
    <LoginPage v-if="!user" />
    <ManagerPanel v-else-if="user.role === 'manager'" />
    <StaffPanel v-else-if="user.role === 'staff'" />
    <CounselorPanel v-else-if="user.role === 'counselor'" />
    <ParentPanel v-else-if="user.role === 'parent'" />
    <ChatPage v-else />`,
  setup() {
    onMounted(async () => {
      if (!session.token) return
      try { session.user = await api("/me") } catch { clearSession() }
    })
    watch(() => session.user, () => document.body.classList.remove("no-scroll"))
    return { user: computed(() => session.user) }
  },
}).mount("#app")
