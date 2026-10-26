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

// On phones, dialogs and drawers are sheets that come up from the bottom of the screen
const isPhone = () => window.matchMedia("(max-width: 767px)").matches
const slideUp = (el) => motion && gsap.fromTo(el, { yPercent: 100 }, { yPercent: 0, duration: .5, ease: "power4.out", clearProps: "transform" })

// A sheet follows the finger when it is pulled down from its top part, and closes past 110px (or a quick flick).
// Closing is a click on the overlay behind it, the same thing that closes it on a computer.
function draggable(el) {
  let startY = null, dy = 0, t0 = 0
  const down = (e) => {
    if (!isPhone() || e.button > 0 || e.clientY - el.getBoundingClientRect().top > 64 || e.target.closest("button, input, textarea, select")) return
    startY = e.clientY; dy = 0; t0 = Date.now(); el.style.transition = "none"
  }
  const move = (e) => {
    if (startY === null) return
    dy = Math.max(0, e.clientY - startY); el.style.transform = `translateY(${dy}px)`
  }
  const up = () => {
    if (startY === null) return
    startY = null; el.style.transition = "transform .25s ease"
    const flick = dy > 40 && dy / Math.max(1, Date.now() - t0) > .6
    if (dy > 110 || flick) {
      el.style.transform = "translateY(100%)"
      setTimeout(() => el.parentElement?.dispatchEvent(new MouseEvent("click", { bubbles: true })), 200)
    } else el.style.transform = ""
  }
  el.addEventListener("pointerdown", down)
  window.addEventListener("pointermove", move)
  window.addEventListener("pointerup", up)
  el._undrag = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up) }
}

// v-pop: dialogs spring in. v-pop:drop is the smaller version for dropdown menus.
export const vPop = {
  unmounted(el, { arg }) { if (arg !== "drop") { releaseFocus(el); el._undrag?.() } },
  mounted(el, { arg }) {
    const drop = arg === "drop"
    if (!drop) { el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); trapFocus(el); draggable(el) }
    if (!motion) return
    if (isPhone() && !drop) return slideUp(el)
    gsap.fromTo(el, drop ? { opacity: 0, y: -10, scale: .96 } : { opacity: 0, y: 30, scale: .94 },
      { opacity: 1, y: 0, scale: 1, duration: drop ? .3 : .45, ease: drop ? "power2.out" : "back.out(1.5)", clearProps: "opacity,transform" })
  },
}

// v-drawer: side drawers slide in from the right edge (from the bottom on phones)
export const vDrawer = {
  unmounted(el) { releaseFocus(el); el._undrag?.() },
  mounted(el) {
    el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); trapFocus(el); draggable(el)
    if (!motion) return
    if (isPhone()) return slideUp(el)
    gsap.fromTo(el, { xPercent: 100 }, { xPercent: 0, duration: .5, ease: "power4.out", clearProps: "transform" })
  },
}
