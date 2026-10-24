import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import db, students, checks
from auth import require_role
from llm import ask_llm
from manager import today
from db import LEVELS
from jalali import jstr

router = APIRouter(prefix="/parent")
parent_only = require_role("parent")
_reports = {}

def child(c, user):
    # A parent can only ever reach their own child: the id comes from the login, never from the request
    f = students.facts(c, user["ref_id"], today())
    if not f:
        raise HTTPException(status_code=404, detail="دانش‌آموز پیدا نشد")
    return f

@router.get("/child")
def my_child(user: dict = Depends(parent_only)):
    with db.conn() as c:
        f = child(c, user)
        suggestions = [dict(r) for r in c.execute(
            "SELECT for_parent, approved_at FROM suggestions WHERE student_id = ? AND status = 'approved' ORDER BY id DESC",
            (f["id"],))]
        messages = [dict(r) for r in c.execute(
            """SELECT id, title, body, created_at, read_at FROM notifications WHERE user_id = ? AND kind = 'referral'
               ORDER BY id DESC LIMIT 5""", (user["id"],))]
    # Private items stay with the counselor
    f.pop("notes", None)
    f.pop("signals", None)
    f["forms"] = {k: {"date": v["date"]} for k, v in f["forms"].items()}
    f["suggestions"], f["messages"] = suggestions, messages
    return f

def other_students(c, sid):
    """Full names of every other student. A text for this parent must not mention any of them."""
    return [r[0] for r in c.execute("SELECT first_name || ' ' || last_name FROM students WHERE id != ?", (sid,))]

def plain_report(f):
    """Short weekly report built by code, used when the model's text fails a check or the model is down."""
    best = max((p["now"] for p in f["progress"]), default=None)
    strong = [p["subject"] for p in f["progress"] if p["now"] == best]
    weak = [p["subject"] for p in f["progress"] if p["now"] <= 2]
    a = f["attendance"]
    text = f"{f['first_name']} در {'، '.join(strong)} وضعیت «{LEVELS[best]}» دارد. " if strong else ""
    if weak:
        text += f"{'، '.join(weak)} به تمرین بیشتری نیاز دارد. "
    return text + f"در ۳۰ روز اخیر {a['present']} روز حاضر بوده، {a['absent']} روز غیبت و {a['late']} بار تأخیر داشته است."

@router.get("/report")
def weekly_report(user: dict = Depends(parent_only)):
    with db.conn() as c:
        f = child(c, user)
        others = other_students(c, f["id"])
    key = (f["id"], today().isoformat())
    if key not in _reports:
        facts = students.facts_text(f, include_private=False)
        try:
            text = ask_llm(
                f"تو دبستان جاوید هستی و برای ولیِ {f['first_name']} یک گزارش کوتاه هفتگی می‌نویسی. "
                "سه یا چهار جمله ساده، گرم و محترمانه. اول نقطه‌های قوت را بگو، بعد درسی که نیاز به تمرین بیشتر دارد را بدون نگرانی‌افزایی بگو، "
                "و در پایان وضعیت حضور را با عدد بگو. هیچ تشخیص یا حدسی نزن و فقط از اطلاعات داده‌شده استفاده کن.",
                facts, max_tokens=260, temperature=0.3)
        except Exception:
            return {"text": plain_report(f)}   # model down: answer from code, and try the model again next time
        # numbers must come from the facts, and nothing a parent must not read (diagnosis, comparison, other children)
        if not checks.only_known_numbers(text, facts) or checks.unsafe_for_parent(text, others):
            text = plain_report(f)
        _reports[key] = text
    return {"text": _reports[key]}

@router.get("/forms/{kind}")
def get_form(kind: str, user: dict = Depends(parent_only)):
    if kind not in students.FORM_FIELDS:
        raise HTTPException(status_code=404, detail="فرم پیدا نشد")
    with db.conn() as c:
        r = c.execute("SELECT data, jdate FROM health_forms WHERE student_id = ? AND kind = ? ORDER BY id DESC LIMIT 1",
                      (user["ref_id"], kind)).fetchone()
    return {"fields": students.FORM_FIELDS[kind], "data": json.loads(r["data"]) if r else {}, "date": r["jdate"] if r else None}

class FormRequest(BaseModel):
    data: dict

@router.post("/forms/{kind}")
def save_form(kind: str, req: FormRequest, user: dict = Depends(parent_only)):
    if kind not in students.FORM_FIELDS:
        raise HTTPException(status_code=404, detail="فرم پیدا نشد")
    try:
        data = students.clean_form(kind, req.data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    flags = students.form_flags(kind, data)
    t = today()
    with db.conn() as c:
        c.execute("""INSERT INTO health_forms (student_id, kind, data, filled_by, date, jdate, created_at, flags)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (user["ref_id"], kind, json.dumps(data, ensure_ascii=False), user["id"], t.isoformat(), jstr(t),
                   db.stamp(), json.dumps(flags, ensure_ascii=False)))
        name = c.execute("SELECT first_name || ' ' || last_name FROM students WHERE id = ?", (user["ref_id"],)).fetchone()[0]
    title = "فرم سلامت جسمی" if kind == "physical" else "فرم حال و احوال"
    if flags:  # the counselor only hears about it when something needs attention
        db.notify(db.users_with("counselor"), "info", f"{title} {name} ثبت شد: {len(flags)} مورد قابل توجه", "، ".join(flags))
    return {"ok": True}
