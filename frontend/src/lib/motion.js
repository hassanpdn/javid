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

// v-pop: dialogs spring in. v-pop:drop is the smaller version for dropdown menus.
export const vPop = {
  mounted(el, { arg }) {
    if (!motion) return
    const drop = arg === "drop"
    gsap.fromTo(el, drop ? { opacity: 0, y: -10, scale: .96 } : { opacity: 0, y: 30, scale: .94 },
      { opacity: 1, y: 0, scale: 1, duration: drop ? .3 : .45, ease: drop ? "power2.out" : "back.out(1.5)", clearProps: "opacity,transform" })
  },
}

// v-drawer: side drawers slide in from the right edge
export const vDrawer = {
  mounted(el) {
    if (!motion) return
    gsap.fromTo(el, { xPercent: 100 }, { xPercent: 0, duration: .5, ease: "power4.out", clearProps: "transform" })
  },
}
