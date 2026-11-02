"""Every number and date the dental clinic's panels and the model use, computed by code from dental.db.

The clinic works Saturday to Thursday, 10:00 to 14:00 and 16:00 to 20:00, in half-hour slots; Friday is closed.
Prices are the clinic's own list (SERVICES), in toman: made up for the demo, a real clinic enters its own.
"""
from datetime import date, timedelta
from jalali import to_jalali, MONTHS
from . import store

# service: (name, minutes, price in toman)
SERVICES = {
    "checkup": ("معاینه", 30, 400_000),
    "scaling": ("جرم‌گیری", 30, 1_500_000),
    "filling": ("ترمیم دندان", 60, 3_000_000),
    "extraction": ("کشیدن دندان", 30, 2_000_000),
    "rootcanal": ("عصب‌کشی", 60, 7_000_000),
    "crown": ("روکش", 60, 14_000_000),
    "implant": ("ایمپلنت", 60, 38_000_000),
    "ortho": ("ارتودنسی", 60, 95_000_000),
    "whitening": ("سفید کردن دندان", 60, 8_000_000),
}
STATUS = {"booked": "تأییدنشده", "confirmed": "تأییدشده", "done": "انجام شد", "noshow": "نیامد", "cancelled": "لغو شد"}
SLOTS = [f"{h:02d}:{m:02d}" for h in (10, 11, 12, 13, 16, 17, 18, 19) for m in (0, 30)]
FOLLOW_DAYS = 14     # a plan not started, with no contact this long, needs a call
NOSHOW_COUNT = 2     # a patient who did not come this many times in NOSHOW_DAYS
NOSHOW_DAYS = 90
UNPAID_DAYS = 14     # a balance left this long after the treatment
HALFWAY_DAYS = 45    # a plan begun, with nothing done and nothing booked this long
METHODS = {"card": "کارت‌خوان", "cash": "نقد", "transfer": "کارت به کارت"}

def today():
    return store.today()

def money(v):
    """Toman in plain words: 38_000_000 -> «38 میلیون تومان», 1_500_000 -> «1.5 میلیون تومان», 400_000 -> «400 هزار تومان»."""
    v = int(round(v or 0))
    if v >= 1_000_000_000:
        b, m = divmod(round(v / 1_000_000), 1000)
        return f"{b} میلیارد" + (f" و {m} میلیون" if m else "") + " تومان"
    if v >= 1_000_000:
        m = v / 1_000_000
        return (f"{m:.1f}".rstrip("0").rstrip(".") if m < 10 and v % 1_000_000 else str(round(m))) + " میلیون تومان"
    if v >= 1000:
        return f"{round(v / 1000)} هزار تومان"
    return f"{v} تومان"

def jfull(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{y}/{m:02d}/{d:02d}"

def jday(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{d} {MONTHS[m - 1]}"

WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]   # date.weekday(): Monday is 0

def jlong(iso):
    """«شنبه 17 آبان»"""
    return f"{WEEKDAYS[date.fromisoformat(iso[:10]).weekday()]} {jday(iso)}"

def days_ago(iso):
    return (today() - date.fromisoformat(iso[:10])).days

def day_word(iso):
    """«امروز», «فردا», or «شنبه 17 آبان»"""
    n = (date.fromisoformat(iso[:10]) - today()).days
    return "امروز" if n == 0 else "فردا" if n == 1 else jlong(iso)

def open_day(d):
    return d.weekday() != 4

def next_workday(d=None):
    d = (d or today()) + timedelta(days=1)
    while not open_day(d):
        d += timedelta(days=1)
    return d

def service_name(key):
    return SERVICES.get(key, (key,))[0]

def names(c):
    return {r["id"]: r["name"] for r in c.execute("SELECT id, name FROM patients")}

# ---------- the day's schedule ----------

def taken(c, day):
    """{slot: appointment} for a day's live appointments (cancelled ones free their slots)."""
    out = {}
    for a in c.execute("SELECT * FROM appointments WHERE substr(at, 1, 10) = ? AND status != 'cancelled' ORDER BY at", (day,)):
        i = SLOTS.index(a["at"][11:16]) if a["at"][11:16] in SLOTS else -1
        for k in range(max(1, a["minutes"] // 30)):
            if 0 <= i + k < len(SLOTS):
                out[SLOTS[i + k]] = dict(a)
    return out

def free_slots(c, day):
    if not open_day(date.fromisoformat(day)):
        return []
    busy = taken(c, day)
    return [s for s in SLOTS if s not in busy]

def _mins(s):
    return int(s[:2]) * 60 + int(s[3:])

def fits_session(time, minutes):
    """True when an appointment this long starting at this time ends in the same session (not across the midday break)."""
    if time not in SLOTS:
        return False
    i, need = SLOTS.index(time), max(1, minutes // 30)
    run = SLOTS[i:i + need]
    return len(run) == need and all(_mins(run[k + 1]) - _mins(run[k]) == 30 for k in range(len(run) - 1))

def run_of(time, minutes):
    i = SLOTS.index(time)
    return SLOTS[i:i + max(1, minutes // 30)]

def fits(c, day, time, minutes, ignore=None):
    """True when an appointment of this length can start at this time: the slots are free and in one session."""
    if not open_day(date.fromisoformat(day)) or not fits_session(time, minutes):
        return False
    busy = {k: v for k, v in taken(c, day).items() if v["id"] != ignore}
    return not any(s in busy for s in run_of(time, minutes))

def gaps(free):
    """Runs of free slots: [("17:00", "18:00"), ...] (the end is when the last free half hour ends)."""
    out, start, prev, mins = [], None, None, _mins
    for s in free + [None]:
        if s and prev and mins(s) - mins(prev) == 30:
            prev = s
            continue
        if start:
            end = mins(prev) + 30
            out.append((start, f"{end // 60:02d}:{end % 60:02d}"))
        start = prev = s
    return out

def appt_view(a, who=None):
    a = dict(a)
    return a | {"service_text": service_name(a["service"]), "status_text": STATUS.get(a["status"], a["status"]), "time": a["at"][11:16],
                "date_text": jfull(a["at"]), "day_text": day_word(a["at"]), "price_text": money(a["price"]), "patient": (who or {}).get(a["patient_id"], "")}

def schedule(c, day):
    who = names(c)
    busy = taken(c, day)
    rows, seen = [], set()
    for s in SLOTS if open_day(date.fromisoformat(day)) else []:
        a = busy.get(s)
        if a and a["id"] in seen:
            continue
        if a:
            seen.add(a["id"])
            rows.append({"time": s, "appt": appt_view(a, who)})
        else:
            rows.append({"time": s, "appt": None})
    cancelled = [appt_view(a, who) for a in c.execute("SELECT * FROM appointments WHERE substr(at, 1, 10) = ? AND status = 'cancelled' ORDER BY at", (day,))]
    return {"date": day, "date_text": jlong(day) + " " + jfull(day), "closed": not open_day(date.fromisoformat(day)), "rows": rows, "cancelled": cancelled}

# ---------- money ----------

def balance(c, pid):
    """(owed, paid): what done appointments cost and what was paid."""
    owed = c.execute("SELECT COALESCE(SUM(price), 0) FROM appointments WHERE patient_id = ? AND status = 'done'", (pid,)).fetchone()[0]
    paid = c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE patient_id = ?", (pid,)).fetchone()[0]
    return owed, paid

def balances(c):
    """Patients who owe something: [{patient_id, name, owed, paid, left, last_done}] most owed first."""
    who, out = names(c), []
    rows = c.execute("""SELECT patient_id, SUM(price) owed, MAX(substr(at, 1, 10)) last FROM appointments WHERE status = 'done' GROUP BY patient_id""").fetchall()
    paid = {r[0]: r[1] for r in c.execute("SELECT patient_id, SUM(amount) FROM payments GROUP BY patient_id")}
    for r in rows:
        left = r["owed"] - paid.get(r["patient_id"], 0)
        if left > 0:
            out.append({"patient_id": r["patient_id"], "name": who.get(r["patient_id"], ""), "owed": r["owed"], "paid": paid.get(r["patient_id"], 0),
                        "left": left, "last_done": r["last"]})
    return sorted(out, key=lambda b: -b["left"])

# ---------- plans ----------

def plan_view(c, p, who=None):
    p = dict(p)
    items = [dict(i) | {"service_text": service_name(i["service"]), "price_text": money(i["price"]), "done_text": jfull(i["done_on"]) if i["done_on"] else ""}
             for i in c.execute("SELECT * FROM plan_items WHERE plan_id = ? ORDER BY id", (p["id"],))]
    total = sum(i["price"] for i in items)
    done = [i for i in items if i["status"] == "done"]
    contact = c.execute("SELECT MAX(at) FROM contacts WHERE plan_id = ?", (p["id"],)).fetchone()[0]
    nxt = c.execute("""SELECT * FROM appointments WHERE patient_id = ? AND status IN ('booked', 'confirmed') AND substr(at, 1, 10) >= ?
                       ORDER BY at LIMIT 1""", (p["patient_id"], today().isoformat())).fetchone()
    since = (contact or p["created"])[:10]
    return p | {"items": items, "total": total, "total_text": money(total), "done_count": len(done), "left_total": total - sum(i["price"] for i in done),
                "created_text": jfull(p["created"]), "last_contact": contact[:10] if contact else None, "last_contact_text": jfull(contact) if contact else "",
                "quiet_days": days_ago(since), "last_done": max((i["done_on"] for i in done), default=None),
                "next": appt_view(nxt) if nxt else None, "patient": (who or names(c)).get(p["patient_id"], "")}

def plans(c):
    """Every plan worth following, in groups: not started, in progress, finished, declined."""
    who, out = names(c), {"waiting": [], "going": [], "finished": [], "declined": []}
    for p in c.execute("SELECT * FROM plans ORDER BY created DESC"):
        v = plan_view(c, p, who)
        if p["status"] == "declined":
            out["declined"].append(v)
        elif v["done_count"] == len(v["items"]):
            out["finished"].append(v)
        elif v["done_count"] or v["next"]:
            out["going"].append(v)
        else:
            out["waiting"].append(v)
    out["waiting"].sort(key=lambda v: -v["total"])
    return out

def not_started(c):
    """Plans proposed and never started, nothing booked, no call in FOLLOW_DAYS: the money a call might bring back."""
    return [v for v in plans(c)["waiting"] if v["quiet_days"] >= FOLLOW_DAYS]

# ---------- what needs doing ----------

def alerts(c):
    """Today's work, most urgent first: the next working day's unconfirmed appointments, its empty slots when someone
    waits, patients who often do not come and have an appointment soon, plans not started that wait for a call."""
    who, t, out = names(c), today(), []
    nxt = next_workday().isoformat()
    for a in c.execute("SELECT * FROM appointments WHERE substr(at, 1, 10) = ? AND status = 'booked' ORDER BY at", (nxt,)):
        out.append({"type": "unconfirmed", "tone": "warning", "icon": "clock", "patient_id": a["patient_id"], "appt_id": a["id"], "order": 1,
                    "title": f"نوبت {day_word(nxt)} ساعت {a['at'][11:16]} هنوز تأیید نشده است: {who.get(a['patient_id'], '')}",
                    "detail": f"{service_name(a['service'])}، {a['minutes']} دقیقه. پیام یادآوری آماده است؛ اگر نیاید، این وقت خالی می‌ماند."})
    waiting = c.execute("SELECT COUNT(*) FROM waitlist WHERE status = 'waiting'").fetchone()[0]
    if waiting:
        for start, end in gaps(free_slots(c, nxt)):
            out.append({"type": "slot", "tone": "info", "icon": "calendar", "day": nxt, "date": jfull(nxt), "time": start, "order": 2,
                        "title": f"{day_word(nxt)} از ساعت {start} تا {end} وقت خالی است",
                        "detail": f"{waiting} نفر در فهرست انتظار هستند. با یکی تماس بگیرید و همین وقت را به او بدهید."})
    week = (t + timedelta(days=7)).isoformat()
    since = (t - timedelta(days=NOSHOW_DAYS)).isoformat()
    for a in c.execute("""SELECT * FROM appointments WHERE status IN ('booked', 'confirmed') AND substr(at, 1, 10) >= ? AND substr(at, 1, 10) <= ?
                          ORDER BY at""", (t.isoformat(), week)):
        missed = c.execute("SELECT COUNT(*) FROM appointments WHERE patient_id = ? AND status = 'noshow' AND substr(at, 1, 10) >= ?",
                           (a["patient_id"], since)).fetchone()[0]
        if missed >= NOSHOW_COUNT:
            out.append({"type": "noshow", "tone": "warning", "icon": "alert", "patient_id": a["patient_id"], "appt_id": a["id"], "order": 3,
                        "title": f"{who.get(a['patient_id'], '')} در سه ماه گذشته {missed} بار نیامده و {day_word(a['at'])} ساعت {a['at'][11:16]} نوبت دارد",
                        "detail": f"{service_name(a['service'])}. یک روز قبل تماس بگیرید و اگر نمی‌آید، وقت را به فهرست انتظار بدهید."})
    for v in not_started(c):
        out.append({"type": "plan", "tone": "danger" if v["total"] >= 30_000_000 else "info", "icon": "heart", "patient_id": v["patient_id"], "plan_id": v["id"],
                    "order": 4, "money": v["total"],
                    "title": f"طرح درمان «{v['title']}» برای {v['patient']} ({v['total_text']}) شروع نشده است",
                    "detail": f"پیشنهاد در {v['created_text']}. " + (f"آخرین تماس {v['quiet_days']} روز پیش." if v["last_contact"] else f"{v['quiet_days']} روز است کسی با بیمار تماس نگرفته است.")})
    return sorted(out, key=lambda a: (a["order"], -a.get("money", 0), a["title"]))

def checks(c):
    """The dentist's checks, from the records alone: balances left unpaid after treatment, plans begun and left
    halfway. They say what the records show, never blame."""
    who, out = names(c), []
    for b in balances(c):
        if days_ago(b["last_done"]) >= UNPAID_DAYS:
            rows = c.execute("SELECT * FROM appointments WHERE patient_id = ? AND status = 'done' ORDER BY at DESC LIMIT 6", (b["patient_id"],)).fetchall()
            pays = c.execute("SELECT * FROM payments WHERE patient_id = ? ORDER BY at DESC LIMIT 6", (b["patient_id"],)).fetchall()
            out.append({"type": "unpaid", "tone": "danger", "patient_id": b["patient_id"],
                        "title": f"{b['name']} {money(b['left'])} بدهکار است",
                        "detail": f"آخرین درمان {days_ago(b['last_done'])} روز پیش انجام شد و مانده‌ی آن هنوز پرداخت نشده است.",
                        "how": [f"{jfull(a['at'])} · {service_name(a['service'])}: {money(a['price'])}" for a in rows] +
                               [f"{jfull(p['at'])} · پرداخت ({METHODS.get(p['method'], p['method'])}): {money(p['amount'])}" for p in pays] +
                               [f"= کل درمان‌ها {money(b['owed'])}، پرداخت‌شده {money(b['paid'])}، مانده {money(b['left'])}"]})
    for v in plans(c)["going"]:
        if v["done_count"] and not v["next"] and v["last_done"] and days_ago(v["last_done"]) >= HALFWAY_DAYS:
            out.append({"type": "halfway", "tone": "warning", "patient_id": v["patient_id"], "plan_id": v["id"],
                        "title": f"طرح «{v['title']}» برای {v['patient']} نیمه‌کاره مانده است",
                        "detail": f"{v['done_count']} از {len(v['items'])} مرحله انجام شد؛ {days_ago(v['last_done'])} روز است نه کاری شده و نه نوبتی گرفته شده. "
                                  f"مانده‌ی طرح {money(v['left_total'])}.",
                        "how": [f"{i['service_text']}" + (f"، دندان {i['tooth']}" if i["tooth"] else "") + f": {i['price_text']} · " +
                                (f"انجام شد {i['done_text']}" if i["status"] == "done" else "انجام نشده") for i in v["items"]] +
                               ["نوبت آینده: ندارد"]})
    return out

def stats(c):
    t, nxt = today(), next_workday().isoformat()
    who = names(c)
    tomorrow = [appt_view(a, who) for a in c.execute("SELECT * FROM appointments WHERE substr(at, 1, 10) = ? AND status != 'cancelled' ORDER BY at", (nxt,))]
    confirmed = [a for a in tomorrow if a["status"] == "confirmed"]
    waiting = not_started(c)
    month = (t - timedelta(days=30)).isoformat()
    past = c.execute("""SELECT status, COUNT(*) n FROM appointments WHERE substr(at, 1, 10) >= ? AND substr(at, 1, 10) < ?
                        AND status IN ('done', 'noshow') GROUP BY status""", (month, t.isoformat())).fetchall()
    counts = {r["status"]: r["n"] for r in past}
    came, missed = counts.get("done", 0), counts.get("noshow", 0)
    owed = [b for b in balances(c)]
    left = sum(b["left"] for b in owed)
    return [
        {"label": f"نوبت‌های {day_word(nxt)}", "value": str(len(tomorrow)), "sub": f"{len(confirmed)} تأییدشده، {len(tomorrow) - len(confirmed)} تأییدنشده",
         "icon": "calendar", "tone": "primary", "how": [f"{a['time']} · {a['patient']} · {a['service_text']} · {a['status_text']}" for a in tomorrow] or ["نوبتی نیست"]},
        {"label": "طرح‌های درمان منتظر تماس", "value": money(sum(v["total"] for v in waiting)), "sub": f"{len(waiting)} بیمار",
         "icon": "heart", "tone": "danger" if waiting else "success",
         "how": [f"{v['patient']} · {v['title']}: {v['total_text']}" for v in waiting] + [f"= جمع: {money(sum(v['total'] for v in waiting))}"]},
        {"label": "نیامدن در سی روز گذشته", "value": f"{missed} از {came + missed}", "sub": f"{round(100 * missed / (came + missed)) if came + missed else 0} درصد نوبت‌ها",
         "icon": "alert", "tone": "warning", "how": [f"نوبت‌های انجام‌شده: {came}", f"نیامد: {missed}", f"= {missed} از {came + missed} نوبت"]},
        {"label": "مانده‌ی پرداخت‌نشده", "value": money(left), "sub": f"{len(owed)} بیمار", "icon": "chart", "tone": "info",
         "how": [f"{b['name']}: درمان {money(b['owed'])} − پرداخت {money(b['paid'])} = {money(b['left'])}" for b in owed] + [f"= جمع: {money(left)}"]},
    ]

def overview(c):
    t = today().isoformat()
    return {"today": jfull(t), "today_long": jlong(t), "next_day": day_word(next_workday().isoformat()), "stats": stats(c), "alerts": alerts(c),
            "schedule": schedule(c, t)}

def brief_facts(c):
    o = overview(c)
    lines = [f"امروز: {o['today_long']} {o['today']}"] + [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]]
    lines += ["کارهای امروز به ترتیب فوریت:"] + [f"{i + 1}. {a['title']}" for i, a in enumerate(o["alerts"][:6])]
    return "\n".join(lines), o

def events(c, after=0, limit=40, patient_id=None):
    q, args = "SELECT * FROM events WHERE id > ?", [after]
    if patient_id:
        q += " AND patient_id = ?"; args.append(patient_id)
    rows = c.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit)).fetchall()
    t = today().isoformat()
    return [{"id": e["id"], "kind": e["kind"], "text": e["text"], "who": e["who"], "role": e["role"], "today": e["at"][:10] == t,
             "day": jday(e["at"]), "time": e["at"][11:16], "patient_id": e["patient_id"]} for e in rows]
