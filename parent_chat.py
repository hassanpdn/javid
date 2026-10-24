"""Parent Q&A about their own child.

Safety design:
- The student id comes only from the parent's login (user["ref_id"]). Nothing in the question can change it.
- Code pulls only this child's data and computes every number. The model only phrases the answer.
- Private items (counselor notes, health flags, unapproved suggestions) are never loaded here.
- Every number in the model's answer is checked against the computed facts; if one doesn't match,
  a plain answer built by code is shown instead.
"""
import re
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import db
from auth import require_role
from common import normalize
from llm import ask_llm, ask_json
from manager import today
from jalali import to_jalali, to_gregorian, MONTHS
from db import LEVELS

router = APIRouter(prefix="/parent")
parent_only = require_role("parent")

TERM_START = date(2026, 9, 23)  # 1 Mehr 1405
FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
WORD_NUMS = {"یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10}
SUBJECT_ALIASES = {  # what parents say -> subject name in the database
    "ریاضی": "ریاضی", "حساب": "ریاضی", "فارسی": "فارسی", "املا": "فارسی", "انشا": "فارسی",
    "علوم": "علوم تجربی", "مطالعات": "مطالعات اجتماعی", "اجتماعی": "مطالعات اجتماعی",
    "هدیه": "هدیه‌های آسمان", "دینی": "هدیه‌های آسمان", "ورزش": "ورزش", "قرآن": "قرآن",
    "هنر": "هنر", "نقاشی": "هنر", "انگلیسی": "زبان انگلیسی", "زبان": "زبان انگلیسی",
}

# Fixed answers: these never go through the model
OTHER_STUDENT = "من فقط می‌تونم درباره فرزند خودتون اطلاعات بدم. اطلاعات بقیه دانش‌آموزها محرمانه‌ست."
COMPARE = ("مدرسه پیشرفت هر بچه رو با خودش می‌سنجه، نه با همکلاسی‌هاش. "
           "می‌تونم بگم فرزندتون توی هر درس نسبت به اول سال چه تغییری کرده.")
SENSITIVE = ("این سؤال نیاز به بررسی تخصصی داره و من نمی‌تونم درباره‌ش نظر بدم. "
             "پیشنهاد می‌کنم با خانم کاظمی، مشاور مدرسه، صحبت کنید. می‌تونید از دفتر مدرسه وقت بگیرید.")
UNCLEAR = ("متوجه سؤالتون نشدم. می‌تونید درباره نمره‌ها، درس‌ها، غیبت و تأخیر، فرم‌های سلامت، "
           "پیام‌های مشاور یا مقررات مدرسه بپرسید.")

def fa(v):
    return str(v).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

def jshort(iso):
    y, m, d = to_jalali(date.fromisoformat(iso))
    return f"{d} {MONTHS[m - 1]}"

# ---------- 1. understanding the question (code first, model only as fallback) ----------

def other_student_named(c, q, sid):
    """True if the question names another student and not this child."""
    own = c.execute("SELECT first_name FROM students WHERE id = ?", (sid,)).fetchone()["first_name"]
    words = set(re.findall(r"[\w‌]+", q))
    others = {r["first_name"] for r in c.execute("SELECT first_name FROM students WHERE id != ?", (sid,))}
    if re.search(r"(همه|بقیه|سایر|لیست|فهرست)( ?ی)? (دانش[ ‌]?آموز|بچه|شاگرد)", q):
        return True
    return bool(words & (others - {own})) and own not in words

def find_subject(q):
    for word, subject in SUBJECT_ALIASES.items():
        if word in q:
            return subject
    return None

def find_period(q, t):
    """Returns (start_date, label). Default is the last 30 days."""
    q = q.translate(FA_DIGITS)
    if "امروز" in q:
        return t, "امروز"
    if "این ماه" in q:
        y, m, _ = to_jalali(t)
        return to_gregorian(y, m, 1), f"از اول {MONTHS[m - 1]} تا امروز"
    if re.search(r"امسال|ترم|از اول سال|از مهر|کل سال", q):
        return TERM_START, "از اول مهر تا امروز"
    if "این هفته" in q:
        return t - timedelta(days=6), "در هفت روز اخیر"
    m = re.search(r"(?<![\w‌])(\d+|" + "|".join(WORD_NUMS) + r")\s*(روز|هفته|ماه)", q)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else WORD_NUMS[m.group(1)]
        days = n * {"روز": 1, "هفته": 7, "ماه": 30}[m.group(2)]
        return t - timedelta(days=days - 1), f"در {days} روز اخیر"
    if re.search(r"هفته (اخیر|گذشته|پیش)", q):
        return t - timedelta(days=6), "در هفت روز اخیر"
    return t - timedelta(days=29), "در ۳۰ روز اخیر"

RULES = [  # (intent, pattern). Order matters.
    ("compare", r"مقایسه|رتبه|نفر اول|بقیه بچه|همکلاسی|میانگین کلاس|از بقیه"),
    ("sensitive", r"افسرد|اضطراب|بیش ?فعال|اوتیس|روانی|بیماری|اختلال|روانشناس|دارو"),
    ("rules", r"قانون|مقررات|آیین|مجاز|ممنوع|اجازه|ساعت (شروع|کلاس|تعطیل)|چطور موجه|موجه میشه|موبایل|تلفن همراه|پوشش|لباس|جلسه (اولیا|اولیاء)"),
    ("attendance", r"غیبت|غایب|نیومده|نیامده|تاخیر|تأخیر|دیر (اومده|آمده|رسیده)|حضور|حاضر"),
    ("suggestions", r"مشاور (چی )?گفته|پیشنهاد|توصیه|پیام مشاور"),
    ("forms", r"فرم"),
    ("teacher", r"معلم|آموزگار|مشاورش کیه|مدیر کیه"),
    ("weakest", r"ضعیف|ضعف|مشکل داره|کجا(ش)? مشکل|تقویت|عقب|کمک (لازم|نیاز)"),
    ("strongest", r"قوی|بهترین درس|خوبه|استعداد|عالیه"),
    ("grades", r"نمره|کارنامه|وضعیت درسی|درس(ش|ها)|پیشرفت|ارزشیابی|چطوره"),
]

def classify(q):
    subject = find_subject(q)
    for intent, pattern in RULES:
        if re.search(pattern, q):
            if intent in ("weakest", "strongest", "grades") and subject:
                return "subject", subject
            return intent, subject
    if subject:
        return "subject", subject
    # Nothing matched: ask the model, but only to pick one label from a fixed list
    try:
        r = _ask_label(q)
    except Exception:
        r = {}
    intent = r.get("intent")
    return (intent if intent in {i for i, _ in RULES} | {"rules", "unclear"} else "unclear"), None

def _ask_label(q):
    return ask_json(
        "سؤال یک ولی را دسته‌بندی کن. فقط یکی از این برچسب‌ها: "
        "grades (وضعیت درسی کلی)، weakest (درس ضعیف)، strongest (درس قوی)، attendance (غیبت و تأخیر)، "
        "teacher (معلم‌ها)، suggestions (پیام مشاور)، forms (فرم سلامت)، rules (مقررات و قوانین مدرسه)، "
        "compare (مقایسه با بچه‌های دیگر)، sensitive (تشخیص پزشکی یا روانی)، unclear (نامفهوم یا بی‌ربط).\n"
        'خروجی: {"intent": "..."}', q, max_tokens=30) or {}

# ---------- 2. computing the facts (code only, this child only) ----------

def subject_rows(c, sid, subject):
    return c.execute("""SELECT a.date, a.level, a.note, t.full_name AS teacher FROM assessments a
                        JOIN teachers t ON t.id = a.teacher_id
                        WHERE a.student_id = ? AND a.subject = ? ORDER BY a.date""", (sid, subject)).fetchall()

def subject_summary(c, sid):
    out = []
    for (sub,) in c.execute("SELECT DISTINCT subject FROM assessments WHERE student_id = ?", (sid,)):
        rows = subject_rows(c, sid, sub)
        start, now = rows[0]["level"], rows[-1]["level"]
        note = next((r["note"] for r in reversed(rows) if r["note"]), None)
        out.append({"subject": sub, "start": start, "now": now, "note": note, "teacher": rows[-1]["teacher"]})
    return out

def trend_word(start, now):
    return "پیشرفت کرده" if now > start else "افت کرده" if now < start else "ثابت مانده"

def build_facts(c, sid, intent, subject, q, t):
    """Returns (facts text for the model, plain answer built by code, source label)."""
    name = c.execute("SELECT first_name FROM students WHERE id = ?", (sid,)).fetchone()["first_name"]

    if intent == "attendance":
        start, label = find_period(q, t)
        rows = c.execute("""SELECT date, status, excused FROM student_attendance WHERE student_id = ?
                            AND date >= ? AND date <= ? ORDER BY date""", (sid, start.isoformat(), t.isoformat())).fetchall()
        absent = [r for r in rows if r["status"] == "absent"]
        late = [r for r in rows if r["status"] == "late"]
        unexcused = [r for r in absent if not r["excused"]]
        days_txt = "، ".join(jshort(r["date"]) + ("" if r["excused"] else " (غیرموجه)") for r in absent)
        late_txt = "، ".join(jshort(r["date"]) for r in late)
        facts = (f"بازه: {label} ({len(rows)} روز درسی)\nتعداد غیبت: {len(absent)} (غیرموجه: {len(unexcused)})\n"
                 f"تاریخ غیبت‌ها: {days_txt or 'ندارد'}\nتعداد تأخیر: {len(late)}\nتاریخ تأخیرها: {late_txt or 'ندارد'}")
        plain = (f"{label} ({len(rows)} روز درسی)، {name} {len(absent)} روز غیبت داشته"
                 + (f" که {len(unexcused)} روزش غیرموجه بوده" if unexcused else "")
                 + (f" ({days_txt})" if absent else "") + f" و {len(late)} بار با تأخیر رسیده.")
        return facts, plain, ("حضور و غیاب", label.removeprefix("در "))

    if intent == "subject":
        rows = subject_rows(c, sid, subject)
        if not rows:
            return None, f"برای درس {subject} ارزشیابی‌ای از {name} ثبت نشده.", ("ارزشیابی", subject)
        trend = "، ".join(f"{jshort(r['date'])}: {LEVELS[r['level']]}" for r in rows)
        note = next((r["note"] for r in reversed(rows) if r["note"]), None)
        facts = (f"درس: {subject}، آموزگار: {rows[-1]['teacher']}\nارزشیابی‌ها از مهر تا امروز: {trend}\n"
                 f"وضعیت فعلی: {LEVELS[rows[-1]['level']]}، نسبت به اول سال {trend_word(rows[0]['level'], rows[-1]['level'])}"
                 + (f"\nیادداشت آموزگار: {note}" if note else ""))
        plain = (f"وضعیت {name} در {subject} الان «{LEVELS[rows[-1]['level']]}» است و نسبت به اول سال "
                 f"{trend_word(rows[0]['level'], rows[-1]['level'])}." + (f" یادداشت آموزگار: {note}" if note else ""))
        return facts, plain, ("ارزشیابی", subject)

    if intent in ("grades", "weakest", "strongest"):
        subs = subject_summary(c, sid)
        lines = "\n".join(f"{s['subject']}: الان {LEVELS[s['now']]}، اول سال {LEVELS[s['start']]}"
                          + (f" (یادداشت آموزگار: {s['note']})" if s["note"] else "") for s in subs)
        if intent == "grades":
            facts = f"وضعیت همه درس‌ها از مهر تا امروز:\n{lines}"
            plain = "وضعیت فعلی درس‌ها: " + "، ".join(f"{s['subject']} {LEVELS[s['now']]}" for s in subs) + "."
            return facts, plain, ("ارزشیابی", "همه درس‌ها")
        pick = min if intent == "weakest" else max
        best = pick(s["now"] for s in subs)
        chosen = [s for s in subs if s["now"] == best]
        if intent == "weakest":  # among equals, the one that dropped most needs attention first
            chosen.sort(key=lambda s: s["now"] - s["start"])
        names = "، ".join(s["subject"] for s in chosen)
        kind = "نیاز به تمرین بیشتر" if intent == "weakest" else "قوی‌ترین"
        facts = (f"درس‌هایی که {kind} هستند: {names} (سطح فعلی: {LEVELS[best]})\n"
                 + "\n".join(f"{s['subject']}: اول سال {LEVELS[s['start']]}، الان {LEVELS[s['now']]}"
                             + (f"، یادداشت آموزگار: {s['note']}" if s["note"] else "") for s in chosen))
        if intent == "weakest" and best >= 3:
            facts += "\nتوجه: هیچ درسی پایین‌تر از «خوب» نیست."
        if intent == "weakest" and best >= 3:
            head = f"خوشبختانه هیچ درسی پایین‌تر از «خوب» نیست. درسی که نسبت به بقیه جای تمرین بیشتری داره: {names}"
        else:
            head = f"{'درسی که بیشتر نیاز به تمرین داره' if intent == 'weakest' else 'قوی‌ترین درس‌ها'}: {names}"
        plain = (f"{head} (سطح فعلی «{LEVELS[best]}»)." + (f" یادداشت آموزگار: {chosen[0]['note']}" if chosen[0]["note"] else ""))
        return facts, plain, ("ارزشیابی", "همه درس‌ها")

    if intent == "teacher" and subject:
        r = c.execute("""SELECT t.full_name FROM assessments a JOIN teachers t ON t.id = a.teacher_id
                         WHERE a.student_id = ? AND a.subject = ? LIMIT 1""", (sid, subject)).fetchone()
        if r:
            return None, f"آموزگار {subject} {name}، خانم {r['full_name']} است.", ("اطلاعات کلاس", subject)
    if intent == "teacher":
        home = c.execute("""SELECT t.full_name, cl.name FROM students s JOIN classes cl ON cl.id = s.class_id
                            JOIN teachers t ON t.id = cl.homeroom_teacher_id WHERE s.id = ?""", (sid,)).fetchone()
        others = c.execute("""SELECT DISTINCT a.subject, t.full_name FROM assessments a JOIN teachers t ON t.id = a.teacher_id
                              WHERE a.student_id = ? AND t.full_name != ?""", (sid, home["full_name"])).fetchall()
        facts = (f"کلاس {home['name']}، آموزگار اصلی: {home['full_name']}\n"
                 + "\n".join(f"{r['subject']}: {r['full_name']}" for r in others) + "\nمشاور مدرسه: مریم کاظمی")
        plain = (f"آموزگار کلاس {home['name']} خانم {home['full_name']} است. "
                 + "، ".join(f"{r['subject']}: {r['full_name']}" for r in others) + ". مشاور مدرسه خانم مریم کاظمی است.")
        return facts, plain, ("اطلاعات کلاس", home["name"])

    if intent == "suggestions":
        rows = c.execute("""SELECT for_parent, approved_at FROM suggestions WHERE student_id = ? AND status = 'approved'
                            ORDER BY id DESC LIMIT 3""", (sid,)).fetchall()
        if not rows:
            return None, "تا الان پیامی از طرف مشاور برای شما ثبت نشده.", ("پیام‌های مشاور", "")
        facts = "\n".join(f"پیام مشاور ({r['approved_at']}): {r['for_parent']}" for r in rows)
        return facts, rows[0]["for_parent"], ("پیام‌های مشاور", "")

    if intent == "forms":
        rows = c.execute("""SELECT kind, MAX(jdate) AS jdate FROM health_forms WHERE student_id = ? GROUP BY kind""",
                         (sid,)).fetchall()
        done = {r["kind"]: r["jdate"] for r in rows}
        parts = [f"{'فرم سلامت جسمی' if k == 'physical' else 'فرم حال و احوال'}: "
                 + (f"آخرین ثبت {done[k]}" if k in done else "هنوز تکمیل نشده") for k in ("physical", "wellbeing")]
        plain = "، ".join(parts) + ". از بخش «فرم‌های سلامت» توی همین صفحه می‌تونید به‌روزش کنید."
        return None, plain, ("فرم‌های سلامت", "")

    return None, UNCLEAR, None

# ---------- 3. writing and checking ----------

def numbers_in(text):
    return set(re.findall(r"\d+", text.translate(FA_DIGITS)))

def write(first_name, question, facts):
    return ask_llm(
        f"تو دستیار مدرسه جاوید هستی و به سؤال ولیِ {first_name} جواب می‌دهی.\n"
        "قوانین:\n"
        "- فقط از «اطلاعات» زیر استفاده کن. اگر جواب در اطلاعات نیست، بگو در سامانه ثبت نشده.\n"
        "- عددها و تاریخ‌ها را دقیقا همان‌طور که در اطلاعات آمده بنویس، با رقم.\n"
        "- بچه را با دیگران مقایسه نکن، تشخیص یا حدس نزن، نگرانی ایجاد نکن.\n"
        "- اگر درسی افت کرده، یادداشت آموزگار را بگو و پیشنهاد کن با آموزگار صحبت کنند.\n"
        "- دو یا سه جمله کوتاه، ساده و محترمانه.",
        f"اطلاعات:\n{facts}\n\nسؤال ولی: {question}", max_tokens=220, temperature=0.2)

class AskRequest(BaseModel):
    question: str

@router.post("/ask")
def ask(req: AskRequest, user: dict = Depends(parent_only)):
    sid = user["ref_id"]  # the only place the child is chosen
    q = normalize(req.question)
    t = today()
    with db.conn() as c:
        first_name = c.execute("SELECT first_name FROM students WHERE id = ?", (sid,)).fetchone()["first_name"]
        if len(q.replace("؟", "").split()) < 2:
            result = {"answer": UNCLEAR, "sources": [], "intent": "unclear"}
        elif other_student_named(c, q, sid):
            result = {"answer": OTHER_STUDENT, "sources": [], "intent": "other_student"}
        else:
            intent, subject = classify(q)
            if intent == "rules":
                from app import answer_question  # school rules: same document search, parent access only
                try:
                    result = answer_question(q, "parent")
                except Exception:
                    result = {"answer": "الان به اسناد مدرسه دسترسی ندارم. چند لحظه بعد دوباره امتحان کنید.", "sources": []}
                result["intent"] = "rules"
            elif intent in ("compare", "sensitive", "unclear"):
                result = {"answer": {"compare": COMPARE, "sensitive": SENSITIVE, "unclear": UNCLEAR}[intent],
                          "sources": [], "intent": intent}
            else:
                facts, plain, source = build_facts(c, sid, intent, subject, q, t)
                answer = plain
                if facts:
                    try:
                        draft = write(first_name, q, facts)
                        # every number the model wrote must exist in the facts, otherwise use the code's answer
                        if draft and numbers_in(draft) <= numbers_in(facts):
                            answer = draft
                    except Exception:
                        pass
                result = {"answer": answer, "checked": True, "intent": intent,
                          "sources": [{"doc": source[0], "article": source[1]}] if source else []}
    db.log_chat(user, req.question, result["answer"], result["intent"])
    return result
