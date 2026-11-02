"""A notice (ابلاغیه) from the courts' system (ثنا), from its pasted text: what kind it is, the case number, the archive
number, the branch and court, the date of service, and a hearing's date and time.

Rules read it; when the card's AI is on, the model may fill what the rules missed. Every value is then looked for in
the text: a number must be written in it, a date must be written in it, a kind must have its own words in it. What is
not there stays empty, never a guess, and each value comes back with the words around it.
"""
import re
from llm import ask_json

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
DATE = r"(1[34]\d\d)\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})"
# kind: the words that make it that kind, checked in this order
KIND_WORDS = [
    ("hearing", r"وقت\s*رسیدگی|جهت\s*رسیدگی|جلسه\s*رسیدگی|حضور\s*در\s*جلسه"),
    ("defect", r"رفع\s*نقص"),
    ("expert", r"کارشناس"),
    ("execution", r"اجرائیه|اجراییه"),
    ("default", r"غیابی|واخواهی"),
    ("appeal", r"دادگاه\s*تجدید\s*نظر|دادگاه\s*تجدیدنظر"),
    ("judgment", r"دادنامه|رأی|راي"),
]

def normal(text):
    return (text or "").translate(FA_DIGITS).replace("ي", "ی").replace("ك", "ک")

def _around(t, needle):
    t = " ".join(t.split())
    i = t.find(needle) if needle else -1
    if i < 0:
        return ""
    a, b = max(0, i - 20), min(len(t), i + len(needle) + 20)
    while a > 0 and t[a - 1] != " ":
        a -= 1
    while b < len(t) and t[b] != " ":
        b += 1
    return ("… " if a else "") + t[a:b].strip() + (" …" if b < len(t) else "")

def _date(m):
    y, mo, d = int(m[1]), int(m[2]), int(m[3])
    return f"{y}/{mo:02d}/{d:02d}" if 1 <= mo <= 12 and 1 <= d <= 31 else None

def rules(text):
    t = normal(text)
    f = {}
    f["kind"] = next((k for k, w in KIND_WORDS if re.search(w, t)), None)
    m = re.search(r"شماره\s*(?:ی\s*)?پرونده\s*[:：]?\s*(\d{10,20})", t)
    f["number"] = m[1] if m else None
    m = re.search(r"بایگانی[^\d\n]{0,20}(\d{3,10})", t)
    f["archive"] = m[1] if m else None
    m = re.search(r"شعبه\s*(\d{1,4})\s*([^\n،,.]{0,60}?)(?=[\n،,.]|$)", t)
    f["branch"] = m[1] if m else None
    court = (m[2].strip() if m else "") or ""
    court = re.sub(r"^(?:ی\s+)", "", court)
    f["court"] = court if re.search(r"دادگاه|دادسرا|اجرای احکام|شورای حل اختلاف", court) else None
    m = re.search(r"تاریخ\s*ابلاغ\s*[:：]?\s*" + DATE, t)
    f["served"] = _date(m) if m else None
    m = re.search(r"(?:وقت\s*رسیدگی|جهت\s*رسیدگی|جلسه)[^\n\d]{0,40}" + DATE + r"[^\n\d]{0,20}(\d{1,2}[:：]\d{2})?", t)
    f["hearing_date"] = _date(m) if m else None
    f["hearing_time"] = (m[4].replace("：", ":").zfill(5) if m and m[4] else None)
    return f

PROMPT = ("از متن زیر (ابلاغیه‌ی سامانه‌ی ثنا) این‌ها را دربیاور و فقط یک شیء JSON برگردان: "
          '{"kind": یکی از judgment (دادنامه‌ی بدوی)، default (دادنامه‌ی غیابی)، appeal (دادنامه‌ی تجدیدنظر)، defect (اخطار رفع نقص)، '
          'expert (نظر کارشناس)، execution (اجرائیه)، hearing (وقت رسیدگی)، "number": شماره‌ی پرونده، "archive": شماره‌ی بایگانی، '
          '"branch": شماره‌ی شعبه، "court": نام دادگاه، "served": تاریخ ابلاغ به شکل 1405/08/10، "hearing_date": تاریخ جلسه، "hearing_time": ساعت جلسه}. '
          "هر چیزی که در متن نیامده null باشد. حدس نزن.")

def read(text):
    """{fields, found: {field: words around it}, method}"""
    t = normal(text)
    flat = " ".join(t.split())
    base = rules(text)
    try:
        got = ask_json(PROMPT, text, max_tokens=300)
        method = "model" if isinstance(got, dict) else "rules"
    except Exception:   # switched off (ModelOff) or no answer
        got, method = None, "rules"
    got = got if isinstance(got, dict) else {}
    out, found = {}, {}
    for k, v in base.items():
        mv = got.get(k)
        mv = normal(str(mv)).strip() if mv not in (None, "", "null") else None
        if k == "kind":
            ok = mv in dict(KIND_WORDS) and re.search(dict(KIND_WORDS)[mv], t)
            value = base[k] or (mv if ok else None)
        elif k in ("served", "hearing_date"):
            m = re.fullmatch(DATE, mv or "")
            mv = _date(m) if m else None
            ok = mv and re.search(DATE.replace(r"(1[34]\d\d)", mv[:4]), t) and any(_date(x) == mv for x in re.finditer(DATE, t))
            value = v or (mv if ok else None)
        elif k == "court":
            value = v or (mv if mv and mv in flat else None)
        else:
            value = v or (mv if mv and mv in re.sub(r"\s", "", t) else None)
        if value:
            out[k] = value
            needle = {"kind": None}.get(k, value)
            if k in ("served", "hearing_date"):
                y, mo, d = value.split("/")
                needle = next((x[0] for x in re.finditer(DATE, t) if _date(x) == value), value)
            if k == "kind":
                needle = re.search(dict(KIND_WORDS)[value], t)[0]
            if k == "branch":
                needle = re.search(r"شعبه\s*" + value, t)[0]
            found[k] = _around(t, needle)
    fields = ["kind", "number", "archive", "branch", "court", "served", "hearing_date", "hearing_time"]
    return {"fields": {k: out.get(k) for k in fields}, "found": found, "method": method}
