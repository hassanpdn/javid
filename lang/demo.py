"""Builds a language institute in week eight of its ten-week term, around today (fixed seed): ten teachers, six rooms,
thirty classes, about 280 learners with the terms they passed before, attendance, midterm marks, online tests, the
fees, and the next term half planned with its registrations.

Planted, each found exactly once:
- next term: a teacher given two classes at the same hour (a new Starter class put at the hour of her own class)
- next term: a class with more learners than its room's seats (13 in a room for 10; the bigger room is free)
- next term: a teacher who no longer comes on Wednesdays and Thursdays, with a class on those days
- next term: an Advanced class with only three learners, a few weeks before the term starts
- this term: a learner absent from the last three sessions (in the demo teacher's class)
- this term: two learners whose fee is not paid (one half, one nothing)
- a new learner who took the placement test yesterday and has no class yet
- the demo teacher: the last Tuesday session's attendance not written, a class whose online test averaged under 60,
  and an online test open now in the demo learner's class
- the demo learner: weak in grammar in the last online test, not registered for next term yet, a new book to buy
"""
import json, random
from datetime import date, timedelta
from . import store, institute, curriculum as cur, facts

TEACHERS = [   # name, levels taught, mornings too
    ("سارا احمدی", "A2,B1,B2", True), ("امیر رضایی", "S,A1,A2", True), ("لیلا محمدی", "S,A1,A2", False), ("کاوه کریمی", "B1,B2,C1", False),
    ("نازنین موسوی", "A1,A2,B1", True), ("پویا حسینی", "B2,C1", False), ("مهسا جعفری", "S,A1", False), ("بهرام قاسمی", "A2,B1,B2", False),
    ("شیما رحیمی", "B1,B2,C1", True), ("آرش صادقی", "S,A1,A2,B1", False),
]
FIRST_F = ["نگار", "مریم", "زهرا", "سارا", "فاطمه", "الناز", "نیلوفر", "یاسمن", "رها", "آیدا", "مهتاب", "پریسا", "ترانه", "سمانه", "هستی", "کیمیا",
           "دنیا", "شادی", "آرزو", "مینا", "ستاره", "هانیه", "بهار", "غزل", "نرگس"]
FIRST_M = ["علی", "محمد", "حسین", "رضا", "امید", "سینا", "آرین", "مهدی", "پارسا", "بردیا", "کیان", "عرفان", "میلاد", "سجاد", "نیما", "پیمان",
           "فرهاد", "بابک", "هومن", "یاشار", "ماهان", "سامان", "دانیال", "شایان", "امین"]
LAST = ["صدری", "اکبری", "نوروزی", "یزدانی", "شریفی", "طاهری", "فرهادی", "بهرامی", "زمانی", "کاظمیان", "سلطانی", "مرادی", "نجفی", "عباسی", "ملکی",
        "رستمی", "حیدری", "امیری", "شجاعی", "توکلی", "افشار", "پاکزاد", "خسروی", "دلاوری", "سبحانی", "منصوری", "نیک‌نام", "وحیدی", "هاشمی", "کرمانی"]
COURSES = ["S-1", "S-1", "S-2", "S-2", "A1-1", "A1-1", "A1-1", "A1-2", "A1-2", "A1-2", "A2-1", "A2-1", "A2-1", "A2-2", "A2-2", "A2-2",
           "B1-1", "B1-1", "B1-1", "B1-2", "B1-2", "B1-2", "B2-1", "B2-1", "B2-2", "B2-2", "C1-1", "C1-1", "C1-2", "C1-2"]
DEMO_TEACHER = 1       # سارا احمدی (ostad)
NO_WEDTHU = 7          # مهسا جعفری: no Wednesdays and Thursdays
QUIZ_TITLES = ["آزمون درس‌های ۴ و ۵", "آزمون درس‌های ۱۰ و ۱۱"]

def _phone(rng, used):
    while True:
        p = "09" + rng.choice(["12", "19", "35", "36", "01", "02"]) + "".join(rng.choice("0123456789") for _ in range(7))
        if p not in used:
            used.add(p); return p

def _answers(rng, qids, p, weak=None):
    """Simulated answers: each right with probability p (lower for the weak skill); wrong ones pick another option."""
    out = {}
    for q in qids:
        qq = cur.QUESTIONS[q]
        chance = p - (0.35 if weak and qq["skill"] == weak else 0)
        out[q] = qq["answer"] if rng.random() < chance else rng.choice([i for i in range(4) if i != qq["answer"]])
    return out

def _placement_answers(rng, start_key):
    """Answers that place a learner at start_key: right below its level, mostly wrong at it."""
    level = start_key.split("-")[0]
    keys = [k for k, *_ in cur.LEVELS]
    out = {}
    for q in cur.PLACEMENT:
        qq = cur.QUESTIONS[q]
        lv = q.split("-")[0]
        right = keys.index(lv) < keys.index(level) or (start_key == cur.KEYS[-1])
        if lv == level and start_key != cur.KEYS[-1]:
            right = q.endswith("-1") and rng.random() < 0.5
        out[q] = qq["answer"] if right else (qq["answer"] + 1) % 4
    return out

def build():
    rng = random.Random(1405)
    store.init(); store.wipe()
    s = institute.current()
    t0 = facts.week_start()
    cur_start = t0 - timedelta(weeks=7)
    span = timedelta(weeks=facts.TERM_WEEKS + 1)
    term_start = lambda k: cur_start + span * k          # k: -4..-1 past, 0 current, 1 next
    used_phones, used_names = set(), {"نگار صدری"}
    T = lambda d: d.isoformat()

    def name(female=None):
        while True:
            f = rng.random() < 0.55 if female is None else female
            n = f"{rng.choice(FIRST_F if f else FIRST_M)} {rng.choice(LAST)}"
            if n not in used_names:
                used_names.add(n); return n

    with store.conn() as c:
        terms = {}
        for k in range(-4, 2):
            st = term_start(k)
            y, m, d = facts.to_jalali(st)
            terms[k] = c.execute("INSERT INTO terms (name, start, end, kind) VALUES (?,?,?,?)",
                                 (f"ترم {facts.MONTHS[m - 1]} {str(y).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))}", T(st), T(st + timedelta(weeks=facts.TERM_WEEKS, days=-2)),
                                  "current" if k == 0 else "next" if k == 1 else "past")).lastrowid
        term_rows = {k: facts.term_by_id(c, v) for k, v in terms.items()}

        for i, (n, levels, mornings) in enumerate(TEACHERS, 1):
            slots = facts.SLOTS if mornings else facts.SLOTS[2:]
            av = {p: list(slots) for p in facts.PAIRS if not (i == NO_WEDTHU and p == "wedthu")}
            c.execute("INSERT INTO teachers (id, name, phone, levels, avail, joined) VALUES (?,?,?,?,?,?)",
                      (i, n, _phone(rng, used_phones), levels, json.dumps(av), T(cur_start - timedelta(days=rng.randint(200, 1500)))))
        teachers = {r["id"]: dict(r) for r in c.execute("SELECT * FROM teachers")}

        # ---- this term's timetable: each class to a teacher of its level and a free hour they come, evenings first ----
        busy_cell, busy_teacher, load = set(), set(), {i: 0 for i in teachers}
        fixed = {  # the demo teacher's three classes, where the planted situations need them
            ("A2-2", 0): (DEMO_TEACHER, "suntue", "17:45", 2), ("B1-1", 0): (DEMO_TEACHER, "satmon", "19:30", 1), ("B1-2", 0): (DEMO_TEACHER, "wedthu", "17:45", 2),
            ("A1-2", 0): (3, "satmon", "17:45", 4),     # 13 learners in the 14-seat room; next term it is put in a smaller one
        }
        for tid, pair, time, room in fixed.values():
            busy_cell.add((pair, time, room)); busy_teacher.add((tid, pair, time)); load[tid] += 1
        cls, seen = [], {}
        order = sorted(facts.SLOTS, key=lambda t: (t < "16:00", rng.random()))
        for course in COURSES:
            k = seen.get(course, 0); seen[course] = k + 1
            level = cur.TERM[course]["level"]
            if (course, k) in fixed:
                tid, pair, time, room = fixed[(course, k)]
            else:
                tid = pair = time = room = None
                cands = sorted((t for t in teachers.values() if level in t["levels"].split(",") and t["id"] != DEMO_TEACHER and load[t["id"]] < 4),
                               key=lambda t: (load[t["id"]], rng.random()))
                cells = [(p, tm) for tm in order for p in sorted(facts.PAIRS, key=lambda _: rng.random())]
                for t in cands:
                    for p, tm in cells:
                        if tm not in json.loads(t["avail"]).get(p, []) or (t["id"], p, tm) in busy_teacher:
                            continue
                        free = [r for r in facts.ROOMS if (p, tm, r) not in busy_cell and facts.ROOMS[r] >= 10 and r != 4]
                        if free:
                            tid, pair, time, room = t["id"], p, tm, rng.choice(free); break
                    if tid:
                        break
                assert tid, course
                busy_cell.add((pair, time, room)); busy_teacher.add((tid, pair, time)); load[tid] += 1
            cid = c.execute("INSERT INTO classes (term_id, course, teacher_id, room, pair, time) VALUES (?,?,?,?,?,?)",
                            (terms[0], course, tid, room, pair, time)).lastrowid
            cls.append({"id": cid, "course": course, "teacher_id": tid, "pair": pair, "time": time, "room": room, "k": k})
        by_key = {(x["course"], x["k"]): x for x in cls}
        demo_a22, demo_b11, demo_b12, big = by_key[("A2-2", 0)], by_key[("B1-1", 0)], by_key[("B1-2", 0)], by_key[("A1-2", 0)]

        # ---- learners, their past terms and this term's enrolment ----
        past_class = {}
        def past_cls(k, course):
            if (k, course) not in past_class:
                level = cur.TERM[course]["level"]
                tid = rng.choice([t for t in teachers.values() if level in t["levels"].split(",")])["id"]
                past_class[(k, course)] = c.execute("INSERT INTO classes (term_id, course, teacher_id, room, pair, time) VALUES (?,?,?,?,?,?)",
                                                    (terms[k], course, tid, rng.choice(list(facts.ROOMS)), rng.choice(list(facts.PAIRS)), rng.choice(facts.SLOTS))).lastrowid
            return past_class[(k, course)]

        placement = c.execute("INSERT INTO exams (class_id, kind, title, questions, opens, closes, minutes, created_by, created) VALUES (NULL, 'placement', ?, ?, ?, ?, 20, 'سیستم', ?)",
                              ("آزمون تعیین سطح", json.dumps(cur.PLACEMENT), T(term_start(-4)), T(term_start(1) + timedelta(weeks=20)), T(term_start(-4)))).lastrowid

        def add_student(nm, start_key, created):
            sid = c.execute("INSERT INTO students (name, phone, created, start_key) VALUES (?,?,?,?)",
                            (nm, _phone(rng, used_phones), T(created), start_key)).lastrowid
            if cur.TERM[start_key]["index"] > 0:   # placed above the first station: they took the placement test
                at = f"{T(created)} {rng.choice(['10:20', '11:05', '17:30', '18:40'])}"
                ans = _placement_answers(rng, start_key)
                score, skills, _ = facts.grade(cur.PLACEMENT, ans)
                c.execute("INSERT INTO attempts (exam_id, student_id, started, answers, submitted, score, by_skill, placed) VALUES (?,?,?,?,?,?,?,?)",
                          (placement, sid, at, json.dumps(ans), at, score, json.dumps(skills), facts.place(ans)))
            return sid

        def enrol(sid, class_id, status, registered, fee, paid=None, midterm=None, final=None, score=None):
            eid = c.execute("INSERT INTO enrollments (student_id, class_id, status, registered, fee, midterm, final, score) VALUES (?,?,?,?,?,?,?,?)",
                            (sid, class_id, status, T(registered), fee, midterm, final, score)).lastrowid
            paid = fee if paid is None else paid
            if paid:
                c.execute("INSERT INTO payments (student_id, enrollment_id, at, amount, method, user_id) VALUES (?,?,?,?,?, NULL)",
                          (sid, eid, f"{T(registered)} {rng.choice(['10:30', '12:10', '17:20', '19:05'])}", paid, rng.choice(list(facts.METHODS))))
            return eid

        size = {x["id"]: (13 if x is big else 9 if x is demo_a22 else rng.randint(7, min(11, facts.ROOMS[x["room"]]))) for x in cls}
        members = {x["id"]: [] for x in cls}
        demo_learner = None
        for x in cls:
            idx = cur.KEYS.index(x["course"])
            for j in range(size[x["id"]]):
                is_demo = x is demo_b12 and j == 0
                back = 3 if is_demo else rng.choice([0, 1, 1, 2, 2, 3, 4]) if idx else 0
                back = min(back, idx)
                start_key = cur.KEYS[idx - back]
                created = term_start(-back) - timedelta(days=rng.randint(3, 15))
                sid = add_student("نگار صدری" if is_demo else name(), start_key, created)
                if is_demo:
                    demo_learner = sid
                for b in range(back, 0, -1):
                    course = cur.KEYS[idx - b]
                    reg = term_start(-b) - timedelta(days=rng.randint(2, 12))
                    mid, fin = rng.randint(72, 98), rng.randint(70, 98)
                    enrol(sid, past_cls(-b, course), "passed", reg, cur.TERM[course]["fee"], midterm=mid, final=fin, score=round(0.4 * mid + 0.6 * fin))
                reg = cur_start - timedelta(days=rng.randint(2, 12))
                fee = cur.TERM[x["course"]]["fee"]
                eid = enrol(sid, x["id"], "active", reg, fee, midterm=rng.randint(58, 98))
                members[x["id"]].append({"sid": sid, "eid": eid})

        # two fees not paid: half, and nothing
        for x, part in ((by_key[("A1-1", 1)], 0.5), (by_key[("B2-1", 0)], 0)):
            m = members[x["id"]][-1]
            c.execute("DELETE FROM payments WHERE enrollment_id = ?", (m["eid"],))
            fee = cur.TERM[x["course"]]["fee"]
            if part:
                c.execute("INSERT INTO payments (student_id, enrollment_id, at, amount, method, user_id) VALUES (?,?,?,?, 'card', NULL)",
                          (m["sid"], m["eid"], f"{T(cur_start - timedelta(days=4))} 18:10", int(fee * part)))

        # ---- attendance of the sessions held ----
        cu = term_rows[0]
        absent_one = members[demo_a22["id"]][2]["sid"]
        t_today = T(store.today())
        for x in cls:
            done = [d for d in facts.session_days(cu, x["pair"]) if d < t_today]
            if x is demo_a22:
                done = done[:-1]                      # the last session's attendance was not written
            for m in members[x["id"]]:
                marks = [("absent" if rng.random() < 0.07 else "late" if rng.random() < 0.06 else "present") for _ in done]
                if m["sid"] == absent_one:
                    marks[-3:] = ["absent"] * 3
                elif len(marks) >= 3 and marks[-3:] == ["absent"] * 3:
                    marks[-1] = "present"
                if m["sid"] == demo_learner:
                    marks = ["present"] * len(marks); marks[-4] = "absent"; marks[-2] = "late"
                c.executemany("INSERT INTO attendance (class_id, student_id, day, status) VALUES (?,?,?,?)",
                              [(x["id"], m["sid"], d, st) for d, st in zip(done, marks)])

        # ---- online tests: one closed in week six for every class, one open now in the demo learner's class ----
        for x in cls:
            days = facts.session_days(cu, x["pair"])
            opens = days[11]
            qids = cur.for_quiz(cur.TERM[x["course"]]["level"], 8, rng)
            weak_class = x is demo_b11
            eid = c.execute("INSERT INTO exams (class_id, kind, title, questions, opens, closes, minutes, created_by, created) VALUES (?, 'quiz', ?, ?, ?, ?, 15, ?, ?)",
                            (x["id"], QUIZ_TITLES[0] if cur.TERM[x["course"]]["num"] == 1 else QUIZ_TITLES[1], json.dumps(qids), opens,
                             T(date.fromisoformat(opens) + timedelta(days=3)), teachers[x["teacher_id"]]["name"], opens)).lastrowid
            for m in members[x["id"]]:
                if rng.random() < 0.12 and m["sid"] != demo_learner:
                    continue
                if m["sid"] == demo_learner:      # right everywhere but in half the grammar questions (rounded up)
                    gram = [q for q in qids if cur.QUESTIONS[q]["skill"] == "grammar"]
                    wrong = set(gram[:(len(gram) + 1) // 2])
                    ans = {q: (cur.QUESTIONS[q]["answer"] + 1) % 4 if q in wrong else cur.QUESTIONS[q]["answer"] for q in qids}
                else:
                    ans = _answers(rng, qids, rng.uniform(0.55, 0.75) if weak_class else rng.uniform(0.72, 0.97), weak="grammar" if weak_class else None)
                score, skills, _ = facts.grade(qids, ans)
                at = f"{opens} {rng.choice(['18:20', '20:45', '21:30', '22:10'])}"
                c.execute("INSERT INTO attempts (exam_id, student_id, started, answers, submitted, score, by_skill) VALUES (?,?,?,?,?,?,?)",
                          (eid, m["sid"], at, json.dumps(ans), at, score, json.dumps(skills)))
        qids = cur.for_quiz("B1", 8, rng)
        opened = store.today() - timedelta(days=1)
        open_quiz = c.execute("INSERT INTO exams (class_id, kind, title, questions, opens, closes, minutes, created_by, created) VALUES (?, 'quiz', ?, ?, ?, ?, 15, ?, ?)",
                              (demo_b12["id"], "آزمون درس‌های ۱۰ و ۱۱", json.dumps(qids), T(opened), T(store.today() + timedelta(days=2)),
                               teachers[DEMO_TEACHER]["name"], T(opened))).lastrowid
        c.execute("UPDATE exams SET title = 'آزمون درس‌های ۷ و ۸' WHERE class_id = ? AND id != ?", (demo_b12["id"], open_quiz))
        for m in members[demo_b12["id"]][1:6]:
            ans = _answers(rng, qids, rng.uniform(0.7, 0.95))
            score, skills, _ = facts.grade(qids, ans)
            at = f"{T(opened)} {rng.choice(['19:40', '21:15', '22:30'])}"
            c.execute("INSERT INTO attempts (exam_id, student_id, started, answers, submitted, score, by_skill) VALUES (?,?,?,?,?,?,?)",
                      (open_quiz, m["sid"], at, json.dumps(ans), at, score, json.dumps(skills)))

        # ---- next term: each class goes on with its next book, same hour, same room, a teacher of that level ----
        nt_busy_cell, nt_busy_teacher, planned = set(), set(), {}
        for x in cls:
            nk = cur.next_key(x["course"])
            if not nk:
                continue
            level = cur.TERM[nk]["level"]
            tid = x["teacher_id"]
            if level not in teachers[tid]["levels"].split(","):
                tid = next((t["id"] for t in sorted(teachers.values(), key=lambda t: rng.random()) if level in t["levels"].split(",")
                            and x["time"] in json.loads(t["avail"]).get(x["pair"], []) and (t["id"], x["pair"], x["time"]) not in nt_busy_teacher
                            and (t["id"], x["pair"], x["time"]) not in busy_teacher), tid)
            room = x["room"]
            nt_busy_cell.add((x["pair"], x["time"], room)); nt_busy_teacher.add((tid, x["pair"], x["time"]))
            planned[x["id"]] = {"id": c.execute("INSERT INTO classes (term_id, course, teacher_id, room, pair, time) VALUES (?,?,?,?,?,?)",
                                                (terms[1], nk, tid, room, x["pair"], x["time"])).lastrowid, "course": nk, "pair": x["pair"], "time": x["time"], "room": room, "teacher_id": tid}
        # the big class goes to a smaller room by mistake
        p = planned[big["id"]]
        small_room = next(r for r in (3, 5, 1, 2, 6) if (p["pair"], p["time"], r) not in nt_busy_cell)
        nt_busy_cell.discard((p["pair"], p["time"], p["room"])); nt_busy_cell.add((p["pair"], p["time"], small_room))
        c.execute("UPDATE classes SET room = ? WHERE id = ?", (small_room, p["id"]))

        def free_room(pair, time):
            return next(r for r in facts.ROOMS if (pair, time, r) not in nt_busy_cell and facts.ROOMS[r] >= 10)
        # two new Starter classes: one at the hour of its teacher's own class (a clash), one on a day its teacher does not come
        clash_t = next(t for t in (2, 10, 3) if any(q["teacher_id"] == t for q in planned.values()))
        clash_at = next(q for q in planned.values() if q["teacher_id"] == clash_t)
        r1 = free_room(clash_at["pair"], clash_at["time"]); nt_busy_cell.add((clash_at["pair"], clash_at["time"], r1))
        new1 = c.execute("INSERT INTO classes (term_id, course, teacher_id, room, pair, time) VALUES (?, 'S-1', ?, ?, ?, ?)",
                         (terms[1], clash_t, r1, clash_at["pair"], clash_at["time"])).lastrowid
        r2 = free_room("wedthu", "19:30"); nt_busy_cell.add(("wedthu", "19:30", r2))
        new2 = c.execute("INSERT INTO classes (term_id, course, teacher_id, room, pair, time) VALUES (?, 'S-1', ?, ?, 'wedthu', '19:30')",
                         (terms[1], NO_WEDTHU, r2)).lastrowid

        nt_reg = lambda: term_start(1) - timedelta(days=rng.randint(1, 18))
        def reg_date():
            d = nt_reg()
            return min(d, store.today())
        small_class = planned[by_key[("B2-2", 0)]["id"]]["id"]
        for x in cls:
            if x["id"] not in planned:
                continue
            mem = [m for m in members[x["id"]] if m["sid"] != demo_learner]
            n = len(members[x["id"]])
            k = 3 if planned[x["id"]]["id"] == small_class else n if x is big else max(5, min(n, round(n * 0.62)))
            for m in mem[:k] if x is not big else members[x["id"]]:
                fee = cur.TERM[planned[x["id"]]["course"]]["fee"]
                enrol(m["sid"], planned[x["id"]]["id"], "registered", reg_date(), fee, paid=fee if rng.random() < 0.7 else 0)
        for cid in (new1, new2):
            for _ in range(6):
                created = store.today() - timedelta(days=rng.randint(2, 20))
                sid = add_student(name(), "S-1", created)
                enrol(sid, cid, "registered", created, cur.TERM["S-1"]["fee"], paid=cur.TERM["S-1"]["fee"] if rng.random() < 0.8 else 0)
        waiting = add_student(name(True), "A2-1", store.today() - timedelta(days=1))
        yesterday = f"{T(store.today() - timedelta(days=1))} 17:40"
        c.execute("UPDATE attempts SET submitted = ?, started = ? WHERE student_id = ?", (yesterday, yesterday, waiting))

        # ---- logins ----
        store.add_user(c, "modir", institute.person("owner", s), "owner")
        store.add_user(c, "monshi", institute.person("secretary", s), "secretary")
        store.add_user(c, "ostad", teachers[DEMO_TEACHER]["name"], "teacher", DEMO_TEACHER)
        store.add_user(c, "zabanamooz", "نگار صدری", "student", demo_learner)

        # ---- a few lines of today's log ----
        sec, own = {"full_name": institute.person("secretary", s), "role": "secretary"}, {"full_name": institute.person("owner", s), "role": "owner"}
        tday = T(store.today())
        some = [r[0] for r in c.execute("SELECT e.student_id FROM enrollments e JOIN classes cl ON cl.id = e.class_id WHERE cl.term_id = ? AND e.status = 'registered' LIMIT 3", (terms[1],))]
        names = {r["id"]: r["name"] for r in c.execute("SELECT id, name FROM students")}
        store.log(c, sec, "enroll", f"ثبت‌نام ترم بعد: {names[some[0]]}", some[0], at=f"{tday} 09:12")
        store.log(c, sec, "pay", f"پرداخت شهریه‌ی {names[some[1]]}", some[1], at=f"{tday} 09:40")
        store.log(c, own, "class", "کلاس‌های ترم بعد دیده شد", at=f"{tday} 10:05")
        store.log(c, sec, "enroll", f"ثبت‌نام ترم بعد: {names[some[2]]}", some[2], at=f"{tday} 10:31")
        store.set_meta(c, "built_for", tday)
        store.set_meta(c, "demo_teacher", DEMO_TEACHER)
        store.set_meta(c, "demo_learner", demo_learner)
