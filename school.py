"""The school this demo is set up for. Every name the app shows or puts in a prompt comes from here.

The settings live in school.json (path: SCHOOL_PATH). It holds only the school being shown: no list of
earlier schools, so one school never sees another's name. Without the file the demo is the default (Javid),
whose details are only filled in by the setup form's «تنظیمات پیش‌فرض» button.
"""
import json, os

PATH = os.getenv("SCHOOL_PATH", "school.json")

DEFAULT = {
    "name": "جاوید",                  # shown as «دبستان جاوید»
    "gender": "girls",                # girls / boys: student names, teacher names and titles
    "city": "تهران",
    "district": "منطقه ۳",            # letters come from «اداره آموزش و پرورش منطقه ۳ تهران»
    "manager_title": "آقای", "manager_name": "دکتر انوشه‌پور",
    "counselor_title": "خانم", "counselor_name": "مریم کاظمی",
    "staff_title": "خانم", "staff_name": "زهره امینی",
}
FIELDS = {  # key: (label, longest allowed length)
    "name": ("نام مدرسه", 40), "city": ("شهر", 30), "district": ("منطقه", 30),
    "manager_name": ("نام مدیر", 40), "counselor_name": ("نام مشاور", 40), "staff_name": ("نام کارمند اداری", 40),
}
TITLES = ("آقای", "خانم")

# Runtime switches for the roles outside the school staff. With both off the app is an internal
# CRM for the school's own people. They change at once (no data rebuild) and survive a new setup.
FEATURES = {"parents": True, "students": True}
FEATURE_ROLE = {"parents": "parent", "students": "student"}

def _read():
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def current():
    """The active school's settings (Javid when nothing was set up)."""
    return {**DEFAULT, **_read().get("current", {})}

def _write(data):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

def features():
    """Which outside roles are on: {"parents": bool, "students": bool}"""
    return {**FEATURES, **_read().get("features", {})}

def set_features(changes):
    data = _read()
    data["features"] = {k: bool(changes.get(k, v)) for k, v in features().items()}
    _write(data)
    return data["features"]

def role_enabled(role):
    """False for the parent or student role while its switch is off; staff roles are always on."""
    return all(on or FEATURE_ROLE[k] != role for k, on in features().items())

def is_set_up():
    """False on the very first run: the app then opens on the setup form."""
    return "current" in _read()

def clean(data):
    """Check the form. Returns the cleaned settings or raises ValueError with a message for the user."""
    out = {}
    for key, (label, longest) in FIELDS.items():
        value = " ".join(str(data.get(key, "")).split())
        if not value:
            raise ValueError(f"«{label}» را وارد کنید")
        if len(value) > longest:
            raise ValueError(f"«{label}» حداکثر {longest} حرف باشد")
        out[key] = value
    if data.get("gender") not in ("girls", "boys"):
        raise ValueError("دخترانه یا پسرانه بودن مدرسه را انتخاب کنید")
    out["gender"] = data["gender"]
    for key in ("manager_title", "counselor_title", "staff_title"):
        if data.get(key) not in TITLES:
            raise ValueError("عنوان (آقای یا خانم) را انتخاب کنید")
        out[key] = data[key]
    out["name"] = out["name"].removeprefix("دبستان ").strip()   # people often type «دبستان ...»
    return out

def save(settings):
    """Make these settings the active school (the previous school is forgotten; the role switches stay)."""
    _write({"current": settings, "features": features()})

def forget():
    """Back to the first run: no school set up (the role switches stay)."""
    _write({"features": features()})

# ---------- names used across the app ----------

def full_name(s=None):
    return f"دبستان {(s or current())['name']}"

def signature(s=None):
    return f"با احترام، مدیریت {full_name(s)}"

def education_office(s=None):
    s = s or current()
    return f"اداره آموزش و پرورش {s['district']} {s['city']}"

def manager(s=None):
    s = s or current()
    return f"{s['manager_title']} {s['manager_name']}"

def counselor(s=None):
    s = s or current()
    return f"{s['counselor_title']} {s['counselor_name']}"

def staff_member(s=None):
    s = s or current()
    return f"{s['staff_title']} {s['staff_name']}"

def public(s=None):
    """What the login and setup pages may show before anyone logs in."""
    s = s or current()
    return {**s, "full_name": full_name(s), "manager": manager(s), "counselor": counselor(s), "staff": staff_member(s)}
