import { reactive } from "vue"

// The public website's only way to the server (/lodge/public/...): the guest's token from their own login, a time
// limit on every request, and the server's message as the error.
const get = (k) => { try { return localStorage.getItem(k) } catch { return null } }
const set = (k, v) => { try { v ? localStorage.setItem(k, v) : localStorage.removeItem(k) } catch {} }
export const guest = reactive({ token: get("eco_token"), name: get("eco_name") || "" })
export const signIn = (token, name) => { guest.token = token; guest.name = name; set("eco_token", token); set("eco_name", name) }
export const signOut = () => { guest.token = null; guest.name = ""; set("eco_token", null); set("eco_name", null) }

export async function call(path, body, method) {
  const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), body ? 60000 : 20000)
  let res
  try {
    res = await fetch("/lodge/public" + path, { method: method || (body ? "POST" : "GET"), signal: ctl.signal,
      headers: { "Content-Type": "application/json", ...(guest.token ? { Authorization: "Bearer " + guest.token } : {}) },
      body: body ? JSON.stringify(body) : undefined })
  } catch { throw new Error("ارتباط با سایت برقرار نشد. دوباره امتحان کنید.") } finally { clearTimeout(timer) }
  const data = await res.json().catch(() => ({}))
  if (res.status === 401 && guest.token && path !== "/login") signOut()
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "خانه‌ها را درست پر کنید.")
  return data
}

export const fa = (v) => String(v ?? "").replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d])
export const go = (path) => { location.hash = "#" + path; scrollTo({ top: 0 }) }

// a photo chosen by the guest, as a data URL (the server checks and shrinks it)
export const readFile = (file) => new Promise((ok, bad) => {
  if (!file) return bad(new Error("فایلی انتخاب نشد"))
  if (file.size > 6 * 1024 * 1024) return bad(new Error("عکس بیش از ۶ مگابایت است"))
  const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => bad(new Error("فایل خوانده نشد")); r.readAsDataURL(file)
})
