// Performance checks for the frontend, in headless Chromium against the test server (scripts/serve.sh).
// Run from frontend/ (it needs frontend/node_modules/playwright):  node ../.claude/skills/perf-check/scripts/perf.cjs <mode> [role]
//   load   phone on slow 4G (1.6 Mbps, 150 ms) and a 4x slower CPU: first paint, time to the login page, KB downloaded
//          before it, time from picking a role to the panel without skeletons. 3 runs, no cache.
//   idle   a panel left alone for 5 s (desktop, CPU 4x slower): style recalcs, layouts and main-thread time. A still page
//          should be near 0; 60 recalcs a second means an endless animation is running on the main thread.
//   which  the same panel, every running animation on its own: which one makes the recalcs (60/s = not on the graphics card)
//   tour   the first-visit guide stepped through 6 times: frame times and long frames (desktop and phone)
//   wf     the request waterfall up to the login page on the phone profile: what waits on what
//   net    every page of the site on a simulated network, phone and CPU 4x slower, 3 runs each, no cache (needs the
//          server started with HUB=1). Second argument: iran (default; Iranian mobile at a busy hour: 400 kbit/s down,
//          150 up, 400 ms round trip, 3% of packets lost) or 4g (the slow 4G of `load`, no loss). See simulate() below.
// role: the Persian name on the role card, default مدیر.
const { chromium, devices } = require("playwright")
const zlib = require("zlib")
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

// ---------- a simulated network (mode net) ----------
// Chromium's own throttling (used by load and wf) has no packet loss: it accepts a packetLoss setting and ignores it
// (tried on Chromium 153: the same times at 0%, 10% and 30%). So `net` plays the network itself, in Playwright's
// request interception: each request waits one round trip plus its upload, then its body (gzip size, as the server
// sends it) goes through one pipe the page's requests share at the profile's speed, and every lost packet of it
// (1400 bytes each) adds a retransmission wait (rto). The random numbers come from a fixed seed, so runs repeat.
const NETS = {
  iran: { rtt: 400, down: 400e3 / 8, up: 150e3 / 8, loss: .03, rto: 1000 },
  "4g": { rtt: 150, down: 1.6e6 / 8, up: 750e3 / 8, loss: 0, rto: 0 },
}
const TEXT = /javascript|css|json|html|svg|text/
async function simulate(ctx, net, seed) {
  let x = seed, pipe = 0
  const rand = () => (x = (x * 1664525 + 1013904223) % 4294967296) / 4294967296
  const stats = { bytes: 0, requests: 0, slowest: [0, ""] }
  await ctx.route("**/*", async (route) => {
    const start = Date.now(), req = route.request()
    let resp
    try { resp = await route.fetch() } catch { return route.abort() }
    const body = await resp.body(), type = resp.headers()["content-type"] || ""
    const sent = (TEXT.test(type) && body.length > 500 ? zlib.gzipSync(body).length : body.length) + 300
    const asked = (req.postDataBuffer()?.length || 0) + 500
    let lost = 0
    for (let i = 0; i < Math.ceil(sent / 1400) + Math.ceil(asked / 1400); i++) if (rand() < net.loss) lost += net.rto
    const begin = Math.max(start + net.rtt + asked / net.up * 1000, pipe)
    pipe = begin + sent / net.down * 1000
    const wait = pipe + lost - Date.now()
    if (wait > 0) await new Promise((r) => setTimeout(r, wait))
    stats.bytes += sent; stats.requests++
    const took = Date.now() - start
    if (took > stats.slowest[0]) stats.slowest = [took, req.url().replace(/^https?:\/\/[^/]+/, "")]
    await route.fulfill({ response: resp, body }).catch(() => {})
  })
  return stats
}
// every page a visitor reaches, the way they reach it: from the assistants page through cards and role cards
const PAGES = [
  { name: "assistants page", path: [], ready: ".h-card, .h-row" },
  { name: "school login", path: ["دستیار مدرسه"], ready: ".role-card" },
  ...["مدیر", "پرسنل اداری", "مشاور", "ولی"].map((r) => ({ name: "school " + r, path: ["دستیار مدرسه", r], ready: "panel" })),
  { name: "fabric owner", path: ["دستیار پارچه‌فروشی", "صاحب کار"], ready: "panel" },
  { name: "estate owner", path: ["دستیار بنگاه املاک", "مدیر بنگاه"], ready: "panel" },
  { name: "deed", path: ["دستیار استخراج داده‌ی سند"], ready: ".dz-main" },
]
async function reach(page, p) {
  await page.goto(URL)
  await page.locator(".h-card, .h-row").first().waitFor({ timeout: 90000 })
  let last = Date.now()
  for (const [i, step] of p.path.entries()) {
    last = Date.now()
    // on a phone each assistant is a row with its own «ورود» button (HubPage); on a wider screen, a card
    if (i === 0) await page.locator(".h-card, .h-row", { hasText: step }).first().locator(".h-row-go").or(page.locator(".h-card", { hasText: step })).first().click()
    else await page.locator(".role-card", { has: page.locator(`b:text-is("${step}")`) }).first().click()
    if (i === 0 && p.path.length > 1) await page.locator(".role-card").first().waitFor({ timeout: 90000 })
  }
  if (p.ready === "panel") {
    await page.locator(".tabbar").waitFor({ timeout: 90000 })
    await page.locator(".sk").first().waitFor({ state: "detached", timeout: 90000 }).catch(() => {})
  } else await page.locator(p.ready).first().waitFor({ timeout: 90000 })
  return Date.now() - last
}

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
  async net(b) {
    const net = NETS[process.argv[3] || "iran"]
    for (const p of PAGES) {
      const runs = []
      for (let run = 0; run < 3; run++) {
        const ctx = await b.newContext({ ...PHONE, locale: "fa-IR" }), page = await ctx.newPage(), cdp = await ctx.newCDPSession(page)
        await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 })
        const stats = await simulate(ctx, net, 7 + run)
        const t0 = Date.now()
        let step, error = ""
        try { step = await reach(page, p) } catch (e) { error = e.message.split("\n")[0] }
        runs.push({ total: Date.now() - t0, step, kb: Math.round(stats.bytes / 1024), requests: stats.requests, slowest: stats.slowest,
                    retryToast: await page.locator("text=دوباره امتحان کنید").count(), error })
        await ctx.close()
      }
      runs.sort((a, c) => a.total - c.total)
      const m = runs[1]
      console.log(JSON.stringify({ page: p.name, totalMs: m.total, lastStepMs: m.step, kb: m.kb, requests: m.requests,
                                   slowest: `${m.slowest[0]} ms ${m.slowest[1]}`, worstTotalMs: runs[2].total, retryToasts: runs.reduce((n, r) => n + r.retryToast, 0),
                                   errors: runs.filter((r) => r.error).map((r) => r.error) }))
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
