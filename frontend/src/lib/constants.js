import { fa } from "./api.js"

// How each notification kind looks in the bell and in dialogs
export const KINDS = {
  warning: { label: "تذکر", icon: "alert", tone: "danger" },
  letter: { label: "نامه", icon: "mail", tone: "primary" },
  reminder: { label: "یادآوری", icon: "clock", tone: "warning" },
  info: { label: "اطلاع", icon: "check", tone: "success" },
  referral: { label: "ارجاع", icon: "forward", tone: "info" },
  suggestion: { label: "پیام مشاور", icon: "message", tone: "success" },
}

// Each name always gets the same color, so a person is easy to spot across pages
const TONES = ["primary", "success", "info", "warning", "danger", "secondary"]
export const toneOf = (s) => TONES[[...String(s || "")].reduce((n, c) => n + c.charCodeAt(0), 0) % TONES.length]

export const LEVEL_NAMES = { 4: "خیلی خوب", 3: "خوب", 2: "قابل قبول", 1: "نیاز به تلاش بیشتر" }

// health flags are grouped into one chip so the list stays calm
export const groupSignals = (signals) => {
  const health = signals.filter((s) => s.type === "health")
  const rest = signals.filter((s) => s.type !== "health")
  return health.length ? [...rest, { type: "health", text: `فرم سلامت: ${fa(health.length)} مورد` }] : rest
}

export const CATEGORY_OPTIONS = [
  ["ack", "اعلام وصول"], ["stats", "درخواست آمار"], ["meeting", "دعوت به جلسه"],
  ["info", "برای اطلاع"], ["decision", "نیازمند تصمیم مدیر"], ["request", "نیازمند اقدام"],
]

// settings for the floating assistant of staff roles: answers come only from the school documents
export const DOCS_CHAT = { title: "دستیار هوشمند", subtitle: "پاسخ از روی آیین‌نامه‌ها و مقررات مدرسه" }
