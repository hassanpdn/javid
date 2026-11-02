import { reactive } from "vue"
import { gate } from "./gate.js"
import { accessDenied } from "./access.js"
import { toast, toasts } from "./notify.js"
import { countFailure, ready } from "./rum.js"

// localStorage can throw (private window, blocked storage), so every access is wrapped
export const store = {
  get: (k) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k, v) => { try { localStorage.setItem(k, v) } catch {} },
  del: (k) => { try { localStorage.removeItem(k) } catch {} },
}

// Persian digits for everything we show
export const fa = (v) => String(v ?? "").replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d])

// One shared session object; every component reads the token from here
export const session = reactive({ token: store.get("token"), user: null })
export const clearSession = () => { session.token = null; session.user = null; store.del("token") }
// The fabric assistant has its own logins (its own database), so its own session next to the school's.
// Every /fabric/... call sends this token instead of the school's.
export const fabricSession = reactive({ token: store.get("fabric_token"), user: null })
export const setFabricSession = (token, user) => { fabricSession.token = token; fabricSession.user = user; store.set("fabric_token", token) }
export const clearFabricSession = () => { fabricSession.token = null; fabricSession.user = null; store.del("fabric_token") }
const isFabric = (path) => path.startsWith("/fabric/")
// The real estate agency likewise (/estate/...): its own logins, its own session.
export const estateSession = reactive({ token: store.get("estate_token"), user: null })
export const setEstateSession = (token, user) => { estateSession.token = token; estateSession.user = user; store.set("estate_token", token) }
export const clearEstateSession = () => { estateSession.token = null; estateSession.user = null; store.del("estate_token") }
const isEstate = (path) => path.startsWith("/estate/")
const tokenFor = (path) => (isFabric(path) ? fabricSession.token : isEstate(path) ? estateSession.token : session.token) || ""

// On a weak mobile connection a request can hang with no answer at all. So every request has a time limit (20 s for
// reading, 60 s for sending; opts.timeout for a big upload), a read is sent once more if the first try got nothing,
// and a request that gets no answer fails with a plain message (error.connection is true) instead of waiting forever.
const SLOW = "پاسخ سرور خیلی دیر شد؛ اتصال اینترنت کند است. دوباره امتحان کنید."
const DOWN = "ارتباط با سرور برقرار نشد. اتصال اینترنت را بررسی کنید و دوباره امتحان کنید."
function connectionError(message) {
  const e = new Error(message)
  e.connection = true
  return e
}
async function send(path, body, timeout) {
  const stop = new AbortController()
  const timer = setTimeout(() => stop.abort(), timeout)
  try {
    return await fetch(path, {
      method: body ? "POST" : "GET",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${tokenFor(path)}` },
      body: body ? JSON.stringify(body) : undefined,
      signal: stop.signal,
    })
  } catch (e) {
    countFailure()   // for the speed report (lib/rum.js)
    throw connectionError(e.name === "AbortError" ? SLOW : DOWN)
  } finally {
    clearTimeout(timer)
  }
}

export async function api(path, body, opts = {}) {
  const timeout = opts.timeout || (body ? 60_000 : 20_000)
  let res
  try { res = await send(path, body, timeout) }
  catch (e) {
    if (body) throw e                       // sending is not repeated by itself: it might have arrived
    res = await send(path, body, timeout)   // reading is: one more try
  }
  if (res.status === 401 && path !== "/login" && path !== "/fabric/login" && path !== "/estate/login") {
    // "site": the site's own door (gate.py) is closed for this browser, so the door page comes back
    const d = await res.clone().json().catch(() => ({}))
    if (d.detail === "site") { gate.ok = false; throw new Error("site") }
    // "access": this browser may not open that assistant (access.py), so its login box comes back on the assistants page
    if (d.detail === "access") { accessDenied(d.app); throw new Error("access") }
    if (isFabric(path)) clearFabricSession(); else if (isEstate(path)) clearEstateSession(); else clearSession()
    throw new Error("401")
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || res.status)
  return data
}

// While a dialog or drawer is open, the page behind it should not scroll
export const lockScroll = (on) => document.body.classList.toggle("no-scroll", !!on)

// For a page's first load: if it fails, a toast says so with «دوباره امتحان کنید», which runs the same load again,
// so the page never sits on its skeleton without a word. One such toast at a time.
export async function retryable(load) {
  try { await load(); ready() }   // ready: the screen is usable (speed report, lib/rum.js)
  catch (e) {
    if (e.message === "site" || e.message === "access" || e.message === "401") return   // handled by api() itself
    if (toasts.some((t) => t.retry)) return
    toast({ retry: true, tone: "warning", timeout: 0, title: e.connection ? "اتصال کند است" : "اطلاعات این صفحه نرسید",
            body: e.message, action: { label: "دوباره امتحان کنید", run: () => retryable(load) } })
  }
}
