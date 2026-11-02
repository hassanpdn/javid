"""A listing or a buyer's request from text an agent pastes: a Divar ad, a WhatsApp message, notes from a call.

The model reads it when the card's AI switch is on; rules read it otherwise, or when the model gives nothing usable.
Either way every value is then looked for in the text itself: a number must be in it, a neighbourhood or a name must
be written in it, a feature must be named in it. What is not there stays empty, never a guess; what is there comes
back with the line it was found on, so the agent sees where each value came from before saving.
"""
import re
from llm import ask_json, ModelOff
from .agency import HOODS

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
WORDS = {"یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "شیش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10}
ORDINALS = {"اول": 1, "دوم": 2, "سوم": 3, "چهارم": 4, "پنجم": 5, "ششم": 6, "هفتم": 7, "هشتم": 8, "نهم": 9, "دهم": 10}
HOOD_FORMS = {h: [h, h.replace("‌", " "), h.replace("‌", "")] for h in HOODS}
FEATURE_WORDS = {"elevator": "آسانسور", "parking": "پارکینگ", "storage": "انباری"}

def normal(text):
    """Latin digits, Persian letters, number words as digits («دو خواب» → «2 خواب», «طبقه سوم» → «طبقه 3»),
    «۸/۵» and «۸٫۵» as 8.5."""
    t = (text or "").translate(FA_DIGITS).replace("ي", "ی").replace("ك", "ک").replace("٫", ".").replace("،", "، ")
    t = re.sub(r"(\d)[/](\d)", r"\1.\2", t)
    t = re.sub(r"(\d),(\d{3})", r"\1\2", t)
    t = re.sub(r"طبقه\s*(" + "|".join(ORDINALS) + r")\b", lambda m: f"طبقه {ORDINALS[m[1]]}", t)
    t = re.sub(r"(?<![\w‌])(" + "|".join(WORDS) + r")\s+(خواب|خوابه|اتاق|طبقه)", lambda m: f"{WORDS[m[1]]} {m[2]}", t)
    t = re.sub(r"\bهمکف\b", "طبقه 0", t)
    return re.sub(r"[ \t]+", " ", t)

# ---------- money ----------

UNITS = {"میلیارد": 1_000_000_000, "میلیون": 1_000_000, "م": 1_000_000, "هزار": 1_000, "تومان": 1, "تومن": 1}
MONEY = re.compile(r"(\d+(?:\.\d+)?)\s*(میلیارد|میلیون|هزار)(?:\s*و\s*(\d+(?:\.\d+)?)\s*(میلیون|هزار))?")

def amounts(text):
    """Every amount of money in the text: [(toman, start, end)]. «8 میلیارد و 500 میلیون» → 8_500_000_000."""
    out = []
    for m in MONEY.finditer(text):
        v = float(m[1]) * UNITS[m[2]]
        if m[3]:
            v += float(m[3]) * UNITS[m[4]]
        out.append((int(round(v)), m.start(), m.end()))
    return out

def _near(text, words, after=16):
    """The first amount written right after one of these words: «رهن 500 میلیون» → 500_000_000. Only a few letters may
    come between («اجاره ماهی 13 میلیون», «تا 8 میلیارد»), so «دنبال اجاره در ... رهن 400» is not read as the rent."""
    for w in words:
        for m in re.finditer(w, text):
            for v, s, _ in amounts(text):
                if 0 <= s - m.end() <= after:
                    return v
    return None

def _line(text, needle):
    """The words around where the value was found (about 40 letters), so the agent sees its source at a glance."""
    t = " ".join(text.split())
    if needle and needle.isdigit():   # a number on its own, not inside another one
        m = re.search(rf"(?<![\d.]){needle}(?![\d.])", t)
        i = m.start() if m else -1
    else:
        i = t.find(needle) if needle else -1
    if i < 0:
        return t[:60]
    start, end = max(0, i - 18), min(len(t), i + len(needle) + 18)
    while start > 0 and t[start - 1] != " ":
        start -= 1
    while end < len(t) and t[end] != " ":
        end += 1
    return ("… " if start else "") + t[start:end].strip(" ،,") + (" …" if end < len(t) else "")

# ---------- rules ----------

def _kind(t):
    if re.search(r"رهن|اجاره|ودیعه|پیش\s*پرداخت", t):
        return "rent"
    if re.search(r"فروش|فروشی|خرید|قیمت کل", t):
        return "sale"
    return None

def _hoods(t):
    return [h for h, forms in HOOD_FORMS.items() if any(f in t for f in forms)]

def _int(pattern, t):
    m = re.search(pattern, t)
    return int(float(m[1])) if m else None

def _feature(t, word):
    if re.search(rf"(بدون|فاقد)\s+{word}|{word}\s+(ندارد|نداره|نیست)", t):
        return False
    return True if word in t else None

def rules(kind_hint, text):
    t = normal(text)
    kind = _kind(t) or kind_hint
    f = {"kind": kind, "hoods": _hoods(t),
         "area": _int(r"(\d{2,4})\s*(?:متر|متری|مترمربع)", t),
         "rooms": _int(r"(\d)\s*(?:خواب|خوابه|اتاق)", t),
         "floor": _int(r"طبقه\s*(\d{1,2})", t),
         "floors": _int(r"(\d{1,2})\s*طبقه", t),
         "age": 0 if re.search(r"نوساز|کلید نخورده", t) else _int(r"(\d{1,2})\s*سال(?:ه|ساخت)?", t),
         "phone": (re.search(r"09\d{9}", t.replace(" ", "")) or [None])[0]}
    for k, w in FEATURE_WORDS.items():
        f[k] = _feature(t, w)
    if kind != "rent":   # an amount with no word of rent is a price or a budget
        f["price"] = _near(t, ["قیمت", "کل", "فروش", "بودجه", "تا"]) or (max((a for a, _, _ in amounts(t)), default=None))
    if kind == "rent":
        f["deposit"] = _near(t, ["رهن", "ودیعه", "پیش"])
        f["rent"] = _near(t, ["اجاره", "ماهی", "ماهانه"])
    word = r"[\u0600-\u06FF‌]+"
    m = re.search(rf"(?:مالک|متقاضی|نام)[:\s]+(?:(?:آقای|خانم)\s+)?({word}(?:\s+{word})?)", t) or re.search(rf"(?:آقای|خانم)\s+({word}(?:\s+{word})?)", t)
    f["name"] = m[1].strip() if m else None
    m = re.search(r"((?:خیابان|بلوار|میدان)\s+[\u0600-\u06FF‌]+(?:\s+(?:شمالی|جنوبی|شرقی|غربی|[\u0600-\u06FF‌]+(?=[،,\n])))?)", t)
    f["street"] = m[1].strip() if m else None
    return f

# ---------- the model ----------

PROMPT = {
    "listing": ("از متن زیر (آگهی یا یادداشت تماس مالک یک واحد مسکونی در تهران) مشخصات را دربیاور. فقط یک شیء JSON با این کلیدها: "
                '{"kind": "sale" یا "rent", "hood": محله, "street": خیابان, "area": متراژ, "rooms": تعداد خواب, "floor": طبقه (همکف 0), '
                '"floors": تعداد طبقات ساختمان, "age": سن بنا به سال (نوساز 0), "elevator": true/false, "parking": true/false, "storage": true/false, '
                '"price": قیمت کل فروش به تومان, "deposit": ودیعه یا رهن به تومان, "rent": اجاره‌ی ماهانه به تومان, "owner_name": نام مالک, "owner_phone": تلفن مالک}. '
                "هر چیزی که در متن نیامده null باشد. حدس نزن."),
    "request": ("از متن زیر (یادداشت تماس کسی که دنبال خرید یا اجاره‌ی خانه در تهران است) خواسته‌اش را دربیاور. فقط یک شیء JSON با این کلیدها: "
                '{"kind": "sale" (خرید) یا "rent" (اجاره), "hoods": [محله‌ها], "budget": سقف بودجه‌ی خرید به تومان, "deposit": سقف ودیعه به تومان, '
                '"rent": سقف اجاره‌ی ماهانه به تومان, "rooms": حداقل خواب, "area": حداقل متراژ, "parking": true اگر لازم دارد, "elevator": true اگر لازم دارد, '
                '"storage": true اگر لازم دارد, "name": نام, "phone": تلفن}. هر چیزی که در متن نیامده null باشد. حدس نزن.'),
}

def _model(kind, text):
    """The model's reading, or None (switched off, no answer, or not JSON)."""
    try:
        return ask_json(PROMPT[kind], text, max_tokens=400)
    except ModelOff:
        return None
    except Exception:
        return None

def _num(v):
    try:
        return None if v in (None, "", "null") else float(str(v).translate(FA_DIGITS).replace(",", ""))
    except ValueError:
        return None

# ---------- reading, then checking every value against the text ----------

LISTING_FIELDS = ["kind", "hood", "street", "area", "rooms", "floor", "floors", "age", "elevator", "parking", "storage", "price", "deposit", "rent",
                  "owner_name", "owner_phone"]
REQUEST_FIELDS = ["kind", "name", "phone", "hoods", "budget", "deposit", "rent", "rooms", "area", "parking", "elevator", "storage"]

def read(kind, text):
    """kind: "listing" or "request". Returns {fields, found: {field: line of the text}, method: "model" or "rules"}."""
    t = normal(text)
    plain = re.sub(r"\s+", "", t)
    nums = set(re.findall(r"\d+(?:\.\d+)?", t)) | {str(int(float(n))) for n in re.findall(r"\d+\.0\b", t)}
    money = {a for a, _, _ in amounts(t)}
    base = rules(None, text)
    got, method = _model(kind, text), "model"
    if not isinstance(got, dict):
        got, method = {}, "rules"
    out, found = {}, {}

    def take(key, value, needle):
        if value is not None and value != "" and value != []:
            out[key] = value
            found[key] = _line(t, needle)

    k = got.get("kind") if got.get("kind") in ("sale", "rent") else None
    k = k if k and (_kind(t) in (None, k)) else _kind(t)
    take("kind", k, {"sale": "فروش", "rent": "رهن"}.get(k) if k else None)
    # numbers: the model's value only if it is written in the text; else the rules' reading
    for key in ("area", "rooms", "floor", "floors", "age"):
        v = _num(got.get(key))
        if v is None or (str(int(v)) not in nums and not (key in ("floor", "age") and v == 0 and (("طبقه 0" in t) or "نوساز" in t))):
            v = base.get(key)
        take(key, int(v) if v is not None else None, str(int(v)) if v is not None else None)
    kk = k or "sale"
    money_keys = (["price"] if kk == "sale" else ["deposit", "rent"]) if kind == "listing" else (["budget"] if kk == "sale" else ["deposit", "rent"])
    for key in money_keys:
        v = _num(got.get(key))
        v = int(v) if v is not None and int(v) in money else base.get("price" if key in ("price", "budget") else key)
        src = next((t[s:e] for a, s, e in amounts(t) if a == v), None)
        take(key, v, src)
    for key, word in FEATURE_WORDS.items():
        v = got.get(key)
        rv = base.get(key)
        v = rv if rv is not None else (True if v is True and word in t else None)
        take(key, v, word)
    # neighbourhoods and names must be written in the text
    hoods = [h for h in ([got.get("hood")] if kind == "listing" else (got.get("hoods") or [])) if h in HOODS and any(f in t for f in HOOD_FORMS[h])]
    hoods = hoods or base["hoods"]
    if kind == "listing":
        take("hood", hoods[0] if hoods else None, next((f for f in HOOD_FORMS.get(hoods[0], []) if f in t), None) if hoods else None)
        street = str(got.get("street") or "").strip()
        street = street if street and street in t else base.get("street")
        take("street", street, street)
    else:
        take("hoods", hoods, hoods[0] if hoods else None)
    name_key, phone_key = ("owner_name", "owner_phone") if kind == "listing" else ("name", "phone")
    name = str(got.get(name_key) or "").strip()
    name = name if name and re.sub(r"\s+", "", name) in plain else base.get("name")
    take(name_key, name, name.split()[0] if name else None)
    phone = re.sub(r"\D", "", str(got.get(phone_key) or "").translate(FA_DIGITS))
    phone = phone if phone and phone in plain else base.get("phone")
    take(phone_key, phone, phone[-4:] if phone else None)
    out = {k: v for k, v in out.items() if v is not None}
    fields = LISTING_FIELDS if kind == "listing" else REQUEST_FIELDS
    return {"fields": {k: out.get(k) for k in fields}, "found": {k: v for k, v in found.items() if k in out}, "method": method}
