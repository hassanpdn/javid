"""Every number and date the eco-lodge's panel, its website and the model use, computed by code from lodge.db.

A night's price is the unit's own price, or its weekend price on Wednesday and Thursday nights, plus a set amount for
each person beyond the unit's beds (up to its capacity). A stay that includes a weekend night must be at least
MIN_WEEKEND nights. The deposit is DEPOSIT percent of the total, due DEPOSIT_HOURS after the host approves. All of
these are settings with demo defaults; a real lodge enters its own.
"""
import json
from datetime import date, datetime, timedelta
from jalali import to_jalali, MONTHS
from . import store

KINDS = {"dome": "اتاق گنبدی", "court": "اتاق حیاط", "family": "سوئیت خانوادگی", "tower": "اتاق بادگیر", "garden": "خانه‌ی باغ", "roof": "کلبه‌ی بام"}
STATUS = {"requested": "منتظر تأیید میزبان", "approved": "منتظر بیعانه", "paid": "رسید فرستاده شد", "confirmed": "قطعی",
          "rejected": "تأیید نشد", "cancelled": "لغو شد"}
HOLDS = ("requested", "approved", "paid", "confirmed")      # these keep the unit for their nights
SOURCES = {"site": "سایت", "whatsapp": "واتس‌اپ", "instagram": "اینستاگرام", "phone": "تلفن", "booking_site": "سایت رزرو"}
DEFAULTS = {"extra_person": 600_000, "deposit": 50, "deposit_hours": 24, "min_weekend": 2}
ARTS = ("dome", "court", "family", "tower", "garden", "roof")

def today():
    return store.today()

def settings(c):
    row = c.execute("SELECT value FROM meta WHERE key = 'settings'").fetchone()
    return {**DEFAULTS, **(json.loads(row["value"]) if row else {})}

def money(v):
    """2_800_000 -> «2.8 میلیون تومان», 600_000 -> «600 هزار تومان»."""
    v = int(round(v or 0))
    if v >= 1_000_000:
        m = v / 1_000_000
        return (f"{m:.1f}".rstrip("0").rstrip(".") if m < 100 and v % 1_000_000 else str(round(m))) + " میلیون تومان"
    if v >= 1000:
        return f"{round(v / 1000)} هزار تومان"
    return f"{v} تومان"

def jfull(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{y}/{m:02d}/{d:02d}"

def jday(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{d} {MONTHS[m - 1]}"

WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]

def jlong(iso):
    return f"{WEEKDAYS[date.fromisoformat(iso[:10]).weekday()]} {jday(iso)}"

def add(iso, n):
    return (date.fromisoformat(iso[:10]) + timedelta(days=n)).isoformat()

def nights_of(arrive, depart):
    a, d = date.fromisoformat(arrive), date.fromisoformat(depart)
    return [(a + timedelta(days=i)).isoformat() for i in range((d - a).days)]

def weekend(iso):
    return date.fromisoformat(iso).weekday() in (2, 3)

def stay_text(b):
    return f"{jday(b['arrive'])} تا {jday(b['depart'])} ({len(nights_of(b['arrive'], b['depart']))} شب)"

def days_ago(iso):
    return (today() - date.fromisoformat(iso[:10])).days

# ---------- prices and free nights ----------

def unit_price(u, night):
    return u["weekend_price"] if weekend(night) else u["price"]

def quote(c, u, arrive, depart, people):
    """The price of a stay in a unit, night by night, with why it may not be booked."""
    s = settings(c)
    nights = nights_of(arrive, depart)
    if people > u["capacity"]:
        return {"ok": False, "why": f"{u['name']} حداکثر برای {u['capacity']} نفر است"}
    if any(weekend(n) for n in nights) and len(nights) < s["min_weekend"]:
        return {"ok": False, "why": f"رزرو شب‌های چهارشنبه و پنجشنبه دست‌کم {s['min_weekend']} شب است"}
    extra = max(0, people - u["beds"])
    rows = [{"date": n, "amount": unit_price(u, n) + extra * s["extra_person"]} for n in nights]
    total = sum(r["amount"] for r in rows)
    how = [f"{jlong(r['date'])}: {money(unit_price(u, r['date']))}" + (" (آخر هفته)" if weekend(r["date"]) else "") +
           (f" + {extra} نفر اضافه {money(extra * s['extra_person'])}" if extra else "") for r in rows]
    deposit = round(total * s["deposit"] / 100 / 10_000) * 10_000
    return {"ok": True, "nights": rows, "total": total, "total_text": money(total), "deposit": deposit, "deposit_text": money(deposit),
            "how": how + [f"= جمع {len(rows)} شب: {money(total)}", f"بیعانه ({s['deposit']} درصد): {money(deposit)}"]}

def busy(c, unit_id, arrive, depart, ignore=None):
    """Why a unit is not free for these nights ("" when it is): another booking, or a closed date."""
    q = "SELECT * FROM bookings WHERE unit_id = ? AND status IN ('requested', 'approved', 'paid', 'confirmed') AND arrive < ? AND depart > ?"
    args = [unit_id, depart, arrive]
    if ignore:
        q += " AND id != ?"; args.append(ignore)
    if c.execute(q, args).fetchone():
        return "این شب‌ها رزرو شده است"
    b = c.execute("SELECT * FROM blocks WHERE unit_id = ? AND start < ? AND end > ?", (unit_id, depart, arrive)).fetchone()
    if b:
        return f"این شب‌ها بسته است ({b['note'] or 'میزبان بسته است'})"
    return ""

def calendar(c, u, start, days=42):
    """Each night: free or not, and its price (the website's calendar and the host's)."""
    out = []
    for n in nights_of(start, add(start, days)):
        taken = busy(c, u["id"], n, add(n, 1))
        out.append({"date": n, "j": jfull(n), "day": jday(n), "weekday": WEEKDAYS[date.fromisoformat(n).weekday()], "weekend": weekend(n),
                    "free": not taken and bool(u["active"]), "price": unit_price(u, n), "price_text": money(unit_price(u, n))})
    return out

def search(c, arrive, depart, people):
    """The active units free for every night of the stay and big enough, cheapest first, each with its quote."""
    out = []
    for u in c.execute("SELECT * FROM units WHERE active = 1 ORDER BY sort, id"):
        u = dict(u)
        if busy(c, u["id"], arrive, depart):
            continue
        q = quote(c, u, arrive, depart, people)
        if q["ok"]:
            out.append(unit_view(c, u) | {"quote": q})
    return sorted(out, key=lambda x: x["quote"]["total"])

# ---------- views ----------

def photo_urls(c, unit_id):
    return [f"/lodge/public/photo/{p['file']}" for p in c.execute("SELECT file FROM photos WHERE unit_id = ? ORDER BY sort, id", (unit_id,))]

def rating(c, unit_id=None):
    q, args = "SELECT AVG(stars) a, COUNT(*) n FROM reviews WHERE status = 'shown'", []
    if unit_id:
        q += " AND unit_id = ?"; args.append(unit_id)
    r = c.execute(q, args).fetchone()
    return {"avg": round(r["a"], 1) if r["a"] else None, "count": r["n"]}

def unit_view(c, u):
    u = dict(u)
    return u | {"kind_text": KINDS.get(u["kind"], u["kind"]), "price_text": money(u["price"]), "weekend_text": money(u["weekend_price"]),
                "amenities": [a for a in (u["amenities"] or "").split("،") if a.strip()], "photos": photo_urls(c, u["id"]), "rating": rating(c, u["id"])}

def review_view(c, r):
    g = c.execute("SELECT name FROM guests WHERE id = ?", (r["guest_id"],)).fetchone()
    u = c.execute("SELECT name FROM units WHERE id = ?", (r["unit_id"],)).fetchone()
    first = (g["name"].split() or [""])[0] if g else ""
    return dict(r) | {"guest": first, "guest_full": g["name"] if g else "", "unit": u["name"] if u else "", "day": jday(r["at"]), "date": jfull(r["at"])}

def booking_view(c, b):
    b = dict(b)
    g = c.execute("SELECT * FROM guests WHERE id = ?", (b["guest_id"],)).fetchone()
    u = c.execute("SELECT * FROM units WHERE id = ?", (b["unit_id"],)).fetchone()
    t = today().isoformat()
    over = b["depart"] <= t
    rec = c.execute("SELECT * FROM receipts WHERE booking_id = ? ORDER BY id DESC LIMIT 1", (b["id"],)).fetchone()
    rev = c.execute("SELECT * FROM reviews WHERE booking_id = ?", (b["id"],)).fetchone()
    unread = c.execute("SELECT COUNT(*) FROM messages WHERE booking_id = ? AND side = 'guest' AND seen = 0", (b["id"],)).fetchone()[0]
    return b | {"guest": g["name"] if g else "", "phone": g["phone"] if g else "", "has_account": bool(g and g["password"]), "unit": u["name"] if u else "",
                "art": u["art"] if u else "dome", "status_text": ("اقامت تمام شد" if b["status"] == "confirmed" and over else
                                                                     "مهمان در اقامتگاه" if b["status"] == "confirmed" and b["arrive"] <= t else STATUS[b["status"]]),
                "stay_text": stay_text(b), "arrive_text": jlong(b["arrive"]), "depart_text": jlong(b["depart"]), "arrive_j": jfull(b["arrive"]),
                "total_text": money(b["total"]), "deposit_text": money(b["deposit"]), "source_text": SOURCES.get(b["source"], b["source"]),
                "deposit_due_text": (jlong(b["deposit_due"]) + " ساعت " + b["deposit_due"][11:16]) if b["deposit_due"] else "",
                "over": over, "receipt": dict(rec) if rec else None,
                "review": review_view(c, rev) if rev else None, "unread": unread, "nights_count": len(nights_of(b["arrive"], b["depart"]))}

def refund(c, b):
    """What goes back when a booking is cancelled now, by the days left: more than 7 days 90% of what was paid,
    3 to 7 days 50%, less than 3 nothing. Paid means a deposit the host confirmed."""
    days = (date.fromisoformat(b["arrive"]) - today()).days
    paid = b["deposit"] if b["status"] == "confirmed" else 0
    pct = 90 if days > 7 else 50 if days >= 3 else 0
    return {"days": days, "paid": paid, "percent": pct, "amount": round(paid * pct / 100 / 10_000) * 10_000,
            "rule": "بیش از ۷ روز به ورود: ۹۰ درصد بیعانه برمی‌گردد؛ ۳ تا ۷ روز: ۵۰ درصد؛ کمتر از ۳ روز: هیچ."}

# ---------- what is waiting ----------

def feedback_due(c):
    """Stays that ended in the last 30 days with no review yet: ask the guest how it was."""
    t = today().isoformat()
    return [booking_view(c, b) for b in c.execute("""SELECT b.* FROM bookings b WHERE b.status = 'confirmed' AND b.depart <= ? AND b.depart >= ?
                                                     AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.booking_id = b.id) ORDER BY b.depart DESC""",
                                                  (t, add(t, -30)))]

def alerts(c):
    """The host's work for today, most urgent first."""
    t, st, out = today().isoformat(), store.stamp(), []
    for b in c.execute("SELECT * FROM bookings WHERE status = 'requested' ORDER BY created"):
        v = booking_view(c, b)
        hours = int((datetime.fromisoformat(st) - datetime.fromisoformat(v["created"])).total_seconds() // 3600)
        out.append({"type": "request", "tone": "warning", "icon": "calendar", "booking_id": v["id"], "order": 1,
                    "title": f"درخواست رزرو {v['guest']}: {v['unit']}، {v['stay_text']}",
                    "detail": f"از {v['source_text']}، {v['adults']} نفر، {v['total_text']}. " + (f"{hours} ساعت منتظر جواب است." if hours else "همین حالا رسید.")})
    for b in c.execute("SELECT * FROM bookings WHERE status = 'paid' ORDER BY id"):
        v = booking_view(c, b)
        out.append({"type": "receipt", "tone": "info", "icon": "file", "booking_id": v["id"], "order": 1,
                    "title": f"رسید بیعانه‌ی {v['guest']} رسیده است ({v['deposit_text']})",
                    "detail": f"{v['unit']}، {v['stay_text']}. واریز را در حساب ببینید و رزرو را قطعی کنید."})
    for b in c.execute("SELECT * FROM bookings WHERE status = 'approved' AND deposit_due < ? ORDER BY arrive", (st,)):
        v = booking_view(c, b)
        out.append({"type": "deposit", "tone": "danger", "icon": "clock", "booking_id": v["id"], "order": 2,
                    "title": f"مهلت بیعانه‌ی {v['guest']} گذشته است",
                    "detail": f"{v['unit']}، {v['stay_text']}. مهلت {v['deposit_due_text']} بود. تماس بگیرید یا رزرو را لغو کنید تا اتاق آزاد شود."})
    for b in c.execute("SELECT * FROM bookings WHERE status IN ('confirmed', 'approved', 'paid') AND arrive IN (?, ?) ORDER BY arrive", (t, add(t, 1))):
        v = booking_view(c, b)
        out.append({"type": "arrival", "tone": "success" if v["status"] == "confirmed" else "warning", "icon": "users", "booking_id": v["id"], "order": 3,
                    "title": f"{'امروز' if v['arrive'] == t else 'فردا'} {v['guest']} به {v['unit']} می‌آید",
                    "detail": f"{v['adults']} نفر، {v['nights_count']} شب. " + ("بیعانه قطعی است." if v["status"] == "confirmed" else f"هنوز {v['status_text']}.") +
                              (f" یادداشت: {v['note']}" if v["note"] else "")})
    for b in c.execute("""SELECT DISTINCT b.* FROM bookings b JOIN messages m ON m.booking_id = b.id WHERE m.side = 'guest' AND m.seen = 0"""):
        v = booking_view(c, b)
        last = c.execute("SELECT text FROM messages WHERE booking_id = ? AND side = 'guest' ORDER BY id DESC LIMIT 1", (b["id"],)).fetchone()
        out.append({"type": "message", "tone": "info", "icon": "message", "booking_id": v["id"], "order": 2,
                    "title": f"پیام {v['guest']}: «{last['text']}»", "detail": f"{v['unit']}، {v['stay_text']}."})
    for r in c.execute("SELECT * FROM reviews WHERE status = 'waiting' ORDER BY at"):
        v = review_view(c, r)
        out.append({"type": "review", "tone": "warning" if r["stars"] <= 3 else "info", "icon": "heart", "review_id": r["id"], "booking_id": r["booking_id"],
                    "order": 4, "title": f"نظر جدید از {v['guest_full']}: {r['stars']} ستاره برای {v['unit']}",
                    "detail": f"«{r['text']}». پیش از نمایش در سایت، تأیید یا پنهانش کنید؛ می‌توانید پاسخ هم بنویسید."})
    for v in feedback_due(c):
        if not v["feedback_asked"]:
            out.append({"type": "feedback", "tone": "secondary", "icon": "sparkles", "booking_id": v["id"], "order": 5,
                        "title": f"سفر {v['guest']} {days_ago(v['depart']) or 'امروز'}{' روز پیش' if days_ago(v['depart']) else ''} تمام شد؛ نظرش را بپرسید",
                        "detail": f"{v['unit']}، {v['stay_text']}. پیام آماده است؛ در پنل مهمان هم فرم نظر باز شده است."})
    return sorted(out, key=lambda a: (a["order"], a["title"]))

def stats(c):
    t = today().isoformat()
    units = [dict(u) for u in c.execute("SELECT * FROM units WHERE active = 1")]
    nights = nights_of(t, add(t, 30))
    sold = c.execute("""SELECT arrive, depart FROM bookings WHERE status IN ('confirmed', 'paid', 'approved') AND arrive < ? AND depart > ?""",
                     (add(t, 30), t)).fetchall()
    taken = sum(1 for n in nights for b in sold if b["arrive"] <= n < b["depart"])
    cap = len(units) * len(nights) or 1
    month = add(t, -30)
    got = c.execute("SELECT COALESCE(SUM(total), 0) s, COUNT(*) n FROM bookings WHERE status = 'confirmed' AND depart > ? AND depart <= ?", (month, t)).fetchone()
    r = rating(c)
    waiting = c.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('requested', 'paid')").fetchone()[0]
    return [
        {"key": "occupancy", "label": "پر بودن سی شب آینده", "value": f"{round(100 * taken / cap)} درصد", "sub": f"{taken} از {cap} شب-واحد", "icon": "calendar",
         "tone": "primary", "how": [f"واحدهای فعال: {len(units)}", f"شب‌ها: {len(nights)}", f"شب‌های رزروشده (قطعی، رسید فرستاده، منتظر بیعانه): {taken}",
                                    f"= {taken} از {cap}"]},
        {"key": "income", "label": "درآمد سی روز گذشته", "value": money(got["s"]), "sub": f"{got['n']} اقامت تمام‌شده", "icon": "chart", "tone": "success",
         "how": [f"جمع رزروهای قطعی که در سی روز گذشته تمام شده‌اند: {money(got['s'])}", f"تعداد: {got['n']}"]},
        {"key": "rating", "label": "امتیاز مهمانان", "value": f"{r['avg'] or '-'} از ۵", "sub": f"{r['count']} نظر در سایت", "icon": "heart", "tone": "warning",
         "how": [f"میانگین ستاره‌های نظرهای نمایش‌داده‌شده: {r['avg'] or '-'}", f"تعداد: {r['count']}"]},
        {"key": "waiting", "label": "منتظر شما", "value": str(waiting), "sub": "درخواست و رسید", "icon": "clock", "tone": "danger" if waiting else "secondary",
         "how": [f"درخواست‌های منتظر تأیید و رسیدهای منتظر بررسی: {waiting}"]},
    ]

def overview(c):
    t = today().isoformat()
    return {"today": jfull(t), "today_long": jlong(t), "stats": stats(c), "alerts": alerts(c)}

def brief_facts(c):
    o = overview(c)
    lines = [f"امروز: {o['today_long']} {o['today']}"] + [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]]
    lines += ["کارهای امروز:"] + [f"{i + 1}. {a['title']}" for i, a in enumerate(o["alerts"][:6])]
    return "\n".join(lines), o

def events(c, after=0, limit=40, booking_id=None):
    q, args = "SELECT * FROM events WHERE id > ?", [after]
    if booking_id:
        q += " AND booking_id = ?"; args.append(booking_id)
    rows = c.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit)).fetchall()
    t = today().isoformat()
    return [{"id": e["id"], "kind": e["kind"], "text": e["text"], "who": e["who"], "role": e["role"], "today": e["at"][:10] == t,
             "day": jday(e["at"]), "time": e["at"][11:16], "booking_id": e["booking_id"]} for e in rows]
