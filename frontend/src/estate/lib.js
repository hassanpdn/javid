import { reactive, onMounted, onUnmounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import "./estate.css"

// The agency this demo is for, loaded before login (like lib/school.js for the school).
// today: the demo's date as the server has it («1405/08/11»), the date pickers' first day.
export const agencyInfo = reactive({ loaded: false, set_up: false, agency: {}, today: null, setupOpen: false })

export async function loadAgency() {
  Object.assign(agencyInfo, { agency: {} }, await api("/estate/info"), { loaded: true })
  document.title = agencyInfo.agency.name ? `دستیار ${agencyInfo.agency.name}` : "دستیار بنگاه املاک"
}

// the sidebar's brand for AppLayout
export const brand = () => ({ letter: (agencyInfo.agency.name || "ب")[0], name: agencyInfo.agency.name, sub: "دستیار بنگاه املاک" })

// money in words, the same rules as money() on the server
export { money } from "../fabric/lib.js"

export const KINDS = { sale: "فروش", rent: "رهن و اجاره" }
export const FEATURES = { elevator: "آسانسور", parking: "پارکینگ", storage: "انباری" }

export const ROLES = {
  modir: { role: "مدیر بنگاه", desc: "کارهای امروز، تیم، معامله‌ها و بررسی‌ها", icon: "chart", tone: "primary", who: "owner" },
  moshaver1: { role: "مشاور املاک", desc: "فایل‌ها، متقاضیان، بازدیدها و گزارش به مالک", icon: "users", tone: "success", who: "agent1" },
  moshaver2: { role: "مشاور املاک", desc: "فایل‌ها، متقاضیان، بازدیدها و گزارش به مالک", icon: "users", tone: "info", who: "agent2" },
}

// The floating assistant: it answers from numbers the server computes from the agency's files.
const base = {
  endpoint: "/estate/ask", title: "دستیار بنگاه", subtitle: "پاسخ از روی فایل‌های بنگاه",
  intro: "درباره‌ی فایل‌ها، محله‌ها، متقاضیان، بازدیدها و معامله‌ها بپرسید. عددها را خود برنامه حساب می‌کند.",
  loadingText: "در حال حساب کردن از روی فایل‌ها",
}
export const CHAT = {
  owner: { ...base, examples: ["معامله‌های این ماه چقدر کمیسیون داشت؟", "در پونک چند فایل فعال داریم؟", "میانه‌ی قیمت متری سعادت‌آباد چقدر است؟"] },
  agent: { ...base, examples: ["بازدیدهای فردا کدام است؟", "در شهرک غرب چند فایل فعال داریم؟", "هر یک میلیون ودیعه چقدر اجاره است؟"] },
}

// toman ⇄ the number typed in a field: fields take millions («۵۰۰» = ۵۰۰ میلیون تومان)
export const toMillions = (v) => (v ? Math.round(v / 1e5) / 10 : "")
export const fromMillions = (v) => Math.round((Number(String(v ?? "").replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d))) || 0) * 1e6)

// Requests the website made: a toast and the nav badge, for the owner's and the agents' panels.
// open() is called by the toast's «دیدن» button.
export function useLeads(open) {
  const s = reactive({ waiting: 0, last: null })
  let timer
  const check = async () => {
    const r = await api("/estate/site/leads" + (s.last !== null ? `?after=${s.last}` : ""))
    s.waiting = r.waiting
    if (s.last !== null) {
      for (const l of r.new) {
        toast({ tone: "success", timeout: 9000, title: `متقاضی جدید از سایت: ${l.name}`,
                body: `${KINDS[l.kind]} در ${l.hoods.split(",").join("، ")}`, action: { label: "دیدن متقاضی", run: () => open(l.id) } })
      }
    }
    s.last = r.last
  }
  onMounted(() => { check().catch(() => {}); timer = setInterval(() => check().catch(() => {}), 6000) })
  onUnmounted(() => clearInterval(timer))
  return s
}

export { fa }
