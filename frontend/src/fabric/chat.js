// The floating assistant for each fabric role: it answers from numbers the server computes from the Excel files.
const base = {
  endpoint: "/fabric/ask", title: "دستیار فروشگاه", subtitle: "جواب از روی فایل‌های اکسل",
  intro: "هر سؤالی درباره‌ی فروش، انبار و حساب‌ها دارید بپرسید. عددها را خود برنامه از روی اکسل‌ها حساب می‌کند.",
  loadingText: "در حال حساب کردن از روی اکسل‌ها",
}
export const CHAT = {
  owner: { ...base, examples: ["فروش این ماه چقدر بود؟", "کدوم جنس‌ها دارن تموم می‌شن؟", "بدهکارهای بزرگ کیان؟"] },
  seller: { ...base, examples: ["از کتان کش مشکی چند توپ داریم؟", "پرفروش‌ترین جنس‌های این ماه؟", "حساب رضایی چطوره؟"] },
  accountant: { ...base, examples: ["چک‌های این هفته چقدره؟", "کی چک برگشتی داره؟", "حساب کریمی چطوره؟"] },
}
