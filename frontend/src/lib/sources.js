import { reactive } from "vue"
import { access, accessCall } from "./access.js"

// The data map of each assistant (sources.py), for the permanent account only: where each piece of data lives in the
// real business and how it enters the program, and what each computed number is made of. Loaded once per assistant,
// on the first «منبع» mark or map that asks for it; nothing is asked for anyone else.
export const maps = reactive({})
const asked = new Set()
export function loadMap(app) {
  if (!access.admin || asked.has(app)) return
  asked.add(app)
  accessCall(`/access/sources/${app}`).then((m) => { maps[app] = m }).catch(() => asked.delete(app))
}
export const findItem = (app, key) => maps[app]?.items.find((i) => i.key === key)

// The lines a «منبع» mark shows for one item, worded for explaining it to the business's owner.
export function lines(app, item) {
  if (!item) return []
  if (item.kind === "raw") return [`در کسب‌وکار واقعی: ${item.real}`, `راه ورود به برنامه: ${item.way_text}`, `چه کسی: ${item.who}`, ...(item.note ? [item.note] : [])]
  const parts = item.made_of.map((k) => findItem(app, k)).filter(Boolean)
  return [`حساب برنامه: ${item.rule}`, ...parts.map((p) => `«${p.name}»: ${p.real}، ${p.way_text}`)]
}
