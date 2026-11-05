// The invitation letter (permanent account, «دعوت‌نامه» under «دسترسی‌ها»): drawn in the browser on an A4 canvas, then
// wrapped as a one-page PDF. Nothing goes to the server and nothing is saved: the PDF lives in memory until it is
// downloaded or the dialog closes.
// Why a canvas: the browser lays out Persian letters right (joined, right to left) with the site's own Vazirmatn font,
// which a hand-made PDF could not do without a library. The PDF holds the page as one sharp image (200 dpi).
// The page, top to bottom: the Pudineh header and the date, the title, the greeting and the invitation, the
// assistant (its problem, its solution, six gains) or, for two or more, a general overview and their names, the
// login box, and the footer with the contacts, the gold seal and the signature. The words are in lib/inviteTexts.js.
// When the words do not fit above the footer, the body is drawn again a little smaller until they do.
import { MONTHS, faDigits, parse, fromJalali } from "./jalali.js"
import { TEXTS, GENERAL } from "./inviteTexts.js"

export const PAGE = { w: 1654, h: 2339 }          // A4 at 200 dpi
const INK = "#2b3034", TEXT = "#474c52", MUTED = "#8d9197", RULE = "#e6e2d8", GOLD = "#c8ad6e", FRAME = "#dccb9f", BOX = "#f6f4ef", MARKC = "#3b4f4b"
const ADDRESS = "https://agent.pudineh.com", EMAIL = "info@pudineh.com", PHONE = "+98 935 067 2745"
const MARK = "M-100 0A100 100 0 1 1 -37.928 92.528L-100 154.600L-100 116.263L-31.561 47.825A57.3 57.3 0 1 0 -47.825 31.561L-100 83.737ZM34.0 0A34.0 34.0 0 1 1 -34.0 0A34.0 34.0 0 1 1 34.0 0ZM-15.491 -16.041A22.3 22.3 0 0 1 15.768 15.768A2.3 2.3 0 0 1 12.516 12.516A17.7 17.7 0 0 0 -12.295 -12.732A2.3 2.3 0 0 1 -15.491 -16.041Z"

// the letter's fixed words, in each language
const WORDS = {
  fa: {
    hon: { m: "جناب آقای", f: "سرکار خانم", "": "" },
    title1: (t) => `دعوت به بازدید از ${t.replace(/^دستیار /, "دستیار هوشمند ")}`, titleN: "دعوت به بازدید از دستیارهای هوشمند پودینه",
    hello: (hon, n) => `${hon ? hon + " " : ""}${n} عزیز، سلام. `, helloLine: false,
    invite1: (t) => `از شما دعوت می‌کنیم ${t.replace(/^دستیار /, "دستیار هوشمند ")} را از نزدیک ببینید و نظرتان را با ما در میان بگذارید. نگاه شما به ما کمک می‌کند این دستیار با نیازهای واقعی جور شود.`,
    inviteN: (n) => `از شما دعوت می‌کنیم ${faDigits(n)} دستیار هوشمند پودینه را از نزدیک ببینید و نظرتان را با ما در میان بگذارید. نگاه شما به ما کمک می‌کند این دستیارها با نیازهای واقعی جور شوند.`,
    problem: "مسئله", solution: "راه‌حل", gains: "بخشی از دستاوردها", these: "دستیارهایی که می‌بینید", whatFor: "پودینه برای چه ساخته شده است",
    login: "اطلاعات ورود", valid: (t) => `معتبر تا ${t}`, address: "آدرس", username: "نام کاربری", password: "رمز عبور", assistant: "دستیار", assistants: "دستیارها",
    start: "شروع کار", both: "نام کاربری و رمز", separately: "جداگانه برایتان فرستاده می‌شود", sep: "، ",
    contact: "برای تمدید دسترسی، گفت‌وگوی بیشتر یا هر نظر و پیشنهاد:", waiting: "منتظر نظرتان هستیم", sign: "پودینه",
    date: (j) => `${faDigits(j.d)} ${MONTHS[j.m - 1]} ${faDigits(j.y)}`, at: (d, t) => `${d}، ساعت ${faDigits(t)}`,
  },
  en: {
    hon: { m: "Mr.", f: "Ms.", "": "" },
    title1: (t) => `An invitation to see the ${t}`, titleN: "An invitation to see the Pudineh AI assistants",
    hello: (hon, n) => `Dear ${hon ? hon + " " : ""}${n},`, helloLine: true,
    invite1: (t) => `We would like to invite you to see the ${t} for yourself and share your thoughts with us. Your view helps us make it fit real needs.`,
    inviteN: (n) => `We would like to invite you to see ${n} Pudineh AI assistants for yourself and share your thoughts with us. Your view helps us make them fit real needs.`,
    problem: "The problem", solution: "The solution", gains: "Some of the gains", these: "The assistants you will see", whatFor: "What Pudineh is built for",
    login: "Your login", valid: (t) => `Valid until ${t}`, address: "Address", username: "Username", password: "Password", assistant: "Assistant", assistants: "Assistants",
    start: "Getting started", both: "Username and password", separately: "Sent to you separately", sep: ", ",
    contact: "To extend your access or share an idea:", waiting: "We look forward to your thoughts", sign: "Pudineh",
    date: (j) => fromJalali(j).toLocaleDateString("en-GB", { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" }), at: (d, t) => `${d}, ${t}`,
  },
}

const font = (size, bold, serif) => `${bold ? 700 : 400} ${Math.round(size)}px ${serif ? "Georgia, 'Times New Roman', serif" : "Vazirmatn, Tahoma, sans-serif"}`
function wrap(ctx, text, width) {
  const lines = []
  let line = []
  for (const w of text.split(/\s+/).filter(Boolean)) {
    if (line.length && ctx.measureText([...line, w].join(" ")).width > width) { lines.push(line); line = [w] } else line.push(w)
  }
  if (line.length) lines.push(line)
  return lines
}
function mark(ctx, x, y, size, color) {      // the Pudineh mark, its box's top-left at x, y
  const k = size / 254.6
  ctx.save(); ctx.translate(x + 127.3 * k, y + 100 * k); ctx.scale(k, k); ctx.fillStyle = color; ctx.fill(new Path2D(MARK), "evenodd"); ctx.restore()
}
// spaced capitals, as in the header («P U D I N E H …»): drawn letter by letter from x, right-aligned when end is true
function spaced(ctx, text, x, y, gap, end) {
  const widths = [...text].map((ch) => ctx.measureText(ch).width + gap)
  let cx = end ? x - widths.reduce((a, b) => a + b, 0) + gap : x
  ctx.save(); ctx.textAlign = "left"; ctx.direction = "ltr"
  ;[...text].forEach((ch, i) => { ctx.fillText(ch, cx, y); cx += widths[i] })
  ctx.restore()
}

// the gold seal: a round medal with the name around the rim and the mark pressed in the middle
function seal() {
  const S = 420, c = document.createElement("canvas")
  c.width = c.height = S
  const ctx = c.getContext("2d"), r = S / 2 - 8
  ctx.translate(S / 2, S / 2)
  ctx.beginPath()                                            // a scalloped rim, like a foil seal
  for (let i = 0; i <= 72; i++) { const a = (i / 72) * Math.PI * 2, rr = r - (i % 2 ? 7 : 0); ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) }
  const g = ctx.createRadialGradient(-r * 0.35, -r * 0.4, r * 0.1, 0, 0, r)
  g.addColorStop(0, "#fbf1cf"); g.addColorStop(0.55, "#e6cd8a"); g.addColorStop(1, "#bf9a4f")
  ctx.fillStyle = g; ctx.fill()
  ctx.lineWidth = 3; ctx.strokeStyle = "rgba(150,115,45,.55)"
  ctx.beginPath(); ctx.arc(0, 0, r - 22, 0, Math.PI * 2); ctx.stroke()
  ctx.beginPath(); ctx.arc(0, 0, r - 78, 0, Math.PI * 2); ctx.stroke()
  const ring = "PUDINEH  AGENT  CENTER  •  AI  ASSISTANTS  •  "
  ctx.font = font(30, true, true); ctx.textAlign = "center"; ctx.textBaseline = "middle"
  const step = (Math.PI * 2) / ring.length
  for (const [color, dy] of [["rgba(255,250,230,.8)", 1.5], ["#94722c", 0]]) {      // a light edge under dark letters: pressed in
    ctx.fillStyle = color
    for (let i = 0; i < ring.length; i++) { ctx.save(); ctx.rotate(i * step); ctx.translate(0, -(r - 50) + dy); ctx.fillText(ring[i], 0, 0); ctx.restore() }
  }
  mark(ctx, -62, -72 + 2, 124, "rgba(255,250,230,.75)")
  mark(ctx, -62, -72, 124, "#9b7832")
  return c
}

// draws the whole letter.
// lang "fa" | "en"; hon "m" | "f" | ""; name as typed; apps: the chosen assistants (the assistants page's entries,
// with .en for English); login: { username, password, expires } (any may be empty; expires «1405/08/17 20:00»);
// today: the server's Jalali date «1405/08/14».
export async function drawInvite(canvas, { lang, hon, name, apps, login, today }) {
  await Promise.all([document.fonts.load(font(32, false)), document.fonts.load(font(32, true))])
  const T = WORDS[lang], rtl = lang === "fa", { w: W, h: H } = PAGE
  canvas.width = W; canvas.height = H
  const ctx = canvas.getContext("2d")
  const L = { left: 150, right: W - 150 }
  const side = (x0 = 0) => (rtl ? L.right - x0 : L.left + x0)                 // the reading side, x0 in from it
  const far = (x0 = 0) => (rtl ? L.left + x0 : L.right - x0)                  // the other side

  // paper, the thin gold frame
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H)
  ctx.strokeStyle = FRAME; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.roundRect(56, 56, W - 112, H - 112, 26); ctx.stroke()

  // header: the mark and the name on the reading side, the date on the other
  const mx = rtl ? L.right - 76 : L.left
  mark(ctx, mx, 128, 76, MARKC)
  ctx.fillStyle = INK; ctx.font = font(30, true, true)
  spaced(ctx, "PUDINEH AGENT CENTER", rtl ? mx - 30 : mx + 106, 186, 6.5, rtl)
  ctx.direction = rtl ? "rtl" : "ltr"
  ctx.fillStyle = MUTED; ctx.font = font(28); ctx.textAlign = rtl ? "left" : "right"
  ctx.fillText(T.date(parse(today)), far(), 186)
  ctx.fillStyle = RULE; ctx.fillRect(L.left, 252, L.right - L.left, 2)

  const list = apps.map((a) => (lang === "en" ? { ...a, ...a.en } : a))
  const one = list.length === 1
  const words = one ? (TEXTS[apps[0].key] || GENERAL)[lang] : GENERAL[lang]
  const honour = T.hon[hon || ""]

  // the body, drawn at size s (1, or smaller when it does not fit); returns the y under it
  function body(c, s) {
    c.direction = rtl ? "rtl" : "ltr"; c.textBaseline = "alphabetic"
    let y = 350
    // a paragraph, justified like the sample: every line but the last fills the width
    const para = (text, size, { bold = false, color = TEXT, gap = 1.78, x0 = 0, width = L.right - L.left } = {}) => {
      c.font = font(size * s, bold); c.fillStyle = color
      const lines = wrap(c, text, width - x0), space = c.measureText(" ").width
      lines.forEach((words, i) => {
        const last = i === lines.length - 1, total = words.reduce((a, w) => a + c.measureText(w).width, 0)
        const extra = !last && words.length > 1 ? (width - x0 - total) / (words.length - 1) : space
        let x = side(x0)
        c.textAlign = rtl ? "right" : "left"
        for (const w of words) { c.fillText(w, x, y); x += (rtl ? -1 : 1) * (c.measureText(w).width + extra) }
        y += size * s * gap
      })
    }
    const head = (text, size = 31) => { c.font = font(size * s, true); c.fillStyle = INK; c.textAlign = rtl ? "right" : "left"; c.fillText(text, side(), y); y += size * s * 1.55 }
    const rule = () => { c.fillStyle = RULE; c.fillRect(L.left, y, L.right - L.left, 2) }

    c.font = font(58 * s, true); c.fillStyle = INK; c.textAlign = rtl ? "right" : "left"
    c.fillText(one ? T.title1(list[0].title) : T.titleN, side(), y); y += 58 * s * 1.25
    const invite = one ? T.invite1(list[0].title) : T.inviteN(list.length)
    if (T.helloLine) { para(T.hello(honour, name), 33, { bold: true, color: INK }); y += 4 * s; para(invite, 32) }
    else para(T.hello(honour, name) + invite, 32)
    y += 26 * s

    if (one) {
      // the assistant's line: its name, and who works with it on the other side
      const a = list[0]
      c.font = font(38 * s, true); c.fillStyle = "#3c4246"; c.textAlign = rtl ? "right" : "left"; c.fillText(a.title, side(), y)
      c.font = font(25 * s); c.fillStyle = MUTED; c.textAlign = rtl ? "left" : "right"; c.fillText(a.roles.join(T.sep), far(), y)
      y += 26 * s; rule(); y += 66 * s
      head(T.problem); para(words.problem, 29.5); y += 24 * s
      head(T.solution); para(words.solution, 29.5); y += 24 * s
    } else {
      head(T.whatFor); para(words.problem + " " + words.solution, 29.5); y += 30 * s
      head(T.these); y += 6 * s
      // the chosen assistants in two columns: name, and who works with it under it
      const cols = list.length > 3 ? 2 : 1, colW = (L.right - L.left - 40 * (cols - 1)) / cols, rowH = 92 * s
      list.forEach((a, i) => {
        const col = i % cols, top = y + Math.floor(i / cols) * rowH, x = rtl ? L.right - col * (colW + 40) : L.left + col * (colW + 40)
        c.textAlign = rtl ? "right" : "left"
        c.fillStyle = GOLD; c.beginPath(); c.arc(rtl ? x - 7 : x + 7, top - 11 * s, 6 * s, 0, Math.PI * 2); c.fill()
        c.fillStyle = INK; c.font = font(30 * s, true); c.fillText(a.title, rtl ? x - 28 : x + 28, top)
        c.fillStyle = MUTED; c.font = font(24 * s); c.fillText(a.roles.join(T.sep), rtl ? x - 28 : x + 28, top + 38 * s)
      })
      y += Math.ceil(list.length / cols) * rowH + 10 * s
    }

    // the gains, two columns with gold dots
    head(T.gains)
    const colW = (L.right - L.left - 40) / 2
    const rows = Math.ceil(words.gains.length / 2)
    let tallest = y
    for (let col = 0; col < 2; col++) {
      let gy = y
      for (const g of words.gains.slice(col * rows, col * rows + rows)) {
        const x = rtl ? L.right - col * (colW + 40) : L.left + col * (colW + 40)
        c.fillStyle = GOLD; c.beginPath(); c.arc(rtl ? x - 7 : x + 7, gy - 10 * s, 5.5 * s, 0, Math.PI * 2); c.fill()
        c.font = font(28 * s); c.fillStyle = TEXT; c.textAlign = rtl ? "right" : "left"
        for (const line of wrap(c, g, colW - 34)) { c.fillText(line.join(" "), rtl ? x - 28 : x + 28, gy); gy += 28 * s * 1.7 }
      }
      tallest = Math.max(tallest, gy)
    }
    y = tallest + 40 * s

    // the login box: a header with until when, then label and value rows with thin lines between
    const rowsIn = [[T.address, ADDRESS, "ltr"]]
    if (login.username) rowsIn.push([T.username, login.username, "ltr"])
    if (login.username && login.password) rowsIn.push([T.password, login.password, "ltr"])
    if (!login.username) rowsIn.push([T.both, T.separately])
    rowsIn.push([list.length > 1 ? T.assistants : T.assistant, list.map((a) => a.title).join(T.sep)])
    rowsIn.push([T.start, words.start])
    c.font = font(27 * s)                                   // the label column is as wide as its longest label
    const pad = 40, labelW = Math.max(...rowsIn.map(([l]) => c.measureText(l).width)) + 44 * s
    const valueX = rtl ? L.right - pad - labelW : L.left + pad + labelW, valueW = L.right - L.left - 2 * pad - labelW
    c.font = font(28 * s, true)
    const heights = rowsIn.map(([, v, dir]) => (dir ? 1 : wrap(c, v, valueW).length) * 28 * s * 1.65 + 26 * s)
    const boxH = 104 * s + heights.reduce((a, b) => a + b, 0) + 14 * s
    c.fillStyle = BOX; c.beginPath(); c.roundRect(L.left, y, L.right - L.left, boxH, 22); c.fill()
    let by = y + 66 * s
    c.font = font(32 * s, true); c.fillStyle = INK; c.textAlign = rtl ? "right" : "left"; c.fillText(T.login, side(pad), by)
    if (login.expires) {
      const [d, t] = login.expires.split(" ")
      c.font = font(25 * s); c.fillStyle = MUTED; c.textAlign = rtl ? "left" : "right"; c.fillText(T.valid(T.at(T.date(parse(d)), t || "23:55")), far(pad), by)
    }
    by += 32 * s
    rowsIn.forEach(([label, value, dir], i) => {
      c.fillStyle = "#e4e0d6"; c.fillRect(L.left + pad - 12, by, L.right - L.left - 2 * pad + 24, 1.5)
      by += 48 * s
      c.font = font(27 * s); c.fillStyle = MUTED; c.textAlign = rtl ? "right" : "left"; c.fillText(label, side(pad), by)
      if (dir) {
        c.save(); c.direction = "ltr"; c.font = font(29 * s, true, true); c.fillStyle = INK; c.textAlign = rtl ? "right" : "left"; c.fillText(value, valueX, by); c.restore()
      } else {
        c.font = font(28 * s, true); c.fillStyle = INK; c.textAlign = rtl ? "right" : "left"
        wrap(c, value, valueW).forEach((line, k) => c.fillText(line.join(" "), valueX, by + k * 28 * s * 1.65))
      }
      by += heights[i] - 48 * s
    })
    return y + boxH
  }

  // the footer is fixed at the bottom; the body gets smaller until it ends above it
  const FOOT = H - 330
  const probe = document.createElement("canvas").getContext("2d")
  let s = 1
  while (s > 0.7 && body(probe, s) > FOOT - 40) s -= 0.03
  body(ctx, s)

  ctx.fillStyle = RULE; ctx.fillRect(L.left, FOOT, L.right - L.left, 2)
  ctx.direction = rtl ? "rtl" : "ltr"; ctx.textAlign = rtl ? "right" : "left"
  ctx.font = font(26); ctx.fillStyle = MUTED; ctx.fillText(T.contact, side(), FOOT + 72)
  ctx.save(); ctx.direction = "ltr"; ctx.font = font(29, false, true); ctx.fillStyle = INK; ctx.textAlign = rtl ? "right" : "left"
  ctx.fillText(EMAIL, side(), FOOT + 124); ctx.fillText(PHONE, side(), FOOT + 172); ctx.restore()
  const S = 200
  ctx.drawImage(seal(), W / 2 - S / 2, FOOT + 34, S, S)
  ctx.textAlign = rtl ? "left" : "right"
  ctx.font = font(27); ctx.fillStyle = MUTED; ctx.fillText(T.waiting, far(), FOOT + 110)
  ctx.font = font(44, true); ctx.fillStyle = INK; ctx.fillText(T.sign, far(), FOOT + 172)
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
