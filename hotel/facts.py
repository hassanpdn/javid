"""Every number and date the hotel's panels and the model use, computed by code from hotel.db.

Prices: each room type has a base price a night (settings), times the season (Nowruz, summer, the quiet months)
and the weekend (Wednesday and Thursday nights), plus an extra bed, plus meals per person for half or full board;
children under CHILD_FREE are free and take no bed. A booking keeps the price of each of its nights (bookings.nights),
and closing the day posts tonight's price to the folio of every room in the house. The seasons, prices and rules here
are the demo's own: a real hotel enters its own.
"""
import json
from datetime import date, datetime, timedelta
from jalali import to_jalali, MONTHS
from . import store

# type: (name, people in its beds, most people with an extra bed, units)
TYPES = {
    "dbl_garden": ("دوتخته رو به باغ", 2, 3),
    "dbl_sea": ("دوتخته رو به دریا", 2, 3),
    "triple": ("سه‌تخته", 3, 4),
    "suite": ("سوئیت رو به دریا", 4, 5),
    "villa": ("ویلای ساحلی", 6, 8),
}
BOARDS = {"BB": "با صبحانه", "HB": "نیم‌پانسیون (صبحانه و شام)", "FB": "پانسیون کامل (سه وعده)"}
SOURCES = {"phone": "تلفن", "whatsapp": "واتس‌اپ", "walkin": "حضوری", "site": "سایت هتل", "agency": "آژانس", "ota": "سایت رزرو", "company": "شرکت"}
STATUS = {"tentative": "موقت", "confirmed": "قطعی", "in_house": "مقیم", "out": "رفته", "cancelled": "لغو شد", "noshow": "نیامد"}
ROOM_STATUS = {"clean": "تمیز", "dirty": "کثیف", "inspected": "بازرسی‌شده"}
CHARGES = {"room": "اقامت", "restaurant": "رستوران", "minibar": "مینی‌بار", "spa": "اسپا و استخر", "transfer": "ترانسفر", "laundry": "لباسشویی", "other": "سایر"}
METHODS = {"card": "کارت‌خوان", "transfer": "کارت به کارت", "cash": "نقد", "company": "حساب شرکت"}
ACTIVE = ("tentative", "confirmed", "in_house")
CHILD_FREE = 6               # children under this age are free and take no bed
CHECK_IN, CHECK_OUT = "14:00", "12:00"
DEFAULTS = {"prices": {"dbl_garden": 4_500_000, "dbl_sea": 6_200_000, "triple": 7_000_000, "suite": 14_500_000, "villa": 26_000_000},
            "extra_bed": 1_600_000, "HB": 950_000, "FB": 1_900_000, "deposit": 30, "max_discount": 15}

def today():
    return store.today()

def settings(c):
    row = c.execute("SELECT value FROM meta WHERE key = 'settings'").fetchone()
    s = json.loads(row["value"]) if row else {}
    return {**DEFAULTS, **s, "prices": {**DEFAULTS["prices"], **s.get("prices", {})}}

def money(v):
    """38_000_000 -> «38 میلیون تومان», 1_600_000 -> «1.6 میلیون تومان», 950_000 -> «950 هزار تومان»."""
    v = int(round(v or 0))
    sign, v = ("منفی " if v < 0 else ""), abs(v)
    if v >= 1_000_000_000:
        b, m = divmod(round(v / 1_000_000), 1000)
        return sign + f"{b} میلیارد" + (f" و {m} میلیون" if m else "") + " تومان"
    if v >= 1_000_000:
        m = v / 1_000_000
        return sign + (f"{m:.1f}".rstrip("0").rstrip(".") if m < 100 and v % 1_000_000 else str(round(m))) + " میلیون تومان"
    if v >= 1000:
        return sign + f"{round(v / 1000)} هزار تومان"
    return sign + f"{v} تومان"

def jfull(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{y}/{m:02d}/{d:02d}"

def jday(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{d} {MONTHS[m - 1]}"

WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]   # date.weekday(): Monday is 0

def jlong(iso):
    return f"{WEEKDAYS[date.fromisoformat(iso[:10]).weekday()]} {jday(iso)}"

def day_word(iso):
    n = (date.fromisoformat(iso[:10]) - today()).days
    return "امروز" if n == 0 else "فردا" if n == 1 else "دیروز" if n == -1 else jlong(iso)

def add(iso, n):
    return (date.fromisoformat(iso[:10]) + timedelta(days=n)).isoformat()

def nights_of(arrive, depart):
    a, d = date.fromisoformat(arrive), date.fromisoformat(depart)
    return [(a + timedelta(days=i)).isoformat() for i in range((d - a).days)]

def type_name(t):
    return TYPES.get(t, (t,))[0]

def stay_text(b):
    n = len(nights_of(b["arrive"], b["depart"]))
    return f"{jday(b['arrive'])} تا {jday(b['depart'])} ({n} شب)"

# ---------- prices ----------

def season(iso):
    """(name, factor) of a night."""
    _, m, d = to_jalali(date.fromisoformat(iso))
    if (m == 12 and d >= 25) or (m == 1 and d <= 15):
        return "نوروز", 1.6
    if m in (4, 5, 6):
        return "تابستان", 1.3
    if m in (8, 9, 10, 11) and not (m == 8 and d < 15):
        return "کم‌مسافر", 0.8
    return "عادی", 1.0

def weekend(iso):
    return date.fromisoformat(iso).weekday() in (2, 3)     # Wednesday and Thursday nights

def people(adults, ages):
    """(people who need a bed, children under CHILD_FREE)"""
    small = sum(1 for a in ages if a < CHILD_FREE)
    return adults + len(ages) - small, small

def quote(c, rtype, arrive, depart, adults, ages=(), board="BB", discount=0.0):
    """The price of a stay, night by night, with every part named (the «از کجا؟» of a quote)."""
    s = settings(c)
    beds, small = people(adults, ages)
    name, base_beds, most = TYPES[rtype]
    if beds > most:
        return {"fits": False, "why": f"{type_name(rtype)} حداکثر برای {most} نفر است"}
    extra = max(0, beds - base_beds)
    kids = [a for a in ages if a >= CHILD_FREE]
    nights, lines = [], []
    for n in nights_of(arrive, depart):
        sname, f = season(n)
        room = round(s["prices"][rtype] * f * (1.2 if weekend(n) else 1) / 10_000) * 10_000
        meals = 0 if board == "BB" else s[board] * adults + s[board] * len(kids) // 2
        amount = room + extra * s["extra_bed"] + meals
        if discount:
            amount = round(amount * (1 - discount / 100) / 10_000) * 10_000
        nights.append({"date": n, "amount": amount})
        why = [sname] + (["آخر هفته"] if weekend(n) else [])
        lines.append(f"{jlong(n)}: اتاق {money(room)} ({'، '.join(why)})" + (f" + تخت اضافه {money(extra * s['extra_bed'])}" if extra else "") +
                     (f" + {BOARDS[board].split(' ')[0]} {money(meals)}" if meals else "") + (f" − {discount:g} درصد" if discount else "") + f" = {money(amount)}")
    total = sum(n["amount"] for n in nights)
    lines.append(f"= جمع {len(nights)} شب: {money(total)}")
    if small:
        lines.append(f"{small} کودک زیر {CHILD_FREE} سال رایگان و بدون تخت")
    return {"fits": True, "nights": nights, "total": total, "total_text": money(total), "how": lines, "extra_beds": extra,
            "deposit": round(total * s["deposit"] / 100 / 10_000) * 10_000}

# ---------- rooms and availability ----------

def rooms(c):
    return {r["id"]: dict(r) for r in c.execute("SELECT * FROM rooms ORDER BY id")}

def ooo_on(room, night):
    return bool(room["ooo_from"]) and room["ooo_from"] <= night < (room["ooo_to"] or "9999")

def overlapping(c, arrive, depart, room_id=None, rtype=None, ignore=None):
    q, args = "SELECT * FROM bookings WHERE status IN ('tentative', 'confirmed', 'in_house') AND arrive < ? AND depart > ?", [depart, arrive]
    if room_id:
        q += " AND room_id = ?"; args.append(room_id)
    if rtype:
        q += " AND type = ?"; args.append(rtype)
    if ignore:
        q += " AND id != ?"; args.append(ignore)
    return [dict(r) for r in c.execute(q, args)]

def availability(c, arrive, depart, ignore=None):
    """{type: {"rooms": sellable units, "free": how many more can be sold for every night, "tight": the fullest night}}"""
    rm, out = rooms(c), {}
    booked = overlapping(c, arrive, depart, ignore=ignore)
    for t in TYPES:
        worst, tight = None, None
        units = [r for r in rm.values() if r["type"] == t]
        for n in nights_of(arrive, depart):
            sell = sum(1 for r in units if not ooo_on(r, n))
            used = sum(1 for b in booked if b["type"] == t and b["arrive"] <= n < b["depart"])
            if worst is None or sell - used < worst:
                worst, tight = sell - used, n
        out[t] = {"rooms": len(units), "free": worst if worst is not None else len(units), "tight": tight}
    return out

def room_free(c, room, arrive, depart, ignore=None):
    if any(ooo_on(room, n) for n in nights_of(arrive, depart)):
        return False
    return not overlapping(c, arrive, depart, room_id=room["id"], ignore=ignore)

def _neighbours(c, room_id, arrive, depart, ignore=None):
    """(the active booking in this room that departs nearest before arrive, the one that arrives nearest after depart)"""
    q = "SELECT * FROM bookings WHERE status IN ('tentative', 'confirmed', 'in_house') AND room_id = ?" + (" AND id != ?" if ignore else "")
    args = (room_id, ignore) if ignore else (room_id,)
    before = c.execute(q + " AND depart <= ? ORDER BY depart DESC LIMIT 1", (*args, arrive)).fetchone()
    after = c.execute(q + " AND arrive >= ? ORDER BY arrive LIMIT 1", (*args, depart)).fetchone()
    return before, after

def suggest_rooms(c, rtype, arrive, depart, guest_id=None, ignore=None, limit=3):
    """The rooms of this type free for the whole stay, best first: rooms that keep the stays back to back (no single
    night left empty between two bookings, which is almost never sold), the room the guest had last time, a room that
    is ready when the guest arrives today."""
    last_room = None
    vip = False
    if guest_id:
        row = c.execute("SELECT room_id FROM bookings WHERE guest_id = ? AND status = 'out' ORDER BY depart DESC LIMIT 1", (guest_id,)).fetchone()
        last_room = row["room_id"] if row else None
        g = c.execute("SELECT vip FROM guests WHERE id = ?", (guest_id,)).fetchone()
        vip = bool(g and g["vip"])
    out = []
    for r in rooms(c).values():
        if r["type"] != rtype or not room_free(c, r, arrive, depart, ignore):
            continue
        score, why = 0, []
        before, after = _neighbours(c, r["id"], arrive, depart, ignore)
        if before and before["depart"] == arrive:
            score += 2; why.append("پشت سر رزرو قبلی این اتاق")
        elif before and add(before["depart"], 1) == arrive:
            score -= 3; why.append("یک شب خالی پیش از ورود می‌ماند")
        if after and after["arrive"] == depart:
            score += 2; why.append("درست پیش از رزرو بعدی این اتاق")
        elif after and add(depart, 1) == after["arrive"]:
            score -= 3; why.append("یک شب خالی پس از خروج می‌ماند")
        if last_room == r["id"]:
            score += 3; why.append("اتاق سفر قبلی همین مهمان")
        if vip and r["floor"] >= 3:
            score += 1; why.append("طبقه‌ی بالا برای مهمان ویژه")
        if arrive == today().isoformat() and r["status"] in ("clean", "inspected"):
            score += 1; why.append("همین حالا آماده است")
        out.append({"room_id": r["id"], "number": r["number"], "score": score, "why": why or ["آزاد در همه‌ی شب‌ها"]})
    return sorted(out, key=lambda x: (-x["score"], x["number"]))[:limit]

def grid(c, start, days=14):
    """The tape chart: a row per room, and each booking as a bar from its first to its last night in view."""
    end = add(start, days)
    who = {g["id"]: g["name"] for g in c.execute("SELECT id, name FROM guests")}
    vips = {g["id"] for g in c.execute("SELECT id FROM guests WHERE vip = 1")}
    cols = [{"date": d, "day": jday(d), "weekday": WEEKDAYS[date.fromisoformat(d).weekday()], "weekend": weekend(d), "today": d == today().isoformat()}
            for d in nights_of(start, end)]
    rows = []
    bookings = [dict(b) for b in c.execute("SELECT * FROM bookings WHERE status IN ('tentative', 'confirmed', 'in_house', 'out') AND arrive < ? AND depart > ? AND room_id IS NOT NULL",
                                           (end, start))]
    for r in rooms(c).values():
        bars = []
        for b in bookings:
            if b["room_id"] != r["id"]:
                continue
            a = max(b["arrive"], start)
            z = min(b["depart"], end)
            bars.append({"id": b["id"], "from": (date.fromisoformat(a) - date.fromisoformat(start)).days, "span": (date.fromisoformat(z) - date.fromisoformat(a)).days,
                         "guest": who.get(b["guest_id"], ""), "status": b["status"], "vip": b["guest_id"] in vips})
        if r["ooo_from"] and r["ooo_from"] < end and (r["ooo_to"] or "9999") > start:
            a, z = max(r["ooo_from"], start), min(r["ooo_to"] or end, end)
            bars.append({"id": None, "ooo": True, "from": (date.fromisoformat(a) - date.fromisoformat(start)).days,
                         "span": (date.fromisoformat(z) - date.fromisoformat(a)).days, "guest": r["ooo_note"] or "تعمیر", "status": "ooo"})
        rows.append({"id": r["id"], "number": r["number"], "type": r["type"], "type_text": type_name(r["type"]), "status": r["status"], "bars": bars})
    unassigned = [booking_view(c, b) for b in c.execute("""SELECT * FROM bookings WHERE status IN ('tentative', 'confirmed') AND room_id IS NULL
                                                           AND arrive < ? AND depart > ? ORDER BY arrive""", (end, start))]
    return {"start": start, "cols": cols, "rows": rows, "unassigned": unassigned}

# ---------- bookings and folios ----------

def folio(c, bid):
    charges = [dict(r) | {"kind_text": CHARGES.get(r["kind"], r["kind"]), "amount_text": money(r["amount"]), "day_text": jfull(r["day"])}
               for r in c.execute("SELECT * FROM charges WHERE booking_id = ? ORDER BY day, id", (bid,))]
    pays = [dict(r) | {"method_text": METHODS.get(r["method"], r["method"]), "amount_text": money(r["amount"]), "day_text": jfull(r["at"])}
            for r in c.execute("SELECT * FROM payments WHERE booking_id = ? ORDER BY at, id", (bid,))]
    ch, pd = sum(x["amount"] for x in charges), sum(x["amount"] for x in pays)
    return {"charges": charges, "payments": pays, "charged": ch, "paid": pd, "balance": ch - pd, "balance_text": money(ch - pd)}

def balance(c, bid):
    ch = c.execute("SELECT COALESCE(SUM(amount), 0) FROM charges WHERE booking_id = ?", (bid,)).fetchone()[0]
    pd = c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE booking_id = ?", (bid,)).fetchone()[0]
    return ch - pd

def paid(c, bid):
    return c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE booking_id = ?", (bid,)).fetchone()[0]

def booking_view(c, b):
    b = dict(b)
    g = c.execute("SELECT * FROM guests WHERE id = ?", (b["guest_id"],)).fetchone() if b["guest_id"] else None
    r = c.execute("SELECT number, status FROM rooms WHERE id = ?", (b["room_id"],)).fetchone() if b["room_id"] else None
    ag = c.execute("SELECT name FROM agencies WHERE id = ?", (b["agency_id"],)).fetchone() if b["agency_id"] else None
    ages = [int(a) for a in (b["children"] or "").split(",") if a]
    n = len(nights_of(b["arrive"], b["depart"]))
    return b | {"guest": g["name"] if g else "بی‌نام (سهمیه)", "phone": g["phone"] if g else "", "vip": bool(g and g["vip"]), "notes": g["notes"] if g else "",
                "room": r["number"] if r else None, "room_status": r["status"] if r else None, "room_status_text": ROOM_STATUS.get(r["status"], "") if r else "",
                "type_text": type_name(b["type"]), "status_text": STATUS.get(b["status"], b["status"]), "board_text": BOARDS.get(b["board"], ""),
                "source_text": (ag["name"] if ag else SOURCES.get(b["source"], b["source"])), "nights_count": n, "ages": ages,
                "people_text": f"{b['adults']} بزرگسال" + (f" و {len(ages)} کودک" if ages else ""),
                "stay_text": stay_text(b), "arrive_j": jfull(b["arrive"]), "depart_j": jfull(b["depart"]), "arrive_text": jlong(b["arrive"]), "depart_text": jlong(b["depart"]), "total_text": money(b["total"]),
                "deposit_due_text": (day_word(b["deposit_due"]) + " ساعت " + b["deposit_due"][11:16]) if b["deposit_due"] else ""}

def refund(c, b):
    """What goes back to the guest when a booking is cancelled now: by how many days are left before arrival."""
    days = (date.fromisoformat(b["arrive"]) - today()).days
    got = paid(c, b["id"])
    pct = 90 if days > 7 else 50 if days >= 3 else 0
    return {"days": days, "paid": got, "percent": pct, "amount": round(got * pct / 100 / 10_000) * 10_000,
            "rule": "بیش از ۷ روز مانده: ۹۰ درصد پرداختی برمی‌گردد؛ ۳ تا ۷ روز: ۵۰ درصد؛ کمتر از ۳ روز: هیچ."}

# ---------- what needs doing ----------

def _phone_dupes(c):
    rows = c.execute("""SELECT b.*, g.phone FROM bookings b JOIN guests g ON g.id = b.guest_id
                        WHERE b.status IN ('tentative', 'confirmed') AND g.phone != '' AND b.arrive >= ?""", (today().isoformat(),)).fetchall()
    out, seen = [], set()
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["phone"] == b["phone"] and a["arrive"] < b["depart"] and b["arrive"] < a["depart"] and (a["id"], b["id"]) not in seen:
                seen.add((a["id"], b["id"]))
                out.append((dict(a), dict(b)))
    return out

def gaps(c, days=14):
    """A single empty night between two bookings in the same room, with a move that closes it: the later booking
    fits back to back in another room of its type."""
    t, end = today().isoformat(), add(today().isoformat(), days)
    out = []
    for r in rooms(c).values():
        bs = [dict(b) for b in c.execute("""SELECT * FROM bookings WHERE room_id = ? AND status IN ('tentative', 'confirmed', 'in_house')
                                             AND depart >= ? AND arrive <= ? ORDER BY arrive""", (r["id"], t, end))]
        for a, b in zip(bs, bs[1:]):
            if add(a["depart"], 1) != b["arrive"] or b["status"] == "in_house" or a["depart"] < t or ooo_on(r, a["depart"]):
                continue
            fix = [s for s in suggest_rooms(c, b["type"], b["arrive"], b["depart"], b["guest_id"], ignore=b["id"], limit=10)
                   if s["room_id"] != r["id"] and s["score"] >= 2]
            if fix:
                out.append({"room": r["number"], "night": a["depart"], "booking": b, "to": fix[0]})
    return out

def alerts(c):
    """Today's work, most urgent first."""
    t, out = today().isoformat(), []
    rm = rooms(c)
    st = store.stamp()
    for b in c.execute("""SELECT b.* FROM bookings b JOIN guests g ON g.id = b.guest_id WHERE b.arrive = ? AND b.status IN ('confirmed', 'tentative')
                          AND g.vip = 1""", (t,)):
        v = booking_view(c, b)
        if not v["room"] or v["room_status"] == "dirty":
            out.append({"type": "vip", "tone": "danger", "icon": "alert", "booking_id": v["id"], "order": 1,
                        "title": f"مهمان ویژه، {v['guest']}، ساعت {v['eta'] or CHECK_IN} می‌رسد و " + (f"اتاق {v['room']} هنوز تمیز نشده است" if v["room"] else "هنوز اتاقی برایش انتخاب نشده است"),
                        "detail": f"{v['type_text']}، {v['stay_text']}. " + (f"یادداشت: {v['notes']}. " if v["notes"] else "") + "اتاقش را در فهرست خانه‌داری اول بگذارید."})
    for b in c.execute("SELECT * FROM bookings WHERE status = 'tentative' AND deposit_due < ? ORDER BY arrive", (st,)):
        v = booking_view(c, b)
        out.append({"type": "deposit", "tone": "warning", "icon": "clock", "booking_id": v["id"], "order": 2,
                    "title": f"مهلت بیعانه‌ی {v['guest']} گذشته است ({v['stay_text']})",
                    "detail": f"مهلت {v['deposit_due_text']} بود و پرداختی ثبت نشده است. {v['type_text']}، {v['total_text']}. تماس بگیرید؛ اگر نمی‌آید، رزرو را لغو کنید تا اتاق آزاد شود."})
    for v in overbooked(c):
        out.append({"type": "overbooked", "tone": "danger", "icon": "alert", "order": 1, "day": v["night"],
                    "title": f"شب {jlong(v['night'])} از {v['type_text']} {v['over']} اتاق بیشتر از ظرفیت فروخته شده است",
                    "detail": f"{v['sold']} رزرو برای {v['rooms']} اتاق. سابقه‌ی نیامدن: حدود {v['expected_noshow']} نفر در چنین شبی. اتاق نوع بالاتر یا هتل همکار را از حالا در نظر بگیرید."})
    for b in c.execute("SELECT * FROM bookings WHERE status IN ('tentative', 'confirmed') AND room_id IS NOT NULL AND depart > ?", (t,)):
        r = rm.get(b["room_id"])
        if r and any(ooo_on(r, n) for n in nights_of(b["arrive"], b["depart"])):
            v = booking_view(c, b)
            out.append({"type": "ooo", "tone": "warning", "icon": "edit", "booking_id": v["id"], "order": 3,
                        "title": f"اتاق {r['number']} در تعمیر است ولی {v['guest']} برای {v['stay_text']} در آن رزرو دارد",
                        "detail": f"تعمیر: {r['ooo_note'] or '-'}، تا {jfull(r['ooo_to']) if r['ooo_to'] else 'نامعلوم'}. رزرو را به اتاق دیگری از همین نوع ببرید."})
    for r in rm.values():
        bs = [dict(x) for x in c.execute("""SELECT * FROM bookings WHERE room_id = ? AND status IN ('tentative', 'confirmed', 'in_house') AND depart > ?
                                             ORDER BY arrive""", (r["id"], t))]
        for i, x in enumerate(bs):
            for y in bs[i + 1:]:
                if x["arrive"] < y["depart"] and y["arrive"] < x["depart"]:
                    vx, vy = booking_view(c, x), booking_view(c, y)
                    fix = suggest_rooms(c, vy["type"], vy["arrive"], vy["depart"], vy["guest_id"], ignore=vy["id"], limit=1)
                    out.append({"type": "clash", "tone": "danger", "icon": "alert", "booking_id": vy["id"], "order": 1,
                                "title": f"اتاق {r['number']} برای {jday(max(x['arrive'], y['arrive']))} به دو رزرو داده شده است",
                                "detail": f"{vx['guest']} (شماره‌ی {vx['id']}) و {vy['guest']} (شماره‌ی {vy['id']})." +
                                          (f" اتاق {fix[0]['number']} برای رزرو دوم آزاد است." if fix else " اتاق آزادی از همین نوع نیست.")})
    for a, b in _phone_dupes(c):
        va, vb = booking_view(c, a), booking_view(c, b)
        out.append({"type": "duplicate", "tone": "warning", "icon": "users", "booking_id": vb["id"], "order": 3,
                    "title": f"دو رزرو با یک شماره برای تاریخ‌های نزدیک: {va['guest']}",
                    "detail": f"شماره‌ی {va['id']} از {va['source_text']} ({va['stay_text']}) و شماره‌ی {vb['id']} از {vb['source_text']} ({vb['stay_text']}). اگر یک سفر است، یکی را لغو کنید."})
    for al in c.execute("SELECT * FROM allotments WHERE release >= ? AND release <= ?", (t, add(t, 2))):
        used = c.execute("""SELECT COUNT(*) FROM bookings b JOIN groups g ON g.id = b.group_id WHERE g.allotment_id = ?
                            AND b.status IN ('tentative', 'confirmed') AND b.guest_id IS NOT NULL""", (al["id"],)).fetchone()[0]
        if used < al["rooms"]:
            ag = c.execute("SELECT name FROM agencies WHERE id = ?", (al["agency_id"],)).fetchone()
            out.append({"type": "allotment", "tone": "info", "icon": "calendar", "order": 4, "allotment_id": al["id"],
                        "title": f"سهمیه‌ی {ag['name']} {day_word(al['release'])} آزاد می‌شود و {al['rooms'] - used} اتاقش هنوز نام مهمان ندارد",
                        "detail": f"{al['rooms']} اتاق {type_name(al['type'])} برای {jday(al['arrive'])} تا {jday(al['depart'])}. فهرست نام‌ها را بخواهید؛ اگر نیامد، اتاق‌ها به فروش برمی‌گردند."})
    for b in c.execute("SELECT * FROM bookings WHERE status = 'in_house' AND depart = ?", (t,)):
        bal = balance(c, b["id"])
        if bal > 0:
            v = booking_view(c, b)
            out.append({"type": "balance", "tone": "warning", "icon": "chart", "booking_id": v["id"], "order": 2,
                        "title": f"{v['guest']} (اتاق {v['room']}) امروز می‌رود و {money(bal)} مانده دارد",
                        "detail": "صورت‌حساب را پیش از تحویل کلید با مهمان مرور کنید."})
    for b in c.execute("""SELECT b.* FROM bookings b JOIN guests g ON g.id = b.guest_id WHERE b.status IN ('tentative', 'confirmed')
                          AND b.arrive >= ? AND b.arrive <= ? AND g.notes != ''""", (t, add(t, 3))):
        before = c.execute("SELECT COUNT(*) FROM bookings WHERE guest_id = ? AND status = 'out'", (b["guest_id"],)).fetchone()[0]
        v = booking_view(c, b)
        if before and not v["vip"]:
            out.append({"type": "returning", "tone": "info", "icon": "heart", "booking_id": v["id"], "order": 5,
                        "title": f"{v['guest']} {before} بار مهمان ما بوده و {day_word(v['arrive'])} می‌رسد",
                        "detail": f"یادداشت مهمان: {v['notes']}. به رستوران و خانه‌داری خبر بدهید."})
    for g in gaps(c):
        v = booking_view(c, g["booking"])
        out.append({"type": "gap", "tone": "secondary", "icon": "refresh", "booking_id": v["id"], "order": 6, "room_id": g["to"]["room_id"],
                    "title": f"شب {jlong(g['night'])} اتاق {g['room']} بین دو رزرو خالی مانده است",
                    "detail": f"اگر رزرو {v['guest']} ({v['stay_text']}) به اتاق {g['to']['number']} برود ({g['to']['why'][0]})، این شب به شب‌های آزاد بعدی می‌پیوندد و فروختنی می‌شود."})
    now = datetime.fromisoformat(st)
    for k in c.execute("SELECT * FROM tasks WHERE status = 'open' AND kind = 'request' ORDER BY created"):
        mins = int((now - datetime.fromisoformat(k["created"])).total_seconds() // 60)
        if mins >= 60:
            r = rm.get(k["room_id"], {})
            out.append({"type": "task", "tone": "warning", "icon": "message", "task_id": k["id"], "booking_id": k["booking_id"], "order": 2,
                        "title": f"درخواست اتاق {r.get('number', '')} از {mins // 60} ساعت پیش بی‌پاسخ مانده است: «{k['text']}»",
                        "detail": "کسی آن را انجام‌شده نزده است. پیگیری کنید و به مهمان خبر بدهید."})
    for w in c.execute("SELECT * FROM waitlist WHERE status = 'waiting' AND arrive >= ?", (t,)):
        if availability(c, w["arrive"], w["depart"])[w["type"]]["free"] > 0:
            g = c.execute("SELECT name FROM guests WHERE id = ?", (w["guest_id"],)).fetchone()
            out.append({"type": "waitlist", "tone": "success", "icon": "users", "waitlist_id": w["id"], "order": 2,
                        "title": f"برای {g['name'] if g else ''} در فهرست انتظار جا باز شد",
                        "detail": f"{type_name(w['type'])}، {jday(w['arrive'])} تا {jday(w['depart'])}. پیش از آن‌که دوباره پر شود تماس بگیرید."})
    return sorted(out, key=lambda a: (a["order"], a["title"]))

def noshow_rate(c):
    t = today().isoformat()
    row = c.execute("""SELECT SUM(status = 'noshow') ns, SUM(status IN ('out', 'noshow', 'in_house')) n FROM bookings
                       WHERE arrive >= ? AND arrive < ?""", (add(t, -90), t)).fetchone()
    return (row["ns"] or 0) / row["n"] if row["n"] else 0

def overbooked(c, days=30):
    t = today().isoformat()
    rate, out = noshow_rate(c), []
    rm = list(rooms(c).values())
    for n in nights_of(t, add(t, days)):
        for tp in TYPES:
            sell = sum(1 for r in rm if r["type"] == tp and not ooo_on(r, n))
            sold = c.execute("SELECT COUNT(*) FROM bookings WHERE type = ? AND status IN ('tentative', 'confirmed', 'in_house') AND arrive <= ? AND depart > ?",
                             (tp, n, n)).fetchone()[0]
            if sold > sell:
                out.append({"night": n, "type": tp, "type_text": type_name(tp), "sold": sold, "rooms": sell, "over": sold - sell,
                            "expected_noshow": round(rate * sold, 1)})
    return out

def checks(c):
    """The manager's checks, from the records alone. They say what the records show, never blame."""
    s, out = settings(c), []
    names = {u["id"]: u["full_name"] for u in c.execute("SELECT id, full_name FROM users")}
    for b in c.execute("SELECT * FROM bookings WHERE discount > ? AND agency_id IS NULL AND status != 'cancelled' ORDER BY created DESC", (s["max_discount"],)):
        v = booking_view(c, b)
        full = round(v["total"] / (1 - v["discount"] / 100))
        out.append({"type": "discount", "tone": "warning", "booking_id": v["id"], "title": f"تخفیف {v['discount']:g} درصد به {v['guest']}، بیشتر از سقف {s['max_discount']} درصد",
                    "detail": f"رزرو شماره‌ی {v['id']}، {v['stay_text']}، ثبت {names.get(v['created_by'], 'سایت')}.",
                    "how": [f"قیمت بی‌تخفیف: {money(full)}", f"قیمت ثبت‌شده: {v['total_text']}", f"= {money(full - v['total'])} کمتر", f"سقف تخفیف در تنظیمات: {s['max_discount']} درصد"]})
    for b in c.execute("SELECT * FROM bookings WHERE status = 'cancelled' AND checked_in IS NOT NULL ORDER BY checked_in DESC"):
        v = booking_view(c, b)
        ev = [f"{e['at']} · {e['who']}: {e['text']}" for e in c.execute("SELECT * FROM events WHERE booking_id = ? ORDER BY at", (b["id"],))]
        out.append({"type": "cancel_after", "tone": "danger", "booking_id": v["id"], "title": f"رزرو {v['guest']} پس از تحویل اتاق لغو شد",
                    "detail": f"اتاق {v['room']}، ورود {jfull(v['checked_in'])}. اقامتی که شروع شده معمولاً لغو نمی‌شود، تسویه می‌شود؛ پرداختی‌اش را بررسی کنید.",
                    "how": ev + [f"پرداخت‌شده: {money(paid(c, v['id']))}"]})
    for b in c.execute("SELECT * FROM bookings WHERE checked_in IS NOT NULL AND checked_in >= ? AND room_id IS NOT NULL", (add(today().isoformat(), -14),)):
        last = c.execute("SELECT * FROM room_log WHERE room_id = ? AND at <= ? ORDER BY at DESC LIMIT 1", (b["room_id"], b["checked_in"])).fetchone()
        if last and last["status"] == "dirty":
            v = booking_view(c, b)
            out.append({"type": "dirty", "tone": "warning", "booking_id": v["id"], "title": f"{v['guest']} به اتاق {v['room']} رفت در حالی که خانه‌داری آن را کثیف زده بود",
                        "detail": "پیش از تحویل اتاق، وضعیت «تمیز» یا «بازرسی‌شده» لازم است.",
                        "how": [f"{last['at']} · خانه‌داری: کثیف ({names.get(last['user_id'], '')})", f"{v['checked_in']} · تحویل اتاق به مهمان"]})
    for d in c.execute("SELECT * FROM closes WHERE cash_counted != cash_expected ORDER BY day DESC LIMIT 10"):
        diff = d["cash_counted"] - d["cash_expected"]
        out.append({"type": "cash", "tone": "danger", "title": f"صندوق نقدی {jlong(d['day'])} {money(abs(diff))} {'کم' if diff < 0 else 'زیاد'} بود",
                    "detail": f"بستن روز: {names.get(d['user_id'], '')}" + (f". یادداشت: {d['note']}" if d["note"] else ""),
                    "how": [f"دریافت نقدی ثبت‌شده در آن روز: {money(d['cash_expected'])}", f"شمارش صندوق: {money(d['cash_counted'])}", f"= اختلاف {money(diff)}"]})
    return out

# ---------- numbers ----------

def sellable(c, night):
    return sum(1 for r in rooms(c).values() if not ooo_on(r, night))

def occupied(c, night):
    return c.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('confirmed', 'in_house', 'out') AND arrive <= ? AND depart > ?", (night, night)).fetchone()[0]

def stats(c):
    t = today().isoformat()
    sell, occ = sellable(c, t), occupied(c, t)
    by_type = {tp: c.execute("SELECT COUNT(*) FROM bookings WHERE type = ? AND status IN ('confirmed', 'in_house') AND arrive <= ? AND depart > ?", (tp, t, t)).fetchone()[0]
               for tp in TYPES}
    since = add(t, -30)
    room_rev = c.execute("SELECT COALESCE(SUM(amount), 0) n, COUNT(*) k FROM charges WHERE kind = 'room' AND day >= ? AND day < ?", (since, t)).fetchone()
    nights_sold = room_rev["k"]
    nights_avail = sum(sellable(c, n) for n in nights_of(since, t))
    adr = room_rev["n"] / nights_sold if nights_sold else 0
    arr = c.execute("SELECT COUNT(*) FROM bookings WHERE arrive = ? AND status IN ('confirmed', 'tentative', 'in_house')", (t,)).fetchone()[0]
    dep = c.execute("SELECT COUNT(*) FROM bookings WHERE depart = ? AND status IN ('in_house', 'out')", (t,)).fetchone()[0]
    return [
        {"key": "occupancy", "label": "اشغال امشب", "value": f"{round(100 * occ / sell) if sell else 0} درصد", "sub": f"{occ} از {sell} اتاق", "icon": "dashboard", "tone": "primary",
         "how": [f"{type_name(tp)}: {n}" for tp, n in by_type.items()] + [f"اتاق‌های قابل فروش امشب (بدون تعمیری‌ها): {sell}", f"= {occ} از {sell}"]},
        {"key": "arrivals", "label": "ورود و خروج امروز", "value": f"{arr} ورود، {dep} خروج", "sub": f"تحویل اتاق از ساعت {CHECK_IN}", "icon": "users", "tone": "info",
         "how": [f"رزروهای قطعی و موقت با ورود امروز: {arr}", f"اقامت‌هایی که امروز تمام می‌شود: {dep}"]},
        {"key": "adr", "label": "میانگین قیمت هر شب", "value": money(adr), "sub": "سی روز گذشته", "icon": "chart", "tone": "success",
         "how": [f"درآمد اتاق‌ها در سی روز گذشته: {money(room_rev['n'])}", f"شب‌های فروخته‌شده: {nights_sold}", f"= {money(adr)} برای هر شب"]},
        {"key": "revpar", "label": "درآمد هر اتاق موجود", "value": money(room_rev["n"] / nights_avail if nights_avail else 0), "sub": "سی روز گذشته، فروخته یا خالی",
         "icon": "trendDown", "tone": "warning",
         "how": [f"درآمد اتاق‌ها: {money(room_rev['n'])}", f"شب‌های قابل فروش (همه‌ی اتاق‌ها × سی شب): {nights_avail}", f"= {money(room_rev['n'] / nights_avail if nights_avail else 0)}"]},
    ]

def report(c):
    """The manager's report: the next 14 nights on the books against the last eight weeks of the same weekday,
    income by kind and by channel in the last 30 days, and price suggestions worked out from the forecast."""
    t = today().isoformat()
    s = settings(c)
    nights = []
    for n in nights_of(t, add(t, 14)):
        sell = sellable(c, n)
        booked = c.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('tentative', 'confirmed', 'in_house') AND arrive <= ? AND depart > ?", (n, n)).fetchone()[0]
        past = [occupied(c, add(n, -7 * k)) / max(1, sellable(c, add(n, -7 * k))) for k in range(1, 9) if add(n, -7 * k) < t]
        avg = round(100 * sum(past) / len(past)) if past else 0
        pct = round(100 * booked / sell) if sell else 0
        days = (date.fromisoformat(n) - today()).days
        tip = ""
        if pct >= 85 and days >= 3:
            tip = "نزدیک به پر: تخفیف آژانس‌ها را برای این شب نگه دارید و قیمت پایه را بالاتر ببرید."
        elif pct <= 45 and days <= 10:
            tip = "خالی‌تر از معمول: پیشنهاد ویژه برای آژانس‌ها یا مهمانان قبلی بفرستید."
        nights.append({"date": n, "day": jlong(n), "pct": pct, "booked": booked, "rooms": sell, "usual": avg, "tip": tip, "weekend": weekend(n)})
    since = add(t, -30)
    kinds = [{"kind": r["kind"], "label": CHARGES.get(r["kind"], r["kind"]), "amount": r["s"], "text": money(r["s"])}
             for r in c.execute("SELECT kind, SUM(amount) s FROM charges WHERE day >= ? AND day < ? GROUP BY kind ORDER BY s DESC", (since, t))]
    ch = {}
    for r in c.execute("""SELECT b.source, b.agency_id, SUM(ch.amount) s, COUNT(DISTINCT b.id) n FROM charges ch JOIN bookings b ON b.id = ch.booking_id
                          WHERE ch.kind = 'room' AND ch.day >= ? AND ch.day < ? GROUP BY b.source, b.agency_id""", (since, t)):
        ag = c.execute("SELECT name FROM agencies WHERE id = ?", (r["agency_id"],)).fetchone() if r["agency_id"] else None
        name = ag["name"] if ag else SOURCES.get(r["source"], r["source"])
        ch.setdefault(name, [0, 0])
        ch[name][0] += r["s"]; ch[name][1] += r["n"]
    total = sum(v[0] for v in ch.values()) or 1
    channels = sorted(({"name": k, "amount": v[0], "text": money(v[0]), "stays": v[1], "pct": round(100 * v[0] / total)} for k, v in ch.items()), key=lambda x: -x["amount"])
    rate = noshow_rate(c)
    return {"nights": nights, "kinds": kinds, "channels": channels, "noshow_pct": round(100 * rate, 1),
            "overbook_tip": f"در نود روز گذشته {round(100 * rate, 1)} درصد مهمانان قطعی نیامده‌اند؛ در شبی با ۸۰ رزرو یعنی حدود {round(rate * 80)} نفر. فروش بیش از ظرفیت را از این عدد بیشتر نکنید.",
            "max_discount": s["max_discount"]}

def peak(c):
    """«حالت شلوغی»: today's arrivals in the order they come, whether their room is ready, the rooms housekeeping
    should do first (those a guest is waiting for), and tomorrow's arrivals without a room, each with a suggestion."""
    t = today().isoformat()
    arrivals = [booking_view(c, b) for b in c.execute("""SELECT * FROM bookings WHERE arrive = ? AND status IN ('confirmed', 'tentative', 'in_house')
                                                         ORDER BY COALESCE(eta, '14:00'), id""", (t,))]
    first = []
    for a in arrivals:
        if a["status"] != "in_house" and a["room"] and a["room_status"] == "dirty":
            leaving = c.execute("SELECT status FROM bookings WHERE room_id = ? AND depart = ? AND status IN ('in_house', 'out')", (a["room_id"], t)).fetchone()
            first.append({"room": a["room"], "room_id": a["room_id"], "eta": a["eta"] or CHECK_IN, "guest": a["guest"], "vip": a["vip"],
                          "leaving": "مهمان قبلی هنوز نرفته" if leaving and leaving["status"] == "in_house" else "خالی، منتظر نظافت"})
    first.sort(key=lambda x: (not x["vip"], x["eta"]))
    tomorrow = add(t, 1)
    pending = []
    for b in c.execute("SELECT * FROM bookings WHERE arrive = ? AND status IN ('confirmed', 'tentative') AND room_id IS NULL ORDER BY id", (tomorrow,)):
        v = booking_view(c, b)
        v["suggest"] = suggest_rooms(c, v["type"], v["arrive"], v["depart"], v["guest_id"], ignore=v["id"], limit=1)
        pending.append(v)
    departures = [booking_view(c, b) | {"balance": balance(c, b["id"])} for b in c.execute("SELECT * FROM bookings WHERE depart = ? AND status IN ('in_house', 'out') ORDER BY room_id", (t,))]
    for d in departures:
        d["balance_text"] = money(d["balance"])
    return {"arrivals": arrivals, "first": first, "tomorrow": pending, "departures": departures}

def overview(c):
    t = today().isoformat()
    return {"today": jfull(t), "today_long": jlong(t), "stats": stats(c), "alerts": alerts(c)}

def brief_facts(c):
    o = overview(c)
    lines = [f"امروز: {o['today_long']} {o['today']}"] + [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]]
    lines += ["کارهای امروز به ترتیب فوریت:"] + [f"{i + 1}. {a['title']}" for i, a in enumerate(o["alerts"][:7])]
    return "\n".join(lines), o

def events(c, after=0, limit=40, booking_id=None):
    q, args = "SELECT * FROM events WHERE id > ?", [after]
    if booking_id:
        q += " AND booking_id = ?"; args.append(booking_id)
    rows = c.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit)).fetchall()
    t = today().isoformat()
    return [{"id": e["id"], "kind": e["kind"], "text": e["text"], "who": e["who"], "role": e["role"], "today": e["at"][:10] == t,
             "day": jday(e["at"]), "time": e["at"][11:16], "booking_id": e["booking_id"]} for e in rows]
