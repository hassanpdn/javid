import { createApp } from "vue"
import App from "./App.vue"
import { vReveal, vPop, vDrawer } from "./lib/motion.js"
import { chatUi } from "./lib/chat.js"
import "./lib/theme.js"
import "./styles/main.css"

// the three animation directives are used everywhere, so they are registered once for the whole app
createApp(App)
  .directive("reveal", vReveal)
  .directive("pop", vPop)
  .directive("drawer", vDrawer)
  .mount("#app")

// Escape closes the top-most dialog or drawer (the same as clicking outside it), or else the chat window
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return
  const overlays = document.querySelectorAll(".overlay")
  if (overlays.length) overlays[overlays.length - 1].dispatchEvent(new MouseEvent("click", { bubbles: true }))
  else chatUi.open = false
})
