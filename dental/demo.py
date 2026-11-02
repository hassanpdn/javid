"""Builds a dental clinic's last four months and next days around today, for the clinic in clinic.py: patients, past
appointments and what they paid, treatment plans, the schedule, the waiting list. The same every time (a fixed random
seed), moved to today's date.

Planted situations, each one something the panels must find by themselves:
- UNCONFIRMED  the next working day has one appointment nobody confirmed (an implant, an hour)
- GAP          the next working day is full except an hour freed by a cancellation, and three people are waiting
- NOSHOW       a patient who did not come twice in the last two months has an appointment in a few days
- BIG_PLAN     three implants proposed 35 days ago, nothing booked, nobody called
- ORTHO        an orthodontic plan proposed 30 days ago, one call 18 days ago, then nothing
- UNPAID       a root canal done 25 days ago with most of it unpaid (the dentist's checks)
- HALFWAY      a crown plan with two of four steps done two months ago and nothing booked (the dentist's checks)
"""
import random
from datetime import timedelta
from . import clinic, store, facts

FIRST = ["علی", "مریم", "حسین", "زهرا", "رضا", "فاطمه", "محمد", "سارا", "امیر", "نرگس", "مهدی", "لیلا", "حمید", "شیما", "کاوه", "پریسا",
         "سعید", "مینا", "بهزاد", "آزاده", "فرهاد", "نسرین", "پیمان", "الناز", "مجید", "سمیرا", "آرش", "یاسمن", "بابک", "ترانه"]
LAST = ["احمدی", "رضایی", "موسوی", "حسینی", "کریمی", "محمدی", "صادقی", "نوری", "جعفری", "اکبری", "رحیمی", "قاسمی", "یزدانی", "طاهری",
        "شریفی", "عباسی", "مرادی", "فرهادی", "کاظمی", "نجفی", "توکلی", "سلطانی", "زمانی", "بهرامی", "خسروی", "افشار", "پاکزاد"]
SHORT = ["checkup", "checkup", "scaling", "scaling", "extraction"]      # half-hour visits outside any plan
TOOTH = ["۱۶", "۲۶", "۳۶", "۴۶", "۱۴", "۲۵", "۳۷", "۴۵", "۱۱", "۲۱"]

def build():
    rnd, s = random.Random(1405), clinic.current()
    t = store.today()
    iso = lambda n: (t + timedelta(days=n)).isoformat()
    store.init()
    store.wipe()
    with store.conn() as c:
        doc = store.add_user(c, "doktor", clinic.person("owner", s), "owner")
        sec = store.add_user(c, "monshi", clinic.person("secretary", s), "secretary")
        store.set_meta(c, "built_for", t.isoformat())
        who = {doc: (clinic.person("owner", s), "owner"), sec: (clinic.person("secretary", s), "secretary")}
        log = lambda at, uid, kind, text, pid: c.execute("INSERT INTO events (at, who, role, kind, text, patient_id) VALUES (?,?,?,?,?,?)",
                                                         (at, who[uid][0], store.ROLE_NAMES[who[uid][1]], kind, text, pid))
        used = set()
        def patient(created):
            while True:
                name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
                if name not in used:
                    used.add(name)
                    break
            phone = "09" + rnd.choice(["12", "19", "35", "36", "91", "22"]) + "".join(str(rnd.randint(0, 9)) for _ in range(7))
            return c.execute("INSERT INTO patients (name, phone, created) VALUES (?,?,?)", (name, phone, iso(created))).lastrowid

        def appt(pid, day, time, service, status, item=None, price=None, paid=True, method=None):
            name, minutes, list_price = facts.SERVICES[service]
            price = list_price if price is None else price
            aid = c.execute("""INSERT INTO appointments (patient_id, at, minutes, service, price, plan_item_id, status, created, changed)
                               VALUES (?,?,?,?,?,?,?,?,?)""", (pid, f"{iso(day)} {time}", minutes, service, price, item, status,
                                                               iso(min(day, 0) - rnd.randint(2, 12)), iso(min(day, 0)))).lastrowid
            if status == "done":
                if item:
                    c.execute("UPDATE plan_items SET status = 'done', done_on = ? WHERE id = ?", (iso(day), item))
                if paid:
                    c.execute("INSERT INTO payments (patient_id, at, amount, method, user_id) VALUES (?,?,?,?,?)",
                              (pid, f"{iso(day)} {time}", price if paid is True else paid, method or rnd.choice(["card", "card", "card", "transfer", "cash"]), sec))
                log(f"{iso(day)} {time}", doc, "done", f"{name} انجام شد", pid)
            elif status == "noshow":
                log(f"{iso(day)} {time}", sec, "noshow", f"نوبت {name} ساعت {time}: بیمار نیامد", pid)
            return aid

        def plan(pid, title, created, items, status="proposed"):
            plid = c.execute("INSERT INTO plans (patient_id, title, created, status) VALUES (?,?,?,?)", (pid, title, iso(created), status)).lastrowid
            ids = [c.execute("INSERT INTO plan_items (plan_id, service, tooth, price, status) VALUES (?,?,?,?, 'planned')",
                             (plid, srv, tooth, facts.SERVICES[srv][2])).lastrowid for srv, tooth in items]
            log(f"{iso(created)} 11:00", doc, "plan", f"طرح درمان «{title}» پیشنهاد شد", pid)
            return plid, ids

        # the schedule, day by day: which slots are taken
        booked = {}
        def free(day, time, minutes=30):
            return facts.fits_session(time, minutes) and all((day, x) not in booked for x in facts.run_of(time, minutes))
        def take(day, time, minutes):
            for x in facts.run_of(time, minutes):
                booked[(day, x)] = True
        def slot_for(day, minutes):
            opts = [x for x in facts.SLOTS if free(day, x, minutes)]
            return rnd.choice(opts) if opts else None
        def open_(n):
            return facts.open_day(t + timedelta(days=n))

        P = {}
        nxt = (facts.next_workday() - t).days
        patients = [patient(-rnd.randint(130, 900)) for _ in range(150)]
        rnd.shuffle(patients)
        special = patients[:12]; ordinary = patients[12:]
        noshown = set()

        # finished and ongoing plans of ordinary patients, done in the past
        for pid in ordinary[:26]:
            kind = rnd.choice(["filling", "filling", "rootcanal", "crown", "whitening"])
            items = [(kind, rnd.choice(TOOTH))] + ([("filling", rnd.choice(TOOTH))] if rnd.random() < .5 else [])
            start = -rnd.randint(40, 115)
            plid, ids = plan(pid, facts.service_name(kind), start - 3, items, "accepted")
            for k, item in enumerate(ids):
                day = start + 7 * k
                while not (open_(day) and slot_for(day, 60)):
                    day -= 1
                time = slot_for(day, 60)
                take(day, time, 60)
                appt(pid, day, time, items[k][0], "done", item)
        # ongoing plans with their next step booked in the coming days
        for pid in ordinary[26:36]:
            kind = rnd.choice(["rootcanal", "crown", "filling"])
            plid, ids = plan(pid, facts.service_name(kind), -rnd.randint(5, 25), [(kind, rnd.choice(TOOTH)), ("filling", rnd.choice(TOOTH))], "accepted")
            day = rnd.choice([n for n in range(nxt + 1, nxt + 12) if open_(n)])
            time = slot_for(day, 60)
            if time:
                take(day, time, 60)
                appt(pid, day, time, kind, "booked", ids[0])
        # plans proposed lately, or with a recent call: not yet due a follow-up
        for k, pid in enumerate(ordinary[36:44]):
            kind = rnd.choice(["implant", "crown", "whitening", "rootcanal"])
            plid, _ = plan(pid, facts.service_name(kind), -rnd.randint(2, 10) if k % 2 else -rnd.randint(20, 40), [(kind, rnd.choice(TOOTH))])
            if not k % 2:
                c.execute("INSERT INTO contacts (patient_id, plan_id, at, user_id, kind, text) VALUES (?,?,?,?,?,?)",
                          (pid, plid, f"{iso(-rnd.randint(1, 8))} 12:30", sec, "call", "تماس گرفته شد؛ بیمار گفت تا آخر ماه خبر می‌دهد"))
        # a plan the patient declined
        for pid in ordinary[44:47]:
            plid, _ = plan(pid, "ایمپلنت", -rnd.randint(30, 80), [("implant", rnd.choice(TOOTH))], "declined")
            c.execute("INSERT INTO contacts (patient_id, plan_id, at, user_id, kind, text) VALUES (?,?,?,?,?,?)",
                      (pid, plid, f"{iso(-rnd.randint(10, 25))} 13:00", sec, "declined", "بیمار فعلاً نمی‌خواهد؛ هزینه را زیاد دانست"))

        # ordinary short visits over the past four months, most working days half full
        for day in range(-118, 0):
            if not open_(day):
                continue
            for _ in range(rnd.randint(4, 8)):
                srv = rnd.choice(SHORT)
                time = slot_for(day, 30)
                if not time:
                    break
                take(day, time, 30)
                pid = rnd.choice(ordinary[47:])
                if rnd.random() < .05 and pid not in noshown:
                    noshown.add(pid)
                    appt(pid, day, time, srv, "noshow")
                else:
                    appt(pid, day, time, srv, "done")

        # today: a full morning and part of the afternoon, all confirmed
        if open_(0):
            for time in facts.SLOTS[:12]:
                if (0, time) in booked or rnd.random() < .25:
                    continue
                take(0, time, 30)
                appt(rnd.choice(ordinary[47:]), 0, time, rnd.choice(SHORT), "confirmed")

        # the next working day: every slot taken and confirmed, except the planted ones
        gap_at = "17:00"
        unconf_at = "11:00"
        take(nxt, gap_at, 60)                      # held for the cancelled hour
        P["unconfirmed_patient"] = special[0]
        take(nxt, unconf_at, 60)
        P["unconfirmed"] = appt(special[0], nxt, unconf_at, "implant", "booked")
        for time in facts.SLOTS:
            if (nxt, time) in booked:
                continue
            take(nxt, time, 30)
            appt(rnd.choice([p for p in ordinary[47:] if p not in noshown]), nxt, time, rnd.choice(SHORT), "confirmed")
        # GAP: the hour at 17:00 was cancelled this morning
        P["gap_patient"] = special[1]
        appt(special[1], nxt, gap_at, "rootcanal", "cancelled")
        log(f"{iso(0)} 09:20", sec, "cancel", "نوبت عصب‌کشی ساعت 17:00 لغو شد؛ بیمار تماس گرفت", special[1])
        for pid, srv, note in ((special[2], "scaling", "هر روز عصر می‌تواند بیاید"), (special[3], "filling", "ترجیحاً بعد از ساعت ۱۷"),
                               (special[4], "checkup", "دندانش درد می‌کند، هر چه زودتر")):
            c.execute("INSERT INTO waitlist (patient_id, service, added, note, status) VALUES (?,?,?,?, 'waiting')", (pid, srv, iso(-rnd.randint(1, 6)), note))
            log(f"{iso(-1)} 18:40", sec, "wait", f"به فهرست انتظار اضافه شد: {facts.service_name(srv)}", pid)

        # NOSHOW: did not come twice in the last two months, and has an appointment in a few days
        P["noshow"] = special[5]
        for day in (-55, -20):
            day = day if open_(day) else day - 1
            time = slot_for(day, 30) or "19:30"
            take(day, time, 30)
            appt(special[5], day, time, "checkup", "noshow")
        day = next(n for n in range(nxt + 1, nxt + 6) if open_(n))
        time = slot_for(day, 30)
        take(day, time, 30)
        P["noshow_appt"] = appt(special[5], day, time, "scaling", "booked")

        # BIG_PLAN: three implants, 35 days ago, nobody called
        P["big_plan"], _ = plan(special[6], "سه ایمپلنت", -35, [("implant", "۳۶"), ("implant", "۳۷"), ("implant", "۴۶")])
        # ORTHO: proposed 30 days ago, one call 18 days ago
        P["ortho"], _ = plan(special[7], "ارتودنسی", -30, [("ortho", "")])
        c.execute("INSERT INTO contacts (patient_id, plan_id, at, user_id, kind, text) VALUES (?,?,?,?,?,?)",
                  (special[7], P["ortho"], f"{iso(-18)} 12:10", sec, "call", "پدرش گفت با هم صحبت می‌کنند و خبر می‌دهند"))
        # UNPAID: a root canal 25 days ago, 2 million of 7 paid
        P["unpaid"] = special[8]
        day = -25 if open_(-25) else -26
        time = slot_for(day, 60) or "16:00"
        take(day, time, 60)
        appt(special[8], day, time, "rootcanal", "done", paid=2_000_000, method="card")
        # HALFWAY: a crown plan of four steps, two done about two months ago, nothing booked
        P["halfway"], ids = plan(special[9], "دو روکش", -70, [("rootcanal", "۱۴"), ("crown", "۱۴"), ("rootcanal", "۲۵"), ("crown", "۲۵")], "accepted")
        for k, day in enumerate((-66, -59)):
            day = day if open_(day) else day - 1
            time = slot_for(day, 60) or "18:00"
            take(day, time, 60)
            appt(special[9], day, time, ["rootcanal", "crown"][k], "done", ids[k])

        for day in range(-6, 0):
            log(f"{iso(day)} 09:05", sec, "login", "وارد شد", None)
    return P
