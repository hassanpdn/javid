// All animation goes through these helpers. They do nothing when the person
// asked their system for less motion.
export const motion = !window.matchMedia("(prefers-reduced-motion: reduce)").matches

// GSAP is not part of the first download: the site's door uses none of it, and on a slow phone it made the door
// wait (PageSpeed). It comes in the background once the first page is on screen. The directives below just show
// their element without the animation until it is here. Components that animate import "gsap" themselves; they
// live in the pages' own files, which are downloaded later anyway.
let gsap = null
const fetchGsap = () => import("gsap").then((m) => { gsap = m.default }).catch(() => {})
// a second after the page has loaded, so it does not take a slow connection away from the first page's own files
const afterLoad = () => setTimeout(fetchGsap, 1000)
if (document.readyState === "complete") afterLoad()
else window.addEventListener("load", afterLoad, { once: true })

// v-reveal: an element fades up when it appears. Elements that appear in the same
// frame are animated together with a small delay between them, so a page builds up in order.
let revealBatch = []
export const vReveal = {
  mounted(el) {
    if (!motion || !gsap) return
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
const slideUp = (el) => motion && gsap && gsap.fromTo(el, { yPercent: 100 }, { yPercent: 0, duration: .5, ease: "power4.out", clearProps: "transform" })

// A sheet follows the finger when it is pulled down, and closes past 110px (or a quick flick). The pull may start on
// its top part, or anywhere on it while what is under the finger is scrolled to the top (as in the phone's own sheets);
// pulling down in the middle of a list scrolls the list instead. Closing is a click on the overlay behind it, the same
// thing that closes it on a computer.
// Touch events, not pointer events: on a phone the browser takes a downward drag for a scroll and cancels the pointer
// events (pointercancel), so the sheet never moved. touchmove is listened to with passive: false, so once the sheet is
// being pulled the page does not scroll under the finger.
function draggable(el) {
  let startY = null, dy = 0, t0 = 0, pulling = false, scroller = null
  const atTop = (target) => {
    for (let n = target; n && n !== el.parentElement; n = n.parentElement) {
      const o = getComputedStyle(n).overflowY
      if ((o === "auto" || o === "scroll") && n.scrollHeight > n.clientHeight + 1) { scroller = n; return n.scrollTop <= 0 }
    }
    return true
  }
  const start = (y, target) => {
    if (!isPhone() || target.closest("input, textarea, select, canvas")) return
    startY = y; dy = 0; t0 = Date.now(); pulling = false
    const onTop = y - el.getBoundingClientRect().top <= 64 && !target.closest("button")
    pulling = onTop ? "top" : (atTop(target) ? "maybe" : false)
    if (!pulling) startY = null
  }
  const follow = (y, e) => {
    if (startY === null) return
    const d = y - startY
    if (pulling === "maybe") {                       // decide on the first few pixels: down pulls the sheet, up scrolls
      if (Math.abs(d) < 6) return
      if (d < 0 || (scroller && scroller.scrollTop > 0)) { startY = null; return }
      pulling = "body"
    }
    if (e?.cancelable) e.preventDefault()
    if (dy === 0) el.style.transition = "none"
    dy = Math.max(0, d); el.style.transform = `translateY(${dy}px)`
  }
  const end = () => {
    if (startY === null) return
    startY = null; scroller = null; el.style.transition = "transform .25s ease"
    const flick = dy > 40 && dy / Math.max(1, Date.now() - t0) > .6
    if (dy > 110 || flick) {
      el.style.transform = "translateY(100%)"
      setTimeout(() => el.parentElement?.dispatchEvent(new MouseEvent("click", { bubbles: true })), 200)
    } else el.style.transform = ""
    dy = 0
  }
  const ts = (e) => { if (e.touches.length === 1) start(e.touches[0].clientY, e.target) }
  const tm = (e) => follow(e.touches[0].clientY, e)
  // a mouse in a narrow window (testing on a computer) pulls only from the top part, as before
  const pd = (e) => { if (e.pointerType === "mouse" && e.button === 0 && e.clientY - el.getBoundingClientRect().top <= 64 && !e.target.closest("button, input, textarea, select")) start(e.clientY, e.target) }
  const pm = (e) => { if (e.pointerType === "mouse") follow(e.clientY) }
  const pu = (e) => { if (e.pointerType === "mouse") end() }
  el.addEventListener("touchstart", ts, { passive: true })
  el.addEventListener("touchmove", tm, { passive: false })
  el.addEventListener("touchend", end); el.addEventListener("touchcancel", end)
  el.addEventListener("pointerdown", pd)
  window.addEventListener("pointermove", pm); window.addEventListener("pointerup", pu)
  el._undrag = () => { window.removeEventListener("pointermove", pm); window.removeEventListener("pointerup", pu) }
}

// v-pop: dialogs spring in. v-pop:drop is the smaller version for dropdown menus.
export const vPop = {
  unmounted(el, { arg }) { if (arg !== "drop") { releaseFocus(el); el._undrag?.() } },
  mounted(el, { arg }) {
    const drop = arg === "drop"
    if (!drop) { el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); trapFocus(el); draggable(el) }
    if (!motion || !gsap) return
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
    if (!motion || !gsap) return
    if (isPhone()) return slideUp(el)
    gsap.fromTo(el, { xPercent: 100 }, { xPercent: 0, duration: .5, ease: "power4.out", clearProps: "transform" })
  },
}
