import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import tailwindcss from "@tailwindcss/vite"

// API routes that live in FastAPI. In development (npm run dev) Vite forwards them to uvicorn on :8000.
const API = ["/school", "/setup", "/login", "/logout", "/me", "/chat", "/manager", "/staff", "/counselor", "/parent", "/notifications", "/gate", "/fabric", "/deed", "/estate", "/speed", "/law", "/dental", "/hotel/", "/hotel-site", "/lodge/", "/eco"]

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(API.map((p) => [p, "http://localhost:8000"])),
  },
  // npm run build writes the finished site into ../static, which FastAPI serves
  // Three pages: the demos (index.html) and the public websites of the eco-lodge (lodge.html) and the hotel (hotel.html),
  // each with only its own code. ("/hotel/" and "/lodge/" end in a slash above, so hotel.html and lodge.html stay Vite's.)
  build: { outDir: "../static", emptyOutDir: true, rollupOptions: { input: { main: "index.html", lodge: "lodge.html", hotel: "hotel.html" } } },
})
