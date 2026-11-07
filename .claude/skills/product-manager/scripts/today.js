// Today's date in Tehran (Jalali), whether it is the weekly report's day (Saturday), and today's topic.
// The topic comes from a fixed rotation counted over the days with a daily report, so it never depends on memory.
//   node today.js
const CYCLE = [
  { kind: "new" }, { kind: "improve", app: "school" }, { kind: "improve", app: "dental" },
  { kind: "new" }, { kind: "improve", app: "hotel" }, { kind: "improve", app: "estate" },
  { kind: "new" }, { kind: "improve", app: "law" }, { kind: "improve", app: "fabric" },
  { kind: "new" }, { kind: "improve", app: "lodge" }, { kind: "improve", app: "lang" },
  { kind: "new" }, { kind: "improve", app: "deed" },
];
const START = Date.UTC(2026, 10, 8);  // 2026-11-08, the first daily report (a Sunday)
const DAY = 86400000;

const now = process.argv[2] ? new Date(process.argv[2] + "T08:00:00+03:30") : new Date();
const part = (opts, locale = "en-u-ca-persian-nu-latn") =>
  Object.fromEntries(new Intl.DateTimeFormat(locale, { timeZone: "Asia/Tehran", ...opts }).formatToParts(now).map((p) => [p.type, p.value]));
const j = part({ year: "numeric", month: "2-digit", day: "2-digit", weekday: "long" });
const g = part({ year: "numeric", month: "2-digit", day: "2-digit" }, "en-CA");
const today = Date.UTC(+g.year, +g.month - 1, +g.day);
const weekly = j.weekday === "Saturday";

let n = 0;  // daily reports before today
for (let t = START; t < today; t += DAY) if (new Date(t).getUTCDay() !== 6) n++;
const topic = weekly ? { kind: "weekly" } : CYCLE[((n % CYCLE.length) + CYCLE.length) % CYCLE.length];

console.log(JSON.stringify({
  date: `${j.year}/${j.month}/${j.day}`,
  gregorian: `${g.year}-${g.month}-${g.day}`,
  fa: (({ weekday, day, month, year }) => `${weekday} ${day} ${month} ${year}`)(part({ weekday: "long", day: "numeric", month: "long", year: "numeric" }, "fa-IR-u-ca-persian")),
  weekly,
  topic,
}, null, 2));
