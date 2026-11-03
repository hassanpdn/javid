import { reactive } from "vue"
import "../styles/kit.css"
import "./lodge.css"
import { api, fa } from "../lib/api.js"

// The eco-lodge being shown, loaded before login: its words, kinds of unit, sources, and where its website is.
export const lodgeInfo = reactive({ loaded: false, set_up: false, lodge: {}, site: {}, today: null, kinds: {}, sources: {}, site_url: "/eco", setupOpen: false })

export async function loadLodge() {
  Object.assign(lodgeInfo, { lodge: {} }, await api("/lodge/info"), { loaded: true })
  document.title = lodgeInfo.lodge.name ? `دستیار ${lodgeInfo.lodge.name}` : "دستیار اقامتگاه بوم‌گردی"
}

export const brand = () => ({ letter: (lodgeInfo.lodge.name || "ب").replace("اقامتگاه بوم‌گردی ", "")[0], name: lodgeInfo.lodge.name, sub: "دستیار اقامتگاه بوم‌گردی" })

export const ROLES = {
  golin: { role: "میزبان", desc: "همه‌چیز: واحدها، قیمت‌ها، رزروها، نظرها و متن سایت", icon: "heart", tone: "primary", who: "host" },
  hamkar: { role: "همکار", desc: "جواب درخواست‌ها، بررسی رسیدها و پیام مهمانان", icon: "users", tone: "info", who: "helper" },
}

export const CHAT = {
  endpoint: "/lodge/ask", title: "دستیار اقامتگاه", subtitle: "پاسخ از روی رزروها و شب‌های خالی",
  intro: "درباره‌ی شب‌های خالی، درخواست‌ها، مهمان‌های امروز و نظرها بپرسید.",
  loadingText: "در حال دیدن رزروها",
  examples: ["این هفته کدام شب‌ها جای خالی داریم؟", "چه کسی امروز می‌آید؟", "چند درخواست منتظر جواب است؟"],
}

export const STATUS_TONE = { requested: "warning", approved: "info", paid: "info", confirmed: "success", rejected: "secondary", cancelled: "secondary" }
export const digits = (s) => Number(String(s ?? "").replace(/[۰-۹]/g, (x) => "۰۱۲۳۴۵۶۷۸۹".indexOf(x)).replace(/[^\d]/g, "")) || 0
export { fa }
