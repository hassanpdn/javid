import { reactive, watch } from "vue"
import { store } from "./api.js"

// Light/dark theme. index.html already applied the saved one before the first paint.
export const theme = reactive({ dark: document.documentElement.classList.contains("dark") })
watch(() => theme.dark, (dark) => {
  document.documentElement.classList.toggle("dark", dark)
  store.set("theme", dark ? "dark" : "light")
})
