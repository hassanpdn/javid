import { reactive } from "vue"
import { gate } from "./gate.js"
import { accessDenied } from "./access.js"

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

export async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${(isFabric(path) ? fabricSession.token : session.token) || ""}` },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401 && path !== "/login" && path !== "/fabric/login") {
    // "site": the site's own door (gate.py) is closed for this browser, so the door page comes back
    const d = await res.clone().json().catch(() => ({}))
    if (d.detail === "site") { gate.ok = false; throw new Error("site") }
    // "access": this browser may not open that assistant (access.py), so its login box comes back on the assistants page
    if (d.detail === "access") { accessDenied(d.app); throw new Error("access") }
    if (isFabric(path)) clearFabricSession(); else clearSession()
    throw new Error("401")
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || res.status)
  return data
}

// While a dialog or drawer is open, the page behind it should not scroll
export const lockScroll = (on) => document.body.classList.toggle("no-scroll", !!on)
