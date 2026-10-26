import { reactive } from "vue"
import { gate } from "./gate.js"

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

export async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token || ""}` },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401 && path !== "/login") {
    // "site": the site's own door (gate.py) is closed for this browser, so the door page comes back
    const d = await res.clone().json().catch(() => ({}))
    if (d.detail === "site") { gate.ok = false; throw new Error("site") }
    clearSession(); throw new Error("401")
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || res.status)
  return data
}

// While a dialog or drawer is open, the page behind it should not scroll
export const lockScroll = (on) => document.body.classList.toggle("no-scroll", !!on)
