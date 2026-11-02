import { reactive } from "vue"
import { api } from "../lib/api.js"
import "./dental.css"

// The clinic this demo is for, loaded before login. today: the demo's date («1405/08/11»), the date pickers' first day.
// services: the clinic's price list from the server (key, name, minutes, price_text).
export const clinicInfo = reactive({ loaded: false, set_up: false, clinic: {}, today: null, services: [], setupOpen: false })

export async function loadClinic() {
  Object.assign(clinicInfo, { clinic: {}, services: [] }, await api("/dental/info"), { loaded: true })
  document.title = clinicInfo.clinic.name ? `دستیار ${clinicInfo.clinic.name}` : "دستیار مطب دندان‌پزشکی"
}

export const brand = () => ({ letter: (clinicInfo.clinic.name || "د")[0], name: clinicInfo.clinic.name, sub: "دستیار مطب دندان‌پزشکی" })
export const service = (key) => clinicInfo.services.find((s) => s.key === key)

export const ROLES = {
  doktor: { role: "دندان‌پزشک", desc: "کارهای امروز، نوبت‌ها، طرح‌های درمان و بررسی‌ها", icon: "tooth", tone: "primary", who: "owner" },
  monshi: { role: "منشی", desc: "نوبت‌ها، تأیید و یادآوری، فهرست انتظار و پرداخت‌ها", icon: "calendar", tone: "info", who: "secretary" },
}

export const CHAT = {
  endpoint: "/dental/ask", title: "دستیار مطب", subtitle: "پاسخ از روی نوبت‌ها و پرونده‌ها",
  intro: "درباره‌ی نوبت‌ها، طرح‌های درمان و پرداخت‌ها بپرسید. عددها را خود برنامه حساب می‌کند.",
  loadingText: "در حال خواندن نوبت‌ها",
  examples: ["فردا چند نوبت داریم؟", "کدام نوبت فردا تأیید نشده است؟", "کدام طرح‌های درمان منتظر تماس‌اند؟"],
}

export const STATUS_TONE = { booked: "warning", confirmed: "info", done: "success", noshow: "danger", cancelled: "secondary" }
