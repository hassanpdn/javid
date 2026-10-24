import { createApp } from "vue"
import App from "./App.vue"
import { vReveal, vPop, vDrawer } from "./lib/motion.js"
import "./lib/theme.js"
import "./styles/main.css"

// the three animation directives are used everywhere, so they are registered once for the whole app
createApp(App)
  .directive("reveal", vReveal)
  .directive("pop", vPop)
  .directive("drawer", vDrawer)
  .mount("#app")
