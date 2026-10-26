import { ref } from "vue"

// Phones get their own layout (bottom tab bar, sheets that come up from the bottom).
// Tablets and computers keep the sidebar.
const query = window.matchMedia("(max-width: 767px)")
export const phone = ref(query.matches)
query.addEventListener("change", (e) => { phone.value = e.matches })

// When the keyboard opens on a phone, the visible area shrinks but the page does not. --vvh is the
// height that is really visible, so the full-screen chat keeps its input box above the keyboard.
const vv = window.visualViewport
if (vv) {
  const set = () => document.documentElement.style.setProperty("--vvh", vv.height + "px")
  vv.addEventListener("resize", set); set()
}
