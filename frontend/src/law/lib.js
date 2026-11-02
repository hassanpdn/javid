import { reactive } from "vue"
import { api } from "../lib/api.js"
import "./law.css"

// The law office this demo is for, loaded before login. today: the demo's date («1405/08/11»), the date pickers' first day.
export const officeInfo = reactive({ loaded: false, set_up: false, office: {}, today: null, setupOpen: false })

export async function loadOffice() {
  Object.assign(officeInfo, { office: {} }, await api("/law/info"), { loaded: true })
  document.title = officeInfo.office.name ? `دستیار ${officeInfo.office.name}` : "دستیار دفتر وکالت"
}

export const brand = () => ({ letter: (officeInfo.office.name || "و")[0], name: officeInfo.office.name, sub: "دستیار دفتر وکالت" })

export const KINDS = {
  judgment: "دادنامه‌ی بدوی", default: "دادنامه‌ی غیابی", appeal: "دادنامه‌ی تجدیدنظر", defect: "اخطار رفع نقص",
  expert: "ابلاغ نظر کارشناس", execution: "اجرائیه", hearing: "وقت رسیدگی",
}
export const FIELDS = { civil: "حقوقی", criminal: "کیفری", family: "خانواده", enforcement: "اجرای احکام" }

export const ROLES = {
  vakil: { role: "وکیل", desc: "کارهای امروز، مهلت‌ها، بررسی‌ها و تنظیمات", icon: "shield", tone: "primary", who: "owner" },
  hamkar: { role: "همکار وکیل", desc: "پرونده‌ها و مهلت‌های خودش", icon: "book", tone: "success", who: "associate" },
  monshi: { role: "منشی", desc: "ثبت ابلاغیه‌ها و پرونده‌های جدید", icon: "mail", tone: "info", who: "secretary" },
}

const base = {
  endpoint: "/law/ask", title: "دستیار دفتر", subtitle: "پاسخ از روی پرونده‌های دفتر",
  intro: "درباره‌ی مهلت‌ها، جلسه‌ها و پرونده‌ها بپرسید. تاریخ‌ها را خود برنامه حساب می‌کند.",
  loadingText: "در حال خواندن پرونده‌ها",
  examples: ["فردا چه جلسه‌ای داریم؟", "نزدیک‌ترین مهلت کدام است؟", "مهلت پرونده‌ی شرکت پخش سپهر کی تمام می‌شود؟"],
}
export const CHAT = base

// the tone of a deadline by the days left; a hearing is an appointment, not a deadline, so it stays calm
export const toneOf = (left, kind) => kind === "hearing" ? "info" : left < 0 ? "danger" : left <= 3 ? "danger" : left <= 7 ? "warning" : "secondary"
