import { api, fa } from "../lib/api.js"

// The deed assistant's calls (deed/api.py) and the words it shows. No login of its own: the card's login covers it.
export const getInfo = () => api("/deed/info")
export const listDocs = () => api("/deed/documents")
export const getDoc = (id) => api(`/deed/documents/${id}`)
export const uploadFile = (name, data) => api("/deed/documents", { name, data }, { timeout: 300_000 })   // up to 10 MB on a slow line
export const pasteText = (name, text) => api("/deed/documents/text", { name, text })
export const openSample = (key) => api(`/deed/samples/${key}`, {})
export const extractAgain = (id) => api(`/deed/documents/${id}/extract`, {})
export const saveDoc = (id, edit) => api(`/deed/documents/${id}/save`, edit)
export const confirmDoc = (id, edit) => api(`/deed/documents/${id}/confirm`, edit)
export const exportDoc = (id) => api(`/deed/documents/${id}/export`)

export const STATUS = {
  processing: { text: "در حال خواندن", tone: "info" },
  review: { text: "آماده‌ی بررسی", tone: "warning" },
  confirmed: { text: "تأیید شده", tone: "success" },
  error: { text: "خوانده نشد", tone: "danger" },
}
// how surely a value was read (code decides it in deed/extract.py, not the model)
export const CONFIDENCE = {
  high: { text: "مطمئن", tone: "success" },
  medium: { text: "نیاز به نگاه", tone: "warning" },
  low: { text: "نامطمئن", tone: "danger" },
  none: { text: "در سند نیست", tone: "secondary" },
}
export const LABELS = {
  deed_number: "شماره سند", issue_date: "تاریخ صدور", book: "شماره دفتر", page: "شماره صفحه‌ی دفتر",
  main_plate: "پلاک اصلی", sub_plate: "پلاک فرعی", section: "بخش ثبتی", area: "مساحت", area_unit: "واحد مساحت",
  north: "شمالاً", east: "شرقاً", south: "جنوباً", west: "غرباً",
  name: "نام و نام خانوادگی", father_name: "نام پدر", national_id: "شماره ملی", share: "سهم",
}
export const GROUPS = [
  { title: "مشخصات سند", keys: ["deed_number", "issue_date", "book", "page"] },
  { title: "پلاک و مساحت", keys: ["main_plate", "sub_plate", "section", "area", "area_unit"] },
  { title: "حدود اربعه", keys: ["north", "east", "south", "west"], wide: true },
]

// what an input shows: Persian digits (the server turns them back into 0-9 when it saves)
export const shown = (v) => (v === null || v === undefined ? "" : fa(v))

// a JSON file the browser saves
export function download(name, data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }))
  const a = Object.assign(document.createElement("a"), { href: url, download: name })
  document.body.append(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
