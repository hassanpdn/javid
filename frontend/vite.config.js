import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import tailwindcss from "@tailwindcss/vite"

// API routes that live in FastAPI. In development (npm run dev) Vite forwards them to uvicorn on :8000.
const API = ["/school", "/setup", "/login", "/logout", "/me", "/chat", "/manager", "/staff", "/counselor", "/parent", "/notifications", "/gate"]

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(API.map((p) => [p, "http://localhost:8000"])),
  },
  // npm run build writes the finished site into ../static, which FastAPI serves
  build: { outDir: "../static", emptyOutDir: true },
})
