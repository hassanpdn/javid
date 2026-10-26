import { reactive } from "vue"

// Toasts: short messages in a corner of the screen that go away by themselves.
// toast({ title, body, tone, kind, action: { label, run }, timeout })
// tone: success, info, primary, warning, danger. kind: a notification kind (its icon and tone come from KINDS).
export const toasts = reactive([])
let nextId = 1
export function toast(t) {
  const item = { id: nextId++, tone: "primary", timeout: 6000, ...t }
  toasts.push(item)
  if (toasts.length > 3) toasts.shift()           // never more than three at once
  return item.id
}
export function dismiss(id) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i >= 0) toasts.splice(i, 1)
}

// Background work the person should know about (the assistant writing or reading something).
// The navbar shows the newest one. busy("brief", "...") starts or relabels it, idle("brief") ends it.
export const activity = reactive(new Map())
export const busy = (key, label) => activity.set(key, label)
export const idle = (key) => activity.delete(key)
