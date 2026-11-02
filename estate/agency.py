"""The agency this demo is for. Every name the real estate assistant shows or puts in a prompt comes from here.

Settings live in estate.json (path: ESTATE_PATH). Like fabric.json it holds only the agency being shown; without the
file the assistant opens on its setup form. The neighbourhoods are fixed for the demo (west Tehran): the demo data,
prices and the website are built for them.
"""
import json, os

PATH = os.getenv("ESTATE_PATH", "estate.json")
HOODS = ["پونک", "شهرک غرب", "سعادت‌آباد", "جنت‌آباد", "شهران"]

DEFAULT = {
    "name": "مشاور املاک آرمان",
    "place": "پونک، تهران",
    "owner_title": "آقای", "owner_name": "مسعود کرمانی",
    "agent1_title": "خانم", "agent1_name": "الهام رستمی",
    "agent2_title": "آقای", "agent2_name": "بهروز سلیمانی",
}
FIELDS = {  # key: (label, longest allowed length)
    "name": ("نام بنگاه", 40), "place": ("نشانی کوتاه", 40),
    "owner_name": ("نام مدیر بنگاه", 40), "agent1_name": ("نام مشاور اول", 40), "agent2_name": ("نام مشاور دوم", 40),
}
TITLES = ("آقای", "خانم")
PEOPLE = ("owner", "agent1", "agent2")

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
    """Back to the first run: the assistant opens on its setup form."""
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
    """What the setup and login pages may show before anyone logs in."""
    s = s or current()
    return {**s, "hoods": HOODS, **{p: person(p, s) for p in PEOPLE}}
