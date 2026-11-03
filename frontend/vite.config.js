import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import tailwindcss from "@tailwindcss/vite"

// API routes that live in FastAPI. In development (npm run dev) Vite forwards them to uvicorn on :8000.
const API = ["/school", "/setup", "/login", "/logout", "/me", "/chat", "/manager", "/staff", "/counselor", "/parent", "/notifications", "/gate", "/fabric", "/deed", "/estate", "/speed", "/law", "/dental", "/hotel", "/lodge", "/eco"]

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(API.map((p) => [p, "http://localhost:8000"])),
  },
  // npm run build writes the finished site into ../static, which FastAPI serves
  // Two pages: the demos (index.html) and the eco-lodge's public website (lodge.html), each with only its own code.
  build: { outDir: "../static", emptyOutDir: true, rollupOptions: { input: { main: "index.html", lodge: "lodge.html" } } },
})
