"""Facts about one student, computed from the database. Used by the counselor and parent panels."""
import json
from datetime import date, timedelta
from db import LEVELS
from jalali import to_jalali, MONTHS

DROP = 2            # levels dropped (start of term vs now) that count as a decline
ABSENCES = 4        # unexcused absences in 14 days that count as a signal
FORM_FIELDS = {
    "physical": [
        ("height", "قد (سانتی‌متر)", "number"), ("weight", "وزن (کیلوگرم)", "number"),
        ("vision", "وضعیت بینایی", ["عادی", "ضعیف", "نمی‌دانم"]), ("glasses", "عینک", ["خیر", "بله"]),
        ("allergy", "حساسیت", "text"), ("condition", "بیماری یا شرایط خاص", "text"),
        ("medication", "داروی مصرفی", "text"), ("sleep_hours", "ساعت خواب شبانه", "number"),
        ("breakfast", "صبحانه", ["هر روز", "گاهی", "به‌ندرت"]),
    ],
    "wellbeing": [
        ("mood", "حال و حوصله در خانه", "scale"), ("sleep_quality", "کیفیت خواب", "scale"),
        ("school_worry", "نگرانی درباره مدرسه", "scale"), ("friends", "رابطه با دوستان", "scale"),
        ("screen_hours", "ساعت استفاده از صفحه نمایش در روز", "number"), ("note", "توضیح شما", "text"),
    ],
}

def jshort(iso):
    y, m, d = to_jalali(date.fromisoformat(iso))
    return f"{d} {MONTHS[m - 1]}"

NUMBER_RANGES = {"height": (40, 220), "weight": (5, 150), "sleep_hours": (0, 24), "screen_hours": (0, 24)}
TEXT_MAX = 500

def to_number(v):
    """'9', '۹', '8.5' or '۸٫۵' -> float. None if it isn't a number."""
    try:
        return float(str(v).strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٫/", "0123456789..")))
    except ValueError:
        return None

def clean_form(kind, data):
    """Check every answer against its question type. Returns the cleaned answers,
    or raises ValueError with a message the parent can read."""
    out = {}
    for key, label, typ in FORM_FIELDS[kind]:
        v = data.get(key)
        if v in (None, ""):
            continue
        if typ == "number":
            n, (lo, hi) = to_number(v), NUMBER_RANGES[key]
            if n is None or not lo <= n <= hi:
                raise ValueError(f"«{label}» باید عددی بین {lo} و {hi} باشد")
            out[key] = int(n) if n == int(n) else n
        elif typ == "scale":
            n = to_number(v)
            if n not in (1, 2, 3, 4, 5):
                raise ValueError(f"برای «{label}» یکی از گزینه‌های ۱ تا ۵ را انتخاب کنید")
            out[key] = int(n)
        elif typ == "text":
            out[key] = str(v).strip()[:TEXT_MAX]
        else:  # a list of options
            if v not in typ:
                raise ValueError(f"برای «{label}» یکی از گزینه‌ها را انتخاب کنید")
            out[key] = v
    return out

def form_flags(kind, data):
    """Simple, explainable rules. The model never decides these."""
    flags = []
    if kind == "physical":
        sleep = to_number(data.get("sleep_hours", ""))
        if sleep is not None and sleep < 9:
            flags.append("خواب کمتر از ۹ ساعت")
        if data.get("vision") == "ضعیف" and data.get("glasses") == "خیر":
            flags.append("بینایی ضعیف بدون عینک")
        if data.get("breakfast") == "به‌ندرت":
            flags.append("صبحانه نمی‌خورد")
    else:
        scale = lambda k, default: to_number(data.get(k) or default) or default
        if scale("mood", 5) <= 2:
            flags.append("حال و حوصله پایین")
        if scale("school_worry", 1) >= 4:
            flags.append("نگرانی زیاد درباره مدرسه")
        if scale("sleep_quality", 5) <= 2:
            flags.append("خواب نامناسب")
        if scale("friends", 5) <= 2:
            flags.append("مشکل در رابطه با دوستان")
    return flags

def facts(c, sid, today):
    s = c.execute("""SELECT s.*, cl.name AS class, t.full_name AS teacher FROM students s
                     JOIN classes cl ON cl.id = s.class_id JOIN teachers t ON t.id = cl.homeroom_teacher_id
                     WHERE s.id = ?""", (sid,)).fetchone()
    if not s:
        return None
    subjects = {}
    for r in c.execute("SELECT subject, date, level, note FROM assessments WHERE student_id = ? ORDER BY date", (sid,)):
        subjects.setdefault(r["subject"], []).append({"date": jshort(r["date"]), "level": r["level"], "note": r["note"]})
    progress = []
    for sub, rows in subjects.items():
        start = sum(r["level"] for r in rows[:2]) / min(2, len(rows))
        now = sum(r["level"] for r in rows[-2:]) / min(2, len(rows))
        progress.append({"subject": sub, "points": [r["level"] for r in rows], "dates": [r["date"] for r in rows],
                         "now": rows[-1]["level"], "now_label": LEVELS[rows[-1]["level"]],
                         "change": round(now - start, 1), "note": next((r["note"] for r in reversed(rows) if r["note"]), None)})

    since30, since14 = (today - timedelta(days=30)).isoformat(), (today - timedelta(days=14)).isoformat()
    att = c.execute("""SELECT SUM(status != 'absent') AS present, SUM(status = 'absent') AS absent,
                              SUM(status = 'late') AS late, SUM(status = 'absent' AND excused = 0) AS unexcused
                       FROM student_attendance WHERE student_id = ? AND date > ? AND date <= ?""",
                    (sid, since30, today.isoformat())).fetchone()
    absent_days = [{"date": jshort(r["date"]), "excused": bool(r["excused"])} for r in c.execute(
        "SELECT date, excused FROM student_attendance WHERE student_id = ? AND status = 'absent' AND date > ? ORDER BY date DESC",
        (sid, since30))]
    recent_unexcused = c.execute("""SELECT COUNT(*) FROM student_attendance WHERE student_id = ? AND status = 'absent'
                                    AND excused = 0 AND date > ?""", (sid, since14)).fetchone()[0]
    forms = {}
    for r in c.execute("SELECT * FROM health_forms WHERE student_id = ? ORDER BY id", (sid,)):
        data = json.loads(r["data"])
        forms[r["kind"]] = {"date": jshort(r["date"]), "data": data, "flags": form_flags(r["kind"], data),
                            "summary": r["ai_summary"]}
    notes = [{"date": jshort(r["date"]), "note": r["note"]} for r in c.execute(
        "SELECT date, note FROM counselor_notes WHERE student_id = ? ORDER BY date DESC", (sid,))]

    signals = []
    for p in progress:
        if p["change"] <= -DROP:
            signals.append({"type": "grade", "text": f"افت در {p['subject']}"})
    if recent_unexcused >= ABSENCES:
        signals.append({"type": "absence", "text": f"{recent_unexcused} غیبت غیرموجه در دو هفته"})
    for kind in ("physical", "wellbeing"):
        for f in forms.get(kind, {}).get("flags", []):
            signals.append({"type": "health", "text": f})

    return {
        "id": s["id"], "name": f"{s['first_name']} {s['last_name']}", "first_name": s["first_name"],
        "class": s["class"], "teacher": s["teacher"], "parent_name": s["parent_name"],
        "progress": progress, "signals": signals, "notes": notes, "forms": forms,
        "attendance": {"present": att["present"] or 0, "absent": att["absent"] or 0, "late": att["late"] or 0,
                       "unexcused": att["unexcused"] or 0, "absent_days": absent_days},
    }

def facts_text(f, include_private=False):
    """Plain-text facts for the model. Private items (counselor notes, health flags) only for the counselor."""
    lines = [f"دانش‌آموز: {f['name']}، کلاس {f['class']}، آموزگار: {f['teacher']}"]
    for p in f["progress"]:
        trend = "، ".join(LEVELS[x] for x in p["points"])
        lines.append(f"{p['subject']}: {trend}" + (f" (یادداشت آموزگار: {p['note']})" if p["note"] else ""))
    a = f["attendance"]
    lines.append(f"حضور در ۳۰ روز اخیر: {a['present']} روز حاضر، {a['absent']} غیبت ({a['unexcused']} غیرموجه)، {a['late']} تأخیر")
    if include_private:
        for n in f["notes"]:
            lines.append(f"یادداشت مشاور ({n['date']}): {n['note']}")
        for kind, form in f["forms"].items():
            name = "فرم سلامت جسمی" if kind == "physical" else "فرم حال و احوال"
            lines.append(f"{name} ({form['date']}): " + ("، ".join(form["flags"]) or "مورد قابل توجهی ندارد")
                         + (f". توضیح ولی: {form['data'].get('note')}" if form["data"].get("note") else ""))
    return "\n".join(lines)
