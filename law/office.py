"""The law office this demo is for. Every name the assistant shows or puts in a prompt comes from here.

Settings live in law.json (path: LAW_PATH). Like the other assistants it holds only the office being shown; without
the file the assistant opens on its setup form.
"""
import json, os

PATH = os.getenv("LAW_PATH", "law.json")
DEFAULT = {
    "name": "دفتر وکالت پارسا",
    "place": "خیابان مطهری، تهران",
    "owner_title": "آقای", "owner_name": "دکتر کامران پارسا",
    "associate_title": "خانم", "associate_name": "نیلوفر احمدی",
    "secretary_title": "خانم", "secretary_name": "مریم صالحی",
}
FIELDS = {"name": ("نام دفتر", 40), "place": ("نشانی کوتاه", 40), "owner_name": ("نام وکیل", 40),
          "associate_name": ("نام همکار وکیل", 40), "secretary_name": ("نام منشی", 40)}
TITLES = ("آقای", "خانم")
PEOPLE = ("owner", "associate", "secretary")

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
