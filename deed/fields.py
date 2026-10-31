"""The deed's fields: their shape, cleaning, and the checks code makes on them. No model is involved here.

Values are stored cleaned: Persian and Arabic digits as 0-9, «ي» and «ك» as «ی» and «ک», no tatweel, single spaces.
Dates stay Jalali («1384/06/15») and must be real dates, not in the future. Shares are in dang and must add up to 6.
"""
import re
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
import jalali

# ---------- cleaning ----------

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫", "01234567890123456789.")

def clean(text):
    """The same text with Latin digits, Persian «ی»/«ک», no tatweel and single spaces. None stays None."""
    if text is None:
        return None
    t = str(text).translate(DIGITS).replace("ي", "ی").replace("ى", "ی").replace("ك", "ک").replace("ـ", "")
    return re.sub(r"[ \t]+", " ", t).strip() or None

def number(text):
    """«245.50» or «۲۴۵٫۵» -> 245.5; anything else -> None."""
    t = clean(text)
    try:
        return float(t) if t and re.fullmatch(r"\d+(\.\d+)?", t) else None
    except ValueError:
        return None

# ---------- the shape the model must answer in (one page) ----------

class Owner(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = None
    father_name: str | None = None
    national_id: str | None = None
    share: str | None = None          # as written: «سه دانگ», «یک و نیم دانگ», «2 دانگ»

class Transfer(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    date: str | None = None
    from_: str | None = Field(None, alias="from")   # «from» is a Python word
    to: str | None = None
    share: str | None = None
    note: str | None = None

class Boundaries(BaseModel):
    model_config = ConfigDict(extra="ignore")
    north: str | None = None
    east: str | None = None
    south: str | None = None
    west: str | None = None

class PageData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    owners: list[Owner] = []
    main_plate: str | None = None
    sub_plate: str | None = None
    section: str | None = None
    area: str | None = None
    area_unit: str | None = None
    boundaries: Boundaries = Boundaries()
    book: str | None = None
    page: str | None = None
    deed_number: str | None = None
    issue_date: str | None = None
    transfers: list[Transfer] = []

# the single-value fields, in the order the review form shows them
SCALARS = ["deed_number", "issue_date", "book", "page", "main_plate", "sub_plate", "section", "area", "area_unit",
           "north", "east", "south", "west"]
BOUNDARIES = ("north", "east", "south", "west")
NUMERIC = {"deed_number", "book", "page", "main_plate", "sub_plate"}   # whole numbers only

# ---------- checks ----------

def jalali_date(text):
    """(«1384/06/15», "") for a real Jalali date that is not in the future, else (None, the reason)."""
    t = clean(text)
    m = re.fullmatch(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", t or "")
    if not m:
        return None, "تاریخ به شکل سال/ماه/روز نیست."
    y, mo, d = map(int, m.groups())
    if not 1 <= mo <= 12:
        return None, "ماه تاریخ درست نیست."
    days = 31 if mo <= 6 else 30 if mo <= 11 else (30 if _leap(y) else 29)
    if not 1 <= d <= days:
        return None, "روز تاریخ در این ماه وجود ندارد."
    if y < 1250:
        return None, "سال تاریخ درست به نظر نمی‌رسد."
    if jalali.to_gregorian(y, mo, d) > date.today():
        return None, "تاریخ در آینده است."
    return f"{y:04d}/{mo:02d}/{d:02d}", ""

def _leap(y):
    try:
        return jalali.to_jalali(jalali.to_gregorian(y, 12, 30)) == (y, 12, 30)
    except Exception:
        return False

def national_id_ok(nid):
    """The ten-digit Iranian national ID with its check digit."""
    n = clean(nid) or ""
    if not re.fullmatch(r"\d{10}", n) or len(set(n)) == 1:
        return False
    s = sum(int(n[i]) * (10 - i) for i in range(9)) % 11
    return int(n[9]) == (s if s < 2 else 11 - s)

WORDS = {"یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "نیم": 0.5}

def dang(text):
    """A share as a number of dang: «سه دانگ» 3, «یک و نیم دانگ» 1.5, «ششدانگ» 6, «2.5 دانگ» 2.5. Unknown: None."""
    t = clean(text)
    if not t:
        return None
    t = t.replace("دانگ", " ").strip()   # «ششدانگ» becomes «شش»
    if number(t) is not None:
        return number(t)
    parts = [p for p in re.split(r"\s+و\s+|\s+", t) if p]
    if parts and all(p in WORDS for p in parts):
        return sum(WORDS[p] for p in parts)
    return None

def shares_issue(shares):
    """A message when the owners' shares (dang, None = unknown) do not add up to 6, else ""."""
    if not shares:
        return ""
    if any(s is None for s in shares):
        return "سهم برخی مالکین روشن نیست؛ جمع سهم‌ها را نمی‌شود با ۶ دانگ سنجید."
    total = round(sum(shares), 3)
    if abs(total - 6) > 0.001:
        return f"جمع سهم مالکین {total:g} دانگ است، نه ۶ دانگ."
    return ""

def validate(key, raw):
    """A value as typed or read -> (the cleaned value, what is wrong with it). Used for what was extracted and for
    what the reviewer typed."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, []
    value = clean(str(raw))
    if key in ("issue_date", "date"):
        good, why = jalali_date(value)
        return (good, []) if good else (value, [why])
    if key == "national_id":
        value = re.sub(r"\D", "", value)
        return value, ([] if national_id_ok(value) else ["شماره ملی معتبر نیست (رقم کنترل یا طول آن جور نیست)."])
    if key == "area":
        n = number(value)
        if n is None:
            return value, ["مساحت باید عدد باشد."]
        return (int(n) if n == int(n) else n), []
    if key == "share":
        return value, ([] if dang(value) is not None else ["سهم به دانگ خوانده نشد."])
    if key in NUMERIC and not re.fullmatch(r"\d+", value):
        return value, ["باید فقط عدد باشد."]
    return value, []
