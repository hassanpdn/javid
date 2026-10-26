import { reactive } from "vue"

// The site's front door (gate.py on the server). On the live demo it asks for one username and password
// before anything else; locally it is off and ok is true from the start.
// reset: the server wants every page load to start fresh on an empty setup form (RESET_ON_LOAD=1).
// hub: after the door comes the list of assistants (HubPage); app is the one picked there ("" = the list).
// Without the door (local runs, tests) there is no list and the school assistant opens straight away.
export const gate = reactive({ checked: false, ok: true, reset: false, hub: false, app: "" })

export async function checkGate() {
  try {
    const s = await (await fetch("/gate/status")).json()
    Object.assign(gate, { ok: s.ok !== false, reset: s.reset_on_load === true, hub: s.on === true })
  } catch {}
  gate.checked = true
}

// returns "" when the door opened, else the message to show. The caller sets gate.ok, so the door page
// is still there to say so (changing it here would remove the page before it can tell App).
export async function enterGate(username, password) {
  try {
    const res = await fetch("/gate/login", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }),
    })
    if (res.ok) return ""
    return (await res.json()).detail || "ورود انجام نشد"
  } catch { return "اتصال برقرار نشد. اینترنت را بررسی کنید." }
}

// leave the site: the door closes for this browser and the door page comes back
export async function leaveGate() {
  try { await fetch("/gate/logout", { method: "POST" }) } catch {}
  Object.assign(gate, { ok: false, app: "" })
}
