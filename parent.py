import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import db, students
from auth import require_role
from llm import ask_llm
from manager import today
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

@router.get("/report")
def weekly_report(user: dict = Depends(parent_only)):
    with db.conn() as c:
        f = child(c, user)
    key = (f["id"], today().isoformat())
    if key not in _reports:
        _reports[key] = ask_llm(
            f"تو دبستان جاوید هستی و برای ولیِ {f['first_name']} یک گزارش کوتاه هفتگی می‌نویسی. "
            "سه یا چهار جمله ساده، گرم و محترمانه. اول نقطه‌های قوت را بگو، بعد درسی که نیاز به تمرین بیشتر دارد را بدون نگرانی‌افزایی بگو، "
            "و در پایان وضعیت حضور را با عدد بگو. هیچ تشخیص یا حدسی نزن و فقط از اطلاعات داده‌شده استفاده کن.",
            students.facts_text(f, include_private=False), max_tokens=260, temperature=0.3)
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
    allowed = {f[0] for f in students.FORM_FIELDS[kind]}
    data = {k: v for k, v in req.data.items() if k in allowed}
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
