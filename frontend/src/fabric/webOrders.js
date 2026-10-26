import { reactive, onMounted, onUnmounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"

// Orders from the website, for the owner's and seller's panels: how many wait for payment (the nav badge),
// and a toast as soon as a new one comes in. open() is called by the toast's «دیدن» button.
export function useWebOrders(open) {
  const s = reactive({ waiting: 0, last: null })
  let timer
  const check = async () => {
    const r = await api("/fabric/web-orders/new" + (s.last !== null ? `?after=${s.last}` : ""))
    s.waiting = r.waiting
    const newest = r.new.length ? Math.max(...r.new.map((o) => o.id)) : null
    if (s.last !== null) {
      for (const o of r.new) {
        toast({ tone: "success", timeout: 9000, title: `سفارش تازه از سایت: ${fa(o.id)}`,
                body: `${o.name} · ${fa(o.items.length)} قلم · پرداخت نشده`, action: { label: "دیدن سفارش", run: open } })
      }
    }
    if (s.last === null) s.last = newest ?? 0
    else if (newest !== null) s.last = Math.max(s.last, newest)
  }
  onMounted(() => { check().catch(() => {}); timer = setInterval(() => check().catch(() => {}), 5000) })
  onUnmounted(() => clearInterval(timer))
  return s
}
