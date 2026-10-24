import os
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import db
from auth import require_role
from llm import ask_llm
from jalali import jstr, to_jalali, MONTHS

router = APIRouter(prefix="/manager")
manager_only = require_role("manager")

ARRIVAL = "07:30"         # teachers must arrive by this time
LATE_LIMIT = 3            # lates in one month before a written warning
ABSENCE_LIMIT = 4         # unexcused absences in 14 days before an alert
DEADLINE_DAYS = 5         # letters due within this many days

def today():
    return date.fromisoformat(os.getenv("DEMO_TODAY", date.today().isoformat()))

def jdate_long(d):
    y, m, dd = to_jalali(d)
    return f"{dd} {MONTHS[m - 1]} {y}"

def jdate_short(d):
    y, m, dd = to_jalali(d)
    return f"{dd} {MONTHS[m - 1]}"

def collect(c):
    """Everything the manager page needs, computed from the database."""
    t = today()
    t_iso, month = t.isoformat(), jstr(t)[:7]

    rows = c.execute("SELECT status, COUNT(*) n FROM student_attendance WHERE date = ? GROUP BY status", (t_iso,)).fetchall()
    st = {r["status"]: r["n"] for r in rows}
    total_students = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]

    late_today = c.execute("""SELECT t.full_name, a.check_in FROM teacher_attendance a JOIN teachers t ON t.id = a.teacher_id
                              WHERE a.date = ? AND a.check_in > ?""", (t_iso, ARRIVAL)).fetchall()

    open_letters = c.execute("SELECT COUNT(*) FROM letters WHERE status NOT IN ('done', 'forwarded')").fetchone()[0]

    alerts = []
    # 1. Teachers who reached the late limit this month
    late_rows = c.execute("""SELECT t.id, t.full_name, t.subject, a.date, a.check_in
                             FROM teacher_attendance a JOIN teachers t ON t.id = a.teacher_id
                             WHERE a.jdate LIKE ? AND a.check_in > ? ORDER BY a.date""",
                          (month + "%", ARRIVAL)).fetchall()
    by_teacher = {}
    for r in late_rows:
        by_teacher.setdefault(r["id"], []).append(r)
    for tid, rows in by_teacher.items():
        if len(rows) < LATE_LIMIT:
            continue
        r0 = rows[0]
        dates = "، ".join(f"{jdate_short(date.fromisoformat(r['date']))} ساعت {r['check_in'].lstrip('0')}" for r in rows)
        issued = c.execute("SELECT date, acknowledged_at FROM warnings WHERE teacher_id = ? AND jdate LIKE ?",
                           (tid, month + "%")).fetchone()
        done_text = None
        if issued:
            done_text = f"تذکر کتبی در {jdate_short(date.fromisoformat(issued['date']))} صادر شد. "
            done_text += f"رؤیت شد: {issued['acknowledged_at']}" if issued["acknowledged_at"] else "هنوز رؤیت نشده"
        alerts.append({
            "type": "teacher_late", "teacher_id": tid,
            "title": f"{r0['full_name']} این ماه {len(rows)} بار دیر آمده است",
            "detail": f"معلم {r0['subject']}. تأخیرها: {dates}",
            "dates": dates, "count": len(rows), "name": r0["full_name"],
        "facts": [(to_jalali(date.fromisoformat(r["date"]))[2], r["check_in"].lstrip("0")) for r in rows],
            "done": bool(issued),
            "done_text": done_text,
        })
    # 2. Students with many unexcused absences in the last 14 days
    since = (t - timedelta(days=14)).isoformat()
    for r in c.execute("""SELECT s.first_name || ' ' || s.last_name AS name, cl.name AS class, COUNT(*) AS n
                          FROM student_attendance a JOIN students s ON s.id = a.student_id JOIN classes cl ON cl.id = s.class_id
                          WHERE a.status = 'absent' AND a.excused = 0 AND a.date >= ? GROUP BY s.id HAVING n >= ?""",
                       (since, ABSENCE_LIMIT)).fetchall():
        alerts.append({
            "type": "student_absent", "title": f"{r['name']} در دو هفته اخیر {r['n']} غیبت غیرموجه داشته است",
            "detail": f"کلاس {r['class']}. موضوع برای پیگیری به مشاور ارجاع شده است.", "done": False,
        })
    # 3. Letters the agent sent to the manager for a decision
    for r in c.execute("SELECT id, subject, summary, action FROM letters WHERE status = 'needs_manager'").fetchall():
        alerts.append({"type": "letter_decision", "letter_id": r["id"], "title": f"نیاز به تصمیم شما: {r['subject']}",
                       "detail": f"{r['summary']} پیشنهاد دستیار: {r['action']}", "done": False})
    # 4. Letters with a close deadline
    until = (t + timedelta(days=DEADLINE_DAYS)).isoformat()
    for r in c.execute("""SELECT subject, deadline FROM letters WHERE status IN ('new', 'todo', 'awaiting_approval') AND deadline BETWEEN ? AND ?
                          ORDER BY deadline""", (t_iso, until)).fetchall():
        alerts.append({"type": "letter_deadline", "title": f"مهلت نامه «{r['subject']}» نزدیک است",
                       "detail": f"مهلت پاسخ: {jdate_short(date.fromisoformat(r['deadline']))}", "done": False})

    # Attendance rate for the last 10 school days (for the chart)
    trend = [{"jdate": r["jdate"][5:], "rate": round(100 * r["here"] / r["total"])}
             for r in c.execute("""SELECT jdate, SUM(status != 'absent') AS here, COUNT(*) AS total
                                   FROM student_attendance WHERE date <= ? GROUP BY date ORDER BY date DESC LIMIT 10""",
                                (t_iso,)).fetchall()][::-1]

    return {
        "today": jdate_long(t),
        "students": {"total": total_students, "present": st.get("present", 0) + st.get("late", 0),
                     "absent": st.get("absent", 0), "late": st.get("late", 0)},
        "late_teachers": [dict(r) for r in late_today],
        "open_letters": open_letters,
        "alerts": alerts,
        "trend": trend,
    }

@router.get("/overview")
def overview(user: dict = Depends(manager_only)):
    with db.conn() as c:
        return collect(c)

_briefing_cache = {}

@router.get("/briefing")
def briefing(user: dict = Depends(manager_only)):
    key = today().isoformat()
    if key not in _briefing_cache:
        with db.conn() as c:
            d = collect(c)
        actions = [a["title"] for a in d["alerts"] if not a.get("done")]
        facts = (
            f"تاریخ: {d['today']}\n"
            f"حضور: {d['students']['present']} از {d['students']['total']} دانش‌آموز، {d['students']['absent']} غایب\n"
            f"تأخیر معلمان امروز: {len(d['late_teachers'])}\n"
            f"نامه‌های باز: {d['open_letters']}\n"
            "موارد نیازمند اقدام، به ترتیب اهمیت:\n" + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(actions))
        )
        _briefing_cache[key] = ask_llm(
            "تو دستیار مدیر یک دبستان هستی. از روی اطلاعات زیر یک خلاصه صبحگاهی دو یا سه جمله‌ای به فارسی روان بنویس.\n"
            "قوانین:\n"
            "- جمله اول درباره مورد شماره ۱ باشد و اسم شخص یا نامه را دقیق بیاورد.\n"
            "- جمله دوم دو مورد مهم بعدی را با اسم بگوید.\n"
            "- در پایان وضعیت حضور امروز را با عدد بگو.\n"
            "- کلی‌گویی نکن. فقط از اسم‌ها و عددهای داده‌شده استفاده کن. سلام ننویس.\n"
            "مثال لحن: «تأخیرهای خانم الف این ماه به سه بار رسیده و منتظر تصمیم شماست. مهلت نامه ب و پیگیری غیبت‌های ج هم نزدیک است. امروز ۲۸ نفر از ۳۰ دانش‌آموز حاضرند.»",
            facts, max_tokens=220, temperature=0.2)
    return {"text": _briefing_cache[key]}

class DraftRequest(BaseModel):
    teacher_id: int

@router.post("/warnings/draft")
def draft_warning(req: DraftRequest, user: dict = Depends(manager_only)):
    with db.conn() as c:
        alert = next((a for a in collect(c)["alerts"] if a.get("teacher_id") == req.teacher_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="هشداری برای این معلم پیدا نشد")
    text = ask_llm(
        "تو دستیار مدیر یک دبستان هستی. یک تذکر کتبی کوتاه، رسمی و محترمانه به فارسی برای یک معلم بنویس. "
        "ساختار: «همکار گرامی، خانم ...»، بیان تأخیرها با تاریخ و ساعت دقیق، یادآوری اینکه ساعت حضور ۷:۳۰ است، "
        "درخواست رعایت در ادامه، و در پایان «با احترام، مدیریت دبستان جاوید». "
        "فقط از تاریخ‌ها و ساعت‌های داده‌شده استفاده کن. لحن تهدیدآمیز نباشد.",
        f"نام معلم: {alert['name']}\nتعداد تأخیر این ماه: {alert['count']}\nتأخیرها: {alert['dates']}",
        max_tokens=350, temperature=0.3)
    # Check the draft against the database: every late day and time must appear in the text
    import stats
    plain = stats.to_en(text)
    missing = [f"{day} آذر ساعت {time}" for day, time in alert["facts"]
               if str(day) not in plain or time not in plain]
    return {"text": text, "verified": not missing, "missing": missing}

class IssueRequest(BaseModel):
    teacher_id: int
    text: str

@router.post("/warnings")
def issue_warning(req: IssueRequest, user: dict = Depends(manager_only)):
    t = today()
    with db.conn() as c:
        cur = c.execute("INSERT INTO warnings (teacher_id, text, date, jdate, issued_by) VALUES (?, ?, ?, ?, ?)",
                        (req.teacher_id, req.text.strip(), t.isoformat(), jstr(t), user["id"]))
        warning_id = cur.lastrowid
    # Deliver it to the teacher's inbox; they must press "seen"
    db.notify(db.users_with("teacher", req.teacher_id), "warning", "تذکر کتبی از مدیریت",
              req.text.strip(), ref_type="warning", ref_id=warning_id, needs_ack=True)
    _briefing_cache.clear()  # the morning summary should reflect this
    return {"ok": True}


class DecideRequest(BaseModel):
    approve: bool

@router.post("/letters/{lid}/decide")
def decide(lid: int, req: DecideRequest, user: dict = Depends(manager_only)):
    word = "موافقت" if req.approve else "مخالفت"
    with db.conn() as c:
        row = c.execute("SELECT subject FROM letters WHERE id = ? AND status = 'needs_manager'", (lid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="نامه پیدا نشد")
        c.execute("UPDATE letters SET status = 'todo', action = ? WHERE id = ?",
                  (f"مدیر {word} کرد. نتیجه به فرستنده اعلام شود.", lid))
        c.execute("INSERT INTO agent_log (letter_id, action, reason, created_at) VALUES (?, ?, ?, ?)",
                  (lid, f"مدیر با «{row['subject']}» {word} کرد", "تصمیم مدیر ثبت و کار اعلام نتیجه به دفتر سپرده شد.", db.stamp()))
    db.notify(db.users_with("staff"), "letter", f"مدیر با «{row['subject']}» {word} کرد", "لطفا نتیجه را به فرستنده اعلام کنید.")
    _briefing_cache.clear()
    return {"ok": True}
