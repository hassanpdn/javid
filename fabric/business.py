"""The fabric wholesaler this demo is for. Every name the fabric assistant shows or puts in a prompt comes from here.

Settings live in fabric.json (path: FABRIC_PATH). Like school.json it holds only the business being shown.
Without the file the fabric assistant opens on its setup form.
"""
import json, os

PATH = os.getenv("FABRIC_PATH", "fabric.json")

DEFAULT = {
    "name": "پارچه‌سرای مهرگان",
    "place": "بازار بزرگ تهران",
    "owner_title": "آقای", "owner_name": "حمید صدری",
    "seller_title": "آقای", "seller_name": "سعید نادری",
    "accountant_title": "خانم", "accountant_name": "نرگس توکلی",
}
FIELDS = {  # key: (label, longest allowed length)
    "name": ("نام فروشگاه", 40), "place": ("نشانی کوتاه", 40),
    "owner_name": ("نام صاحب کار", 40), "seller_name": ("نام فروشنده", 40), "accountant_name": ("نام حسابدار", 40),
}
TITLES = ("آقای", "خانم")

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
    """Back to the first run: the fabric assistant opens on its setup form."""
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
    for key in ("owner_title", "seller_title", "accountant_title"):
        if data.get(key) not in TITLES:
            raise ValueError("عنوان (آقای یا خانم) را انتخاب کنید")
        out[key] = data[key]
    return out

def person(role, s=None):
    s = s or current()
    return f"{s[role + '_title']} {s[role + '_name']}"

def public(s=None):
    """What the setup and login pages may show before anyone logs in."""
    s = s or current()
    return {**s, "owner": person("owner", s), "seller": person("seller", s), "accountant": person("accountant", s)}
