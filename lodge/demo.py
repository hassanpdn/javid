"""Builds an eco-lodge in the desert around the day it is built, for the lodge in info.py: twelve units (one closed
for repair), four months of stays with their reviews, and the next two months on the books. The same every time (a
fixed random seed). Built from the setup form only, not every day: guests' accounts and reviews made on the public
website stay until the host builds the demo again.

Planted, each something the host's panel must find by itself:
- REQUESTS   two requests waiting for the host's answer, one from the website three hours ago
- RECEIPT    a guest sent the photo of their deposit receipt; the host must check it and confirm
- OVERDUE    an approved booking whose deposit deadline passed yesterday
- MESSAGE    a guest's question, unread
- REVIEW     a three-star review with a complaint, waiting before it is shown
- FEEDBACK   two stays that ended in the last days with no review yet (one is the demo guest's)
- CLOSED     a unit taken out of sale for repairs, with its dates closed
The demo guest (mobile 09120000000, password 1234) has a stay that just ended and one waiting for its deposit.
"""
import json, os, random
from datetime import datetime, timedelta
from . import info, store, facts

FIRST = ["علی", "مریم", "حسین", "زهرا", "رضا", "فاطمه", "سارا", "امیر", "نرگس", "مهدی", "لیلا", "حمید", "شیما", "کاوه", "پریسا",
         "سعید", "مینا", "آزاده", "فرهاد", "نسرین", "پیمان", "الناز", "آرش", "یاسمن", "بابک", "ترانه", "کیوان", "هستی", "نیما", "رویا"]
LAST = ["احمدی", "رضایی", "موسوی", "حسینی", "کریمی", "صادقی", "نوری", "جعفری", "اکبری", "رحیمی", "قاسمی", "یزدانی", "طاهری",
        "شریفی", "عباسی", "مرادی", "کاظمی", "نجفی", "توکلی", "سلطانی", "زمانی", "بهرامی", "خسروی", "افشار", "پاکزاد", "تهرانی"]
UNITS = [  # name, kind/art, beds, capacity, price, weekend price, amenities, description
    ("گنبد آبی", "dome", 2, 3, 2_800_000, 3_400_000, "حمام اختصاصی، صبحانه‌ی محلی، رو به حیاط", "اتاقی زیر گنبد خشتی با پنجره‌ای کوچک رو به آسمان."),
    ("گنبد سبز", "dome", 2, 3, 2_800_000, 3_400_000, "حمام اختصاصی، صبحانه‌ی محلی، رو به حیاط", "خنک در تابستان، گرم در زمستان؛ کف با گلیم دستباف."),
    ("گنبد ماه", "dome", 2, 3, 2_900_000, 3_500_000, "حمام اختصاصی، صبحانه‌ی محلی، نزدیک تنور", "کنار تنور حیاط؛ صبح‌ها بوی نان تازه می‌آید."),
    ("گنبد خورشید", "dome", 2, 3, 2_900_000, 3_500_000, "حمام اختصاصی، صبحانه‌ی محلی", "اولین اتاقی که آفتاب صبح به آن می‌رسد."),
    ("ایوان انار", "court", 2, 3, 2_400_000, 2_900_000, "حمام مشترک، صبحانه‌ی محلی، ایوان", "روبه‌روی درخت انار حیاط، با ایوانی برای چای عصر."),
    ("ایوان انجیر", "court", 2, 3, 2_400_000, 2_900_000, "حمام مشترک، صبحانه‌ی محلی، ایوان", "ایوانی رو به حوض؛ ساده و آرام."),
    ("ایوان بادام", "court", 2, 2, 2_200_000, 2_700_000, "حمام مشترک، صبحانه‌ی محلی", "کوچک‌ترین اتاق خانه، برای سفر دونفره."),
    ("خانه‌ی کاروان", "family", 4, 6, 4_800_000, 5_800_000, "حمام اختصاصی، آشپزخانه‌ی کوچک، صبحانه‌ی محلی", "دو اتاق تودرتو برای خانواده یا چند دوست."),
    ("خانه‌ی شتربان", "family", 4, 6, 4_800_000, 5_800_000, "حمام اختصاصی، آشپزخانه‌ی کوچک، صبحانه‌ی محلی", "خانه‌ی قدیمی شتربان روستا، با حیاط خلوت."),
    ("اتاق بادگیر", "tower", 2, 2, 3_600_000, 4_200_000, "حمام اختصاصی، صبحانه‌ی محلی، زیر بادگیر", "زیر بادگیر صدساله؛ نسیم کویر بی هیچ کولری."),
    ("کلبه‌ی بام", "roof", 2, 2, 3_200_000, 3_900_000, "حمام مشترک، صبحانه‌ی محلی، تخت رو به آسمان", "روی بام؛ برای کسی که آمده ستاره ببیند."),
    ("خانه‌ی باغ", "garden", 6, 8, 7_500_000, 9_000_000, "دو حمام، آشپزخانه، باغ اختصاصی، صبحانه‌ی محلی", "خانه‌ای جدا در باغ پسته، برای گروه‌ها."),
]
REVIEWS = [(5, "شب‌های بام را هیچ‌وقت فراموش نمی‌کنیم. نان صبحانه هنوز در خاطرم است."), (5, "میزبانی گرم و خانه‌ای تمیز؛ دوباره می‌آییم."),
           (4, "همه‌چیز خوب بود، فقط آب گرم حمام مشترک صبح زود کم بود."), (5, "پیاده‌روی تا تپه‌های شنی و شام محلی عالی بود."),
           (4, "اتاق کوچک ولی دلنشین؛ سکوت شب کویر همان چیزی بود که می‌خواستیم."), (5, "برای بچه‌ها تجربه‌ی تازه‌ای بود؛ شترسواری و نان پختن.")]

def _receipt_png(path):
    """A small picture standing in for a photo of a bank receipt (no real numbers on it)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (360, 560), (250, 248, 242))
    d = ImageDraw.Draw(im)
    d.rectangle((20, 20, 340, 540), outline=(180, 170, 150), width=3)
    for y in range(90, 470, 46):
        d.rectangle((50, y, 310, y + 14), fill=(214, 206, 190))
    d.ellipse((140, 470, 220, 530), outline=(46, 125, 90), width=5)
    im.save(path, "PNG")

def build():
    rnd, s = random.Random(1405), info.current()
    t = store.today()
    T = t.isoformat()
    iso = lambda n: (t + timedelta(days=n)).isoformat()
    store.init()
    store.wipe()
    now = datetime.fromisoformat(store.stamp())
    with store.conn() as c:
        host = store.add_user(c, "golin", info.person("host", s), "host")
        helper = store.add_user(c, "hamkar", info.person("helper", s), "helper")
        store.set_meta(c, "built_for", T)
        st = facts.settings(c)
        U = []
        for i, (name, kind, beds, cap, price, wk, am, desc) in enumerate(UNITS):
            U.append(c.execute("INSERT INTO units (name, kind, beds, capacity, price, weekend_price, description, amenities, art, active, sort) VALUES (?,?,?,?,?,?,?,?,?,1,?)",
                               (name, kind, beds, cap, price, wk, desc, am, kind, i)).lastrowid)
        units = {r["id"]: dict(r) for r in c.execute("SELECT * FROM units")}
        closed = U[6]
        c.execute("UPDATE units SET active = 0 WHERE id = ?", (closed,))
        c.execute("INSERT INTO blocks (unit_id, start, end, note) VALUES (?,?,?,?)", (closed, iso(-4), iso(25), "تعمیر سقف پس از باران"))

        def guest(name=None, phone=None, password=None, created=None):
            name = name or f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
            while not phone:
                p = "09" + rnd.choice(["12", "13", "19", "35", "36", "91", "22"]) + "".join(str(rnd.randint(0, 9)) for _ in range(7))
                if not c.execute("SELECT 1 FROM guests WHERE phone = ?", (p,)).fetchone():
                    phone = p
            return c.execute("INSERT INTO guests (name, phone, password, created) VALUES (?,?,?,?)",
                             (name, phone, store.hash_password(password) if password else None, created or iso(-200))).lastrowid
        pool = []
        def pick():
            if pool and rnd.random() < .15:
                return rnd.choice(pool)
            g = guest(password="x" * 12 if rnd.random() < .6 else None)
            pool.append(g)
            return g

        def book(uid, a, d, status, gid=None, source=None, created=None, deposit_due=None, note="", people=None):
            u = units[uid]
            people = people or min(u["capacity"], u["beds"] + (1 if rnd.random() < .2 else 0))
            q = facts.quote(c, u, iso(a), iso(d), people)
            if not q["ok"]:
                q = facts.quote(c, u | {"capacity": 99}, iso(a), iso(d), people) if "نفر" in q["why"] else None
                if not q:
                    return None
            created = created or f"{iso(min(a, 0) - rnd.randint(3, 30) if a <= 0 else -rnd.randint(1, 20))} {rnd.randint(9, 22):02d}:{rnd.choice(['05', '25', '45'])}"
            return c.execute("""INSERT INTO bookings (guest_id, unit_id, arrive, depart, adults, children, status, source, nights, total, deposit, deposit_due,
                                note, created, decided, feedback_asked) VALUES (?,?,?,?,?,0,?,?,?,?,?,?,?,?,?,?)""",
                             (gid or pick(), uid, iso(a), iso(d), people, status, source or rnd.choice(["site", "site", "whatsapp", "instagram", "phone", "booking_site"]),
                              json.dumps(q["nights"]), q["total"], q["deposit"], deposit_due, note, created, created, None)).lastrowid

        # every active unit: four months back and two ahead; a stay with a weekend night is at least two nights
        keep = {}   # unit -> nights kept free for the planted bookings
        for uid in U:
            if uid == closed:
                continue
            d = -120 + rnd.randint(0, 6)
            while d < 60:
                stay = rnd.choice([2, 2, 3, 3, 4, 1])
                if stay == 1 and facts.weekend(iso(d)):
                    stay = 2
                if -1 <= d <= 3 and uid in (U[0], U[4]):
                    d = 4            # free nights kept for the requests below
                    continue
                status = "confirmed"
                if d >= 2 and rnd.random() < .12:
                    status = "approved"
                bid = book(uid, d, d + stay, status, deposit_due=f"{iso(min(d - 1, 2))} 20:00" if status == "approved" else None)
                if bid and d + stay <= 0 and rnd.random() < .05:
                    c.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (bid,))
                d += stay + rnd.choice([0, 0, 1, 2, 3, 5, 7])

        # reviews for most past stays (shown), and the feedback request already sent for the rest
        past = c.execute("SELECT * FROM bookings WHERE status = 'confirmed' AND depart <= ? ORDER BY depart", (iso(-4),)).fetchall()
        for b in past:
            if rnd.random() < .55:
                stars, text = rnd.choice(REVIEWS)
                c.execute("INSERT INTO reviews (booking_id, guest_id, unit_id, stars, text, at, status, reply) VALUES (?,?,?,?,?,?, 'shown', ?)",
                          (b["id"], b["guest_id"], b["unit_id"], stars, text, f"{facts.add(b['depart'], rnd.randint(0, 3))} 20:10",
                           "ممنون که مهمان ما بودید." if rnd.random() < .3 else None))
            else:
                c.execute("UPDATE bookings SET feedback_asked = ? WHERE id = ?", (f"{b['depart']} 18:00", b["id"]))
        # stays that ended in the last three days: asked already, except two (FEEDBACK) and one reviewed (REVIEW)
        recent = c.execute("SELECT * FROM bookings WHERE status = 'confirmed' AND depart > ? AND depart <= ? ORDER BY depart DESC", (iso(-4), T)).fetchall()
        demo = guest("مهمان نمونه", "09120000000", "1234", iso(-300))
        P = {"feedback": []}
        for i, b in enumerate(recent):
            if i == 0:
                c.execute("UPDATE bookings SET guest_id = ? WHERE id = ?", (demo, b["id"]))
                P["feedback"].append(b["id"])
            elif i == 1:
                P["feedback"].append(b["id"])
            elif i == 2:
                c.execute("INSERT INTO reviews (booking_id, guest_id, unit_id, stars, text, at, status) VALUES (?,?,?,?,?,?, 'waiting')",
                          (b["id"], b["guest_id"], b["unit_id"], 3, "جای زیبایی است ولی شب دوم برق قطع شد و کسی خبر نداد.", f"{T} 08:40"))
                P["review"] = b["id"]
            else:
                c.execute("UPDATE bookings SET feedback_asked = ? WHERE id = ?", (f"{b['depart']} 18:00", b["id"]))
        # REQUESTS: two waiting for the host, on nights kept free
        P["requests"] = [book(U[0], 1, 3, "requested", source="site", created=(now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), note="ماه عسل هستیم"),
                         book(U[4], 2, 4, "requested", source="whatsapp", created=(now - timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M"))]
        # RECEIPT: a deposit receipt waiting for the host
        free = lambda uid, a, d: not facts.busy(c, uid, iso(a), iso(d))
        uid, a = next((u, a) for a in range(6, 30) for u in U[7:9] if free(u, a, a + 3))
        rb = book(uid, a, a + 3, "paid", source="site", people=5)
        os.makedirs(store.DIR, exist_ok=True)
        _receipt_png(os.path.join(store.DIR, "receipt-demo.png"))
        c.execute("INSERT INTO receipts (booking_id, at, file, status) VALUES (?,?,?, 'waiting')", (rb, f"{T} 09:12", "receipt-demo.png"))
        P["receipt"] = rb
        # OVERDUE: approved, the deposit was due yesterday
        uid, a = next((u, a) for a in range(5, 30) for u in (U[9], U[10], U[2]) if free(u, a, a + 2))
        P["overdue"] = book(uid, a, a + 2, "approved", source="instagram", deposit_due=f"{iso(-1)} 20:00")
        # the demo guest's next trip, waiting for its deposit (due tomorrow)
        uid, a = next((u, a) for a in range(12, 40) for u in (U[1], U[3], U[5]) if free(u, a, a + 2))
        P["demo_next"] = book(uid, a, a + 2, "approved", gid=demo, source="site", deposit_due=f"{iso(1)} 20:00")
        # MESSAGE: an unread question from a guest arriving soon
        m = c.execute("SELECT * FROM bookings WHERE status = 'confirmed' AND arrive > ? ORDER BY arrive LIMIT 1", (T,)).fetchone()
        c.execute("INSERT INTO messages (booking_id, at, side, text, seen) VALUES (?,?, 'guest', ?, 0)", (m["id"], f"{T} 07:55", "سلام، می‌شود ساعت ۱۰ صبح برسیم؟"))
        P["message"] = m["id"]
        # the log of the last days
        for b in c.execute("SELECT * FROM bookings WHERE created >= ? ORDER BY created", (iso(-2),)).fetchall():
            g = c.execute("SELECT name FROM guests WHERE id = ?", (b["guest_id"],)).fetchone()
            store.log(c, {"name": g["name"]} if b["source"] == "site" else {"full_name": info.person("host", s), "role": "host"}, "book",
                      f"{facts.STATUS[b['status']]}: {units[b['unit_id']]['name']}، {facts.stay_text(b)}", b["id"], at=b["created"])
        store.log(c, {"full_name": info.person("host", s), "role": "host"}, "unit", f"{units[closed]['name']} برای تعمیر سقف از فروش بیرون رفت", at=f"{iso(-4)} 10:00")
    return P
