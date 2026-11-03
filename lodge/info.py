"""The eco-lodge this demo is for, and the words of its website. Every name the assistant shows or puts in a prompt
comes from here.

Settings live in lodge.json (path: LODGE_PATH). Unlike the other demos, the lodge is not forgotten on each visit of
the live site: its website is public, and guests make accounts and leave reviews there (Hassan's choice). It is built
again only from the setup form.
"""
import json, os

PATH = os.getenv("LODGE_PATH", "lodge.json")
DEFAULT = {
    "name": "اقامتگاه بوم‌گردی خانه‌ی گلین",
    "place": "روستای خرانق، یزد",
    "host_title": "خانم", "host_name": "گلین رحمانی",
    "helper_title": "آقای", "helper_name": "یوسف رحمانی",
}
SITE_DEFAULT = {
    "tagline": "خانه‌ای خشتی در دل کویر؛ شب‌های پرستاره، نان تازه و آرامش",
    "story": ("این خانه‌ی صدساله را خانواده‌ی رحمانی با همان خشت و گل قدیم دوباره ساخته‌اند. صبح‌ها نان تنوری از تنور حیاط "
              "می‌آید، عصرها تا تپه‌های شنی پیاده می‌رویم و شب‌ها روی بام، کهکشان راه شیری را بی هیچ نور شهری می‌بینیم."),
    "rules": "تحویل اتاق از ساعت ۱۴ و تخلیه تا ساعت ۱۲. از ساعت ۲۳ تا ۷ سکوت حیاط را رعایت کنید. همراه داشتن کارت ملی برای همه‌ی بزرگسالان لازم است.",
    "phone": "۰۹۱۳۰۰۰۰۰۰۰",
    "payment": "پس از تأیید رزرو، شماره‌ی کارت برای واریز بیعانه در همین صفحه نشان داده می‌شود.",
    "card": "۰۰۰۰ ۰۰۰۰ ۰۰۰۰ ۰۰۰۰ (نمایشی؛ واریز نکنید)",
}
FIELDS = {"name": ("نام اقامتگاه", 40), "place": ("نشانی کوتاه", 40), "host_name": ("نام میزبان", 40), "helper_name": ("نام همکار", 40)}
TITLES = ("آقای", "خانم")
PEOPLE = ("host", "helper")

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

def site():
    return {**SITE_DEFAULT, **_read().get("site", {})}

def save(settings, site_words=None):
    data = _read()
    data["current"] = settings
    if site_words is not None:
        data["site"] = site_words
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

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
