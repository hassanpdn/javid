import { reactive, onMounted, onUnmounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import "./hotel.css"

// The hotel this demo is for, loaded before login, with its room types, meal plans, sources and agencies (all from
// the server). today: the demo's date («1405/08/11»), the date pickers' first day.
export const hotelInfo = reactive({ loaded: false, set_up: false, hotel: {}, today: null, types: [], boards: {}, sources: {}, charges: {}, methods: {},
                                    agencies: [], max_discount: 15, setupOpen: false })

export async function loadHotel() {
  Object.assign(hotelInfo, { hotel: {}, types: [] }, await api("/hotel/info"), { loaded: true })
  document.title = hotelInfo.hotel.name ? `دستیار ${hotelInfo.hotel.name}` : "دستیار هتل"
}

export const brand = () => ({ letter: (hotelInfo.hotel.name || "ه")[0], name: hotelInfo.hotel.name, sub: "دستیار هتل" })

export const ROLES = {
  modir: { role: "مدیر هتل", desc: "همه‌چیز، با گزارش، بررسی‌ها و قیمت‌ها", icon: "shield", tone: "primary", who: "manager" },
  rezerv: { role: "رزرو", desc: "استعلام، رزرو، بیعانه و آژانس‌ها", icon: "calendar", tone: "info", who: "reservation" },
  paziresh: { role: "پذیرش", desc: "ورود و خروج، صورت‌حساب و بستن روز", icon: "key", tone: "success", who: "reception" },
  khanedari: { role: "خانه‌داری", desc: "وضعیت اتاق‌ها و درخواست‌ها، روی گوشی", icon: "bed", tone: "warning", who: "housekeeping" },
}

export const CHAT = {
  endpoint: "/hotel/ask", title: "دستیار هتل", subtitle: "پاسخ از روی رزروها و اتاق‌ها",
  intro: "درباره‌ی اتاق‌های خالی، ورود و خروج امروز، رزروها و وضعیت اتاق‌ها بپرسید. عددها را خود برنامه حساب می‌کند.",
  loadingText: "در حال دیدن رزروها",
  examples: ["امشب چند اتاق رو به دریا خالی است؟", "کدام ورودی‌های امروز هنوز بیعانه نداده‌اند؟", "اتاق ۵۰۳ چه وضعی دارد؟"],
}

export const STATUS_TONE = { tentative: "warning", confirmed: "info", in_house: "success", out: "secondary", cancelled: "secondary", noshow: "danger" }
export const ROOM_TONE = { clean: "info", dirty: "danger", inspected: "success" }

// toman ⇄ what is typed in a field: amounts are typed in toman, Persian digits allowed
export const digits = (s) => Number(String(s ?? "").replace(/[۰-۹]/g, (x) => "۰۱۲۳۴۵۶۷۸۹".indexOf(x)).replace(/[^\d]/g, "")) || 0

// Bookings the hotel's website made: a toast and the nav badge, for the desk's panels.
export function useSiteBookings(open) {
  const s = reactive({ waiting: 0, last: null })
  let timer
  const check = async () => {
    const r = await api("/hotel/site/new" + (s.last !== null ? `?after=${s.last}` : ""))
    s.waiting = r.waiting
    if (s.last !== null) {
      for (const b of r.new) toast({ tone: "success", timeout: 9000, title: `رزرو جدید از سایت هتل: ${b.guest}`, body: `${b.type}، ${b.stay}`, action: { label: "دیدن رزرو", run: () => open(b.id) } })
    }
    s.last = r.last
  }
  onMounted(() => { check().catch(() => {}); timer = setInterval(() => check().catch(() => {}), 6000) })
  onUnmounted(() => clearInterval(timer))
  return s
}

export { fa }
