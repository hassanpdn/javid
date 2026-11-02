"""Every date and number the law office's panels and the model use, computed by code from law.db.

Deadlines: the day of service does not count; the last day is service + the number of days for that kind of notice;
a last day on a Friday or an official holiday moves to the next working day. The number of days per kind and the
holidays are settings: the defaults are the common ones in Iranian civil procedure, and a real office checks them,
and adds this year's lunar holidays (they move every year), before relying on them.
"""
from datetime import date, timedelta
from jalali import to_jalali, to_gregorian, MONTHS
from . import store

# kind: (name of the notice, what has to be done, default days; 0 = no deadline of its own)
KINDS = {
    "judgment": ("دادنامه‌ی بدوی", "تجدیدنظرخواهی", 20),
    "default": ("دادنامه‌ی غیابی", "واخواهی", 20),
    "appeal": ("دادنامه‌ی تجدیدنظر", "فرجام‌خواهی، اگر رأی قابل فرجام باشد", 20),
    "defect": ("اخطار رفع نقص", "رفع نقص دادخواست", 10),
    "expert": ("ابلاغ نظر کارشناس", "اعتراض به نظر کارشناس", 7),
    "execution": ("اجرائیه", "اجرای مفاد اجرائیه یا معرفی مال", 10),
    "hearing": ("وقت رسیدگی", "حضور در جلسه", 0),
}
FIELDS = {"civil": "حقوقی", "criminal": "کیفری", "family": "خانواده", "enforcement": "اجرای احکام"}
STAGES = {"first": "بدوی", "appeal": "تجدیدنظر", "supreme": "فرجام", "enforcement": "اجرا", "closed": "مختومه"}
IDLE_DAYS = 60       # an open case with nothing done this long
REPORT_DAYS = 30     # a client without a report this long
LATE_ENTRY = 3       # a notice entered this many days after its service lost days of its deadline

def today():
    return store.today()

def jfull(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{y}/{m:02d}/{d:02d}"

def jday(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{d} {MONTHS[m - 1]}"

WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]   # date.weekday(): Monday is 0

def jlong(iso):
    """«شنبه 17 آبان»"""
    d = date.fromisoformat(iso[:10])
    return f"{WEEKDAYS[d.weekday()]} {jday(iso)}"

def days_left(iso):
    return (date.fromisoformat(iso[:10]) - today()).days

def left_text(iso):
    n = days_left(iso)
    return "امروز" if n == 0 else "فردا" if n == 1 else f"{n} روز دیگر" if n > 0 else "دیروز" if n == -1 else f"{-n} روز پیش"

def settings(c):
    out = {}
    for k, (_, _, days) in KINDS.items():
        row = c.execute("SELECT value FROM meta WHERE key = ?", ("days_" + k,)).fetchone()
        out[k] = int(row["value"]) if row else days
    row = c.execute("SELECT value FROM meta WHERE key = 'holidays'").fetchone()
    extra = [h for h in (row["value"] if row else "").split(",") if h]
    return {"days": out, "holidays": extra}

def solar_holidays(jy):
    """The official holidays on fixed Jalali dates (Nowruz, 12 and 13 Farvardin, 14 and 15 Khordad, 22 Bahman,
    29 Esfand). Lunar holidays move every year and come from the settings."""
    days = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 12), (1, 13), (3, 14), (3, 15), (11, 22), (12, 29)]
    return {to_gregorian(jy, m, d).isoformat() for m, d in days}

def holidays(c, around=None):
    jy = to_jalali(around or today())[0]
    out = set().union(*(solar_holidays(y) for y in (jy - 1, jy, jy + 1)))
    for h in settings(c)["holidays"]:
        try:
            y, m, d = (int(x) for x in h.split("/"))
            out.add(to_gregorian(y, m, d).isoformat())
        except ValueError:
            pass
    return out

def deadline(served, days, off):
    """(the last day, why it moved or ""). served: ISO date of service; off: holiday ISO dates."""
    last = date.fromisoformat(served) + timedelta(days=days)
    why = []
    while last.weekday() == 4 or last.isoformat() in off:
        why.append("جمعه" if last.weekday() == 4 else "تعطیل رسمی")
        last += timedelta(days=1)
    return last.isoformat(), ("به‌خاطر " + " و ".join(dict.fromkeys(why)) + " یک روز کاری جلوتر رفت") if why else ""

def deadline_how(served, days, last, moved):
    lines = [f"تاریخ ابلاغ: {jfull(served)} (خود این روز شمرده نمی‌شود)", f"مهلت: {days} روز",
             f"= روز آخر: {jlong(last)} {jfull(last)}"]
    if moved:
        lines.insert(2, moved)
    return lines

# ---------- views ----------

def users(c):
    return {r["id"]: r["full_name"] for r in c.execute("SELECT id, full_name FROM users")}

def notice_view(n, case=None, names=None):
    n = dict(n)
    name, todo, _ = KINDS.get(n["kind"], (n["kind"], "", 0))
    out = n | {"kind_text": name, "todo": todo, "served_text": jfull(n["served"]) if n["served"] else "",
               "done_text": jfull(n["done_at"]) if n.get("done_at") else ""}
    if n["deadline"]:
        out |= {"deadline_text": jlong(n["deadline"]) + " " + jfull(n["deadline"]), "left": days_left(n["deadline"]), "left_text": left_text(n["deadline"])}
    if n["hearing"]:
        out |= {"hearing_text": f"{jlong(n['hearing'])} ساعت {n['hearing'][11:16]}", "left": days_left(n["hearing"]), "left_text": left_text(n["hearing"])}
    if case:
        out |= {"case_title": case["title"], "lawyer": (names or {}).get(case["lawyer_id"], "")}
    return out

def case_view(cs, names, client):
    cs = dict(cs)
    return cs | {"field_text": FIELDS.get(cs["field"], cs["field"]), "stage_text": STAGES.get(cs["stage"], cs["stage"]),
                 "lawyer": names.get(cs["lawyer_id"], ""), "client": client["name"] if client else "", "client_phone": client["phone"] if client else "",
                 "created_text": jfull(cs["created"])}

def last_action(c, case_id):
    row = c.execute("SELECT MAX(at) FROM events WHERE case_id = ? AND kind != 'view'", (case_id,)).fetchone()[0]
    return row[:10] if row else None

# ---------- what needs doing ----------

def alerts(c, user_id=None):
    """Today's work, most urgent first: deadlines passed or near, hearings today and tomorrow, idle cases, clients
    without a report. user_id: only the cases of this lawyer (the associate's own list)."""
    names, t, out = users(c), today(), []
    cases = {r["id"]: dict(r) for r in c.execute("SELECT * FROM cases WHERE status = 'open'")}
    mine = lambda cid: not user_id or cases.get(cid, {}).get("lawyer_id") == user_id
    for n in c.execute("SELECT * FROM notices WHERE status = 'open' AND deadline IS NOT NULL ORDER BY deadline"):
        cs = cases.get(n["case_id"])
        if not cs or not mine(cs["id"]):
            continue
        left = days_left(n["deadline"])
        name, todo, _ = KINDS[n["kind"]]
        if left < 0:
            out.append({"type": "overdue", "tone": "danger", "icon": "alert", "case_id": cs["id"], "notice_id": n["id"], "order": left,
                        "title": f"مهلت {todo} در پرونده‌ی «{cs['title']}» {left_text(n['deadline'])} تمام شد",
                        "detail": f"{name} ابلاغ‌شده در {jfull(n['served'])}. هنوز اقدامی ثبت نشده است. مسئول: {names.get(cs['lawyer_id'], '')}"})
        elif left <= 7:
            out.append({"type": "deadline", "tone": "danger" if left <= 3 else "warning", "icon": "clock", "case_id": cs["id"], "notice_id": n["id"], "order": left,
                        "title": f"{left_text(n['deadline'])}: آخرین روز {todo}، پرونده‌ی «{cs['title']}»",
                        "detail": f"روز آخر {jlong(n['deadline'])} {jfull(n['deadline'])}. {name} ابلاغ‌شده در {jfull(n['served'])}. مسئول: {names.get(cs['lawyer_id'], '')}"})
    end = (t + timedelta(days=2)).isoformat()
    for n in c.execute("SELECT * FROM notices WHERE kind = 'hearing' AND status = 'open' AND hearing >= ? AND hearing < ? ORDER BY hearing", (t.isoformat(), end)):
        cs = cases.get(n["case_id"])
        if cs and mine(cs["id"]):
            out.append({"type": "hearing", "tone": "info", "icon": "calendar", "case_id": cs["id"], "notice_id": n["id"], "order": days_left(n["hearing"]),
                        "title": f"جلسه‌ی دادگاه {left_text(n['hearing'])} ساعت {n['hearing'][11:16]}: «{cs['title']}»",
                        "detail": f"{cs['court']}، شعبه‌ی {cs['branch']}. مسئول: {names.get(cs['lawyer_id'], '')}"})
    for cs in cases.values():
        if not mine(cs["id"]):
            continue
        last = last_action(c, cs["id"]) or cs["created"]
        idle = (t - date.fromisoformat(last)).days
        if idle >= IDLE_DAYS and not c.execute("SELECT 1 FROM notices WHERE case_id = ? AND status = 'open'", (cs["id"],)).fetchone():
            out.append({"type": "idle", "tone": "secondary", "icon": "refresh", "case_id": cs["id"], "order": 50,
                        "title": f"{idle} روز است روی پرونده‌ی «{cs['title']}» کاری ثبت نشده است",
                        "detail": f"آخرین کار: {jfull(last)}. شاید وقت پیگیری از شعبه باشد. مسئول: {names.get(cs['lawyer_id'], '')}"})
        base = cs["last_report"] or cs["created"]
        gap = (t - date.fromisoformat(base)).days
        if gap >= REPORT_DAYS:
            client = c.execute("SELECT name FROM clients WHERE id = ?", (cs["client_id"],)).fetchone()
            out.append({"type": "report", "tone": "info", "icon": "message", "case_id": cs["id"], "order": 60,
                        "title": f"{gap} روز است {client['name'] if client else 'موکل'} از پرونده‌اش خبری نگرفته است",
                        "detail": f"پرونده‌ی «{cs['title']}». گزارش کوتاه وضعیت را دستیار آماده می‌کند."})
    return sorted(out, key=lambda a: a["order"])

def checks(c):
    """The owner's checks, from dates alone: deadlines that passed without action, actions done after the last day,
    notices entered days after their service. They say what happened and when, never blame."""
    names, out = users(c), []
    cases = {r["id"]: dict(r) for r in c.execute("SELECT * FROM cases")}
    for n in c.execute("SELECT * FROM notices WHERE deadline IS NOT NULL ORDER BY deadline DESC"):
        cs = cases.get(n["case_id"])
        if not cs:
            continue
        name, todo, _ = KINDS[n["kind"]]
        if n["status"] == "open" and days_left(n["deadline"]) < 0:
            out.append({"type": "missed", "tone": "danger", "case_id": cs["id"], "notice_id": n["id"],
                        "title": f"مهلت {todo} در «{cs['title']}» گذشت و اقدامی ثبت نشد",
                        "detail": f"روز آخر {jfull(n['deadline'])} بود. اگر کار انجام شده و فقط ثبت نشده، در پرونده ثبتش کنید.",
                        "how": [f"ابلاغ: {jfull(n['served'])}", f"ثبت ابلاغیه در دفتر: {jfull(n['entered'])}", f"روز آخر مهلت: {jfull(n['deadline'])}",
                                f"مسئول پرونده: {names.get(cs['lawyer_id'], '')}"]})
        elif n["status"] == "done" and n["done_at"] and n["done_at"][:10] > n["deadline"]:
            out.append({"type": "late", "tone": "warning", "case_id": cs["id"], "notice_id": n["id"],
                        "title": f"{todo} در «{cs['title']}» پس از روز آخر ثبت شد",
                        "detail": f"روز آخر {jfull(n['deadline'])} بود و اقدام در {jfull(n['done_at'])} ثبت شد.",
                        "how": [f"ابلاغ: {jfull(n['served'])}", f"روز آخر: {jfull(n['deadline'])}", f"ثبت اقدام: {jfull(n['done_at'])} · {names.get(n['done_by'], '')}"]})
        if n["entered"] and n["served"]:
            lag = (date.fromisoformat(n["entered"][:10]) - date.fromisoformat(n["served"])).days
            if lag >= LATE_ENTRY:
                out.append({"type": "entry", "tone": "info", "case_id": cs["id"], "notice_id": n["id"],
                            "title": f"ابلاغیه‌ی «{cs['title']}» {lag} روز پس از ابلاغ در دفتر ثبت شد",
                            "detail": f"از {KINDS[n['kind']][2] or 'مهلت'} روز مهلت، {lag} روز پیش از دیده شدن گذشته بود. ابلاغیه‌ها را هر روز از سامانه‌ی ثنا ببینید.",
                            "how": [f"ابلاغ: {jfull(n['served'])}", f"ثبت در دفتر: {jfull(n['entered'])} · {names.get(n['entered_by'], '')}"]})
    return out

def overview(c, user=None):
    t = today()
    week = (t + timedelta(days=7)).isoformat()
    open_cases = c.execute("SELECT COUNT(*) FROM cases WHERE status = 'open'").fetchone()[0]
    due = [dict(r) for r in c.execute("""SELECT n.*, k.title FROM notices n JOIN cases k ON k.id = n.case_id WHERE n.status = 'open'
                                         AND n.deadline IS NOT NULL AND n.deadline >= ? AND n.deadline <= ? ORDER BY n.deadline""", (t.isoformat(), week))]
    hearings = [dict(r) for r in c.execute("""SELECT n.*, k.title FROM notices n JOIN cases k ON k.id = n.case_id WHERE n.kind = 'hearing'
                                              AND n.status = 'open' AND n.hearing >= ? AND n.hearing <= ? ORDER BY n.hearing""", (t.isoformat(), week + " 23:59"))]
    overdue = [dict(r) for r in c.execute("""SELECT n.*, k.title FROM notices n JOIN cases k ON k.id = n.case_id WHERE n.status = 'open'
                                             AND n.deadline IS NOT NULL AND n.deadline < ?""", (t.isoformat(),))]
    by_field = {r["field"]: r["n"] for r in c.execute("SELECT field, COUNT(*) n FROM cases WHERE status = 'open' GROUP BY field")}
    stats = [
        {"label": "پرونده‌ی باز", "value": str(open_cases), "sub": "، ".join(f"{v} {FIELDS[k]}" for k, v in by_field.items()), "icon": "file", "tone": "primary",
         "how": [f"{FIELDS[k]}: {v}" for k, v in by_field.items()] + [f"= پرونده‌های باز: {open_cases}"]},
        {"label": "مهلت در هفت روز آینده", "value": str(len(due)), "sub": f"نزدیک‌ترین: {left_text(due[0]['deadline'])}" if due else "مهلتی نیست",
         "icon": "clock", "tone": "warning", "how": [f"{jfull(d['deadline'])} · {KINDS[d['kind']][1]} · {d['title']}" for d in due]},
        {"label": "جلسه در هفت روز آینده", "value": str(len(hearings)), "sub": f"نزدیک‌ترین: {left_text(hearings[0]['hearing'])}" if hearings else "جلسه‌ای نیست",
         "icon": "calendar", "tone": "info", "how": [f"{jfull(h['hearing'])} ساعت {h['hearing'][11:16]} · {h['title']}" for h in hearings]},
        {"label": "مهلت گذشته بی‌اقدام", "value": str(len(overdue)), "sub": "باید همین امروز بررسی شود" if overdue else "هیچ", "icon": "alert",
         "tone": "danger" if overdue else "success", "how": [f"{jfull(o['deadline'])} · {KINDS[o['kind']][1]} · {o['title']}" for o in overdue] or ["هیچ مهلتی بی‌اقدام نگذشته است"]},
    ]
    team = []
    for uid, name in users(c).items():
        role = c.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()["role"]
        if role == "secretary":
            continue
        team.append({"id": uid, "name": name,
                     "cases": c.execute("SELECT COUNT(*) FROM cases WHERE status = 'open' AND lawyer_id = ?", (uid,)).fetchone()[0],
                     "due": sum(1 for d in due if c.execute("SELECT lawyer_id FROM cases WHERE id = ?", (d["case_id"],)).fetchone()[0] == uid)})
    return {"today": jfull(t.isoformat()), "today_long": jlong(t.isoformat()), "stats": stats, "alerts": alerts(c), "team": team, "checks": len(checks(c))}

def brief_facts(c):
    o = overview(c)
    lines = [f"امروز: {o['today_long']} {o['today']}"] + [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]]
    lines += ["کارهای امروز به ترتیب فوریت:"] + [f"{i + 1}. {a['title']}" for i, a in enumerate(o["alerts"][:6])]
    return "\n".join(lines), o

def events(c, after=0, limit=40, case_id=None):
    q, args = "SELECT * FROM events WHERE id > ?", [after]
    if case_id:
        q += " AND case_id = ?"; args.append(case_id)
    rows = c.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit)).fetchall()
    t = today().isoformat()
    return [{"id": e["id"], "kind": e["kind"], "text": e["text"], "who": e["who"], "role": e["role"], "today": e["at"][:10] == t,
             "day": jday(e["at"]), "time": e["at"][11:16], "case_id": e["case_id"]} for e in rows]
