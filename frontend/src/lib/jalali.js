// Jalali (Persian calendar) dates in the browser. A date is {y, m, d} or the string «1405/08/30».
// Jalali → Gregorian has no built-in, so fromJalali guesses the day and walks to it with the browser's own
// Persian calendar (Intl), which is always right about the conversion.

export const MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
export const WEEKDAYS = ["ش", "ی", "د", "س", "چ", "پ", "ج"]   // the Persian week starts on Saturday
export const faDigits = (v) => String(v).replace(/\d/g, (c) => "۰۱۲۳۴۵۶۷۸۹"[c])
const DAY = 86400000

const fmt = (timeZone) => new Intl.DateTimeFormat("en-u-ca-persian-nu-latn", { year: "numeric", month: "numeric", day: "numeric", timeZone })
const utcFmt = fmt("UTC"), tehranFmt = fmt("Asia/Tehran")
const read = (f, date) => {
  const p = Object.fromEntries(f.formatToParts(date).map((x) => [x.type, x.value]))
  return { y: parseInt(p.year), m: parseInt(p.month), d: parseInt(p.day) }
}

// a Gregorian Date (noon UTC, so no time zone can move it to another day) → {y, m, d}
export const toJalali = (date) => read(utcFmt, date)
// {y, m, d} → that day as a Date at noon UTC
export function fromJalali({ y, m, d }) {
  const key = (j) => j.y * 400 + j.m * 32 + j.d
  // 1 Farvardin is around 21 March; months 1-6 have 31 days, 7-12 have 30
  let t = Date.UTC(y + 621, 2, 21, 12) + ((m <= 6 ? (m - 1) * 31 : 186 + (m - 7) * 30) + d - 1) * DAY
  for (let i = 0; i < 5; i++) {
    const diff = key({ y, m, d }) - key(toJalali(new Date(t)))
    if (!diff) break
    t += Math.sign(diff) * DAY
  }
  return new Date(t)
}

export const today = () => read(tehranFmt, new Date())
export const addDays = (j, n) => toJalali(new Date(fromJalali(j).getTime() + n * DAY))
export const jalaliIn = (n) => addDays(today(), n)
export const daysInMonth = (y, m) => m <= 6 ? 31 : m <= 11 ? 30 : Math.round((fromJalali({ y: y + 1, m: 1, d: 1 }) - fromJalali({ y, m: 12, d: 1 })) / DAY)
// 0 = Saturday ... 6 = Friday
export const weekday = (j) => (fromJalali(j).getUTCDay() + 1) % 7
export const compare = (a, b) => (a.y - b.y) || (a.m - b.m) || (a.d - b.d)

export const parse = (s) => { if (!s) return null; const [y, m, d] = s.split("/").map(Number); return { y, m, d } }
export const format = (j) => j ? `${j.y}/${String(j.m).padStart(2, "0")}/${String(j.d).padStart(2, "0")}` : null
// «1405/08/30» or {y, m, d} → «۳۰ آبان ۱۴۰۵»; «1405/08/30 18:30» → «۳۰ آبان ۱۴۰۵، ساعت ۱۸:۳۰»
export const jalaliText = (v) => {
  const [day, time] = typeof v === "string" ? v.split(" ") : [v]
  const j = typeof day === "string" ? parse(day) : day
  return j ? faDigits(`${j.d} ${MONTHS[j.m - 1]} ${j.y}` + (time ? `، ساعت ${time}` : "")) : ""
}
