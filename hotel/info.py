"""The hotel this demo is for. Every name the assistant shows or puts in a prompt comes from here.

Settings live in hotel.json (path: HOTEL_PATH). Like the other assistants it holds only the hotel being shown;
without the file the assistant opens on its setup form.
"""
import json, os

PATH = os.getenv("HOTEL_PATH", "hotel.json")
DEFAULT = {
    "name": "هتل موج آبی",
    "place": "ساحل نوشهر، مازندران",
    "manager_title": "آقای", "manager_name": "بهرام کیانی",
    "reservation_title": "خانم", "reservation_name": "نگار سلیمی",
    "reception_title": "آقای", "reception_name": "امید فروتن",
    "housekeeping_title": "خانم", "housekeeping_name": "فرشته داوری",
}
FIELDS = {"name": ("نام هتل", 40), "place": ("نشانی کوتاه", 40), "manager_name": ("نام مدیر", 40),
          "reservation_name": ("نام کارشناس رزرو", 40), "reception_name": ("نام مسئول پذیرش", 40), "housekeeping_name": ("نام سرپرست خانه‌داری", 40)}
TITLES = ("آقای", "خانم")
PEOPLE = ("manager", "reservation", "reception", "housekeeping")

def _read():
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def is_set_up():
    return "current" in _read()

def current():
    return {**DEFAULT, **_read().get("current", {})}

def save(settings):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump({"current": settings}, f, ensure_ascii=False, indent=1)

def forget():
    try:
        os.remove(PATH)
    except OSError:
        pass

def clean(data):
    """Check the setup form. Returns the cleaned settings or raises ValueError with a message for the user."""
    out = {}
    for key, (label, longest) in FIELDS.items():
        value = " ".join(str(data.get(key, "")).split())
        if not value:
            raise ValueError(f"«{label}» را وارد کنید")
        if len(value) > longest:
            raise ValueError(f"«{label}» حداکثر {longest} حرف باشد")
        out[key] = value
    for p in PEOPLE:
        if data.get(p + "_title") not in TITLES:
            raise ValueError("عنوان (آقای یا خانم) را انتخاب کنید")
        out[p + "_title"] = data[p + "_title"]
    return out

def person(role, s=None):
    s = s or current()
    return f"{s[role + '_title']} {s[role + '_name']}"

def public(s=None):
    s = s or current()
    return {**s, **{p: person(p, s) for p in PEOPLE}}
