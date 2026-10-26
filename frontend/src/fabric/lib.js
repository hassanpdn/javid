import { reactive } from "vue"
import { api, fa } from "../lib/api.js"

// The fabric wholesaler this demo is for, loaded before login (like lib/school.js for the school).
export const shop = reactive({ loaded: false, set_up: false, business: {}, setupOpen: false })

export async function loadShop() {
  Object.assign(shop, { business: {} }, await api("/fabric/info"), { loaded: true })
  document.title = shop.business.name ? `دستیار ${shop.business.name}` : "دستیار پارچه‌فروشی"
}

// the sidebar's brand for AppLayout
export const brand = () => ({ letter: (shop.business.name || "پ")[0], name: shop.business.name, sub: "دستیار عمده‌فروشی پارچه" })

// Toman the way the bazaar says it; the same rules as money() in fabric/facts.py
export function money(v) {
  v = Math.round(v || 0)
  const sign = v < 0 ? "منفی " : ""
  v = Math.abs(v)
  let out
  if (v >= 1e9) {
    const m = Math.round(v / 1e6), b = Math.floor(m / 1000), r = m % 1000
    out = `${b} میلیارد` + (r ? ` و ${r} میلیون` : "") + " تومان"
  } else if (v >= 1e6) out = `${Math.round(v / 1e6)} میلیون تومان`
  else if (v >= 1000) out = `${Math.round(v / 1000)} هزار تومان`
  else out = `${v} تومان`
  return fa(sign + out)
}
// the full number with Persian separators, for invoice tables: 37٬000٬000
export const num = (v) => fa(Math.round(v || 0).toLocaleString("en-US").replace(/,/g, "٬"))
export const meters = (m) => fa(`${Math.round((m || 0) * 10) / 10} متر`)

export const ROLES = {
  sahebkar: { role: "صاحب کار", desc: "خلاصه‌ی روز، فروش، چک‌ها و کارهای امروز", icon: "chart", tone: "primary", who: "owner" },
  forooshande: { role: "فروشنده", desc: "میز تلفن: کارت مشتری و فاکتور از روی سفارش تلفنی", icon: "message", tone: "success", who: "seller" },
  hesabdar: { role: "حسابدار", desc: "چک‌ها، طلب‌ها و پیامک یادآوری", icon: "file", tone: "info", who: "accountant" },
}

// a small colour sample next to each fabric in the lists
const SWATCH = {
  "آبی نفتی": "#1f3b57", "مشکی": "#1d1d1f", "کرم": "#e8dcc2", "سفید": "#f4f4f2", "آبی آسمانی": "#8cc4ec", "زرشکی": "#7b1e2b",
  "قهوه‌ای": "#6b4430", "سرمه‌ای": "#1f2a4d", "سبز یشمی": "#2e6b55", "صورتی": "#f1b8c8", "طوسی": "#8d9096", "بژ": "#d8c6a5",
  "گلدار": "linear-gradient(135deg, #f3b6c6 25%, #9fd3a8 25% 50%, #f7e3a0 50% 75%, #a9c8f0 75%)", "سبز": "#3f8f5a",
  "آبی": "#3e6fb0", "طلایی": "#c9a243", "شتری": "#b08954", "ذغالی": "#3a3b3d",
}
export const swatch = (color) => SWATCH[color] || "#b9b4a8"
