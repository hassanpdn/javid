import { reactive } from "vue"
import { gate } from "./gate.js"

// Who may open which assistant (access.py on the server). On the live demo each card on the assistants page asks
// for a username and password: the permanent account opens every card, a guest code only the cards it was made for.
// Locally it is off and every assistant opens straight away.
// ask: the card whose login box should open (an assistant's call came back 401 "access" while it was open).
export const access = reactive({ on: false, admin: false, apps: ["school", "fabric"], guest: null, ask: "" })

export const canOpen = (app) => !access.on || access.apps.includes(app)

export async function checkAccess() {
  try {
    const s = await (await fetch("/access/status")).json()
    Object.assign(access, { on: s.on === true, admin: s.admin === true, apps: s.apps || [], guest: s.guest || null })
    if (access.on) gate.hub = true   // the login boxes live on the assistants page
  } catch {}
}

// returns "" when the login worked, else the message to show
export async function enterAccess(username, password) {
  try {
    const res = await fetch("/access/login", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) { Object.assign(access, { admin: data.admin === true, apps: data.apps || [], guest: data.guest || null }); return "" }
    return data.detail || "ورود نشد. دوباره امتحان کنید."
  } catch { return "اتصال برقرار نشد. اینترنت را بررسی کنید." }
}

// an assistant's call said this browser may not open it (a guest's time is up, or the code was ended)
export async function accessDenied(app) {
  await checkAccess()
  if (gate.app && gate.app === app) { gate.app = ""; access.ask = app }
}
