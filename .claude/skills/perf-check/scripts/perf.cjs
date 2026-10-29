// Performance checks for the frontend, in headless Chromium against the test server (scripts/serve.sh).
// Run from frontend/ (it needs frontend/node_modules/playwright):  node ../.claude/skills/perf-check/scripts/perf.cjs <mode> [role]
//   load   phone on slow 4G (1.6 Mbps, 150 ms) and a 4x slower CPU: first paint, time to the login page, KB downloaded
//          before it, time from picking a role to the panel without skeletons. 3 runs, no cache.
//   idle   a panel left alone for 5 s (desktop, CPU 4x slower): style recalcs, layouts and main-thread time. A still page
//          should be near 0; 60 recalcs a second means an endless animation is running on the main thread.
//   which  the same panel, every running animation on its own: which one makes the recalcs (60/s = not on the graphics card)
//   tour   the first-visit guide stepped through 6 times: frame times and long frames (desktop and phone)
//   wf     the request waterfall up to the login page on the phone profile: what waits on what
// role: the Persian name on the role card, default مدیر.
const { chromium, devices } = require("playwright")
const URL = process.env.PERF_URL || "http://127.0.0.1:8765/"
const [mode = "load", role = "مدیر"] = process.argv.slice(2)
const PHONE = devices["Pixel 7"], DESK = { viewport: { width: 1440, height: 900 } }

async function open(b, opts, { slowNet = false, cpu = 4, tour = false } = {}) {
  const ctx = await b.newContext({ ...opts, locale: "fa-IR" }), page = await ctx.newPage(), cdp = await ctx.newCDPSession(page)
  if (tour) await page.addInitScript(() => localStorage.setItem("tour:test", "1"))
  if (slowNet) {
    await cdp.send("Network.enable"); await cdp.send("Network.setCacheDisabled", { cacheDisabled: true })
    await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: 2e5, uploadThroughput: 9e4 })
  }
  if (cpu > 1) await cdp.send("Emulation.setCPUThrottlingRate", { rate: cpu })
  return { ctx, page, cdp }
}
const card = (page) => page.locator(".role-card", { has: page.locator(`b:text-is("${role}")`) })
const metrics = async (cdp) => Object.fromEntries((await cdp.send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]))
const frames = (f) => { f.sort((a, b) => a - b); const p = (q) => +f[Math.floor(f.length * q)].toFixed(1); return { frames: f.length, p50: p(.5), p95: p(.95), max: +f.at(-1).toFixed(1), over50: f.filter((x) => x > 50).length } }

const modes = {
  async load(b) {
    for (let run = 0; run < 3; run++) {
      const { ctx, page, cdp } = await open(b, PHONE, { slowNet: true })
      let bytes = 0; cdp.on("Network.loadingFinished", (e) => (bytes += e.encodedDataLength))
      const t0 = Date.now(); await page.goto(URL); await page.locator(".role-card").first().waitFor()
      const login = Date.now() - t0, kb = Math.round(bytes / 1024)
      const fcp = await page.evaluate(() => Math.round(performance.getEntriesByName("first-contentful-paint")[0]?.startTime || 0))
      const t1 = Date.now(); await card(page).click(); await page.locator(".tabbar").waitFor()
      await page.locator(".sk").first().waitFor({ state: "detached", timeout: 30000 }).catch(() => {})
      console.log(JSON.stringify({ fcp, login, kbBeforeLogin: kb, panel: Date.now() - t1 }))
      await ctx.close()
    }
  },
  async idle(b) {
    const { page, cdp } = await open(b, DESK)
    await page.goto(URL); await card(page).click(); await page.locator(".navbar").waitFor(); await page.waitForTimeout(4000)
    await cdp.send("Performance.enable"); const m0 = await metrics(cdp); await page.waitForTimeout(5000); const m1 = await metrics(cdp)
    console.log(JSON.stringify({ styleRecalcs: m1.RecalcStyleCount - m0.RecalcStyleCount, layouts: m1.LayoutCount - m0.LayoutCount, mainThreadS: +(m1.TaskDuration - m0.TaskDuration).toFixed(2) }))
  },
  async which(b) {
    const { page, cdp } = await open(b, DESK, { cpu: 1 })
    await page.goto(URL); await card(page).click(); await page.locator(".navbar").waitFor(); await page.waitForTimeout(4000)
    await cdp.send("Performance.enable")
    const names = await page.evaluate(() => document.getAnimations().map((a) => `${a.animationName || a.constructor.name} on .${a.effect?.target?.getAttribute?.("class")}`))
    for (let i = 0; i < names.length; i++) {
      await page.evaluate((i) => document.getAnimations().forEach((a, j) => (j === i ? a.play() : a.pause())), i)
      const a = (await metrics(cdp)).RecalcStyleCount; await page.waitForTimeout(1000)
      console.log(`${(await metrics(cdp)).RecalcStyleCount - a} recalcs/s  ${names[i]}`)
    }
  },
  async tour(b) {
    for (const opts of [DESK, PHONE]) {
      const { ctx, page } = await open(b, opts, { tour: true })
      await page.goto(URL); await card(page).click()
      const pop = page.locator(".driver-popover"); await pop.waitFor({ timeout: 30000 })
      await page.evaluate(() => { window.__f = []; let l = performance.now(); const t = (n) => { window.__f.push(n - l); l = n; requestAnimationFrame(t) }; requestAnimationFrame(t) })
      for (let i = 0; i < 6; i++) { const next = pop.locator(".driver-popover-next-btn"); if (!(await next.count())) break; await next.click(); await page.waitForTimeout(900) }
      console.log(opts === DESK ? "desktop" : "phone", JSON.stringify(frames(await page.evaluate(() => window.__f))))
      await ctx.close()
    }
  },
  async wf(b) {
    const { page } = await open(b, PHONE, { slowNet: true })
    await page.goto(URL); await page.locator(".role-card").first().waitFor()
    console.log((await page.evaluate(() => performance.getEntriesByType("resource").map((e) =>
      `${Math.round(e.startTime)}-${Math.round(e.responseEnd)} ms  ${Math.round(e.encodedBodySize / 1024)} KB  ${e.name.replace(location.origin, "")}`))).join("\n"))
    console.log("first paint", await page.evaluate(() => Math.round(performance.getEntriesByName("first-contentful-paint")[0]?.startTime)))
  },
}

;(async () => {
  if (!modes[mode]) { console.log("modes:", Object.keys(modes).join(", ")); process.exit(1) }
  const b = await chromium.launch()
  try { await modes[mode](b) } finally { await b.close() }
})()
