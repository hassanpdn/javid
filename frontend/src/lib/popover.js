import { ref, watch, nextTick, onBeforeUnmount } from "vue"

// A small box that opens under a field (above it when the screen has no room below), for the core pickers.
// The box is moved to <body> by the component (so a scrolling dialog can't cut it off), takes the field's --dp-*
// colours, closes on a click outside, and Escape closes only the box, not the dialog around it.
const COLOURS = ["--dp-panel", "--dp-text", "--dp-muted", "--dp-accent"]

export function usePopover() {
  const open = ref(false), field = ref(null), pop = ref(null), place = ref({})

  const position = () => {
    if (!field.value || !pop.value) return
    const css = getComputedStyle(field.value)
    for (const v of COLOURS) pop.value.style.setProperty(v, css.getPropertyValue(v))
    const r = field.value.getBoundingClientRect(), h = pop.value.offsetHeight, w = pop.value.offsetWidth
    const below = window.innerHeight - r.bottom >= h + 12 || r.top < h + 12
    const left = Math.min(Math.max(8, r.right - w), window.innerWidth - w - 8)
    place.value = { top: (below ? r.bottom + 6 : r.top - h - 6) + "px", left: left + "px" }
  }
  const show = async (focus) => {
    open.value = true
    await nextTick()
    position()
    if (focus) pop.value?.querySelector(focus)?.focus()
  }
  const close = (refocus) => {
    open.value = false
    if (refocus) field.value?.querySelector("button")?.focus()
  }
  const outside = (e) => { if (!pop.value?.contains(e.target) && !field.value?.contains(e.target)) close() }
  const key = (e) => { if (e.key === "Escape") { e.stopPropagation(); close(true) } }

  watch(open, (on) => {
    const f = on ? "addEventListener" : "removeEventListener"
    document[f]("pointerdown", outside, true)
    window[f]("resize", close); window[f]("scroll", position, true)
  })
  onBeforeUnmount(() => { open.value = false })
  return { open, field, pop, place, show, close, key }
}
