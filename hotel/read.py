"""A booking request from pasted text: a WhatsApp message, a phone note, an agency's email.

Rules read the dates («۱۵ تا ۱۸ آبان», «از ۱۴۰۵/۰۸/۱۵ سه شب»), the people («دو بزرگسال و یک بچه‌ی ۶ ساله»), the
room (sea view, suite, villa, triple), the meals, a name and a mobile number. When the card's AI is on the model may
fill a name, a room or the meals the rules missed; a value is kept only if its own words are in the text. Dates and
numbers come from the rules alone. What is not in the text stays empty, never a guess, and each value comes back
with the words around it.
"""
import re
from datetime import date
from jalali import to_jalali, to_gregorian, MONTHS
from llm import ask_json
from . import store

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
WORDS = {"یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10}
NUM = r"(\d{1,2}|یک|یه|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده)"
MONTH = "(" + "|".join(MONTHS) + ")"
TYPE_WORDS = [("villa", r"ویلا"), ("suite", r"سوئیت|سوییت"), ("triple", r"سه\s*‌?\s*تخته"), ("dbl_sea", r"(?:رو\s*به|ویو|منظره‌?ی?)\s*دریا|دریا"),
              ("dbl_garden", r"(?:رو\s*به\s*)?باغ")]
BOARD_WORDS = [("FB", r"پانسیون\s*کامل|فول\s*برد|سه\s*وعده"), ("HB", r"نیم\s*‌?\s*پانسیون|صبحانه\s*و\s*شام|با\s*شام"), ("BB", r"صبحانه")]

def normal(text):
    return (text or "").translate(FA_DIGITS).replace("ي", "ی").replace("ك", "ک")

def num(s):
    return int(s) if s.isdigit() else WORDS.get(s)

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

def _year_for(m, d):
    """The year of a day written without one: this year, or next year when that day has passed."""
    y, tm, td = to_jalali(store.today())
    return y + 1 if (m, d) < (tm, td) else y

def _jal(y, m, d):
    try:
        to_gregorian(y, m, d)
        return f"{y}/{m:02d}/{d:02d}"
    except Exception:
        return None

def rules(text):
    t = normal(text)
    f, found = {}, {}
    full = list(re.finditer(r"(1[34]\d\d)\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})", t))
    span = re.search(r"(\d{1,2})\s*(?:تا|الی|-|–)\s*(\d{1,2})\s*" + MONTH, t)
    one = list(re.finditer(r"(\d{1,2})\s*(?:ام\s*)?" + MONTH, t)) or [m for m in re.finditer(MONTH + r"\s*(\d{1,2})(?!\s*/)", t)]
    if one and not one[0][1].isdigit():          # «اسفند ۲۸»: the month first
        one = [(x[0], x[2], x[1]) for x in one]
    nights = re.search(NUM + r"\s*شب", t)
    if nights and num(nights[1]):
        f["nights"] = num(nights[1]); found["nights"] = _around(t, nights[0])
    if full:
        f["arrive"] = _jal(int(full[0][1]), int(full[0][2]), int(full[0][3])); found["arrive"] = _around(t, full[0][0])
        if len(full) > 1:
            f["depart"] = _jal(int(full[1][1]), int(full[1][2]), int(full[1][3])); found["depart"] = _around(t, full[1][0])
    elif span:
        m = MONTHS.index(span[3]) + 1
        y = _year_for(m, int(span[1]))
        f["arrive"], f["depart"] = _jal(y, m, int(span[1])), _jal(y, m, int(span[2]))
        found["arrive"] = found["depart"] = _around(t, span[0])
    elif one:
        m = MONTHS.index(one[0][2]) + 1
        f["arrive"] = _jal(_year_for(m, int(one[0][1])), m, int(one[0][1])); found["arrive"] = _around(t, one[0][0])
        if len(one) > 1:
            m2 = MONTHS.index(one[1][2]) + 1
            f["depart"] = _jal(_year_for(m2, int(one[1][1])), m2, int(one[1][1])); found["depart"] = _around(t, one[1][0])
    if f.get("arrive") and not f.get("depart") and f.get("nights"):
        y, m, d = (int(x) for x in f["arrive"].split("/"))
        g = date.fromordinal(to_gregorian(y, m, d).toordinal() + f["nights"])
        jy, jm, jd = to_jalali(g)
        f["depart"] = f"{jy}/{jm:02d}/{jd:02d}"; found["depart"] = found.get("nights", "")
    ages = [int(a) for a in re.findall(r"(\d{1,2})\s*سال(?:ه|ش)", t)]
    kids = re.search(NUM + r"\s*(?:تا\s*)?(?:بچه|کودک|فرزند)", t)
    if kids and num(kids[1]):
        f["children"] = num(kids[1]); found["children"] = _around(t, kids[0])
    elif ages:
        f["children"] = len(ages)
    if ages:
        f["ages"] = ages[:f.get("children") or len(ages)]; found["ages"] = _around(t, re.search(r"\d{1,2}\s*سال(?:ه|ش)", t)[0])
    adults = re.search(NUM + r"\s*(?:تا\s*)?بزرگسال", t)
    total = re.search(NUM + r"\s*(?:تا\s*)?نفر", t)
    if adults and num(adults[1]):
        f["adults"] = num(adults[1]); found["adults"] = _around(t, adults[0])
    elif total and num(total[1]):
        f["adults"] = max(1, num(total[1]) - (f.get("children") or 0)); found["adults"] = _around(t, total[0])
    for k, w in TYPE_WORDS:
        m = re.search(w, t)
        if m:
            f["type"] = k; found["type"] = _around(t, m[0]); break
    for k, w in BOARD_WORDS:
        m = re.search(w, t)
        if m:
            f["board"] = k; found["board"] = _around(t, m[0]); break
    m = re.search(r"09\d{9}", re.sub(r"[\s\-]", "", t))
    if m:
        f["phone"] = m[0]; found["phone"] = m[0]
    m = re.search(r"(?:به\s*نام|اسم(?:م)?|نام)\s*[:：]?\s*((?:آقای|خانم)?\s*[؀-ۿ‌]{2,}\s+[؀-ۿ‌]{2,})", t) or \
        re.search(r"(?:من|بنده)\s+([؀-ۿ‌]{2,}\s+[؀-ۿ‌]{2,})\s+هستم", t)
    if m:
        f["name"] = " ".join(m[1].replace("آقای", "").replace("خانم", "").split()); found["name"] = _around(t, m[1])
    return f, found

PROMPT = ("از متن زیر (درخواست رزرو هتل) فقط این‌ها را دربیاور و یک شیء JSON برگردان: "
          '{"name": نام مهمان، "type": یکی از dbl_garden (دوتخته رو به باغ)، dbl_sea (دوتخته رو به دریا)، triple (سه‌تخته)، suite (سوئیت)، villa (ویلا)، '
          '"board": یکی از BB (صبحانه)، HB (نیم‌پانسیون)، FB (پانسیون کامل)}. هر چیزی که در متن نیامده null باشد. حدس نزن.')

def read(text):
    """{fields, found: {field: words around it}, method}"""
    t = normal(text)
    flat = " ".join(t.split())
    f, found = rules(text)
    method = "rules"
    if not all(f.get(k) for k in ("name", "type", "board")):
        try:
            got = ask_json(PROMPT, text, max_tokens=150)
            method = "model" if isinstance(got, dict) else "rules"
        except Exception:     # switched off (ModelOff) or no answer
            got = None
        got = got if isinstance(got, dict) else {}
        name = " ".join(normal(str(got.get("name") or "")).split())
        if not f.get("name") and len(name) >= 5 and name in flat:
            f["name"] = name; found["name"] = _around(t, name)
        for key, words in (("type", TYPE_WORDS), ("board", BOARD_WORDS)):
            v = got.get(key)
            if not f.get(key) and v in dict(words):
                m = re.search(dict(words)[v], t)
                if m:
                    f[key] = v; found[key] = _around(t, m[0])
    keys = ["arrive", "depart", "nights", "adults", "children", "ages", "type", "board", "name", "phone"]
    return {"fields": {k: f.get(k) for k in keys}, "found": found, "method": method}
