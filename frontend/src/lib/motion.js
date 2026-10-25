import gsap from "gsap"

// All animation goes through these helpers. They do nothing when the person
// asked their system for less motion.
export const motion = !window.matchMedia("(prefers-reduced-motion: reduce)").matches
export { gsap }

// v-reveal: an element fades up when it appears. Elements that appear in the same
// frame are animated together with a small delay between them, so a page builds up in order.
let revealBatch = []
export const vReveal = {
  mounted(el) {
    if (!motion) return
    gsap.set(el, { opacity: 0, y: 18 })
    revealBatch.push(el)
    if (revealBatch.length > 1) return
    requestAnimationFrame(() => {
      const els = revealBatch; revealBatch = []
      gsap.to(els, { opacity: 1, y: 0, duration: .6, ease: "power3.out", stagger: .07, clearProps: "opacity,transform" })
    })
  },
}

// Keyboard users stay inside an open dialog: focus moves into it, Tab cycles through its buttons and
// fields, and when it closes focus goes back to whatever opened it.
const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
function trapFocus(el) {
  el._returnTo = document.activeElement
  el._onKey = (e) => {
    if (e.key !== "Tab") return
    const items = [...el.querySelectorAll(FOCUSABLE)].filter((x) => x.offsetParent !== null)
    if (!items.length) return
    const first = items[0], last = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
  }
  el.addEventListener("keydown", el._onKey)
  requestAnimationFrame(() => (el.querySelector("textarea, input, select") || el.querySelector(FOCUSABLE) || el).focus({ preventScroll: true }))
}
function releaseFocus(el) {
  el.removeEventListener("keydown", el._onKey)
  el._returnTo?.focus?.({ preventScroll: true })
}

// v-pop: dialogs spring in. v-pop:drop is the smaller version for dropdown menus.
export const vPop = {
  unmounted(el, { arg }) { if (arg !== "drop") releaseFocus(el) },
  mounted(el, { arg }) {
    if (arg !== "drop") { el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); trapFocus(el) }
    if (!motion) return
    const drop = arg === "drop"
    gsap.fromTo(el, drop ? { opacity: 0, y: -10, scale: .96 } : { opacity: 0, y: 30, scale: .94 },
      { opacity: 1, y: 0, scale: 1, duration: drop ? .3 : .45, ease: drop ? "power2.out" : "back.out(1.5)", clearProps: "opacity,transform" })
  },
}

// v-drawer: side drawers slide in from the right edge
export const vDrawer = {
  unmounted: releaseFocus,
  mounted(el) {
    el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); trapFocus(el)
    if (!motion) return
    gsap.fromTo(el, { xPercent: 100 }, { xPercent: 0, duration: .5, ease: "power4.out", clearProps: "transform" })
  },
}
