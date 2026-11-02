"""Builds an agency's last six months around today: listings, buyers and renters, calls, visits and a year of deals,
for the agency in agency.py. The same every time (a fixed random seed), moved to today's date.

Planted situations, each one something the panels must find by themselves:
- DUPLICATE   one unit entered twice by the two agents (same owner phone, floor and area)
- STALE       a listing nobody has called its owner about for 52 days
- OVERPRICED  a listing asking far more per square metre than the neighbourhood's deals
- MISSED      a new listing that fits an old buyer exactly, and nobody has called the buyer in five days
- UNCONFIRMED tomorrow's visit, not confirmed with the customer yet
- NO_REPORT   an owner whose unit had three visits this month and who has heard nothing for 41 days
- OUTSIDE     a unit withdrawn by its owner days after a customer's third visit, and that customer's request closed
              as lost days later: the pattern a deal made around the agency leaves
- LOW_FEE     a deal whose commission was written down well under the agency's tariff
"""
import random
from datetime import timedelta
from . import agency, store, facts

HOOD_PRICE = {"شهرک غرب": 135_000_000, "سعادت‌آباد": 112_000_000, "پونک": 78_000_000, "جنت‌آباد": 66_000_000, "شهران": 57_000_000}
STREETS = {
    "پونک": ["خیابان سردار جنگل", "بلوار عدل", "خیابان میرزابابایی", "خیابان سمنگان", "میدان پونک"],
    "شهرک غرب": ["بلوار دادمان", "خیابان سیمای ایران", "خیابان زرافشان", "بلوار فرحزادی", "خیابان هرمزان"],
    "سعادت‌آباد": ["خیابان سرو غربی", "خیابان علامه شمالی", "بلوار دریا", "خیابان کاج", "میدان کاج"],
    "جنت‌آباد": ["جنت‌آباد مرکزی", "خیابان لاله شرقی", "خیابان گلستان", "بلوار شاهین", "خیابان چهارباغ"],
    "شهران": ["خیابان کوهسار", "خیابان کن", "میدان شهران", "خیابان پارک", "خیابان ساحل"],
}
FIRST = ["علی", "مریم", "حسین", "زهرا", "رضا", "فاطمه", "محمد", "سارا", "امیر", "نرگس", "مهدی", "لیلا", "حمید", "شیما", "کاوه",
         "پریسا", "سعید", "مینا", "بهزاد", "آزاده", "فرهاد", "نسرین", "پیمان", "الناز", "مجید", "سمیرا", "جواد", "هانیه"]
LAST = ["احمدی", "رضایی", "موسوی", "حسینی", "کریمی", "محمدی", "صادقی", "نوری", "جعفری", "اکبری", "رحیمی", "قاسمی", "یزدانی",
        "طاهری", "شریفی", "عباسی", "مرادی", "فرهادی", "کاظمی", "نجفی", "توکلی", "سلطانی", "زمانی", "بهرامی", "خسروی", "نیک‌نام"]
OUTCOMES = ["پسندیدند، منتظر همسرش برای بازدید دوم", "متراژ را کم دانستند", "پیشنهاد کمتر از قیمت دادند", "نور واحد را نپسندیدند",
            "پسندیدند، درباره‌ی ودیعه مذاکره می‌کنند", "پارکینگ را تنگ دانستند", "دنبال طبقه‌ی بالاتر هستند"]

def _r(seed=1405):
    return random.Random(seed)

def _name(rnd):
    return f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"

def _phone(rnd):
    return "09" + str(rnd.choice([12, 19, 35, 36, 91, 22, 38])) + "".join(str(rnd.randint(0, 9)) for _ in range(7))

def _round(v, step):
    return int(round(v / step) * step)

def fair_m2(hood, age):
    return HOOD_PRICE[hood] * (1 - 0.012 * min(age, 30))

def priced(rnd, kind, hood, area, age, rate, noise=(0.95, 1.1)):
    """Sale: a price. Rent: a deposit and a rent with the whole monthly rent near 0.42% of the unit's value."""
    value = fair_m2(hood, age) * area * rnd.uniform(*noise)
    if kind == "sale":
        return {"price": _round(value, 50_000_000), "deposit": 0, "rent": 0}
    eq = value * 0.0042
    full = eq / (rate / 100)
    deposit = _round(full * rnd.choice([0.3, 0.4, 0.5, 0.6, 1.0]), 50_000_000)
    rent = max(0, _round(eq - deposit * rate / 100, 500_000))
    return {"price": 0, "deposit": deposit, "rent": rent}

def build():
    """Wipe and rebuild estate.db for the agency in estate.json."""
    rnd, s = _r(), agency.current()
    t = store.today()
    d = lambda n: (t + timedelta(days=n)).isoformat()   # n days from today (negative: ago)
    store.init()
    store.wipe()
    rate = facts.DEFAULTS["rate"]
    with store.conn() as c:
        owner = store.add_user(c, "modir", agency.person("owner", s), "owner")
        a1 = store.add_user(c, "moshaver1", agency.person("agent1", s), "agent")
        a2 = store.add_user(c, "moshaver2", agency.person("agent2", s), "agent")
        team = [a1, a2, a1, a2, owner]
        store.set_meta(c, "built_for", t.isoformat())
        hoods = agency.HOODS

        # a year of deals: the price history of each neighbourhood
        for i in range(160):
            kind = "sale" if i % 2 else "rent"
            hood, area, age = rnd.choice(hoods), rnd.randint(60, 160), rnd.randint(0, 25)
            p = priced(rnd, kind, hood, area, age, rate, noise=(0.97, 1.03))
            who = rnd.sample([a1, a2], rnd.choice([1, 1, 2]))
            fee = facts.commission(kind, p["price"], p["deposit"], p["rent"], facts.DEFAULTS)["total"]
            c.execute("""INSERT INTO deals (kind, date, hood, area, age, price, deposit, rent, buyer, seller, agents, commission, expected)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (kind, d(-rnd.randint(9, 360)), hood, area, age, p["price"], p["deposit"], p["rent"], _name(rnd), _name(rnd),
                       ",".join(map(str, who)), fee, fee))

        # listings: no two active ones share kind, neighbourhood, floor and area (that is the planted duplicate's job)
        seen, ids = set(), []
        for i in range(118):
            kind = "rent" if i % 9 < 5 else "sale"
            while True:
                hood, area, floor = rnd.choice(hoods), rnd.randint(55, 170), rnd.randint(0, 7)
                if not any(k == (kind, hood, floor) and abs(a - area) <= 4 for k, a in seen):
                    seen.add(((kind, hood, floor), area)); break
            age = rnd.choice([0, 1, 2, 4, 5, 7, 8, 10, 12, 15, 18, 22])
            created = -rnd.randint(4, 120)
            status = "active" if i % 7 else rnd.choice(["sold" if kind == "sale" else "rented", "withdrawn"])
            p = priced(rnd, kind, hood, area, age, rate, noise=(0.97, 1.07))
            contact = max(created, -rnd.randint(1, 24)) if status == "active" else created + 5
            report = -rnd.randint(2, 24) if created <= -26 else None
            cur = c.execute("""INSERT INTO listings (kind, hood, street, area, rooms, floor, floors, age, elevator, parking, storage, price, deposit,
                               rent, owner_name, owner_phone, note, agent_id, status, created, last_contact, last_report, closed, source)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (kind, hood, rnd.choice(STREETS[hood]), area, 1 if area < 70 else 2 if area < 110 else 3, floor,
                             max(floor, rnd.randint(3, 8)), age, int(floor > 1 or rnd.random() < .5), int(rnd.random() < .8), int(rnd.random() < .7),
                             p["price"], p["deposit"], p["rent"], _name(rnd), _phone(rnd), "", rnd.choice(team), status, d(created), d(contact),
                             d(report) if report is not None else None, None if status == "active" else d(created + rnd.randint(5, 30)), "phone"))
            ids.append(cur.lastrowid)

        # buyers and renters, each built around a real unit so most have something that fits
        active = [dict(r) for r in c.execute("SELECT * FROM listings WHERE status = 'active'")]
        for i in range(62):
            base = rnd.choice(active)
            hoods_wanted = [base["hood"]] + rnd.sample([h for h in hoods if h != base["hood"]], rnd.choice([0, 1, 1, 2]))
            needs = ",".join(n for n in ("parking", "elevator", "storage") if base[n] and rnd.random() < .35)
            stretch = rnd.uniform(0.9, 1.25)
            status = "open" if i % 6 else rnd.choice(["won", "lost"])
            created = -rnd.randint(1, 60)
            c.execute("""INSERT INTO requests (kind, name, phone, hoods, budget, deposit, rent, rooms, area, needs, note, agent_id, status, created, closed, source)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (base["kind"], _name(rnd), _phone(rnd), ",".join(hoods_wanted), _round(base["price"] * stretch, 100_000_000) if base["kind"] == "sale" else 0,
                       _round(base["deposit"] * stretch, 50_000_000) if base["kind"] == "rent" else 0,
                       _round(base["rent"] * stretch, 1_000_000) if base["kind"] == "rent" else 0,
                       base["rooms"], _round(base["area"] * 0.9, 5), needs, "", rnd.choice([a1, a2, a1, a2, owner]), status, d(created),
                       None if status == "open" else d(min(-1, created + rnd.randint(3, 30))), "site" if rnd.random() < .2 else "phone"))

        # the planted situations
        P = {}
        # DUPLICATE: a unit of Poonak entered by agent 1, and again ten days later by agent 2 from the owner's second call
        dup = dict(kind="rent", hood="پونک", street="خیابان سمنگان", area=92, rooms=2, floor=3, floors=5, age=6, elevator=1, parking=1, storage=1,
                   price=0, deposit=500_000_000, rent=13_000_000, owner_name="فرشته یزدانی", owner_phone="09123370418")
        P["dup_a"] = _listing(c, dup | {"agent_id": a1, "created": d(-24), "last_contact": d(-6), "note": "مالک ساکن خارج از کشور، کلید نزد سرایدار"})
        P["dup_b"] = _listing(c, dup | {"area": 91, "deposit": 550_000_000, "rent": 11_500_000, "agent_id": a2, "created": d(-14), "last_contact": d(-3),
                                         "note": "واحد ۹۱ متری، تماس مالک"})
        # STALE
        P["stale"] = _listing(c, dict(kind="sale", hood="جنت‌آباد", street="خیابان لاله شرقی", area=78, rooms=2, floor=2, floors=4, age=12, elevator=1,
                                      parking=1, storage=0, owner_name="جمشید طاهری", owner_phone="09352281904", agent_id=a2, created=d(-80),
                                      last_contact=d(-52), last_report=d(-20)) | priced(rnd, "sale", "جنت‌آباد", 78, 12, rate, (1, 1.04)))
        # OVERPRICED
        over = priced(rnd, "sale", "سعادت‌آباد", 128, 8, rate, (1, 1))
        P["over"] = _listing(c, dict(kind="sale", hood="سعادت‌آباد", street="خیابان سرو غربی", area=128, rooms=3, floor=5, floors=7, age=8, elevator=1,
                                     parking=1, storage=1, price=_round(over["price"] * 1.38, 50_000_000), deposit=0, rent=0, owner_name="منصور کاظمی",
                                     owner_phone="09121184620", agent_id=a1, created=d(-18), last_contact=d(-4)))
        # MISSED: a fresh Poonak unit and an old buyer who wants exactly that; nobody has called him
        miss = priced(rnd, "sale", "پونک", 104, 5, rate, (1.0, 1.0))
        P["miss_l"] = _listing(c, dict(kind="sale", hood="پونک", street="بلوار عدل", area=104, rooms=2, floor=4, floors=6, age=5, elevator=1, parking=1,
                                       storage=1, owner_name="پروین قاسمی", owner_phone="09195527310", agent_id=a2, created=d(-5), last_contact=d(-5)) | miss)
        P["miss_r"] = _request(c, dict(kind="sale", name="کیوان رحیمی", phone="09122045178", hoods="پونک,شهران", budget=_round(miss["price"] * 1.06, 100_000_000),
                                       rooms=2, area=95, needs="parking,elevator", agent_id=a1, created=d(-21),
                                       note="دو خواب، پارکینگ و آسانسور حتماً، تا اسفند باید جابه‌جا شود"))
        # NO_REPORT: three visits this month, nothing told to the owner for 41 days
        P["quiet"] = _listing(c, dict(kind="rent", hood="شهرک غرب", street="بلوار دادمان", area=140, rooms=3, floor=6, floors=8, age=4, elevator=1, parking=1,
                                      storage=1, owner_name="ژیلا فرهادی", owner_phone="09121650093", agent_id=a1, created=d(-70), last_contact=d(-12),
                                      last_report=d(-41)) | priced(rnd, "rent", "شهرک غرب", 140, 4, rate, (1.02, 1.04)))
        # OUTSIDE: a Shahrak-e Gharb unit, three visits by one couple, withdrawn by the owner, their request closed as lost
        P["out_l"] = _listing(c, dict(kind="sale", hood="شهرک غرب", street="خیابان زرافشان", area=118, rooms=3, floor=4, floors=6, age=7, elevator=1,
                                      parking=1, storage=1, owner_name="داریوش نیک‌نام", owner_phone="09123009871", agent_id=a2, created=d(-46),
                                      last_contact=d(-8), last_report=d(-15), status="withdrawn", closed=d(-8),
                                      note="مالک منصرف شد، فعلاً نمی‌فروشد") | priced(rnd, "sale", "شهرک غرب", 118, 7, rate, (1, 1.02)))
        P["out_r"] = _request(c, dict(kind="sale", name="سیما و آرش بهرامی", phone="09356610284", hoods="شهرک غرب,سعادت‌آباد", budget=17_000_000_000,
                                      rooms=3, area=110, needs="parking", agent_id=a2, created=d(-30), status="lost", closed=d(-5),
                                      note="زوج جوان، وام بانکی دارند"))
        # LOW_FEE
        low = priced(rnd, "sale", "سعادت‌آباد", 96, 10, rate, (1, 1))
        fee = facts.commission("sale", low["price"], 0, 0, facts.DEFAULTS)["total"]
        c.execute("""INSERT INTO deals (kind, date, hood, area, age, price, deposit, rent, buyer, seller, agents, commission, expected)
                     VALUES ('sale',?,?,?,?,?,0,0,?,?,?,?,?)""", (d(-6), "سعادت‌آباد", 96, 10, low["price"], "نادر سلطانی", "هما زمانی", str(a1),
                                                                 _round(fee * 0.55, 1_000_000), fee))

        # visits: a month of past ones, today's, tomorrow's (one not confirmed) and the rest of the week
        reqs = {r["id"]: dict(r) for r in c.execute("SELECT * FROM requests")}
        pairs = [(m["listing"], m["request"]) for m in facts.all_matches(c)
                 if m["listing"]["id"] not in P.values() and m["request"]["id"] not in P.values()]
        rnd.shuffle(pairs)
        for n, (l, r) in enumerate(pairs[:46]):
            day = -rnd.randint(1, 28) if n < 36 else (0 if n < 39 else 1 if n < 41 else rnd.randint(2, 6))
            at = f"{d(day)} {rnd.choice(['10:00', '11:30', '16:00', '17:30', '18:30'])}"
            done = day < 0
            c.execute("INSERT INTO visits (listing_id, request_id, at, agent_id, status, outcome, note) VALUES (?,?,?,?,?,?,?)",
                      (l["id"], r["id"], at, r["agent_id"], "done" if done else "confirmed", "" if not done else rnd.choice(OUTCOMES), ""))
        miss_r = reqs[P["miss_r"]]
        for when in ("-17 18:00", "-11 17:30", "-4 11:00"):
            day, hour = when.split()
            other = next(r for r in reqs.values() if r["kind"] == "rent" and r["status"] == "open" and "شهرک غرب" in r["hoods"])
            c.execute("INSERT INTO visits (listing_id, request_id, at, agent_id, status, outcome) VALUES (?,?,?,?,?,?)",
                      (P["quiet"], other["id"], f"{d(int(day))} {hour}", a1, "done", rnd.choice(OUTCOMES)))
        for day, hour, out in ((-18, "17:30", "پسندیدند، می‌خواهند با پدرشان دوباره ببینند"), (-13, "18:00", "با پدرشان آمدند، درباره‌ی قیمت پرسیدند"),
                               (-10, "11:00", "بازدید سوم؛ گفتند تا آخر هفته خبر می‌دهند")):
            c.execute("INSERT INTO visits (listing_id, request_id, at, agent_id, status, outcome) VALUES (?,?,?,?,?,?)",
                      (P["out_l"], P["out_r"], f"{d(day)} {hour}", a2, "done", out))
        tomorrow_pick = next(r for r in reqs.values() if r["status"] == "open" and r["kind"] == "rent" and r["id"] != P["miss_r"])
        unit = next(l for l, r in pairs if r["id"] == tomorrow_pick["id"]) if any(r["id"] == tomorrow_pick["id"] for _, r in pairs) else \
            dict(c.execute("SELECT * FROM listings WHERE status = 'active' AND kind = 'rent' LIMIT 1").fetchone())
        c.execute("INSERT INTO visits (listing_id, request_id, at, agent_id, status) VALUES (?,?,?,?, 'booked')",
                  (unit["id"], tomorrow_pick["id"], f"{d(1)} 17:30", a1))

        # calls: every match older than a day was offered, except the planted one; some of the newest wait for the agents
        for m in facts.all_matches(c):
            l, r = m["listing"], m["request"]
            if (l["id"], r["id"]) == (P["miss_l"], P["miss_r"]):
                continue
            if m["waiting"] <= 1 and rnd.random() < .6:
                continue
            c.execute("INSERT INTO calls (listing_id, request_id, at, user_id, outcome) VALUES (?,?,?,?,?)",
                      (l["id"], r["id"], d(-min(m["waiting"], rnd.randint(0, 2))), r["agent_id"],
                       rnd.choice(["پیشنهاد شد، علاقه نداشت", "پیشنهاد شد، بازدید می‌خواهد", "پیشنهاد شد، فکر می‌کند"])))

        # the event log: the planted case's own trail, then a few ordinary lines of the last days
        names = facts.agents(c)
        log = lambda day, hour, who, kind, text, lid=None, rid=None: c.execute(
            "INSERT INTO events (at, who, role, kind, text, listing_id, request_id) VALUES (?,?,?,?,?,?,?)",
            (f"{d(day)} {hour}", names[who], store.ROLE_NAMES["owner" if who == owner else "agent"], kind, text, lid, rid))
        log(-46, "10:15", a2, "listing", f"فایل {P['out_l']} ثبت شد: فروش، شهرک غرب، ۱۱۸ متر", P["out_l"])
        log(-30, "12:40", a2, "request", f"متقاضی جدید: سیما و آرش بهرامی، خرید در شهرک غرب", rid=P["out_r"])
        log(-8, "19:05", a2, "status", f"فایل {P['out_l']}: مالک منصرف شد («فعلاً نمی‌فروشد»)", P["out_l"])
        log(-5, "13:20", a2, "status", f"درخواست سیما و آرش بهرامی بسته شد: منصرف شد («خانه‌ی دیگری خریدند»)", rid=P["out_r"])
        log(-5, "09:40", a2, "listing", f"فایل {P['miss_l']} ثبت شد: فروش، پونک، ۱۰۴ متر", P["miss_l"])
        log(-14, "11:05", a2, "listing", f"فایل {P['dup_b']} ثبت شد: رهن و اجاره، پونک، ۹۱ متر", P["dup_b"])
        log(-1, "18:10", a1, "visit", "بازدید فردا ساعت ۱۷:۳۰ ثبت شد", unit["id"], tomorrow_pick["id"])
        log(0, "09:05", owner, "login", "وارد شد")
    return P

def _listing(c, f):
    row = {"price": 0, "deposit": 0, "rent": 0, "note": "", "status": "active", "last_report": None, "closed": None, "source": "phone", "floors": None} | f
    cols = ["kind", "hood", "street", "area", "rooms", "floor", "floors", "age", "elevator", "parking", "storage", "price", "deposit", "rent",
            "owner_name", "owner_phone", "note", "agent_id", "status", "created", "last_contact", "last_report", "closed", "source"]
    return c.execute(f"INSERT INTO listings ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [row[k] for k in cols]).lastrowid

def _request(c, f):
    row = {"budget": 0, "deposit": 0, "rent": 0, "status": "open", "closed": None, "source": "phone", "note": ""} | f
    cols = ["kind", "name", "phone", "hoods", "budget", "deposit", "rent", "rooms", "area", "needs", "note", "agent_id", "status", "created", "closed", "source"]
    return c.execute(f"INSERT INTO requests ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [row[k] for k in cols]).lastrowid
