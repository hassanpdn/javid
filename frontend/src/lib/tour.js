import { reactive } from "vue"
import { store } from "./api.js"

// First-visit guides (driver.js): the page darkens, one part stays lit, and a box beside it explains it, with
// «بعدی» / «قبلی», a progress bar and a × to close at any step. Each guide runs once per browser: when it ends or is
// closed, «tour:<key>» goes into localStorage, so it only comes back after the site's data is cleared, or from a
// «راهنما» button (force).
//
// A step: { el, title, text, side }. el is a CSS selector, or a list of them: the first one that is on screen is used
// (e.g. the sidebar item on wide screens, the bottom tab on phones). A step whose el is not on screen is shown in the
// middle of the page, unless it says optional: true, then it is left out. No el: a box in the middle (welcome, end).
//
// driver.js and its styles are loaded only when a guide is about to run (most visits have none), so they are not part
// of the code every page downloads first.
// prepareTour starts that download early (the account menu calls it when it opens, so the guide's code is usually here
// before «راهنمای این صفحه» is pressed); the download happens once, later calls get the same one.
let loading = null
const loadDriver = () => (loading ||= Promise.all([import("driver.js"), import("driver.js/dist/driver.css"), import("../styles/tour.css")])
  .then(([m]) => m.driver).catch((e) => { loading = null; throw e }))
export const prepareTour = () => { loadDriver().catch(() => {}) }

export const tourState = reactive({ running: false })
const SEEN = (key) => "tour:" + key
export const seen = (key) => !!store.get(SEEN(key))
const fa = (v) => String(v).replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d])

const visible = (sel) => [...document.querySelectorAll(sel)].find((e) => {
  const r = e.getBoundingClientRect(), s = getComputedStyle(e)
  return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && !e.closest("[inert]")
})
const find = (el) => (Array.isArray(el) ? el : [el]).map(visible).find(Boolean)

// wait until the page has settled: no skeletons left (content loaded) and the first lit part is on screen
// quick: opened from the menu, the page is already there and still, so no extra wait once it is found
async function settle(steps, { timeout = 8000, quick = false } = {}) {
  const first = steps.find((s) => s.el)
  const until = Date.now() + timeout
  while (Date.now() < until) {
    if (!document.querySelector(".sk") && (!first || find(first.el))) break
    await new Promise((ok) => setTimeout(ok, 200))
  }
  if (!quick) await new Promise((ok) => setTimeout(ok, 500))   // let the cards finish sliding in (v-reveal)
}

/**
 * Run a guide. key: «manager», «fabric-owner», ... steps: see above (a list, or a function that returns one).
 * force: run even if seen (the «راهنما» button). dark: the dark look (assistants page).
 * onClose(finished): called when it ends; finished is false when it was closed before the last step.
 */
// Automated browsers (the e2e tests) would have every click blocked by the guide, so there it only runs when a test
// asks for it with localStorage «tour:test».
const robot = () => navigator.webdriver && !store.get("tour:test")

export async function runTour(key, steps, { force = false, dark = false, onClose } = {}) {
  if (tourState.running || (!force && (seen(key) || robot()))) return
  tourState.running = true
  // steps may be a function: then it is asked once the page has settled, so it sees the page as it really is
  const make = typeof steps === "function" ? steps : () => steps
  let driver
  try { [driver] = await Promise.all([loadDriver(), settle(make(), { quick: force })]) }
  catch { tourState.running = false; return }   // the guide's code did not arrive (connection dropped): no guide this time
  // start from the top: a page opened after scrolling another one (login → panel) keeps that scroll, and a part half
  // under the fixed top bar still counts as on screen, so it would not be scrolled clear
  window.scrollTo({ top: 0 })
  const list = make()
    .map((s) => ({ ...s, node: s.el ? find(s.el) : null }))
    .filter((s) => !(s.el && !s.node && s.optional))
  if (!list.length) { tourState.running = false; return }

  let finished = false, over = false
  // every way out ends here once: «پایان», ×, Escape, a click outside the box, «رد کردن راهنما»
  const finish = () => {
    if (over) return
    over = true
    store.set(SEEN(key), "seen")
    tourState.running = false
    document.documentElement.classList.remove("touring")
    onClose?.(finished)
  }
  const d = driver({
    steps: list.map((s) => ({
      element: s.node || undefined,
      popover: { title: s.title, description: s.text, side: s.side || "bottom", align: s.align || "center" },
    })),
    showProgress: true,
    progressText: "{{current}} از {{total}}",
    nextBtnText: "بعدی", prevBtnText: "قبلی", doneBtnText: "پایان",
    allowClose: true, allowKeyboardControl: true, smoothScroll: true,
    overlayOpacity: dark ? 0.7 : 0.55, stagePadding: 6, stageRadius: 14, popoverOffset: 12,
    popoverClass: "pd-tour" + (dark ? " pd-tour-dark" : ""),
    onPopoverRender: (pop, { driver: drv }) => {
      const i = drv.getActiveIndex() ?? 0, n = list.length
      pop.progress.textContent = fa(`${i + 1} از ${n}`)
      // a thin bar over the box that fills as the guide goes on
      const bar = document.createElement("span")
      bar.className = "pd-tour-bar"
      bar.style.setProperty("--p", ((i + 1) / n) * 100 + "%")
      pop.wrapper.prepend(bar)
      pop.closeButton.setAttribute("aria-label", "بستن راهنما")
      pop.closeButton.title = "بستن راهنما"
      // «رد کردن راهنما» on every step but the last, for someone who does not want the guide at all
      if (i < n - 1) {
        const skip = document.createElement("button")
        skip.type = "button"; skip.className = "pd-tour-skip"; skip.textContent = "رد کردن راهنما"
        skip.addEventListener("click", () => { finish(); drv.destroy() })
        pop.footer.prepend(skip)
      }
      if (i === n - 1) finished = true
    },
    // driver.js calls this before closing in every case (its onDestroyed is skipped when the step lights nothing)
    onDestroyStarted: (el, step, { driver: drv }) => { finish(); drv.destroy() },
  })
  document.documentElement.classList.add("touring")
  d.drive()
}
