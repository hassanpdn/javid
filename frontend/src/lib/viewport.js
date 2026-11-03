import { ref } from "vue"

// Phones get their own layout (bottom tab bar, sheets that come up from the bottom).
// Tablets and computers keep the sidebar.
const query = window.matchMedia("(max-width: 767px)")
export const phone = ref(query.matches)
query.addEventListener("change", (e) => { phone.value = e.matches })

// When the keyboard opens on a phone, the visible area shrinks but the page does not, and iPhone Safari also scrolls
// the page up under it. --vvh is the height that is really visible and --vvt how far down it starts, so the
// full-screen chat and the sheets sit exactly in the visible part, their input above the keyboard and their header
// on screen. kb-open on <html> while the keyboard is up hides the bottom tab bar, which would float mid-screen.
const vv = window.visualViewport
if (vv) {
  const root = document.documentElement
  let frame = 0
  const set = () => {
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(() => {
      root.style.setProperty("--vvh", vv.height + "px")
      root.style.setProperty("--vvt", vv.offsetTop + "px")
      root.classList.toggle("kb-open", window.innerHeight - vv.height > 120)
    })
  }
  vv.addEventListener("resize", set); vv.addEventListener("scroll", set); set()
}
