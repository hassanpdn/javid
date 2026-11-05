// The invitation letter (permanent account, «دعوت‌نامه» under «دسترسی‌ها»): drawn in the browser on an A4 canvas, then
// wrapped as a one-page PDF. Nothing goes to the server and nothing is saved: the PDF lives in memory until it is
// downloaded or the dialog closes.
// Why a canvas: the browser lays out Persian letters right (joined, right to left) with the site's own Vazirmatn font,
// which a hand-made PDF could not do without a library. The PDF holds the page as one sharp image (200 dpi).
import { ICONS } from "./icons.js"
import { MONTHS, faDigits, parse, fromJalali } from "./jalali.js"

export const PAGE = { w: 1654, h: 2339 }          // A4 at 200 dpi
const INK = "#24205e", TEXT = "#4a4766", MUTED = "#8a87a6", GOLD = "#c9a24a", LINE = "#e7e4f7"
const HUES = {
  violet: ["#7367f0", "#00bad1"], teal: ["#0f8b7d", "#f3b33d"], rose: ["#b23a62", "#36c2a3"], indigo: ["#3c4a8f", "#e0a785"], sky: ["#1d6fa3", "#f28b82"],
  ocean: ["#0d5c7a", "#e8c27a"], clay: ["#8a4320", "#f2c27a"], amber: ["#8a5a1c", "#5fb3f0"], cobalt: ["#2a5bd0", "#f5b82e"],
}
const MARK = "M-100 0A100 100 0 1 1 -37.928 92.528L-100 154.600L-100 116.263L-31.561 47.825A57.3 57.3 0 1 0 -47.825 31.561L-100 83.737ZM34.0 0A34.0 34.0 0 1 1 -34.0 0A34.0 34.0 0 1 1 34.0 0ZM-15.491 -16.041A22.3 22.3 0 0 1 15.768 15.768A2.3 2.3 0 0 1 12.516 12.516A17.7 17.7 0 0 0 -12.295 -12.732A2.3 2.3 0 0 1 -15.491 -16.041Z"

// every word of the letter, in each language
const WORDS = {
  fa: {
    brand: "مرکز دستیارهای هوشمند پودینه", title: "دعوت‌نامه", dear: (n) => `${n} گرامی،`,
    one: (t) => `با احترام، از شما دعوت می‌کنیم نسخه‌ی نمایشی «${t}» را ببینید و از نزدیک با آن کار کنید. این دستیار برای همان کارهایی ساخته شده است که هر روز وقت و حوصله می‌گیرند: عددها را خود برنامه از داده‌ها حساب می‌کند و هر چیزی که از دفتر بیرون می‌رود، پیش از فرستادن به تأیید یک نفر می‌رسد.`,
    many: (n) => `با احترام، از شما دعوت می‌کنیم نسخه‌ی نمایشی ${faDigits(n)} دستیار هوشمند پودینه را ببینید و از نزدیک با آن‌ها کار کنید.`,
    overview: "دستیارهای پودینه برای کسب‌وکارهای ایرانی ساخته شده‌اند. هر کدام کارهای تکراری یک حرفه را سبک می‌کند، آنچه ممکن است فراموش شود یادآوری می‌کند و هر روز می‌گوید چه کاری منتظر شماست. عددها را خود برنامه حساب می‌کند، هوش مصنوعی فقط متن می‌نویسد و تصمیم همیشه با شماست.",
    who: "چه کسانی با آن کار می‌کنند: ", these: "دستیارهایی که می‌بینید", sep: "، ",
    visit: "برای دیدن، به نشانی زیر بروید و با نام کاربری و رمزی که جداگانه برایتان فرستاده می‌شود وارد شوید.",
    thanks: "با سپاس و احترام", date: (j) => `${faDigits(j.d)} ${MONTHS[j.m - 1]} ${faDigits(j.y)}`, num: faDigits,
    stampName: "پودینه",
  },
  en: {
    brand: "Pudineh Agent Center", title: "Invitation", dear: (n) => `Dear ${n},`,
    one: (t) => `We would be glad to invite you to see the demo of the ${t} and work with it yourself. It is built for the everyday tasks that take time and attention: the numbers are worked out by the program from real data, and nothing leaves the office before a person has approved it.`,
    many: (n) => `We would be glad to invite you to see the demo of ${n} Pudineh assistants and work with them yourself.`,
    overview: "Pudineh assistants are built for businesses in Iran. Each one takes the repetitive work of a trade off your hands, reminds you of what could be forgotten and tells you every day what is waiting for you. The numbers are worked out by the program, the AI only writes text, and the decision is always yours.",
    who: "Who works with it: ", these: "The assistants you will see", sep: ", ",
    visit: "To see them, go to the address below and sign in with the username and password sent to you separately.",
    thanks: "With thanks and kind regards", num: String, stampName: "PUDINEH",
    date: (j) => fromJalali(j).toLocaleDateString("en-GB", { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" }),
  },
}

const font = (size, bold) => `${bold ? 700 : 400} ${size}px Vazirmatn, Tahoma, sans-serif`
function wrap(ctx, text, width) {
  const lines = []
  let line = ""
  for (const w of text.split(/\s+/)) {
    const next = line ? line + " " + w : w
    if (line && ctx.measureText(next).width > width) { lines.push(line); line = w } else line = next
  }
  if (line) lines.push(line)
  return lines
}
// writes a paragraph from the reading side (right in Persian, left in English); returns the y under it
function para(ctx, L, text, y, { size = 35, bold = false, color = TEXT, gap = 1.95, x0 = 0, x1 = 0, center = false } = {}) {
  ctx.font = font(size, bold); ctx.fillStyle = color
  const width = L.right - L.left - x0 - x1
  for (const line of wrap(ctx, text, width)) {
    if (center) { ctx.textAlign = "center"; ctx.fillText(line, (L.left + x0 + L.right - x1) / 2, y) }
    else if (L.rtl) { ctx.textAlign = "right"; ctx.fillText(line, L.right - x1, y) }
    else { ctx.textAlign = "left"; ctx.fillText(line, L.left + x0, y) }
    y += size * gap
  }
  return y
}
function icon(ctx, name, x, y, size, color = "#fff") {
  ctx.save(); ctx.translate(x, y); ctx.scale(size / 24, size / 24)
  ctx.strokeStyle = color; ctx.lineWidth = 1.9; ctx.lineCap = "round"; ctx.lineJoin = "round"
  ctx.stroke(new Path2D(ICONS[name] || ICONS.sparkles)); ctx.restore()
}
function mark(ctx, x, y, size, color) {      // the Pudineh mark, its box's top-left at x, y
  const k = size / 254.6
  ctx.save(); ctx.translate(x + 127.3 * k, y + 100 * k); ctx.scale(k, k); ctx.fillStyle = color; ctx.fill(new Path2D(MARK), "evenodd"); ctx.restore()
}
function badge(ctx, a, x, y, size) {        // an assistant's icon on its two colours, the same as on its card
  const [c1, c2] = HUES[a.hue] || HUES.violet
  const g = ctx.createLinearGradient(x, y, x + size, y + size); g.addColorStop(0, c1); g.addColorStop(1, c2)
  ctx.fillStyle = g; ctx.beginPath(); ctx.roundRect(x, y, size, size, size * 0.3); ctx.fill()
  icon(ctx, a.icon, x + size * 0.22, y + size * 0.22, size * 0.56)
}

// the seal: two rings, the name around them and the mark in the middle, in blue ink, a little turned and worn
function stamp(lang) {
  const S = 380, c = document.createElement("canvas")
  c.width = c.height = S
  const ctx = c.getContext("2d"), ink = "#2f2a9e", r = 158
  ctx.translate(S / 2, S / 2); ctx.rotate(-0.21)
  ctx.strokeStyle = ink; ctx.fillStyle = ink
  ctx.lineWidth = 8; ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke()
  ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(0, 0, r - 54, 0, Math.PI * 2); ctx.stroke()
  const ring = "PUDINEH  AGENT  CENTER  ★  AI ASSISTANTS  ★  "
  ctx.font = font(27, true); ctx.textAlign = "center"; ctx.textBaseline = "middle"
  const step = (Math.PI * 2) / ring.length
  for (let i = 0; i < ring.length; i++) {
    ctx.save(); ctx.rotate(i * step); ctx.translate(0, -(r - 28)); ctx.fillText(ring[i], 0, 0); ctx.restore()
  }
  mark(ctx, -44, -76, 88, ink)
  ctx.font = font(lang === "fa" ? 34 : 26, true); ctx.fillText(WORDS[lang].stampName, 0, 52)
  // worn ink: small specks rubbed out, the same every time
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = "destination-out"
  let seed = 7
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
  for (let i = 0; i < 900; i++) { ctx.globalAlpha = 0.25 + rnd() * 0.6; ctx.beginPath(); ctx.arc(rnd() * S, rnd() * S, 0.6 + rnd() * 2.2, 0, Math.PI * 2); ctx.fill() }
  return c
}

// draws the whole letter. lang: "fa" or "en"; name: the guest's name as typed; apps: the chosen assistants (the
// assistants page's entries, with .en for English); today: the server's Jalali date «1405/08/14».
export async function drawInvite(canvas, { lang, name, apps, today }) {
  await Promise.all([document.fonts.load(font(32, false)), document.fonts.load(font(32, true))])
  const T = WORDS[lang], rtl = lang === "fa", { w: W, h: H } = PAGE
  const pick = (a) => (lang === "en" ? { ...a, ...a.en } : a)
  canvas.width = W; canvas.height = H
  const ctx = canvas.getContext("2d")
  ctx.direction = rtl ? "rtl" : "ltr"; ctx.textBaseline = "alphabetic"
  const L = { left: 170, right: W - 170, rtl }

  // paper, frame and a thin gold line inside it
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H)
  ctx.strokeStyle = LINE; ctx.lineWidth = 3; ctx.beginPath(); ctx.roundRect(56, 56, W - 112, H - 112, 34); ctx.stroke()
  ctx.strokeStyle = GOLD; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.roundRect(76, 76, W - 152, H - 152, 26); ctx.stroke()

  // the header: the brand on a band of the site's colours
  ctx.save(); ctx.beginPath(); ctx.roundRect(56, 56, W - 112, 330, [34, 34, 0, 0]); ctx.clip()
  const g = ctx.createLinearGradient(0, 56, W, 386); g.addColorStop(0, "#241f6b"); g.addColorStop(0.55, "#5b4fe0"); g.addColorStop(1, "#1fb8d6")
  ctx.fillStyle = g; ctx.fillRect(56, 56, W - 112, 330)
  ctx.fillStyle = "rgba(255,255,255,.07)"
  for (const [x, y, r] of [[W - 260, 40, 260], [210, 380, 210], [W / 2, -120, 200]]) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill() }
  ctx.restore()
  const markX = rtl ? W - 170 - 120 : 170
  mark(ctx, markX, 140, 120, "#fff")
  ctx.fillStyle = "#fff"; ctx.textAlign = rtl ? "right" : "left"
  const brandX = rtl ? markX - 34 : markX + 154
  ctx.font = font(rtl ? 48 : 52, true); ctx.fillText(T.brand, brandX, 205)
  ctx.font = font(28, false); ctx.fillStyle = "rgba(255,255,255,.82)"
  ctx.fillText(rtl ? "Pudineh Agent Center" : "Smart assistants for everyday business", brandX, 258)
  ctx.textAlign = rtl ? "left" : "right"; ctx.font = font(28, false); ctx.fillStyle = "rgba(255,255,255,.9)"
  ctx.fillText(T.date(parse(today)), rtl ? 170 : W - 170, 205)

  // the title between two gold lines
  ctx.textAlign = "center"; ctx.fillStyle = INK; ctx.font = font(rtl ? 92 : 84, true); ctx.fillText(T.title, W / 2, 545)
  const tw = ctx.measureText(T.title).width / 2 + 40
  ctx.strokeStyle = GOLD; ctx.lineWidth = 3
  for (const s of [-1, 1]) {
    ctx.beginPath(); ctx.moveTo(W / 2 + s * tw, 515); ctx.lineTo(W / 2 + s * (tw + 190), 515); ctx.stroke()
    ctx.fillStyle = GOLD; ctx.beginPath(); ctx.arc(W / 2 + s * (tw + 200), 515, 7, 0, Math.PI * 2); ctx.fill()
  }

  let y = 690
  y = para(ctx, L, T.dear(name), y, { size: 46, bold: true, color: INK }) + 14
  const list = apps.map(pick)
  if (list.length === 1) {
    const a = list[0]
    y = para(ctx, L, T.one(a.title), y) + 30
    // the assistant's own card: its icon, name, what it does, who uses it and its three points
    ctx.font = font(34, false)
    const descLines = wrap(ctx, a.desc, L.right - L.left - 96).length
    const cardH = 236 + descLines * 66 + 112
    const [c1] = HUES[a.hue] || HUES.violet
    ctx.fillStyle = "#f7f6fe"; ctx.beginPath(); ctx.roundRect(L.left, y, L.right - L.left, cardH, 30); ctx.fill()
    ctx.fillStyle = c1; ctx.beginPath(); ctx.roundRect(rtl ? L.right - 12 : L.left, y + 30, 12, cardH - 60, 6); ctx.fill()
    badge(ctx, a, rtl ? L.right - 48 - 110 : L.left + 48, y + 46, 110)
    const inner = { left: L.left + 48, right: L.right - 48, rtl }
    const textSide = rtl ? { ...inner, right: inner.right - 140 } : { ...inner, left: inner.left + 140 }
    para(ctx, textSide, a.title, y + 106, { size: 44, bold: true, color: INK })
    para(ctx, textSide, T.who + a.roles.join(T.sep), y + 158, { size: 27, color: MUTED })
    let cy = para(ctx, inner, a.desc, y + 240, { size: 34 }) + 8
    // the three points as pills, from the reading side
    ctx.font = font(27, true)
    let px = rtl ? inner.right : inner.left
    for (const p of a.perks.map((x) => x.text || x)) {      // the assistants page keeps {icon, text}; English, plain words
      const pw = ctx.measureText(p).width + 56
      const x = rtl ? px - pw : px
      ctx.fillStyle = "#fff"; ctx.strokeStyle = LINE; ctx.lineWidth = 2; ctx.beginPath(); ctx.roundRect(x, cy - 44, pw, 62, 31); ctx.fill(); ctx.stroke()
      ctx.fillStyle = c1; ctx.textAlign = "center"; ctx.fillText(p, x + pw / 2, cy - 3)
      px = rtl ? x - 16 : x + pw + 16
    }
    y += cardH + 70
  } else {
    y = para(ctx, L, T.many(list.length), y) + 8
    y = para(ctx, L, T.overview, y) + 34
    ctx.textAlign = rtl ? "right" : "left"; ctx.fillStyle = INK; ctx.font = font(34, true)
    ctx.fillText(T.these, rtl ? L.right : L.left, y); y += 40
    // the chosen assistants with their icons: two columns, or three smaller ones (without the roles) for five or more
    const cols = list.length > 4 ? 3 : 2, compact = cols === 3
    const colW = (L.right - L.left - 30 * (cols - 1)) / cols, rowH = compact ? 96 : 128
    list.forEach((a, i) => {
      const col = i % cols, row = Math.floor(i / cols)
      const x = rtl ? L.right - colW - col * (colW + 30) : L.left + col * (colW + 30), top = y + row * (rowH + 18)
      ctx.fillStyle = "#f7f6fe"; ctx.beginPath(); ctx.roundRect(x, top, colW, rowH, 24); ctx.fill()
      const bs = rowH - 44
      badge(ctx, a, rtl ? x + colW - 22 - bs : x + 22, top + 22, bs)
      ctx.textAlign = rtl ? "right" : "left"; ctx.fillStyle = INK
      const tx = rtl ? x + colW - 40 - bs : x + 40 + bs, room = colW - bs - 62
      let fs = compact ? 27 : 31
      ctx.font = font(fs, true)
      while (fs > 20 && ctx.measureText(a.title).width > room) ctx.font = font(--fs, true)    // a long name gets a smaller size, never cut
      ctx.fillText(a.title, tx, top + rowH / 2 + (compact ? 10 : -4))
      if (!compact) { ctx.fillStyle = MUTED; ctx.font = font(23, false); ctx.fillText(a.roles.slice(0, 3).join(T.sep), tx, top + rowH / 2 + 36) }
    })
    y += Math.ceil(list.length / cols) * (rowH + 18) + 50
  }

  // where to go
  y = para(ctx, L, T.visit, y, { size: 31 }) + 6
  ctx.font = font(40, true)
  const addr = "agent.pudineh.com", aw = ctx.measureText(addr).width + 110
  const ax = rtl ? L.right - aw : L.left
  ctx.fillStyle = "#efedff"; ctx.beginPath(); ctx.roundRect(ax, y - 58, aw, 86, 43); ctx.fill()
  ctx.save(); ctx.direction = "ltr"; ctx.fillStyle = "#4b3fd6"; ctx.textAlign = "center"; ctx.fillText(addr, ax + aw / 2, y); ctx.restore()

  // the closing words a little under the letter (not lower than the footer allows), the seal pressed over the end of
  // their lines (left in Persian, right in English)
  const close = Math.min(H - 400, Math.max(y + 250, H - 720))
  ctx.textAlign = rtl ? "left" : "right"; ctx.fillStyle = INK; ctx.font = font(38, true)
  const sx = rtl ? L.left + 290 : L.right - 290
  ctx.fillText(T.thanks, sx, close)
  ctx.font = font(30, false); ctx.fillStyle = TEXT; ctx.fillText(T.brand, sx, close + 56)
  const S = 340
  ctx.save(); ctx.globalAlpha = 0.88; ctx.globalCompositeOperation = "multiply"
  ctx.drawImage(stamp(lang), rtl ? sx - S + 80 : sx - 80, close - 210, S, S); ctx.restore()
  const fg = ctx.createLinearGradient(170, 0, W - 170, 0); fg.addColorStop(0, "#5b4fe0"); fg.addColorStop(1, "#1fb8d6")
  ctx.fillStyle = fg; ctx.fillRect(170, H - 160, W - 340, 4)
  ctx.save(); ctx.direction = "ltr"; ctx.textAlign = "center"; ctx.fillStyle = MUTED; ctx.font = font(24, false)
  ctx.fillText("agent.pudineh.com  ·  Pudineh Agent Center", W / 2, H - 112); ctx.restore()
}

// one A4 page holding the canvas as a JPEG: a PDF of five objects written by hand (no library)
export async function toPdf(canvas, title) {
  const jpeg = new Uint8Array(await (await new Promise((ok) => canvas.toBlob(ok, "image/jpeg", 0.92))).arrayBuffer())
  const enc = new TextEncoder(), parts = [], offsets = []
  let size = 0
  const put = (x) => { const b = typeof x === "string" ? enc.encode(x) : x; parts.push(b); size += b.length }
  const W = 595.28, H = 841.89
  const draw = `q ${W} 0 0 ${H} 0 0 cm /Im0 Do Q`
  // the title as UTF-16 with its byte mark, so a Persian name shows in the PDF viewer's window title
  const hex = "FEFF" + [...title].map((ch) => { const c = ch.codePointAt(0); return c > 0xffff ? "003F" : c.toString(16).toUpperCase().padStart(4, "0") }).join("")
  put("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
  const obj = (n, body) => { offsets[n] = size; put(`${n} 0 obj\n`); for (const b of [].concat(body)) put(b); put("\nendobj\n") }
  obj(1, "<< /Type /Catalog /Pages 2 0 R >>")
  obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
  obj(3, `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${W} ${H}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>`)
  obj(4, [`<< /Type /XObject /Subtype /Image /Width ${canvas.width} /Height ${canvas.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`, jpeg, "\nendstream"])
  obj(5, `<< /Length ${draw.length} >>\nstream\n${draw}\nendstream`)
  obj(6, `<< /Title <${hex}> /Producer (Pudineh Agent Center) >>`)
  const xref = size
  put(`xref\n0 7\n0000000000 65535 f \n${[1, 2, 3, 4, 5, 6].map((n) => String(offsets[n]).padStart(10, "0") + " 00000 n \n").join("")}`)
  put(`trailer\n<< /Size 7 /Root 1 0 R /Info 6 0 R >>\nstartxref\n${xref}\n%%EOF\n`)
  return new Blob(parts, { type: "application/pdf" })
}
