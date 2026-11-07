// Turns the report's HTML body into an A4 Persian PDF (right to left, Vazirmatn).
// Uses the Playwright that is already installed in the session; adds nothing to the project.
//   node make_pdf.js body.html out.pdf "عنوان گزارش" "1405/08/17"
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const [bodyFile, outFile, title = "گزارش مدیر محصول", date = ""] = process.argv.slice(2);
if (!bodyFile || !outFile) {
  console.error("usage: node make_pdf.js body.html out.pdf [title] [date]");
  process.exit(1);
}
const fonts = path.resolve(__dirname, "../../../../frontend/public/fonts");
const font = (f) => "data:font/woff2;base64," + fs.readFileSync(path.join(fonts, f)).toString("base64");
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);

const html = `<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><style>
@font-face { font-family: V; src: url(${font("Vazirmatn-Regular.woff2")}); font-weight: 400; }
@font-face { font-family: V; src: url(${font("Vazirmatn-Bold.woff2")}); font-weight: 700; }
@page { size: A4; margin: 18mm 16mm 20mm; }
body { font-family: V, sans-serif; font-size: 11pt; line-height: 1.9; color: #1f2933; margin: 0; }
header { border-bottom: 2px solid #0f766e; padding-bottom: 8px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: baseline; }
header h1 { font-size: 18pt; margin: 0; color: #0f766e; }
header span { color: #52606d; font-size: 10pt; }
h2 { font-size: 14pt; color: #0f766e; margin: 22px 0 6px; }
h3 { font-size: 12pt; margin: 16px 0 4px; }
p { margin: 6px 0; }
ul, ol { margin: 6px 0; padding-right: 22px; }
li { margin: 3px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 10pt; }
th, td { border: 1px solid #cbd2d9; padding: 5px 8px; text-align: right; vertical-align: top; }
th { background: #f0f4f8; }
a { color: #0b5ea8; text-decoration: none; word-break: break-all; }
.guess { background: #fff7e6; border-right: 3px solid #d97706; padding: 2px 8px; }
.box { background: #f0fdfa; border: 1px solid #99f6e4; border-radius: 6px; padding: 8px 12px; margin: 10px 0; }
.src { font-size: 9pt; color: #52606d; direction: ltr; text-align: left; }
h2, h3 { break-after: avoid; } tr, li { break-inside: avoid; }
</style></head><body>
<header><h1>${esc(title)}</h1><span>${esc(date)}</span></header>
${fs.readFileSync(bodyFile, "utf8")}
</body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: outFile, format: "A4", printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: "<span></span>",
    footerTemplate: '<div style="width:100%;text-align:center;font-size:8pt;color:#888"><span class="pageNumber"></span> / <span class="totalPages"></span></div>' });
  await browser.close();
  console.log(outFile, fs.statSync(outFile).size, "bytes");
})();
