import { reactive } from "vue"
import { gate } from "./gate.js"

// Who may open which assistant (access.py on the server). On the live demo: the permanent account (admin) opens every
// card and gives access to other people; anyone else sees only the cards they were given. Locally it is off and every
// assistant opens straight away.
// ask: the card whose login box should open (an assistant's call came back 401 "access" while it was open).
export const access = reactive({ on: false, admin: false, name: "", apps: ["school", "fabric"], expires_on: null, ask: "" })

export const canOpen = (app) => !access.on || access.apps.includes(app)

const take = (s) => Object.assign(access, { on: s.on === true, admin: s.admin === true, name: s.name || "", apps: s.apps || [], expires_on: s.expires_on || null })

export async function checkAccess() {
  try {
    take(await (await fetch("/access/status")).json())
    if (access.on) gate.hub = true   // the cards and the login box live on the assistants page
  } catch {}
}

// returns "" when the login worked, else the message to show
export async function enterAccess(username, password) {
  try {
    const res = await fetch("/access/login", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) { take(data); return "" }
    return data.detail || "ورود نشد. دوباره امتحان کنید."
  } catch { return "اتصال برقرار نشد. اینترنت را بررسی کنید." }
}

export const forgetAccess = () => Object.assign(access, { admin: false, name: "", apps: [], expires_on: null })

// an assistant's call said this browser may not open it (their last day passed, their access was changed or removed)
export async function accessDenied(app) {
  await checkAccess()
  if (gate.app && gate.app === app) { gate.app = ""; access.ask = app }
}

// The permanent account's calls for people's accounts. Throws the server's message when something is wrong.
export async function accessCall(path, body) {
  const res = await fetch(path, { method: body ? "POST" : "GET", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "کار انجام نشد. دوباره امتحان کنید.")
  return data
}

// Jalali dates: today and «n days from today» as {y, m, d}, from the browser's own Persian calendar
const parts = (date) => {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-u-ca-persian-nu-latn", { year: "numeric", month: "numeric", day: "numeric", timeZone: "Asia/Tehran" })
    .formatToParts(date).map((x) => [x.type, x.value]))
  return { y: parseInt(p.year), m: parseInt(p.month), d: parseInt(p.day) }
}
export const jalaliIn = (days) => parts(new Date(Date.now() + days * 86400000))
export const MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
// «1405/08/30» → «۳۰ آبان ۱۴۰۵»
export const jalaliText = (s) => {
  if (!s) return ""
  const [y, m, d] = s.split("/").map(Number)
  return `${d} ${MONTHS[m - 1]} ${y}`.replace(/\d/g, (c) => "۰۱۲۳۴۵۶۷۸۹"[c])
}
