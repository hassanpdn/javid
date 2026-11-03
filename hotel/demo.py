"""Builds a luxury hotel by the Caspian around today, for the hotel in info.py: 80 rooms in three types, 6 suites and
4 villas, four months of stays with their folios and payments, and the next two months on the books. The same every
time (a fixed random seed), moved to today's date.

Every room's stays follow one another with no single empty night between them (that is what a good reservations
desk does), so the one planted below is found alone. Planted situations, each something the panels must find:
- VIP        a VIP arrives today at 14:00 and their suite is still dirty
- DEPOSIT    two tentative bookings for tomorrow whose deposit deadline passed yesterday
- OVERBOOK   next Thursday two more sea-view doubles are sold than there are rooms
- CLASH      one room given to two bookings for the same nights
- OOO        a room under repair (a leaking bathroom) with a booking in it next week
- DUPLICATE  the same guest booked by phone and through a booking site for the same nights
- ALLOTMENT  an agency's block of eight rooms is released tomorrow with four still without names
- BALANCE    a guest leaving today with restaurant and minibar charges unpaid
- RETURNING  a guest who has stayed twice, with a food allergy, arrives the day after tomorrow
- GAP        a single empty night between two bookings in a triple, closed by moving the later one
- TASK       a guest's request («no hot water») open for two hours
- checks: a discount over the limit, a booking cancelled after check-in, a guest checked in to a dirty room,
  yesterday's cash 1.2 million short
"""
import json, random
from datetime import datetime, timedelta
from . import info, store, facts

FIRST = ["علی", "مریم", "حسین", "زهرا", "رضا", "فاطمه", "محمد", "سارا", "امیر", "نرگس", "مهدی", "لیلا", "حمید", "شیما", "کاوه", "پریسا",
         "سعید", "مینا", "بهزاد", "آزاده", "فرهاد", "نسرین", "پیمان", "الناز", "مجید", "سمیرا", "آرش", "یاسمن", "بابک", "ترانه", "کیوان", "هستی"]
LAST = ["احمدی", "رضایی", "موسوی", "حسینی", "کریمی", "محمدی", "صادقی", "نوری", "جعفری", "اکبری", "رحیمی", "قاسمی", "یزدانی", "طاهری",
        "شریفی", "عباسی", "مرادی", "فرهادی", "کاظمی", "نجفی", "توکلی", "سلطانی", "زمانی", "بهرامی", "خسروی", "افشار", "پاکزاد", "تهرانی"]
AGENCIES = [("آژانس گردشگری سفرهای سبز", "agency", 12, 0), ("آژانس مسافرتی پرواز شمال", "agency", 10, 0), ("اسنپ‌تریپ", "ota", 0, 15),
            ("جاباما", "ota", 0, 15), ("علی‌بابا", "ota", 0, 12), ("شرکت فولاد البرز", "company", 10, 0)]

def build():
    rnd, s = random.Random(1405), info.current()
    t = store.today()
    T = t.isoformat()
    iso = lambda n: (t + timedelta(days=n)).isoformat()
    store.init()
    kept = store.keep_site()   # the public website's guests keep their trips still to come
    store.wipe()
    now = datetime.fromisoformat(store.stamp())
    with store.conn() as c:
        U = {r: store.add_user(c, u, info.person(r, s), r) for u, r in (("modir", "manager"), ("rezerv", "reservation"), ("paziresh", "reception"),
                                                                         ("khanedari", "housekeeping"))}
        store.set_meta(c, "built_for", T)
        names = {v: (info.person(k, s), store.ROLE_NAMES[k]) for k, v in U.items()}
        log = lambda at, uid, kind, text, bid=None: c.execute("INSERT INTO events (at, who, role, kind, text, booking_id) VALUES (?,?,?,?,?,?)",
                                                              (at, *(names[uid] if uid else ("سایت هتل", "")), kind, text, bid))
        # rooms: four floors of 20 (garden side 1-10, sea side 11-20; the fourth floor is triples), suites, villas
        R = {}
        for f in (1, 2, 3, 4):
            for k in range(1, 21):
                tp = "triple" if f == 4 else "dbl_garden" if k <= 10 else "dbl_sea"
                R[f"{f}{k:02d}"] = c.execute("INSERT INTO rooms (number, type, floor, status) VALUES (?,?,?, 'inspected')", (f"{f}{k:02d}", tp, f)).lastrowid
        for k in range(1, 7):
            R[f"50{k}"] = c.execute("INSERT INTO rooms (number, type, floor, status) VALUES (?, 'suite', 5, 'inspected')", (f"50{k}",)).lastrowid
        for k in range(1, 5):
            R[f"ویلا {k}"] = c.execute("INSERT INTO rooms (number, type, floor, status) VALUES (?, 'villa', 0, 'inspected')", (f"ویلا {k}",)).lastrowid
        rooms = facts.rooms(c)
        ag = {name: c.execute("INSERT INTO agencies (name, kind, discount, commission, phone) VALUES (?,?,?,?,?)",
                              (name, kind, d, m, "011" + str(rnd.randint(52000000, 52999999)))).lastrowid for name, kind, d, m in AGENCIES}

        last_out = {}
        def guest(created, name=None, phone=None, notes="", vip=0):
            name = name or f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
            phone = phone or "09" + rnd.choice(["12", "19", "35", "36", "91", "22", "11"]) + "".join(str(rnd.randint(0, 9)) for _ in range(7))
            return c.execute("INSERT INTO guests (name, phone, national_id, vip, notes, created) VALUES (?,?,?,?,?,?)",
                             (name, phone, "".join(str(rnd.randint(0, 9)) for _ in range(10)), vip, notes, created)).lastrowid
        def pick_guest(arrive):
            ok = [g for g, d in last_out.items() if d < arrive]
            if ok and rnd.random() < .15:
                return rnd.choice(ok)
            return guest(arrive)

        def book(room, tp, a, d, status=None, gid=None, source=None, agency=None, discount=None, adults=None, ages=(), board=None, eta=None,
                 deposit_due=None, by=None, created=None, group=None, ref=None, requests=""):
            """One booking with its folio as it would stand today."""
            a_iso, d_iso = iso(a), iso(d)
            gid = gid or pick_guest(a_iso)
            last_out[gid] = max(last_out.get(gid, ""), d_iso)
            base, most = facts.TYPES[tp][1:]
            adults = adults or base
            if source is None:
                source = rnd.choices(["phone", "whatsapp", "site", "agency", "ota", "walkin", "company"], [30, 15, 10, 20, 18, 3, 4])[0]
            if source in ("agency", "ota", "company") and agency is None:
                agency = ag[rnd.choice([n for n, k, *_ in AGENCIES if k == {"agency": "agency", "ota": "ota", "company": "company"}[source]])]
            if discount is None:
                discount = c.execute("SELECT discount FROM agencies WHERE id = ?", (agency,)).fetchone()[0] if agency else rnd.choice([0, 0, 0, 0, 5, 10])
            board = board or rnd.choice(["BB", "BB", "BB", "HB", "HB", "FB"])
            q = facts.quote(c, tp, a_iso, d_iso, adults, list(ages), board, discount)
            if status is None:
                # the morning of today: stays that end today are still in the house; arrivals of today have not come yet
                status = "out" if d < 0 else "in_house" if a < 0 else "confirmed"
                if status == "out" and rnd.random() < .04:
                    status = "noshow"
                elif a > 0 and rnd.random() < .08:
                    status = "tentative"
            if status == "tentative" and deposit_due is None:
                deposit_due = f"{iso(a - 1)} 12:00" if a > 1 else f"{T} 23:59"
            if not created:
                day = a - rnd.randint(1, 35)
                created = f"{iso(day if day <= 0 else -rnd.randint(0, 3))} {rnd.randint(9, 21):02d}:{rnd.choice(['05', '20', '40'])}"
            by = by if by is not None else (None if source in ("site", "ota") else rnd.choice([U["reservation"], U["reservation"], U["reception"]]))
            checked_in = f"{a_iso} {rnd.choice(['13:40', '14:10', '15:30', '17:20', '19:05'])}" if status in ("in_house", "out") else None
            bid = c.execute("""INSERT INTO bookings (guest_id, room_id, type, arrive, depart, adults, children, board, source, agency_id, group_id, ref, status,
                               deposit_due, nights, total, discount, eta, requests, created, created_by, checked_in, checked_out, docs)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (gid, room, tp, a_iso, d_iso, adults, ",".join(str(x) for x in ages), board, source, agency, group, ref, status, deposit_due,
                             json.dumps(q["nights"]), q["total"], discount, eta or rnd.choice(["13:00", "14:00", "15:30", "17:00", "19:00", "21:00"]),
                             requests, created, by, checked_in, f"{d_iso} 11:30" if status == "out" else None, 1 if checked_in else 0)).lastrowid
            method = "company" if source == "company" else rnd.choice(["card", "card", "transfer", "cash"])
            if status in ("confirmed", "in_house", "out", "noshow"):
                pre = q["total"] if (source in ("ota", "company") or status == "in_house") else q["deposit"]
                c.execute("INSERT INTO payments (booking_id, at, amount, method, kind, user_id) VALUES (?,?,?,?,?,?)",
                          (bid, created, pre, method, "deposit", by))
            if status in ("in_house", "out"):
                for n in q["nights"]:
                    if n["date"] < T:
                        c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?,?,?,?,?)",
                                  (bid, n["date"], f"{n['date']} 23:50", "room", n["amount"], "شب اقامت", U["reception"]))
                for _ in range(rnd.choice([0, 0, 1, 2])):
                    day = rnd.choice(q["nights"])["date"]
                    if day >= T:
                        continue
                    kind = rnd.choice(["restaurant", "restaurant", "minibar", "spa", "laundry", "transfer"])
                    amt = rnd.choice([450_000, 780_000, 1_200_000, 1_650_000, 2_300_000])
                    c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?,?,?,?,?)",
                              (bid, day, f"{day} 21:15", kind, amt, "", U["reception"]))
                    c.execute("INSERT INTO payments (booking_id, at, amount, method, kind, user_id) VALUES (?,?,?,?,?,?)",
                              (bid, f"{day} 21:16", amt, rnd.choice(["card", "cash"]), "payment", U["reception"]))
                if status == "out":
                    rest = facts.balance(c, bid)
                    if rest > 0:
                        c.execute("INSERT INTO payments (booking_id, at, amount, method, kind, user_id) VALUES (?,?,?,?,?,?)",
                                  (bid, f"{d_iso} 11:30", rest, method, "payment", U["reception"]))
            if status == "noshow":
                c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?,?,?,?,?)",
                          (bid, a_iso, f"{a_iso} 23:55", "other", min(q["nights"][0]["amount"], q["deposit"]), "جریمه‌ی نیامدن (شب اول)", U["reception"]))
            return bid

        # rooms kept for the planted stories; the generator leaves these days empty in them
        P = {"room": {}}
        ooo_room, clash_room = R["214"], R["107"]
        gap1, gap2 = R["412"], R["413"]
        blocks = {ooo_room: (-1, 10), clash_room: (8, 12), gap1: (3, 12), gap2: (3, 12), R["503"]: (0, 3)}

        # every room's stays one after another: no stay leaves a single empty night behind it
        for num, rid in R.items():
            tp = rooms[rid]["type"]
            d = -120 + rnd.randint(0, 5)
            while d < 62:
                b0, b1 = blocks.get(rid, (999, 999))
                if b0 <= d < b1:
                    d = b1 + rnd.choice([0, 2, 3])
                    continue
                stay = rnd.choices([1, 2, 3, 4, 5, 7], [12, 30, 26, 16, 10, 6])[0]
                if d < b0 < d + stay:
                    stay = b0 - d
                elif b0 - (d + stay) == 1:
                    stay += 1          # never leave one night empty before a kept block
                adults = facts.TYPES[tp][1]
                ages = [rnd.choice([3, 8, 11])] if rnd.random() < .2 and tp != "villa" else []
                book(rid, tp, d, d + stay, adults=adults, ages=ages)
                d += stay + rnd.choices([0, 2, 3, 4, 6], [40, 20, 18, 12, 10])[0]

        def free_type(a, d, need, types=("dbl_garden", "dbl_sea", "triple")):
            av = facts.availability(c, iso(a), iso(d))
            return max(types, key=lambda tp: av[tp]["free"]) if max(av[tp]["free"] for tp in types) >= need else None

        # VIP: a suite free for three nights from today, still dirty, a guest arriving at 14:00
        suite = facts.rooms(c)[R["503"]]
        vip = guest(iso(-400), notes="همسرش به گل یاس حساسیت دارد؛ آب معدنی بدون گاز", vip=1)
        P["vip"] = book(suite["id"], "suite", 0, 3, "confirmed", gid=vip, source="phone", discount=0, adults=2, board="HB", eta="14:00", by=U["reservation"])
        c.execute("UPDATE rooms SET status = 'dirty' WHERE id = ?", (suite["id"],))
        # DEPOSIT: two tentative bookings for tomorrow, the deposit due yesterday evening
        for k in range(2):
            tp = free_type(1, 3, 1)
            P.setdefault("deposit", []).append(book(None, tp, 1, 3, "tentative", source=rnd.choice(["phone", "whatsapp"]), discount=0, deposit_due=f"{iso(-1)} 18:00",
                                                    created=f"{iso(-2)} 16:{10 + k * 20}", by=U["reservation"]))
        # OOO: the bathroom of 214 leaks; a booking stays in it next week
        c.execute("UPDATE rooms SET ooo_from = ?, ooo_to = ?, ooo_note = ? WHERE id = ?", (iso(-1), iso(10), "نشتی لوله‌ی حمام", ooo_room))
        c.execute("INSERT INTO tasks (room_id, kind, text, created, status) VALUES (?, 'repair', 'نشتی لوله‌ی حمام؛ کاشی باید برداشته شود', ?, 'open')",
                  (ooo_room, f"{iso(-1)} 09:10"))
        P["ooo"] = book(ooo_room, "dbl_sea", 5, 7, "confirmed", source="phone", discount=0)
        # CLASH: room 107 given twice for the same two nights
        P["clash"] = [book(clash_room, "dbl_garden", 8, 10, "confirmed", source="phone", discount=0),
                      book(clash_room, "dbl_garden", 8, 10, "confirmed", source="whatsapp", discount=0)]
        # GAP: 412 has stays on both sides of one empty night; the later one fits right after a stay in 413
        book(gap1, "triple", 3, 5, "confirmed", source="phone", discount=0)
        P["gap"] = book(gap1, "triple", 6, 8, "confirmed", source="whatsapp", discount=0)
        book(gap2, "triple", 3, 6, "confirmed", source="agency", discount=None)
        # DUPLICATE: one trip, booked by phone and again on a booking site, the name written another way
        dup_phone = "09121834470"
        g1 = guest(iso(-3), "محمدرضا صالحی", dup_phone)
        g2 = guest(iso(-1), "محمد رضا صالحی", dup_phone)
        tp = free_type(6, 8, 2, ("dbl_sea", "dbl_garden"))
        P["duplicate"] = [book(None, tp, 6, 8, "confirmed", gid=g1, source="phone", discount=0, created=f"{iso(-3)} 12:40", by=U["reservation"]),
                          book(None, tp, 6, 8, "confirmed", gid=g2, source="ota", agency=ag["جاباما"], created=f"{iso(-1)} 22:05", ref="JB-482139")]
        # ALLOTMENT: eight rooms held for an agency, released tomorrow, four with names
        tp = free_type(5, 8, 4)
        al = c.execute("INSERT INTO allotments (agency_id, type, arrive, depart, rooms, release) VALUES (?,?,?,?,?,?)",
                       (ag["آژانس گردشگری سفرهای سبز"], tp, iso(5), iso(8), 8, iso(1))).lastrowid
        grp = c.execute("INSERT INTO groups (name, agency_id, allotment_id, created) VALUES (?,?,?,?)",
                        ("تور پاییزی سفرهای سبز", ag["آژانس گردشگری سفرهای سبز"], al, iso(-20))).lastrowid
        P["allotment"] = al
        for _ in range(4):
            book(None, tp, 5, 8, "confirmed", source="agency", agency=ag["آژانس گردشگری سفرهای سبز"], group=grp, by=U["reservation"])
        # RETURNING: twice before, a peanut allergy, arriving the day after tomorrow
        ret = guest(iso(-500), "سیمین افشار", "09123301845", notes="حساسیت شدید به بادام‌زمینی؛ اتاق دور از آسانسور")
        for a in (-300, -170):
            c.execute("""INSERT INTO bookings (guest_id, room_id, type, arrive, depart, adults, children, board, source, status, nights, total, discount, created, checked_in, checked_out)
                         VALUES (?,?,?,?,?,2,'','HB','phone','out','[]',?,0,?,?,?)""", (ret, None, "dbl_sea", iso(a), iso(a + 3), 18_000_000, iso(a - 10), f"{iso(a)} 14:30", f"{iso(a + 3)} 11:00"))
        tp = free_type(2, 5, 1, ("dbl_sea", "dbl_garden"))
        P["returning"] = book(None, tp, 2, 5, "confirmed", gid=ret, source="phone", discount=0, board="HB")
        # OVERBOOK: next Thursday (at least three days ahead), two more sea-view doubles sold than there are rooms
        thu = next(k for k in range(3, 11) if (t + timedelta(days=k)).weekday() == 3)
        sell = sum(1 for r in facts.rooms(c).values() if r["type"] == "dbl_sea" and not facts.ooo_on(r, iso(thu)))
        sold = c.execute("SELECT COUNT(*) FROM bookings WHERE type = 'dbl_sea' AND status IN ('tentative', 'confirmed', 'in_house') AND arrive <= ? AND depart > ?",
                         (iso(thu), iso(thu))).fetchone()[0]
        for _ in range(sell - sold + 2):
            book(None, "dbl_sea", thu, thu + 1, "confirmed", source=rnd.choice(["phone", "ota", "site", "whatsapp"]))
        P["overbook"] = iso(thu)
        for _ in range(2):
            c.execute("INSERT INTO waitlist (guest_id, type, arrive, depart, adults, note, added, status) VALUES (?,?,?,?,2,?,?, 'waiting')",
                      (guest(iso(-2)), "dbl_sea", iso(thu), iso(thu + 1), "اتاق دیگری هم باشد قبول دارد", iso(-2)))
        # BALANCE: leaving today with restaurant and minibar not paid
        b = c.execute("SELECT * FROM bookings WHERE status = 'in_house' AND depart = ? AND room_id IS NOT NULL ORDER BY id LIMIT 1", (T,)).fetchone()
        for kind, amt, note in (("restaurant", 5_400_000, "شام دیشب، چهار نفر"), ("minibar", 2_400_000, "")):
            c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?,?,?,?,?)", (b["id"], iso(-1), f"{iso(-1)} 22:30", kind, amt, note, U["reception"]))
        P["balance"] = b["id"]
        # TASK: an in-house guest asked two hours ago, nobody answered
        h = c.execute("SELECT * FROM bookings WHERE status = 'in_house' AND depart > ? ORDER BY id LIMIT 1", (T,)).fetchone()
        P["task"] = c.execute("INSERT INTO tasks (room_id, booking_id, kind, text, created, status) VALUES (?,?, 'request', ?, ?, 'open')",
                              (h["room_id"], h["id"], "آب گرم حمام کار نمی‌کند", (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"))).lastrowid
        for k in range(5):     # earlier requests, done
            x = c.execute("SELECT * FROM bookings WHERE status = 'in_house' ORDER BY id LIMIT 1 OFFSET ?", (k + 2,)).fetchone()
            c.execute("INSERT INTO tasks (room_id, booking_id, kind, text, created, status, done_at, done_by) VALUES (?,?, 'request', ?, ?, 'done', ?, ?)",
                      (x["room_id"], x["id"], rnd.choice(["حوله‌ی اضافه", "تخت بچه", "بالش اضافه", "تعمیر کنترل تلویزیون", "آب معدنی"]), f"{iso(-1)} 20:1{k}",
                       f"{iso(-1)} 20:4{k}", U["housekeeping"]))
        # checks: a discount over the limit, a cancel after check-in, a guest put in a dirty room, yesterday's cash short
        tp = free_type(9, 11, 1, ("dbl_sea", "dbl_garden"))
        P["discount"] = book(None, tp, 9, 11, "confirmed", source="phone", discount=25, by=U["reception"], created=f"{iso(-1)} 19:40")
        x = c.execute("SELECT * FROM bookings WHERE status = 'out' AND arrive = ? AND source = 'phone' AND room_id IS NOT NULL LIMIT 1", (iso(-10),)).fetchone() \
            or c.execute("SELECT * FROM bookings WHERE status = 'out' AND arrive <= ? AND room_id IS NOT NULL ORDER BY arrive DESC LIMIT 1", (iso(-8),)).fetchone()
        c.execute("UPDATE bookings SET status = 'cancelled', checked_out = NULL WHERE id = ?", (x["id"],))
        c.execute("DELETE FROM charges WHERE booking_id = ? AND kind = 'room'", (x["id"],))
        log(x["checked_in"], U["reception"], "checkin", "تحویل اتاق به مهمان", x["id"])
        log(f"{x['checked_in'][:10]} 22:40", U["reception"], "cancel", "رزرو لغو شد", x["id"])
        P["cancel_after"] = x["id"]
        y = c.execute("SELECT * FROM bookings WHERE status IN ('out', 'in_house') AND arrive = ? AND room_id IS NOT NULL ORDER BY id LIMIT 1", (iso(-3),)).fetchone()
        c.execute("INSERT INTO room_log (room_id, at, status, user_id) VALUES (?,?, 'dirty', ?)", (y["room_id"], f"{iso(-3)} 12:10", U["housekeeping"]))
        c.execute("UPDATE bookings SET checked_in = ? WHERE id = ?", (f"{iso(-3)} 13:20", y["id"]))
        c.execute("INSERT INTO room_log (room_id, at, status, user_id) VALUES (?,?, 'clean', ?)", (y["room_id"], f"{iso(-3)} 15:10", U["housekeeping"]))
        P["dirty"] = y["id"]

        # bookings further ahead often have no room yet: the desk gives one the day before
        for b in c.execute("SELECT * FROM bookings WHERE arrive >= ? AND arrive <= ? AND status IN ('confirmed', 'tentative')", (iso(1), iso(20))).fetchall():
            if b["room_id"] not in blocks and (facts.nights_of(b["arrive"], b["depart"]).__len__() >= 2) and rnd.random() < .35:
                c.execute("UPDATE bookings SET room_id = NULL WHERE id = ?", (b["id"],))

        # the rooms this morning: stayovers and departures to clean, the rest ready
        for r in facts.rooms(c).values():
            stay = c.execute("SELECT * FROM bookings WHERE room_id = ? AND status = 'in_house'", (r["id"],)).fetchone()
            if r["id"] == suite["id"]:
                st = "dirty"
            elif stay:
                st = "dirty" if stay["depart"] == T or rnd.random() < .6 else "clean"
            else:
                st = rnd.choice(["inspected", "inspected", "clean"])
            c.execute("UPDATE rooms SET status = ? WHERE id = ?", (st, r["id"]))
            c.execute("INSERT INTO room_log (room_id, at, status, user_id) VALUES (?,?,?,?)", (r["id"], f"{T} 07:30", st, U["housekeeping"]))

        # every past day closed; yesterday the cash was 1.2 million short
        for k in range(30, 0, -1):
            day = iso(-k)
            cash = c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE method = 'cash' AND substr(at, 1, 10) = ?", (day,)).fetchone()[0]
            posted = c.execute("SELECT COUNT(*) FROM charges WHERE kind = 'room' AND day = ?", (day,)).fetchone()[0]
            short = 1_200_000 if k == 1 else 0
            c.execute("INSERT INTO closes (day, at, user_id, posted, cash_expected, cash_counted, note) VALUES (?,?,?,?,?,?,?)",
                      (day, f"{day} 23:55", U["reception"], posted, cash, cash - short, "صندوق شمرده شد" if short else ""))

        store.restore_site(c, kept)

        # the log of the last days
        for b in c.execute("SELECT * FROM bookings WHERE created >= ? ORDER BY created", (iso(-2),)).fetchall():
            log(b["created"], b["created_by"], "book", f"رزرو {facts.STATUS[b['status']]} {facts.type_name(b['type'])}، {facts.stay_text(b)}", b["id"])
        for b in c.execute("SELECT * FROM bookings WHERE checked_in >= ? AND status IN ('in_house', 'out') ORDER BY checked_in", (iso(-1),)).fetchall():
            log(b["checked_in"], U["reception"], "checkin", f"تحویل اتاق {rooms.get(b['room_id'], {}).get('number', '')}", b["id"])
        log(f"{iso(-1)} 23:55", U["reception"], "close", "روز بسته شد؛ صندوق نقدی ۱.۲ میلیون تومان کمتر از دریافتی‌ها شمرده شد")
        log(f"{T} 07:30", U["housekeeping"], "rooms", "وضعیت صبح اتاق‌ها ثبت شد")
    return P
