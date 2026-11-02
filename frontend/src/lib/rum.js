import { watch } from "vue"
import { gate } from "./gate.js"
import { session, fabricSession, estateSession, lawSession } from "./api.js"

// Real visitors' speed (speed.py on the server). For each screen behind the site's door (the assistants page and every
// assistant's panel; not the door, login or setup pages) the browser sends one line: how many ms until it was usable,
// counted from the page load the first time and from the moment the screen opened after that, plus KB, failed requests,
// phone or computer, and the connection type when the browser tells it. Automated browsers (tests, perf-check) send
// nothing. ready() is called when a screen's first data has arrived (retryable in api.js, HubPage, DeedApp).

const off = typeof navigator !== "undefined" && navigator.webdriver
let start = 0, kind = "load", pending = false, failures = 0, failuresAtStart = 0, current = null

const ROLE = { manager: "manager", staff: "staff", counselor: "counselor", parent: "parent", teacher: "teacher", student: "student" }
function screen() {
  const app = gate.app || (gate.hub ? "" : "school")
  if (!gate.ok) return null
  if (app === "") return "hub"
  if (app === "deed") return "deed"
  const u = app === "school" ? session.user : app === "fabric" ? fabricSession.user : app === "estate" ? estateSession.user : app === "law" ? lawSession.user : null
  if (!u) return null
  if (app === "school") return ROLE[u.role] ? "school:" + ROLE[u.role] : null
  if (app === "estate") return u.role === "owner" ? "estate:owner" : "estate:agent"
  if (app === "law") return "law:" + u.role
  return "fabric:" + u.role
}

// a request that got no answer (lib/api.js)
export const countFailure = () => { failures++ }

// The first screen counts from the page load only if nobody touched the page before it (no login form typed in, no
// card clicked): otherwise it counts from the moment it opened, like every later screen.
let touched = false
export function startRum() {
  if (off) return
  for (const ev of ["pointerdown", "keydown"]) addEventListener(ev, () => { touched = true }, { once: true, capture: true })
  watch(screen, (s) => {
    current = s
    if (!s) { pending = false; return }
    if (kind === "load" && !touched) { start = 0; pending = true; failuresAtStart = 0; return }
    kind = "open"; start = performance.now(); pending = true; failuresAtStart = failures
  }, { immediate: true })
}

export function ready() {
  if (off || !pending || !current) return
  pending = false
  const now = performance.now()
  const kb = Math.round((performance.getEntriesByType("resource").filter((e) => e.startTime >= start).reduce((n, e) => n + (e.transferSize || 0), 0)
    + (kind === "load" ? performance.getEntriesByType("navigation")[0]?.transferSize || 0 : 0)) / 1024)
  const fcp = kind === "load" ? Math.round(performance.getEntriesByName("first-contentful-paint")[0]?.startTime || 0) || null : null
  const body = JSON.stringify({ screen: current, kind, ms: Math.round(now - start), fcp, kb, failed: failures - failuresAtStart,
    phone: window.matchMedia("(max-width: 767px)").matches, net: navigator.connection?.effectiveType || "" })
  try {
    if (!navigator.sendBeacon?.("/speed", new Blob([body], { type: "application/json" }))) throw 0
  } catch { fetch("/speed", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {}) }
  kind = "open"
}
