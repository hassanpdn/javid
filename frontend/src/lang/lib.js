import { reactive } from "vue"
import "../styles/kit.css"
import "./lang.css"
import { api } from "../lib/api.js"

// The institute this demo is for, loaded before login, with the road (levels, the twelve terms, the book of each),
// the day pairs, slots and rooms of the timetable. today: the demo's date («1405/08/14»).
export const instInfo = reactive({ loaded: false, set_up: false, institute: {}, today: null, levels: [], terms: [], pairs: {}, slots: [], rooms: {}, skills: {}, setupOpen: false })

export async function loadInstitute() {
  Object.assign(instInfo, { institute: {}, levels: [], terms: [] }, await api("/lang/info"), { loaded: true })
  document.title = instInfo.institute.name ? `دستیار ${instInfo.institute.name}` : "دستیار آموزشگاه زبان"
}

export const brand = () => ({ letter: (instInfo.institute.name || "ز")[0], name: instInfo.institute.name, sub: "دستیار آموزشگاه زبان" })
export const term = (key) => instInfo.terms.find((t) => t.key === key)
export const level = (key) => instInfo.levels.find((l) => l.key === key)
// «B1 · 2»: a station's short name, the same in every language
export const short = (key) => key ? key.replace("S-", "Starter-").replace("-", " · ") : ""

export const ROLES = {
  modir: { role: "مدیر", desc: "جدول کلاس‌ها، استادها، ثبت‌نام ترم بعد و کارهای امروز", icon: "dashboard", tone: "primary", who: "owner" },
  monshi: { role: "منشی", desc: "ثبت‌نام، تعیین سطح، شهریه و تماس با زبان‌آموزان", icon: "users", tone: "info", who: "secretary" },
  ostad: { role: "استاد", desc: "کلاس‌های خودش، حضور و غیاب، نمره و آزمون آنلاین", icon: "book", tone: "success", who: "teacher" },
  zabanamooz: { role: "زبان‌آموز", desc: "مسیر خودش، کتاب این ترم و ترم بعد، برنامه‌ی هفته و آزمون", icon: "route", tone: "warning", who: "student" },
}

const EXAMPLES = {
  owner: ["کدام کلاس‌های ترم بعد مشکل دارند؟", "چند نفر برای ترم بعد ثبت‌نام کرده‌اند؟", "امروز چه کلاس‌هایی داریم؟"],
  secretary: ["شهریه‌ی چه کسانی مانده است؟", "چه کسی سه جلسه غایب بوده است؟", "امروز چه کلاس‌هایی داریم؟"],
  teacher: ["کلاس بعدی من کی است؟", "میانگین آزمون‌های کلاس‌هایم چقدر است؟", "چه کسی غیبت زیاد دارد؟"],
  student: ["کلاس بعدی من کی است؟", "ترم بعد چه کتابی باید بخرم؟", "مسیر من کی تمام می‌شود؟"],
}
export const chatFor = (role) => ({
  endpoint: "/lang/ask", title: "دستیار آموزشگاه", subtitle: role === "student" ? "پاسخ از روی پرونده‌ی خود شما" : "پاسخ از روی کلاس‌ها و ثبت‌نام‌ها",
  intro: role === "student" ? "درباره‌ی کلاس، کتاب، ترم بعد و مسیرتان بپرسید." : "درباره‌ی کلاس‌ها، ثبت‌نام، آزمون‌ها و شهریه بپرسید. عددها را خود برنامه حساب می‌کند.",
  loadingText: "در حال خواندن پرونده‌ها", examples: EXAMPLES[role] || EXAMPLES.owner,
})

export const ATT = { present: "حاضر", late: "با تأخیر", absent: "غایب" }
export const ATT_TONE = { present: "success", late: "warning", absent: "danger" }
