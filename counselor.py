from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import db, students
from auth import require_role
from llm import ask_llm, ask_json
from manager import today
from jalali import jstr

router = APIRouter(prefix="/counselor")
counselor_only = require_role("counselor", "manager")
_insights = {}   # cache: same student + same day + same signals -> same text

def load(c, sid):
    f = students.facts(c, sid, today())
    if not f:
        raise HTTPException(status_code=404, detail="دانش‌آموز پیدا نشد")
    return f

@router.get("/students")
def all_students(user: dict = Depends(counselor_only)):
    with db.conn() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM students ORDER BY class_id, last_name")]
        rows = [students.facts(c, sid, today()) for sid in ids]
        pending = {r[0] for r in c.execute("SELECT student_id FROM suggestions WHERE status = 'approved'")}
    out = [{"id": f["id"], "name": f["name"], "class": f["class"], "signals": f["signals"],
            "has_suggestion": f["id"] in pending} for f in rows]
    return sorted(out, key=lambda s: -len(s["signals"]))

@router.get("/students/{sid}")
def profile(sid: int, user: dict = Depends(counselor_only)):
    with db.conn() as c:
        f = load(c, sid)
        f["suggestions"] = [dict(r) for r in c.execute(
            "SELECT * FROM suggestions WHERE student_id = ? AND status != 'dismissed' ORDER BY id DESC", (sid,))]
    f["fields"] = students.FORM_FIELDS
    return f

@router.get("/students/{sid}/insight")
def insight(sid: int, user: dict = Depends(counselor_only)):
    with db.conn() as c:
        f = load(c, sid)
    key = (sid, today().isoformat(), tuple(s["text"] for s in f["signals"]), len(f["notes"]))
    if key not in _insights:
        if not f["signals"]:
            _insights[key] = "نشانه قابل توجهی در نمره‌ها، حضور یا فرم‌ها دیده نمی‌شود."
        else:
            _insights[key] = ask_llm(
                "تو دستیار مشاور یک دبستان هستی. از روی اطلاعات زیر، در دو جمله کوتاه بگو چه چیزی تغییر کرده و "
                "چه نشانه‌هایی ممکن است به هم ربط داشته باشند. تشخیص پزشکی یا روان‌شناختی نده و از «ممکن است» استفاده کن. "
                "فقط از اطلاعات داده‌شده استفاده کن.",
                students.facts_text(f, include_private=True), max_tokens=180)
    return {"text": _insights[key]}

class NoteRequest(BaseModel):
    note: str

@router.post("/students/{sid}/notes")
def add_note(sid: int, req: NoteRequest, user: dict = Depends(counselor_only)):
    if not req.note.strip():
        raise HTTPException(status_code=400, detail="یادداشت خالی است")
    t = today()
    with db.conn() as c:
        load(c, sid)
        c.execute("INSERT INTO counselor_notes (student_id, date, jdate, note) VALUES (?, ?, ?, ?)",
                  (sid, t.isoformat(), jstr(t), req.note.strip()))
    return {"ok": True}

@router.post("/students/{sid}/suggest")
def draft_suggestion(sid: int, user: dict = Depends(counselor_only)):
    with db.conn() as c:
        f = load(c, sid)
    r = ask_json(
        "تو دستیار مشاور یک دبستان هستی. از روی اطلاعات زیر دو متن بنویس:\n"
        "for_counselor: یک یا دو گام عملی و مشخص برای خود مشاور (مثلا گفت‌وگو با آموزگار درباره موضوعی مشخص).\n"
        f"for_parent: پیامی سه تا چهار جمله‌ای، گرم و محترمانه برای ولیِ {f['first_name']}. اول یک نقطه قوت واقعی بگو، "
        "بعد موضوع را بدون سرزنش و بدون تشخیص پزشکی بیان کن، یک کار ساده و عملی در خانه پیشنهاد بده و برای گفت‌وگو با مشاور دعوت کن. "
        "یادداشت‌های مشاور و جزئیات فرم‌ها را عینا نقل نکن.\n"
        "فقط از اطلاعات داده‌شده استفاده کن.",
        students.facts_text(f, include_private=True), max_tokens=450) or {}
    for_counselor, for_parent = (r.get("for_counselor") or "").strip(), (r.get("for_parent") or "").strip()
    if not for_parent:
        raise HTTPException(status_code=503, detail="دستیار نتوانست پیشنهاد بنویسد. دوباره امتحان کنید.")
    with db.conn() as c:
        cur = c.execute("INSERT INTO suggestions (student_id, for_counselor, for_parent, status, created_at) VALUES (?, ?, ?, 'draft', ?)",
                        (sid, for_counselor, for_parent, db.stamp()))
        return dict(c.execute("SELECT * FROM suggestions WHERE id = ?", (cur.lastrowid,)).fetchone())

class ApproveRequest(BaseModel):
    for_counselor: str = ""
    for_parent: str

@router.post("/suggestions/{gid}/approve")
def approve(gid: int, req: ApproveRequest, user: dict = Depends(counselor_only)):
    if not req.for_parent.strip():
        raise HTTPException(status_code=400, detail="متن پیام ولی خالی است")
    with db.conn() as c:
        g = c.execute("SELECT * FROM suggestions WHERE id = ?", (gid,)).fetchone()
        if not g:
            raise HTTPException(status_code=404, detail="پیشنهاد پیدا نشد")
        c.execute("""UPDATE suggestions SET for_counselor = ?, for_parent = ?, status = 'approved', approved_at = ?, approved_by = ?
                     WHERE id = ?""", (req.for_counselor.strip(), req.for_parent.strip(), db.stamp(), user["id"], gid))
        name = c.execute("SELECT first_name FROM students WHERE id = ?", (g["student_id"],)).fetchone()[0]
    db.notify(db.users_with("parent", g["student_id"]), "suggestion", f"پیام مشاور مدرسه درباره {name}",
              req.for_parent.strip(), ref_type="suggestion", ref_id=gid)
    return {"ok": True}

@router.post("/suggestions/{gid}/dismiss")
def dismiss(gid: int, user: dict = Depends(counselor_only)):
    with db.conn() as c:
        c.execute("UPDATE suggestions SET status = 'dismissed' WHERE id = ? AND status = 'draft'", (gid,))
    return {"ok": True}
