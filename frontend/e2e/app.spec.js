// End-to-end tests: real browser, real app, fake model (see tests/serve.py). Run: pnpm test:e2e
import { test, expect } from "@playwright/test"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"

const AXE = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8")
// The tests run in file order on one worker: later steps use what earlier steps did (warning -> teacher -> manager)

async function loginAs(page, role) {
  await page.goto("/")
  await page.locator(".role-card", { has: page.locator(`b:text-is("${role}")`) }).click()
  await expect(page.locator(".navbar")).toBeVisible()
}
const noPageErrors = (page) => {
  const errors = []
  page.on("pageerror", (e) => errors.push(e.message))
  page.on("dialog", (d) => { errors.push("unexpected dialog: " + d.message()); d.dismiss() })
  return errors
}
async function seriousA11y(page) {
  await page.waitForTimeout(1500)   // let entrance animations finish, half-faded text would fail contrast
  await page.addScriptTag({ content: AXE })
  return page.evaluate(async () => (await axe.run(document)).violations
    .filter((v) => ["serious", "critical"].includes(v.impact)).map((v) => `${v.id}: ${v.nodes[0].target.join(" ")}`))
}
async function askAssistant(page, question) {
  await page.locator(".fab-chat").click()
  const win = page.locator(".chat-window")
  await expect(win).toBeVisible()
  await win.locator(".composer input").fill(question)
  await win.locator(".composer input").press("Enter")
  await expect(win.locator(".msg-row.bot .bubble").last()).not.toHaveText(/در حال/, { timeout: 20_000 })
  return win
}

const SETUP_PASSWORD = "setup-test"   // set by tests/serve.py

test("first visit opens an empty setup; each step is checked; quick start builds Javid", async ({ page }) => {
  const errors = noPageErrors(page)
  await page.goto("/")
  await expect(page.locator(".setup-top h1")).toHaveText("راه‌اندازی دمو برای مدرسه")
  await expect(page.locator(".name-row input")).toHaveValue("")          // no names filled in for you
  await page.locator(".step-actions .btn.primary").click()               // "next" with nothing filled
  await expect(page.locator(".step-panel .error-text")).toHaveCount(2)
  await expect(page.locator(".stepper li").first()).not.toHaveClass(/done/)
  expect(await seriousA11y(page)).toEqual([])
  await page.locator(".chip-btn", { hasText: "پیش‌فرض" }).click()          // quick start: Javid fills every step
  await expect(page.locator(".stepper li.done")).toHaveCount(3)
  await expect(page.locator(".school-card")).toContainText("دبستان جاوید")
  await page.locator('input[type="password"]').fill(SETUP_PASSWORD)
  await page.locator(".step-actions .btn.primary").click()
  await expect(page.locator(".sc-build")).toBeVisible()
  await expect(page.locator(".role-card")).toHaveCount(7, { timeout: 30_000 })
  await expect(page.locator(".auth-form")).toContainText("دبستان جاوید")
  expect(errors).toEqual([])
})

test("login page shows every role and has no serious accessibility issues", async ({ page }) => {
  const errors = noPageErrors(page)
  await page.goto("/")
  await expect(page.locator(".role-card")).toHaveCount(7)
  expect(await seriousA11y(page)).toEqual([])
  expect(errors).toEqual([])
})

for (const role of ["مدیر", "پرسنل اداری", "مشاور", "ولی", "آموزگار"]) {
  test(`${role}: floating assistant instead of a chat menu item`, async ({ page }) => {
    const errors = noPageErrors(page)
    await loginAs(page, role)
    await expect(page.locator(".side-item", { hasText: "پرسش" })).toHaveCount(0)
    await expect(page.locator(".fab-chat")).toBeVisible()
    const win = await askAssistant(page, role === "ولی" ? "این ماه چند روز غیبت داشته؟" : "ساعت شروع کلاس‌ها چنده؟")
    await expect(win.locator(".msg-row.user")).toHaveCount(1)
    await page.keyboard.press("Escape")
    await expect(win).toBeHidden()
    await page.locator(".fab-chat").click()                       // the conversation is still there
    await expect(page.locator(".chat-window .msg-row.user")).toHaveCount(1)
    expect(errors).toEqual([])
  })
}

test("manager drafts a verified warning in the letter font, Escape closes the dialog", async ({ page }) => {
  await loginAs(page, "مدیر")
  await expect(page.locator(".welcome-text p")).not.toBeEmpty({ timeout: 15_000 })
  await page.locator(".alert", { has: page.locator("button", { hasText: "پیش‌نویس تذکر" }) }).first().locator("button").click()
  const dialog = page.locator(".dialog")
  await expect(dialog.locator("textarea.ai-draft")).toBeVisible({ timeout: 15_000 })
  await expect(dialog.locator(".check.ok")).toBeVisible()
  expect(await dialog.locator("textarea").evaluate((el) => getComputedStyle(el).fontFamily)).toContain("B Nazanin")
  expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true)   // focus moved into the dialog
  await page.keyboard.press("Escape")
  await expect(dialog).toBeHidden()
  await page.locator(".alert button", { hasText: "پیش‌نویس تذکر" }).first().click()
  await expect(dialog.locator(".check.ok")).toBeVisible({ timeout: 15_000 })
  await dialog.locator(".dialog-actions .btn.primary").click()
  await expect(page.locator(".alert.done")).not.toHaveCount(0)
  expect(await seriousA11y(page)).toEqual([])
})

test("teacher acknowledges the warning and the manager is told", async ({ browser }) => {
  const teacher = await (await browser.newContext()).newPage()
  await loginAs(teacher, "معلم ورزش")
  await teacher.locator(".bell-wrap .icon-btn").click()
  await teacher.locator(".bp-item", { hasText: "تذکر" }).click()
  await teacher.locator(".dialog-actions .btn.primary").click()
  await expect(teacher.locator(".dialog .check.ok")).toBeVisible()
  const manager = await (await browser.newContext()).newPage()
  await loginAs(manager, "مدیر")
  await manager.locator(".bell-wrap .icon-btn").click()
  await expect(manager.locator(".bp-item", { hasText: "رؤیت کرد" })).not.toHaveCount(0)
})

test("staff: agent works the queue, a reply is approved and a letter is referred to parents", async ({ page }) => {
  const errors = noPageErrors(page)
  await loginAs(page, "پرسنل اداری")
  await expect(page.locator(".agent")).toContainText("همه نامه‌ها بررسی شد", { timeout: 60_000 })
  await page.locator("button", { hasText: "بررسی و تأیید پاسخ" }).first().click()
  await expect(page.locator(".dialog textarea.ai-draft")).toBeVisible()
  await page.locator(".dialog-actions .btn.primary").click()
  await expect(page.locator(".dialog")).toBeHidden()
  await page.locator(".letter-card button", { hasText: "ارجاع" }).first().click()
  await page.locator(".person", { hasText: "اولیای کلاس چهارم الف" }).click()
  await expect(page.locator(".parent-box textarea.ai-draft")).not.toHaveValue("", { timeout: 15_000 })
  await page.locator(".dialog-actions .btn.primary").click()
  await expect(page.locator(".dialog")).toBeHidden()
  // a letter with HTML in it is shown as text, no script runs
  await page.locator("button", { hasText: "ثبت نامه جدید" }).click()
  await page.locator(".field input").nth(1).fill("<img src=x onerror=alert(1)>")
  await page.locator(".field textarea").fill("متن نامه آزمایشی <img src=x onerror=alert(1)> برای اطلاع.")
  await page.locator(".dialog-actions .btn.primary").click()
  await expect(page.locator(".agent")).toContainText("همه نامه‌ها بررسی شد", { timeout: 30_000 })
  expect(await seriousA11y(page)).toEqual([])
  expect(errors).toEqual([])
})

test("counselor sends a message for Ava; Escape closes the drawer", async ({ page }) => {
  await loginAs(page, "مشاور")
  await page.locator(".segmented button").nth(1).click()
  await page.locator(".small-search").fill("آوا")
  await page.locator(".student-row").first().click()
  await page.locator(".drawer button", { hasText: "نوشتن پیام با دستیار" }).click()
  await expect(page.locator(".drawer textarea.ai-draft").nth(1)).toBeVisible({ timeout: 15_000 })
  await page.locator(".drawer .btn.primary", { hasText: "تأیید و ارسال" }).click()
  await expect(page.locator(".sent-msg")).not.toHaveCount(0)
  expect(await seriousA11y(page)).toEqual([])
  await page.keyboard.press("Escape")
  await expect(page.locator(".drawer")).toBeHidden()
})

test("parent sees the counselor and school messages but nothing private, and fills a form", async ({ page }) => {
  await loginAs(page, "ولی")
  await expect(page.locator(".counsel")).not.toHaveCount(0)
  await expect(page.getByText("پیام‌های مدرسه")).toBeVisible()
  await expect(page.locator("body")).not.toContainText("اظهار نگرانی")
  await page.locator(".form-tile.action").nth(1).click()
  await page.locator(".q", { hasText: "حال و حوصله" }).locator(".dot-btn").first().click()
  await page.locator(".dialog-actions .btn.primary").click()
  await expect(page.locator(".dialog")).toBeHidden()
  await page.locator(".profile .btn.primary").click()            // "ask about Ava" opens the assistant
  await expect(page.locator(".chat-window")).toBeVisible()
  expect(await seriousA11y(page)).toEqual([])
})

test("dark mode stays after reload and passes contrast", async ({ page }) => {
  await loginAs(page, "مدیر")
  await page.locator(".nav-actions .icon-btn").first().click()
  await page.reload()
  await expect(page.locator("html")).toHaveClass(/dark/)
  await expect(page.locator(".stat")).toHaveCount(4)
  expect(await seriousA11y(page)).toEqual([])
})

test("phone width: no sideways scrolling, the assistant opens full screen", async ({ browser }) => {
  let page
  for (const role of ["ولی", "پرسنل اداری"]) {
    page = await (await browser.newContext({ viewport: { width: 375, height: 760 } })).newPage()
    await loginAs(page, role)
    await page.waitForTimeout(1200)
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0)
  }
  await page.locator(".fab-chat").click()
  await page.waitForTimeout(700)   // let the opening animation finish
  const box = await page.locator(".chat-window").boundingBox()
  expect(box.width).toBeGreaterThanOrEqual(374)
})

test("an expired session goes back to the login page", async ({ page }) => {
  await loginAs(page, "ولی")
  await page.evaluate(() => fetch("/logout", { method: "POST", headers: { Authorization: "Bearer " + localStorage.getItem("token") } }))
  await expect(page.locator(".role-card").first()).toBeVisible({ timeout: 20_000 })   // the bell polls every 15s
})

test("a demo for another school, step by step, with the card filling in", async ({ page }) => {
  await page.goto("/")
  await page.locator(".switch-school").click()
  const next = page.locator(".step-actions .btn.primary")
  await page.locator(".name-row input").fill("نیکان")
  await page.locator(".choice", { hasText: "پسرانه" }).click()
  await expect(page.locator(".sc-title")).toContainText("دبستان نیکان")   // the card follows the typing
  await next.click()
  await page.locator("label", { hasText: "شهر" }).locator("input").fill("اصفهان")
  await page.locator("label", { hasText: "منطقه" }).locator("input").fill("ناحیه ۲")
  await next.click()
  await expect(page.locator(".sc-row.done").first()).toContainText("ناحیه ۲، اصفهان")
  for (const [i, name] of [[0, "علی رستمی"], [1, "رضا یزدانی"], [2, "سمیرا امینی"]]) {
    const field = page.locator(".step-panel .field").nth(i)
    await field.locator(".segmented button").nth(i === 2 ? 1 : 0).click()
    await field.locator("input").fill(name)
  }
  await next.click()
  await expect(page.locator(".school-card")).toContainText("آقای علی رستمی")
  await expect(page.locator(".school-card.ready")).toBeVisible()
  await page.locator('input[type="password"]').fill(SETUP_PASSWORD)
  await next.click()
  await expect(page.locator(".auth-form")).toContainText("دبستان نیکان", { timeout: 30_000 })
  await expect(page.locator(".role-card", { hasText: "مدیر" }).first()).toContainText("آقای علی رستمی")
  await loginAs(page, "مدیر")
  await expect(page.locator(".side-brand")).toContainText("دبستان نیکان")
  await expect(page.locator("body")).not.toContainText("جاوید")
  // and back to the default for the next run
  await page.locator(".avatar-btn").click(); await page.locator(".dd-item.danger").click()
  await page.locator(".switch-school").click()
  await page.locator(".chip-btn", { hasText: "پیش‌فرض" }).click()
  await page.locator('input[type="password"]').fill(SETUP_PASSWORD)
  await page.locator(".step-actions .btn.primary").click()
  await expect(page.locator(".auth-form")).toContainText("دبستان جاوید", { timeout: 30_000 })
})
