import re, threading
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import db, stats, checks
from auth import require_role
from llm import ask_llm, ask_json
from jalali import MONTHS, to_jalali, to_gregorian, jstr
from manager import today, jdate_short, _briefing_cache

router = APIRouter(prefix="/staff")
staff_or_manager = require_role("staff", "manager")
_lock = threading.Lock()   # two browsers must never process the same letter

CATEGORIES = {
    "ack": "اعلام وصول", "stats": "درخواست آمار", "meeting": "دعوت به جلسه",
    "info": "برای اطلاع", "decision": "نیازمند تصمیم مدیر", "request": "نیازمند اقدام",
}
STATUS = {
    "new": "در صف", "processing": "در حال بررسی", "done": "بسته شد",
    "awaiting_approval": "منتظر تأیید شما", "todo": "نیازمند اقدام شما",
    "needs_manager": "ارجاع به مدیر", "forwarded": "ارسال به مدیر",
}
SIGN = "با احترام، مدیریت دبستان جاوید"

CLASSIFY = """تو دستیار دفتر اداری یک دبستان هستی. یک نامه رسیده را بخوان و دسته‌بندی کن.
دسته‌ها:
- ack: فقط وقتی که در متن نامه صریحا عبارت «اعلام وصول» یا «وصول ... را اعلام کنید» آمده باشد.
- stats: نامه آمار یا عدد خواسته است.
- meeting: خود مدیر به جلسه‌ای دعوت شده و باید حاضر شود.
- info: بخشنامه یا اطلاعیه‌ای که فقط برای اطلاع است و نه اعلام وصول می‌خواهد نه اقدامی از دفتر.
- decision: پیشنهاد، قرارداد، هزینه یا موضوعی که تصمیم مدیر لازم دارد.
- request: یک کار مشخص از دفتر خواسته شده، معمولا با مهلت (معرفی فرد یا شرکت‌کننده، ارسال فهرست، تغییر چیزی).
نکته: اگر نامه درباره کارگاه یا برنامه‌ای است و از مدرسه خواسته شرکت‌کننده معرفی کند، request است نه meeting.
کلیدها:
- category: یکی از شش مقدار بالا
- subject: عنوان کوتاه نامه در حداکثر ده کلمه
- summary: یک جمله کوتاه فارسی
- action: کاری که باید انجام شود یا پیشنهاد تو، یک جمله
- deadline: اگر در نامه مهلتی آمده، فقط روز و ماه آن مثل «5 دی»؛ اگر مهلتی نیست null
مثال: {"category": "ack", "subject": "بخشنامه زمان ثبت‌نام", "summary": "بخشنامه زمان ثبت‌نام که اعلام وصول می‌خواهد.", "action": "اعلام وصول ثبت شود.", "deadline": null}"""

def log(c, letter_id, action, reason):
    c.execute("INSERT INTO agent_log (letter_id, action, reason, created_at) VALUES (?, ?, ?, ?)",
              (letter_id, action, reason, db.stamp()))

def guess_month(text):
    for i, name in enumerate(MONTHS):
        if name in text:
            return i + 1
    return None

def draft_stats_reply(c, letter):
    text = letter["subject"] + " " + letter["body"]
    month = guess_month(letter["subject"])
    data = stats.absence_text(c, month) if ("غیبت" in text and month) else stats.students_text(c)
    example = c.execute("SELECT reply FROM letters WHERE category = 'stats' AND reply IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
    fallback = f"با سلام و احترام\nدر پاسخ به نامه شما، {data}\n{SIGN}"
    reply = ask_llm(
        "تو کارمند دفتر یک دبستان هستی. برای نامه زیر یک پاسخ اداری کوتاه بنویس. "
        "دقیقا همان قالب و لحن «پاسخ قبلی» را رعایت کن و فقط از عددهای «داده‌ها» استفاده کن. هیچ عددی را تغییر نده.",
        f"نامه: {letter['subject']}\n\nپاسخ قبلی مدرسه به نامه مشابه:\n{example['reply'] if example else fallback}\n\nداده‌ها:\n{data}",
        max_tokens=300)
    # Safety check: after each grade the draft must have exactly that grade's numbers, and no number
    # that isn't in the data. Otherwise use the plain template with the database numbers.
    if not reply or not checks.grade_lines_match(reply, data) or not checks.only_known_numbers(reply, data):
        return stats.to_fa(fallback), "پیش‌نویس مدل عددها را دقیق نیاورد؛ از قالب ثابت با عددهای پایگاه داده استفاده شد."
    return stats.to_fa(reply), "پاسخ با قالب پاسخ‌های قبلی و عددهای واقعی پایگاه داده نوشته شد."

def parse_deadline(text):
    """'5 دی' -> date, using the demo year. Returns None if it can't be read."""
    if not text:
        return None
    text = stats.to_en(str(text))
    day = re.search(r"\d{1,2}", text)
    month = guess_month(text)
    if not day or not month:
        return None
    year, this_month, _ = to_jalali(today())
    if month < this_month:          # e.g. a Farvardin deadline written in Azar belongs to next year
        year += 1
    try:
        return to_gregorian(year, month, int(day.group(0)))
    except Exception:
        return None

def handle(letter):
    """Run the agent on one letter. Returns the updated letter."""
    lid = letter["id"]
    with db.conn() as c:
        fixed = c.execute("""SELECT subject, body, category FROM letters WHERE corrected = 1
                             ORDER BY handled_at DESC LIMIT 5""").fetchall()
    lessons = ""
    if fixed:
        lessons = "\nنمونه‌هایی که کارمند مدرسه دسته‌شان را اصلاح کرده (از این‌ها یاد بگیر):\n" + "\n".join(
            f"- «{f['subject']}: {f['body'][:120]}» ← {f['category']}" for f in fixed)
    result = ask_json(CLASSIFY + lessons, f"فرستنده: {letter['sender']}\nموضوع: {letter['subject']}\nمتن: {letter['body']}") or {}
    category = result.get("category") if result.get("category") in CATEGORIES else "request"
    # Safety rule: acknowledgements are closed automatically, so only accept "ack" when the letter really asks for it
    if category == "ack" and "وصول" not in letter["body"]:
        category = "info"
    summary = (result.get("summary") or letter["subject"]).strip()
    action = (result.get("action") or "").strip()
    # Letters typed in by staff may have no subject or deadline yet: take them from the model
    if not letter["subject"]:
        letter["subject"] = (result.get("subject") or summary)[:120]
    if not letter["deadline"]:
        d = parse_deadline(result.get("deadline"))
        if d and d >= today():
            letter["deadline"] = d.isoformat()
    staff_ids, manager_ids = db.users_with("staff"), db.users_with("manager")
    reply, status = None, "todo"
    outbox = []   # notifications are sent after the database write finishes (SQLite allows one writer at a time)
    def notify(*args):
        outbox.append(args)

    with db.conn() as c:
        log(c, lid, f"نامه را خواند و در دسته «{CATEGORIES[category]}» گذاشت", summary)
        if category == "ack":
            reply = f"با سلام و احترام\nوصول «{letter['subject']}» بدین‌وسیله اعلام می‌گردد.\n{SIGN}"
            status = "done"
            log(c, lid, "پاسخ اعلام وصول را خودکار ثبت کرد و نامه را بست",
                "اعلام وصول کاری تکراری و بدون ریسک است و تأیید انسانی لازم ندارد.")
        elif category == "stats":
            reply, why = draft_stats_reply(c, letter)
            status = "awaiting_approval"
            log(c, lid, "عددها را از پایگاه داده حساب کرد و پیش‌نویس پاسخ نوشت", why)
            notify(staff_ids, "letter", f"پیش‌نویس پاسخ «{letter['subject']}» آماده تأیید است", summary)
        elif category == "meeting":
            status = "forwarded"
            log(c, lid, "دعوت را برای مدیر فرستاد", "حضور در جلسه با مدیر است.")
            notify(manager_ids, "letter", f"دعوت به جلسه: {letter['subject']}", summary)
        elif category == "info":
            status = "done"
            log(c, lid, "خلاصه را ثبت و نامه را بایگانی کرد", "نامه فقط برای اطلاع است و اقدامی نمی‌خواهد.")
        elif category == "decision":
            status = "needs_manager"
            log(c, lid, "نامه را با خلاصه و پیشنهاد به مدیر ارجاع داد",
                "تصمیم‌های مالی و اداری فقط با مدیر است؛ دستیار فقط پیشنهاد می‌دهد.")
            notify(manager_ids, "letter", f"نیاز به تصمیم شما: {letter['subject']}", f"{summary}\nپیشنهاد دستیار: {action}")
        else:
            status = "todo"
            log(c, lid, "کار را برای کارمند اداری ثبت کرد", action or "این نامه یک اقدام مشخص از دفتر می‌خواهد.")
            notify(staff_ids, "letter", f"کار جدید: {letter['subject']}", action)

        # Deadline reminder for anything still open
        if status in ("todo", "awaiting_approval") and letter["deadline"]:
            days = (date.fromisoformat(letter["deadline"]) - today()).days
            if days <= 3:
                notify(staff_ids, "reminder", f"یادآوری: مهلت «{letter['subject']}» {jdate_short(date.fromisoformat(letter['deadline']))} است",
                          action)
                log(c, lid, "برای مهلت نزدیک یادآوری فرستاد", f"تا پایان مهلت {days} روز مانده است.")

        c.execute("""UPDATE letters SET status = ?, category = ?, summary = ?, action = ?, reply = ?, handled_at = ?,
                            subject = ?, deadline = ?, jdeadline = ? WHERE id = ?""",
                  (status, category, summary, action, reply, db.stamp(), letter["subject"], letter["deadline"],
                   jstr(date.fromisoformat(letter["deadline"])) if letter["deadline"] else None, lid))
        updated = dict(c.execute("SELECT * FROM letters WHERE id = ?", (lid,)).fetchone())
    for args in outbox:
        db.notify(*args)
    _briefing_cache.clear()
    return updated

def referrals(c, lid):
    rows = c.execute("""SELECT u.full_name, n.needs_ack, n.ack_at FROM notifications n JOIN users u ON u.id = n.user_id
                        WHERE n.kind = 'referral' AND n.ref_id = ?""", (lid,)).fetchall()
    if not rows:
        return None
    pending = [r["full_name"] for r in rows if r["needs_ack"] and not r["ack_at"]]
    return {"count": len(rows), "acked": sum(1 for r in rows if r["ack_at"]),
            "needs_ack": any(r["needs_ack"] for r in rows), "pending": pending[:8], "more": max(0, len(pending) - 8)}

def view(l, c=None):
    d = dict(l)
    if c is not None:
        d["referral"] = referrals(c, l["id"])
    d["category_name"] = CATEGORIES.get(l["category"], "")
    d["status_name"] = STATUS.get(l["status"], l["status"])
    d["deadline_short"] = jdate_short(date.fromisoformat(l["deadline"])) if l["deadline"] else None
    d["received_short"] = jdate_short(date.fromisoformat(l["received_date"]))
    d["days_left"] = (date.fromisoformat(l["deadline"]) - today()).days if l["deadline"] else None
    return d

@router.get("/letters")
def letters(user: dict = Depends(staff_or_manager)):
    with db.conn() as c:
        rows = c.execute("SELECT * FROM letters ORDER BY received_date DESC, id DESC").fetchall()
        return [view(r, c) for r in rows]

@router.post("/agent/next")
def agent_next(user: dict = Depends(staff_or_manager)):
    with _lock:
        with db.conn() as c:
            letter = c.execute("SELECT * FROM letters WHERE status = 'new' ORDER BY received_date LIMIT 1").fetchone()
            remaining = c.execute("SELECT COUNT(*) FROM letters WHERE status = 'new'").fetchone()[0]
            if not letter:
                return {"done": True}
            c.execute("UPDATE letters SET status = 'processing' WHERE id = ?", (letter["id"],))
    try:
        updated = handle(dict(letter))
    except Exception:
        with db.conn() as c:   # put it back in the queue if the model failed
            c.execute("UPDATE letters SET status = 'new' WHERE id = ?", (letter["id"],))
        raise HTTPException(status_code=503, detail="دستیار در دسترس نیست")
    return {"done": False, "letter": view(updated), "remaining": remaining - 1}

@router.get("/log")
def agent_log(user: dict = Depends(staff_or_manager)):
    with db.conn() as c:
        rows = c.execute("""SELECT g.*, l.subject FROM agent_log g JOIN letters l ON l.id = g.letter_id
                            ORDER BY g.id DESC LIMIT 60""").fetchall()
    return [dict(r) for r in rows]

class ApproveRequest(BaseModel):
    reply: str

def require_status(c, lid, status):
    """404 if the letter doesn't exist, 409 if it is not in the expected state (e.g. already closed)."""
    if get_letter(c, lid)["status"] != status:
        raise HTTPException(status_code=409, detail="این نامه در وضعیت مناسب برای این کار نیست")

@router.post("/letters/{lid}/approve")
def approve(lid: int, req: ApproveRequest, user: dict = Depends(staff_or_manager)):
    if not req.reply.strip():
        raise HTTPException(status_code=400, detail="متن پاسخ خالی است")
    with db.conn() as c:
        require_status(c, lid, "awaiting_approval")
        c.execute("UPDATE letters SET status = 'done', reply = ? WHERE id = ?", (req.reply.strip(), lid))
        log(c, lid, f"{user['full_name']} پاسخ را تأیید کرد و نامه بسته شد", "تأیید انسانی انجام شد.")
    _briefing_cache.clear()
    return {"ok": True}

@router.post("/letters/{lid}/complete")
def complete(lid: int, user: dict = Depends(staff_or_manager)):
    with db.conn() as c:
        require_status(c, lid, "todo")
        c.execute("UPDATE letters SET status = 'done' WHERE id = ?", (lid,))
        log(c, lid, f"{user['full_name']} کار را انجام‌شده علامت زد", "کار توسط کارمند انجام شد.")
    _briefing_cache.clear()
    return {"ok": True}


class NewLetter(BaseModel):
    sender: str = ""
    subject: str = ""
    body: str

@router.post("/letters")
def add_letter(req: NewLetter, user: dict = Depends(staff_or_manager)):
    """A staff member types or pastes a letter that just arrived. The agent picks it up from the queue."""
    body = req.body.strip()
    if len(body) < 15:
        raise HTTPException(status_code=400, detail="متن نامه خیلی کوتاه است")
    t = today()
    with db.conn() as c:
        cur = c.execute("""INSERT INTO letters (received_date, jreceived, sender, subject, body, status)
                           VALUES (?, ?, ?, ?, ?, 'new')""",
                        (t.isoformat(), jstr(t), req.sender.strip() or "نامشخص", req.subject.strip(), body))
    return {"id": cur.lastrowid}


# ---------- manual referral ----------

def recipient_options(c):
    teachers = c.execute("""SELECT u.id, u.full_name, t.subject FROM users u JOIN teachers t ON t.id = u.ref_id
                            WHERE u.role = 'teacher' ORDER BY t.id""").fetchall()
    staff = c.execute("SELECT id, full_name, role FROM users WHERE role IN ('staff', 'counselor', 'manager')").fetchall()
    parents = c.execute("""SELECT u.id, u.full_name, s.first_name || ' ' || s.last_name AS child, cl.name AS class, cl.id AS class_id
                           FROM users u JOIN students s ON s.id = u.ref_id JOIN classes cl ON cl.id = s.class_id
                           WHERE u.role = 'parent' ORDER BY cl.id, s.last_name""").fetchall()
    classes = c.execute("SELECT id, name FROM classes").fetchall()
    groups = [{"key": "group:teachers", "label": "همه معلمان", "kind": "teacher"},
              {"key": "group:parents", "label": "همه اولیا", "kind": "parent"}]
    groups += [{"key": f"group:class:{cl['id']}", "label": f"اولیای کلاس {cl['name']}", "kind": "parent"} for cl in classes]
    people = [{"key": f"user:{r['id']}", "label": r["full_name"], "sub": {"staff": "پرسنل اداری", "counselor": "مشاور", "manager": "مدیر"}[r["role"]], "kind": "staff"} for r in staff]
    people += [{"key": f"user:{r['id']}", "label": r["full_name"], "sub": f"معلم {r['subject']}", "kind": "teacher"} for r in teachers]
    people += [{"key": f"user:{r['id']}", "label": r["full_name"], "sub": f"ولیِ {r['child']}، {r['class']}", "kind": "parent"} for r in parents]
    return groups, people

KEY = re.compile(r"group:teachers|group:parents|group:class:\d+|user:\d+")

def expand(c, keys):
    """Turn recipient keys into user ids, split into parents and everyone else."""
    bad = [k for k in keys if not KEY.fullmatch(k)]
    if bad:
        raise HTTPException(status_code=400, detail="گیرنده نامعتبر است")
    ids = set()
    for k in keys:
        if k == "group:teachers":
            ids |= {r[0] for r in c.execute("SELECT id FROM users WHERE role = 'teacher'")}
        elif k == "group:parents":
            ids |= {r[0] for r in c.execute("SELECT id FROM users WHERE role = 'parent'")}
        elif k.startswith("group:class:"):
            cid = int(k.split(":")[2])
            ids |= {r[0] for r in c.execute("""SELECT u.id FROM users u JOIN students s ON s.id = u.ref_id
                                               WHERE u.role = 'parent' AND s.class_id = ?""", (cid,))}
        elif k.startswith("user:"):
            ids.add(int(k.split(":")[1]))
    rows = c.execute(f"SELECT id, role FROM users WHERE id IN ({','.join('?' * len(ids)) or 'NULL'})", list(ids)).fetchall()
    return [r["id"] for r in rows if r["role"] == "parent"], [r["id"] for r in rows if r["role"] != "parent"]

def get_letter(c, lid):
    l = c.execute("SELECT * FROM letters WHERE id = ?", (lid,)).fetchone()
    if not l:
        raise HTTPException(status_code=404, detail="نامه پیدا نشد")
    return l

@router.get("/recipients")
def recipients(user: dict = Depends(staff_or_manager)):
    with db.conn() as c:
        groups, people = recipient_options(c)
    return {"groups": groups, "people": people}

@router.post("/letters/{lid}/suggest")
def suggest(lid: int, user: dict = Depends(staff_or_manager)):
    """The agent proposes who should receive this letter."""
    with db.conn() as c:
        l = get_letter(c, lid)
        groups, people = recipient_options(c)
    choices = groups + [p for p in people if p["kind"] != "parent"]
    menu = "\n".join(f"{p['key']}: {p['label']}" + (f" ({p['sub']})" if p.get("sub") else "") for p in choices)
    result = ask_json(
        "تو دستیار دفتر یک دبستان هستی. از فهرست زیر، مناسب‌ترین گیرنده یا گیرنده‌های این نامه را انتخاب کن "
        "(حداکثر سه مورد). اگر نامه گفته به اولیا اطلاع داده شود، گروه اولیای مناسب را هم انتخاب کن.\n"
        "کلیدها: keys (فهرستی از کلیدهای دقیق فهرست)، reason (یک جمله کوتاه فارسی).\n\nفهرست:\n" + menu,
        f"موضوع: {l['subject']}\nمتن: {l['body']}", max_tokens=200) or {}
    valid = {p["key"] for p in choices}
    keys = [k for k in (result.get("keys") or []) if k in valid][:3]
    return {"keys": keys, "reason": (result.get("reason") or "").strip()}

@router.post("/letters/{lid}/parent-draft")
def parent_draft(lid: int, user: dict = Depends(staff_or_manager)):
    """Rewrite an official letter as a short, friendly message for parents."""
    with db.conn() as c:
        l = get_letter(c, lid)
    text = ask_llm(
        "تو دفتر یک دبستان هستی. این نامه اداری را به یک پیام کوتاه، ساده و مؤدبانه برای اولیای دانش‌آموزان تبدیل کن. "
        "شماره بخشنامه و اصطلاحات اداری را حذف کن. فقط آنچه برای اولیا مهم است را بگو: چه خبر است، چه کاری از آن‌ها خواسته شده و تا چه زمانی. "
        "حداکثر چهار جمله. در پایان بنویس «دبستان جاوید».",
        f"موضوع: {l['subject']}\nمتن: {l['body']}", max_tokens=250, temperature=0.3)
    return {"text": stats.to_fa(text)}

class ReferRequest(BaseModel):
    recipients: list[str]
    note: str = ""
    needs_ack: bool = True
    parent_text: str = ""

@router.post("/letters/{lid}/refer")
def refer(lid: int, req: ReferRequest, user: dict = Depends(staff_or_manager)):
    with db.conn() as c:
        l = get_letter(c, lid)
        parent_ids, other_ids = expand(c, req.recipients)
    if not parent_ids and not other_ids:
        raise HTTPException(status_code=400, detail="گیرنده‌ای انتخاب نشده است")
    if parent_ids and not req.parent_text.strip():
        raise HTTPException(status_code=400, detail="برای اولیا متن پیام لازم است")
    note = req.note.strip()
    if other_ids:   # staff and teachers get the original letter plus the note
        body = (f"یادداشت {user['full_name']}: {note}\n\n" if note else "") + f"متن نامه:\n{l['body']}"
        db.notify(other_ids, "referral", f"ارجاع نامه: {l['subject']}", body, ref_type="letter", ref_id=lid, needs_ack=req.needs_ack)
    if parent_ids:  # parents get the friendly version only, never the raw administrative letter
        db.notify(parent_ids, "referral", f"پیام مدرسه: {l['subject']}", req.parent_text.strip(),
                  ref_type="letter", ref_id=lid, needs_ack=req.needs_ack)
    with db.conn() as c:
        who = []
        if other_ids:
            who.append(f"{len(other_ids)} نفر از کارکنان و معلمان")
        if parent_ids:
            who.append(f"{len(parent_ids)} نفر از اولیا")
        log(c, lid, f"{user['full_name']} نامه را به {' و '.join(who)} ارجاع داد", note or "ارجاع دستی")
        if l["status"] in ("new", "todo"):
            c.execute("UPDATE letters SET status = 'todo' WHERE id = ?", (lid,))
    return {"ok": True, "sent": len(parent_ids) + len(other_ids)}

class CategoryRequest(BaseModel):
    category: str

NEXT_STATUS = {"ack": "done", "info": "done", "request": "todo", "stats": "todo", "meeting": "forwarded", "decision": "needs_manager"}

@router.post("/letters/{lid}/category")
def change_category(lid: int, req: CategoryRequest, user: dict = Depends(staff_or_manager)):
    """Staff fixes the agent's category. The letter is saved as an example the agent learns from."""
    if req.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="دسته نامعتبر است")
    with db.conn() as c:
        l = get_letter(c, lid)
        old = CATEGORIES.get(l["category"], "بدون دسته")
        c.execute("UPDATE letters SET category = ?, status = ?, corrected = 1, handled_at = ? WHERE id = ?",
                  (req.category, NEXT_STATUS[req.category], db.stamp(), lid))
        log(c, lid, f"{user['full_name']} دسته را از «{old}» به «{CATEGORIES[req.category]}» تغییر داد",
            "این نامه از این به بعد به عنوان نمونه به دستیار نشان داده می‌شود.")
    if req.category in ("decision", "meeting"):
        db.notify(db.users_with("manager"), "letter", f"ارجاع به شما: {l['subject']}", l["summary"] or "")
    _briefing_cache.clear()
    return {"ok": True}
