import { reactive } from "vue"

// The site's front door (gate.py on the server). On the live demo it asks for one username and password
// before anything else; locally it is off and ok is true from the start.
// reset: the server wants every page load to start fresh on an empty setup form (RESET_ON_LOAD=1).
export const gate = reactive({ checked: false, ok: true, reset: false })

export async function checkGate() {
  try {
    const s = await (await fetch("/gate/status")).json()
    Object.assign(gate, { ok: s.ok !== false, reset: s.reset_on_load === true })
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
