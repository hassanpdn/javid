"""Every number and date the language institute's panels and the model use, computed by code from lang.db.

The week: classes meet twice a week on a pair of days (شنبه و دوشنبه، یکشنبه و سه‌شنبه، چهارشنبه و پنجشنبه), 90
minutes, at one of five slots; Friday is closed. A term is ten weeks from a Saturday, so each pair has its 20 sessions;
the next term starts after a week's break. Rooms and their seats are fixed here (ROOMS); holidays are not counted yet.
"""
import json
from datetime import date, timedelta
from jalali import to_jalali, MONTHS
from . import store, curriculum as cur

PAIRS = {"satmon": ("شنبه و دوشنبه", (5, 0)), "suntue": ("یکشنبه و سه‌شنبه", (6, 1)), "wedthu": ("چهارشنبه و پنجشنبه", (2, 3))}
SLOTS = ["09:00", "10:45", "16:00", "17:45", "19:30"]
ROOMS = {1: 12, 2: 12, 3: 10, 4: 14, 5: 8, 6: 12}      # room: seats
TERM_WEEKS = 10
MIN_FILL = 5          # a class of the next term with fewer learners than this, starting within FILL_DAYS, needs a decision
FILL_DAYS = 30
LOW_QUIZ = 60         # a class whose online test averages under this
STREAK = 3            # absent this many sessions in a row: call the learner
UNPAID_DAYS = 14      # a term's fee left unpaid this long after registering
RENEW_DAYS = 21       # the last weeks of a term, when learners should register for the next one
METHODS = {"card": "کارت‌خوان", "cash": "نقد", "transfer": "کارت به کارت"}
ATT = {"present": "حاضر", "absent": "غایب", "late": "با تأخیر"}

def today():
    return store.today()

def money(v):
    """Toman in plain words: 4_900_000 -> «4.9 میلیون تومان», 620_000 -> «620 هزار تومان»."""
    v = int(round(v or 0))
    if v >= 1_000_000_000:
        b, m = divmod(round(v / 1_000_000), 1000)
        return f"{b} میلیارد" + (f" و {m} میلیون" if m else "") + " تومان"
    if v >= 1_000_000:
        m = v / 1_000_000
        return (f"{m:.1f}".rstrip("0").rstrip(".") if m < 10 and v % 1_000_000 else str(round(m))) + " میلیون تومان"
    if v >= 1000:
        return f"{round(v / 1000)} هزار تومان"
    return f"{v} تومان"

def jfull(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{y}/{m:02d}/{d:02d}"

def jday(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{d} {MONTHS[m - 1]}"

def jmonth(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{MONTHS[m - 1]} {y}"

WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]   # date.weekday(): Monday is 0

def weekday(iso):
    return WEEKDAYS[date.fromisoformat(iso[:10]).weekday()]

def jlong(iso):
    """«شنبه 17 آبان»"""
    return f"{weekday(iso)} {jday(iso)}"

def days_ago(iso):
    return (today() - date.fromisoformat(iso[:10])).days

def day_word(iso):
    n = (date.fromisoformat(iso[:10]) - today()).days
    return "امروز" if n == 0 else "فردا" if n == 1 else "دیروز" if n == -1 else jlong(iso)

def week_start(d=None):
    """The Saturday that starts d's week."""
    d = d or today()
    return d - timedelta(days=(d.weekday() - 5) % 7)

def slot_end(t):
    m = int(t[:2]) * 60 + int(t[3:]) + 90
    return f"{m // 60:02d}:{m % 60:02d}"

def room_name(r):
    return f"کلاس {r}"

# ---------- terms and sessions ----------

def term(c, kind):
    row = c.execute("SELECT * FROM terms WHERE kind = ?", (kind,)).fetchone()
    return dict(row) if row else None

def term_by_id(c, tid):
    return dict(c.execute("SELECT * FROM terms WHERE id = ?", (tid,)).fetchone())

def session_days(t, pair):
    """The 20 dates a class of term t meets on its pair of days."""
    start, days = date.fromisoformat(t["start"]), PAIRS[pair][1]
    return [(start + timedelta(days=i)).isoformat() for i in range(TERM_WEEKS * 7) if (start + timedelta(days=i)).weekday() in days]

def held(t, pair):
    """The sessions already held (before today) and today's, if the class meets today."""
    days = session_days(t, pair)
    t0 = today().isoformat()
    return [d for d in days if d < t0], (t0 if t0 in days else None)

def term_view(t):
    if not t:
        return None
    left = (date.fromisoformat(t["end"]) - today()).days
    return t | {"start_text": jfull(t["start"]), "end_text": jfull(t["end"]), "start_long": jlong(t["start"]), "days_left": left,
                "starts_in": (date.fromisoformat(t["start"]) - today()).days}

# ---------- classes ----------

def lookups(c):
    return {"teachers": {r["id"]: dict(r) for r in c.execute("SELECT * FROM teachers")},
            "seats": {r[0]: r[1] for r in c.execute("SELECT class_id, COUNT(*) FROM enrollments WHERE status IN ('active', 'registered') GROUP BY class_id")}}

def avail(t):
    """A teacher's hours: {pair: [slots]}."""
    return json.loads(t["avail"] or "{}")

def class_view(c, cl, lk=None, t=None):
    lk = lk or lookups(c)
    cl = dict(cl)
    course = cur.TERM[cl["course"]]
    t = t or term_by_id(c, cl["term_id"])
    teacher = lk["teachers"].get(cl["teacher_id"], {})
    done, now = held(t, cl["pair"])
    upcoming = [d for d in session_days(t, cl["pair"]) if d > today().isoformat()]
    seats = lk["seats"].get(cl["id"], 0)
    return cl | {"course_name": course["name"], "course_en": course["en"], "level": course["level"], "hue": course["hue"], "cefr": course["cefr"],
                 "book": course["book"], "units": course["units"], "teacher": teacher.get("name", ""), "room_name": room_name(cl["room"]),
                 "capacity": ROOMS[cl["room"]], "seats": seats, "free": ROOMS[cl["room"]] - seats, "pair_text": PAIRS[cl["pair"]][0],
                 "time_text": f"{cl['time']} تا {slot_end(cl['time'])}", "kind": t["kind"],
                 "held": len(done), "today": bool(now), "next_day": (now or (upcoming[0] if upcoming else None)),
                 "next_text": (day_word(now or upcoming[0]) if (now or upcoming) else "")}

def classes(c, term_id):
    lk = lookups(c)
    t = term_by_id(c, term_id)
    return [class_view(c, r, lk, t) for r in c.execute("SELECT * FROM classes WHERE term_id = ? ORDER BY pair, time, room", (term_id,))]

def roster(c, class_id):
    return [dict(r) for r in c.execute("""SELECT e.*, s.name, s.phone FROM enrollments e JOIN students s ON s.id = e.student_id
                                          WHERE e.class_id = ? AND e.status IN ('active', 'registered') ORDER BY s.name""", (class_id,))]

def cell_reasons(c, cl, pair, time, room, lk=None):
    """Why a class cannot go to this cell of its term's timetable; [] when it can."""
    lk = lk or lookups(c)
    out = []
    for o in c.execute("SELECT * FROM classes WHERE term_id = ? AND pair = ? AND time = ? AND id != ?", (cl["term_id"], pair, time, cl["id"])):
        if o["room"] == room:
            out.append(f"{room_name(room)} در این ساعت جای کلاس {cur.TERM[o['course']]['name']} است")
        if o["teacher_id"] == cl["teacher_id"]:
            out.append(f"{lk['teachers'][cl['teacher_id']]['name']} در این ساعت کلاس {cur.TERM[o['course']]['name']} را دارد")
    teacher = lk["teachers"].get(cl["teacher_id"])
    if teacher and time not in avail(teacher).get(pair, []):
        out.append(f"{teacher['name']} {PAIRS[pair][0]} ساعت {time} کلاس نمی‌گیرد")
    seats = lk["seats"].get(cl["id"], 0)
    if seats > ROOMS[room]:
        out.append(f"{room_name(room)} {ROOMS[room]} جا دارد و این کلاس {seats} زبان‌آموز")
    return out

def move_grid(c, class_id):
    """Every cell of the class's term: can it go there, and if not, why."""
    cl = dict(c.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone())
    lk = lookups(c)
    cells = []
    for pair in PAIRS:
        for time in SLOTS:
            for room in ROOMS:
                here = (pair, time, room) == (cl["pair"], cl["time"], cl["room"])
                why = [] if here else cell_reasons(c, cl, pair, time, room, lk)
                cells.append({"pair": pair, "time": time, "room": room, "ok": not why, "here": here, "why": why})
    return cells

def teacher_options(c, class_id):
    """Who could teach this class at its hour: teaches its level, is free and comes at that hour."""
    cl = dict(c.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone())
    level = cur.TERM[cl["course"]]["level"]
    out = []
    for t in c.execute("SELECT * FROM teachers ORDER BY name"):
        if t["id"] == cl["teacher_id"]:
            continue
        why = []
        if level not in t["levels"].split(","):
            why.append(f"سطح {cur.LEVEL[level]['fa']} را درس نمی‌دهد")
        if cl["time"] not in avail(t).get(cl["pair"], []):
            why.append("در این ساعت نمی‌آید")
        busy = c.execute("SELECT course FROM classes WHERE term_id = ? AND pair = ? AND time = ? AND teacher_id = ?",
                         (cl["term_id"], cl["pair"], cl["time"], t["id"])).fetchone()
        if busy:
            why.append(f"در این ساعت کلاس {cur.TERM[busy['course']]['name']} را دارد")
        out.append({"id": t["id"], "name": t["name"], "ok": not why, "why": why})
    return sorted(out, key=lambda o: (not o["ok"], o["name"]))

def problems(c, t):
    """What does not work in a term's timetable: a room or a teacher in two places, a teacher at an hour they do not
    come, more learners than seats, and (for the next term, close to its start) a class too small to open."""
    lk, out = lookups(c), []
    rows = [dict(r) for r in c.execute("SELECT * FROM classes WHERE term_id = ? ORDER BY pair, time, room", (t["id"],))]
    name = lambda cl: cur.TERM[cl["course"]]["name"]
    seen = set()
    for a in rows:
        for b in rows:
            if a["id"] >= b["id"] or (a["pair"], a["time"]) != (b["pair"], b["time"]):
                continue
            if a["room"] == b["room"] and ("room", a["id"], b["id"]) not in seen:
                seen.add(("room", a["id"], b["id"]))
                out.append({"type": "room", "tone": "danger", "class_ids": [a["id"], b["id"]], "order": 1,
                            "title": f"دو کلاس {PAIRS[a['pair']][0]} ساعت {a['time']} در {room_name(a['room'])}",
                            "detail": f"{name(a)} و {name(b)} هر دو در یک اتاق‌اند. یکی را در جدول کلاس‌ها جابه‌جا کنید."})
            if a["teacher_id"] == b["teacher_id"]:
                teacher = lk["teachers"][a["teacher_id"]]["name"]
                out.append({"type": "teacher", "tone": "danger", "class_ids": [a["id"], b["id"]], "order": 1, "teacher_id": a["teacher_id"],
                            "title": f"{teacher} {PAIRS[a['pair']][0]} ساعت {a['time']} دو کلاس دارد",
                            "detail": f"{name(a)} در {room_name(a['room'])} و {name(b)} در {room_name(b['room'])}. یکی از کلاس‌ها را جابه‌جا کنید یا استاد دیگری بدهید."})
    for a in rows:
        teacher = lk["teachers"].get(a["teacher_id"])
        if teacher and a["time"] not in avail(teacher).get(a["pair"], []):
            out.append({"type": "unavailable", "tone": "warning", "class_ids": [a["id"]], "order": 2, "teacher_id": a["teacher_id"],
                        "title": f"{teacher['name']} {PAIRS[a['pair']][0]} ساعت {a['time']} نمی‌آید، ولی کلاس {name(a)} با اوست",
                        "detail": "ساعت‌های این استاد با این کلاس جور نیست. کلاس را به ساعتی ببرید که می‌آید، یا استاد دیگری بدهید."})
        seats = lk["seats"].get(a["id"], 0)
        if seats > ROOMS[a["room"]]:
            out.append({"type": "capacity", "tone": "warning", "class_ids": [a["id"]], "order": 2,
                        "title": f"کلاس {name(a)} {seats} زبان‌آموز دارد و {room_name(a['room'])} {ROOMS[a['room']]} جا",
                        "detail": f"{PAIRS[a['pair']][0]} ساعت {a['time']}، {teacher['name'] if teacher else ''}. کلاس را به اتاق بزرگ‌تری ببرید."})
        starts = (date.fromisoformat(t["start"]) - today()).days
        if t["kind"] == "next" and seats < MIN_FILL and starts <= FILL_DAYS:
            out.append({"type": "small", "tone": "info", "class_ids": [a["id"]], "order": 3,
                        "title": f"کلاس {name(a)} ترم بعد فقط {seats} زبان‌آموز دارد",
                        "detail": f"{PAIRS[a['pair']][0]} ساعت {a['time']}، {starts} روز تا شروع ترم. با کمتر از {MIN_FILL} نفر، کلاس را با کلاس دیگری یکی کنید یا ثبت‌نام را پیگیری کنید."})
    return sorted(out, key=lambda p: p["order"])

# ---------- money ----------

def paid_of(c, enrollment_id):
    return c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE enrollment_id = ?", (enrollment_id,)).fetchone()[0]

def unpaid(c):
    """Learners of the running term whose fee is not all paid, UNPAID_DAYS after registering, most owed first."""
    t = term(c, "current")
    out = []
    for e in c.execute("""SELECT e.*, s.name, s.phone, cl.course FROM enrollments e JOIN classes cl ON cl.id = e.class_id JOIN students s ON s.id = e.student_id
                          WHERE cl.term_id = ? AND e.status = 'active'""", (t["id"],)):
        left = e["fee"] - paid_of(c, e["id"])
        if left > 0 and days_ago(e["registered"]) >= UNPAID_DAYS:
            out.append({"student_id": e["student_id"], "name": e["name"], "phone": e["phone"], "enrollment_id": e["id"], "fee": e["fee"],
                        "paid": e["fee"] - left, "left": left, "days": days_ago(e["registered"]), "course": cur.TERM[e["course"]]["name"]})
    return sorted(out, key=lambda u: -u["left"])

# ---------- attendance ----------

def streaks(c, class_ids=None):
    """Learners absent in each of their class's last STREAK recorded sessions."""
    t = term(c, "current")
    out = []
    q = """SELECT e.student_id, e.class_id, s.name, s.phone, cl.course FROM enrollments e JOIN classes cl ON cl.id = e.class_id JOIN students s ON s.id = e.student_id
           WHERE cl.term_id = ? AND e.status = 'active'"""
    for e in c.execute(q, (t["id"],)).fetchall():
        if class_ids is not None and e["class_id"] not in class_ids:
            continue
        last = [r["status"] for r in c.execute("SELECT status FROM attendance WHERE class_id = ? AND student_id = ? ORDER BY day DESC LIMIT ?",
                                                (e["class_id"], e["student_id"], STREAK))]
        if len(last) == STREAK and all(s == "absent" for s in last):
            days = [r["day"] for r in c.execute("SELECT day FROM attendance WHERE class_id = ? AND student_id = ? ORDER BY day DESC LIMIT ?",
                                                 (e["class_id"], e["student_id"], STREAK))]
            out.append(dict(e) | {"days": sorted(days), "course_name": cur.TERM[e["course"]]["name"]})
    return out

def missing_attendance(c, class_ids):
    """Sessions of the last week already held with no attendance written: (class_id, day)."""
    t = term(c, "current")
    week = (today() - timedelta(days=7)).isoformat()
    out = []
    for cl in c.execute("SELECT * FROM classes WHERE term_id = ?", (t["id"],)):
        if cl["id"] not in class_ids:
            continue
        done, _ = held(t, cl["pair"])
        written = {r[0] for r in c.execute("SELECT DISTINCT day FROM attendance WHERE class_id = ?", (cl["id"],))}
        out += [(cl["id"], d) for d in done if d >= week and d not in written]
    return out

def attendance_of(c, student_id, class_id):
    rows = c.execute("SELECT day, status FROM attendance WHERE student_id = ? AND class_id = ? ORDER BY day", (student_id, class_id)).fetchall()
    n = {k: sum(1 for r in rows if r["status"] == k) for k in ATT}
    return {"rows": [dict(r) | {"day_text": jday(r["day"]), "status_text": ATT[r["status"]]} for r in rows], "counts": n,
            "rate": round(100 * (n["present"] + n["late"]) / len(rows)) if rows else None}

# ---------- tests ----------

def grade(question_ids, answers):
    """(score out of 100, {skill: [right, of]}, [question ids answered wrong])."""
    right, skills, wrong = 0, {}, []
    for qid in question_ids:
        q = cur.QUESTIONS[qid]
        ok = answers.get(qid) == q["answer"]
        s = skills.setdefault(q["skill"], [0, 0])
        s[1] += 1
        if ok:
            right += 1; s[0] += 1
        else:
            wrong.append(qid)
    return round(100 * right / len(question_ids)) if question_ids else 0, skills, wrong

def place(answers):
    """The placement test: the first level where fewer than two of its three questions are right is where the learner
    starts (its first term). All levels right: the last term."""
    for key, *_ in cur.LEVELS:
        qs = [q for q in cur.PLACEMENT if q.startswith(key + "-")]
        if sum(answers.get(q) == cur.QUESTIONS[q]["answer"] for q in qs) < 2:
            return f"{key}-1"
    return cur.KEYS[-1]

def exam_view(c, e, student_id=None):
    e = dict(e)
    qs = json.loads(e["questions"])
    out = e | {"count": len(qs), "opens_text": jfull(e["opens"]), "closes_text": jfull(e["closes"]), "closes_word": day_word(e["closes"]),
               "open": e["opens"][:10] <= today().isoformat() <= e["closes"][:10], "over": e["closes"][:10] < today().isoformat()}
    out.pop("questions")
    if e["class_id"]:
        stats = c.execute("SELECT COUNT(*), AVG(score) FROM attempts WHERE exam_id = ? AND submitted IS NOT NULL", (e["id"],)).fetchone()
        out |= {"taken": stats[0], "average": round(stats[1]) if stats[1] is not None else None,
                "of": c.execute("SELECT COUNT(*) FROM enrollments WHERE class_id = ? AND status = 'active'", (e["class_id"],)).fetchone()[0]}
    if student_id:
        a = c.execute("SELECT * FROM attempts WHERE exam_id = ? AND student_id = ? ORDER BY id DESC LIMIT 1", (e["id"], student_id)).fetchone()
        out["mine"] = {"id": a["id"], "score": a["score"], "submitted": a["submitted"]} if a else None
    return out

def skill_totals(c, student_id):
    """A learner's right answers by skill over the online tests of the running term."""
    t = term(c, "current")
    tot = {}
    for a in c.execute("""SELECT a.by_skill FROM attempts a JOIN exams e ON e.id = a.exam_id JOIN classes cl ON cl.id = e.class_id
                          WHERE a.student_id = ? AND a.submitted IS NOT NULL AND cl.term_id = ?""", (student_id, t["id"])):
        for k, (r, n) in json.loads(a["by_skill"]).items():
            s = tot.setdefault(k, [0, 0]); s[0] += r; s[1] += n
    return {k: {"right": r, "of": n, "pct": round(100 * r / n), "name": cur.SKILLS[k]} for k, (r, n) in tot.items()}

def quiz_avg(c, student_id, class_id):
    r = c.execute("""SELECT AVG(a.score) FROM attempts a JOIN exams e ON e.id = a.exam_id WHERE a.student_id = ? AND e.class_id = ?
                     AND a.submitted IS NOT NULL""", (student_id, class_id)).fetchone()[0]
    return round(r) if r is not None else None

def so_far(midterm, quiz):
    """The term's mark so far: the midterm and the online tests' average, equally."""
    parts = [p for p in (midterm, quiz) if p is not None]
    return round(sum(parts) / len(parts)) if parts else None

def low_quizzes(c, class_ids=None):
    t = term(c, "current")
    out = []
    for e in c.execute("""SELECT e.* FROM exams e JOIN classes cl ON cl.id = e.class_id WHERE cl.term_id = ? AND e.kind = 'quiz' AND substr(e.closes, 1, 10) < ?""",
                       (t["id"], today().isoformat())):
        if class_ids is not None and e["class_id"] not in class_ids:
            continue
        v = exam_view(c, e)
        if v["average"] is not None and v["average"] < LOW_QUIZ:
            skills = {}
            for a in c.execute("SELECT by_skill FROM attempts WHERE exam_id = ? AND submitted IS NOT NULL", (e["id"],)):
                for k, (r, n) in json.loads(a["by_skill"]).items():
                    s = skills.setdefault(k, [0, 0]); s[0] += r; s[1] += n
            weakest = min(skills, key=lambda k: skills[k][0] / skills[k][1])
            out.append(v | {"weakest": cur.SKILLS[weakest], "weakest_pct": round(100 * skills[weakest][0] / skills[weakest][1])})
    return out

# ---------- the learner's road ----------

def road(c, student_id):
    """The twelve stations and where this learner is: done (with the mark), skipped (placed above them), current (the
    book, the units, sessions held), next (its book, when it starts, the class registered for or the ones to pick),
    future; and when the road ends if they go on without a break."""
    s = dict(c.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone())
    s["created_text"] = jfull(s["created"])
    rows = c.execute("""SELECT e.*, cl.course, cl.term_id, cl.teacher_id, t.name term_name, t.kind, t.start FROM enrollments e
                        JOIN classes cl ON cl.id = e.class_id JOIN terms t ON t.id = cl.term_id WHERE e.student_id = ? AND e.status != 'dropped'
                        ORDER BY t.start""", (student_id,)).fetchall()
    by = {}
    for r in rows:
        by.setdefault(r["course"], []).append(dict(r))
    start_i = cur.KEYS.index(s["start_key"]) if s["start_key"] else 0
    current = next((r for r in rows if r["status"] == "active"), None)
    registered = next((r for r in rows if r["status"] == "registered"), None)
    cur_i = cur.KEYS.index(current["course"]) if current else None
    passed = [r for r in rows if r["status"] == "passed"]
    last_done = max((cur.KEYS.index(r["course"]) for r in passed), default=start_i - 1)
    next_i = cur_i + 1 if cur_i is not None else (cur.KEYS.index(registered["course"]) if registered else last_done + 1)
    stations = []
    for i, k in enumerate(cur.KEYS):
        tk = cur.TERM[k]
        st = {"key": k, "name": tk["name"], "fa": tk["fa"], "level": tk["level"], "cefr": tk["cefr"], "hue": tk["hue"], "book": tk["book"],
              "units": tk["units"], "new_book": tk["num"] == 1}
        mine = by.get(k, [])
        ok = next((r for r in mine if r["status"] == "passed"), None)
        if ok:
            st |= {"state": "done", "score": ok["score"], "term": ok["term_name"], "repeated": sum(1 for r in mine if r["status"] == "failed")}
        elif cur_i == i:
            st["state"] = "current"
        elif i == next_i and next_i < len(cur.KEYS):
            st["state"] = "next"
        elif i < start_i:
            st["state"] = "skipped"
        else:
            st["state"] = "future"
        stations.append(st)
    out = {"student": s, "stations": stations, "current": None, "next": None}
    if current:
        cl = c.execute("SELECT * FROM classes WHERE id = ?", (current["class_id"],)).fetchone()
        v = class_view(c, cl)
        t = term(c, "current")
        done, now = held(t, cl["pair"])
        n = len(done) + (1 if now else 0)
        unit = cur.unit_of_session(min(max(n, 1), cur.SESSIONS))
        tk = cur.TERM[current["course"]]
        qa = quiz_avg(c, student_id, cl["id"])
        out["current"] = {"class": v, "enrollment_id": current["id"], "term": term_view(t), "sessions": n, "of": cur.SESSIONS,
                          "pct": round(100 * len(done) / cur.SESSIONS), "attendance": attendance_of(c, student_id, cl["id"]),
                          "midterm": current["midterm"], "quiz": qa, "so_far": so_far(current["midterm"], qa),
                          "unit": (tk["units"][0] + unit) if unit is not None else None,
                          "topic": tk["topics"][tk["units"][0] - 1 + unit] if unit is not None else None,
                          "fee": current["fee"], "paid": paid_of(c, current["id"]), "left": current["fee"] - paid_of(c, current["id"]),
                          "left_text": money(current["fee"] - paid_of(c, current["id"]))}
    if next_i < len(cur.KEYS):
        tk = cur.TERM[cur.KEYS[next_i]]
        nt = term(c, "next")
        same = current and cur.TERM[current["course"]]["level"] == tk["level"]
        nx = {"key": tk["key"], "name": tk["name"], "fa": tk["fa"], "book": tk["book"], "units": tk["units"], "same_book": bool(same),
              "book_price": tk["book_price"], "book_price_text": money(tk["book_price"]), "fee": tk["fee"], "fee_text": money(tk["fee"]),
              "term": term_view(nt), "registered": None, "options": []}
        if registered and registered["course"] == tk["key"]:
            nx["registered"] = class_view(c, c.execute("SELECT * FROM classes WHERE id = ?", (registered["class_id"],)).fetchone()) | {
                "enrollment_id": registered["id"], "paid": paid_of(c, registered["id"]), "fee": registered["fee"], "left": registered["fee"] - paid_of(c, registered["id"])}
        elif nt:
            lk = lookups(c)
            nx["options"] = [class_view(c, r, lk, nt) for r in c.execute("SELECT * FROM classes WHERE term_id = ? AND course = ? ORDER BY pair, time",
                                                                          (nt["id"], tk["key"]))]
        out["next"] = nx
        left = len(cur.KEYS) - next_i
        if nt:
            finish = date.fromisoformat(nt["start"]) + timedelta(weeks=(TERM_WEEKS + 1) * left - 1, days=-2)
            out["finish"] = {"terms": left + (1 if current else 0), "month": jmonth(finish.isoformat())}
    done_n = sum(1 for st in stations if st["state"] in ("done", "skipped"))
    part = (out["current"]["sessions"] / cur.SESSIONS) if out["current"] else 0
    out["pct"] = round(100 * (done_n + part) / len(cur.KEYS))
    return out

# ---------- the week's plan ----------

def week_plan(c, student_id):
    """What to do this week, built from the book's units, the sessions of this week, the weak skills in the online
    tests, an absence and an open test. Items keep a stable key so their ticks last the week."""
    r = road(c, student_id)
    cu = r["current"]
    wk = week_start().isoformat()
    if not cu:
        return {"week": wk, "items": []}
    t, cl = cu["term"], cu["class"]
    tk = cur.TERM[cl["course"]]
    days = session_days(t, cl["pair"])
    this_week = [(i + 1, d) for i, d in enumerate(days) if wk <= d < (week_start() + timedelta(days=7)).isoformat()]
    items = []
    for n, d in this_week:
        u = cur.unit_of_session(n)
        when = "گذشت" if d < today().isoformat() else day_word(d)
        if u is None:
            first, last = (tk["units"][0], tk["units"][0] + 2) if n == cur.MIDTERM else (tk["units"][0], tk["units"][1])
            items.append({"key": f"s{n}-exam", "kind": "exam", "when": when, "day": d,
                          "text": f"جلسه‌ی {n}، {jlong(d)}: آزمون {'میان‌ترم' if n == cur.MIDTERM else 'پایان ترم'}. درس‌های {first} تا {last} را مرور کنید."})
            continue
        unit = tk["units"][0] + u
        topic = tk["topics"][unit - 1]
        if ((n - 1) if n < cur.MIDTERM else (n - 11)) % 3 == 0:       # the first session of a unit
            items.append({"key": f"s{n}-read", "kind": "book", "when": when, "day": d,
                          "text": f"پیش از جلسه‌ی {n} ({jlong(d)}): درس {unit} کتاب، «{topic}»، را یک بار بخوانید و واژه‌های جدیدش را علامت بزنید."})
        items.append({"key": f"s{n}-wb", "kind": "workbook", "when": when, "day": d,
                      "text": f"پس از جلسه‌ی {n}: تمرین‌های کتاب کار درس {unit}."})
    weak = {k: v for k, v in skill_totals(c, student_id).items() if v["pct"] < 60}
    unit_now = cu["unit"] or tk["units"][0]
    tips = {"grammar": f"روزی ۱۵ دقیقه دستور زبان درس {unit_now}: جمله‌های تمرین را بلند بخوانید و پنج جمله‌ی جدید بسازید.",
            "vocab": f"روزی ۱۰ دقیقه واژه‌های درس {unit_now} و درس پیش از آن را با کارت مرور کنید.",
            "reading": "یک متن کوتاه از بخش Reading کتاب کار را بخوانید و خلاصه‌اش را در سه جمله بنویسید."}
    for k, v in weak.items():
        items.append({"key": f"weak-{k}", "kind": "skill", "when": "این هفته", "text": tips[k],
                      "why": f"در آزمون‌های آنلاین این ترم {v['right']} از {v['of']} پرسش {v['name']} را درست جواب داده‌اید."})
    att = cu["attendance"]["rows"]
    if att and att[-1]["status"] == "absent":
        items.append({"key": f"absent-{att[-1]['day']}", "kind": "absent", "when": "پیش از جلسه‌ی بعد",
                      "text": f"جلسه‌ی {jlong(att[-1]['day'])} غایب بودید. درس آن جلسه را از استاد یا هم‌کلاسی‌ها بگیرید."})
    for e in c.execute("SELECT * FROM exams WHERE class_id = ? AND kind = 'quiz'", (cl["id"],)):
        v = exam_view(c, e, student_id)
        if v["open"] and not (v["mine"] and v["mine"]["submitted"]):
            items.append({"key": f"exam-{e['id']}", "kind": "test", "when": f"تا {v['closes_word']}", "exam_id": e["id"],
                          "text": f"آزمون آنلاین «{e['title']}»: {v['count']} پرسش در {e['minutes']} دقیقه."})
    ticked = {x[0] for x in c.execute("SELECT item FROM ticks WHERE student_id = ? AND week = ?", (student_id, wk))}
    for i in items:
        i["done"] = i["key"] in ticked
    return {"week": wk, "week_text": f"هفته‌ی {jday(wk)} تا {jday((week_start() + timedelta(days=5)).isoformat())}", "items": items,
            "done": sum(i["done"] for i in items)}

# ---------- what needs doing ----------

def renewals(c):
    """Learners of the running term not registered for the next one, with the class they would go to."""
    cu, nt = term(c, "current"), term(c, "next")
    regd = {r[0] for r in c.execute("""SELECT e.student_id FROM enrollments e JOIN classes cl ON cl.id = e.class_id
                                       WHERE cl.term_id = ? AND e.status = 'registered'""", (nt["id"],))}
    lk = lookups(c)
    out = []
    for e in c.execute("""SELECT e.*, s.name, s.phone, cl.course, cl.teacher_id, cl.pair, cl.time FROM enrollments e JOIN classes cl ON cl.id = e.class_id
                          JOIN students s ON s.id = e.student_id WHERE cl.term_id = ? AND e.status = 'active' ORDER BY s.name""", (cu["id"],)):
        if e["student_id"] in regd:
            continue
        nk = cur.next_key(e["course"])
        if not nk:
            continue
        options = c.execute("SELECT * FROM classes WHERE term_id = ? AND course = ?", (nt["id"], nk)).fetchall()
        best = next((o for o in options if o["teacher_id"] == e["teacher_id"]), options[0] if options else None)
        out.append({"student_id": e["student_id"], "name": e["name"], "phone": e["phone"], "course": cur.TERM[e["course"]]["name"],
                    "next": cur.TERM[nk]["name"], "class": class_view(c, best, lk, nt) if best else None})
    return out

def waiting_new(c):
    """New learners who took the placement test and have no class yet."""
    return [dict(r) | {"placed_name": cur.TERM[r["placed"]]["name"], "day_text": day_word(r["submitted"]), "phone": r["phone"]}
            for r in c.execute("""SELECT a.*, s.name, s.phone FROM attempts a JOIN exams e ON e.id = a.exam_id JOIN students s ON s.id = a.student_id
                                  WHERE e.kind = 'placement' AND a.submitted IS NOT NULL
                                  AND NOT EXISTS (SELECT 1 FROM enrollments x WHERE x.student_id = a.student_id AND x.status IN ('active', 'registered'))
                                  ORDER BY a.submitted DESC""")]

def office_alerts(c, role):
    """Today's work for the manager and the secretary, most urgent first."""
    out = []
    if role == "owner":
        for kind in ("current", "next"):
            out += [p | {"icon": "calendar", "act": "board", "term": kind} for p in problems(c, term(c, kind))]
        for q in low_quizzes(c):
            out.append({"type": "quiz", "tone": "info", "icon": "chart", "order": 4, "class_id": q["class_id"], "act": "class",
                        "title": f"میانگین آزمون آنلاین «{q['title']}» {q['average']} از ۱۰۰ است",
                        "detail": f"{q['taken']} نفر آزمون دادند. ضعیف‌ترین بخش: {q['weakest']} با {q['weakest_pct']} درصد پاسخ درست."})
    for s in streaks(c):
        out.append({"type": "absent", "tone": "warning", "icon": "user", "order": 2, "student_id": s["student_id"], "act": "student",
                    "title": f"{s['name']} سه جلسه‌ی آخر کلاس {s['course_name']} را غایب بوده است",
                    "detail": "جلسه‌های " + "، ".join(jday(d) for d in s["days"]) + ". تماس بگیرید و بپرسید چه شده است.", "message": "absent"})
    for u in unpaid(c):
        out.append({"type": "unpaid", "tone": "warning" if u["paid"] else "danger", "icon": "chart", "order": 3, "student_id": u["student_id"], "act": "student",
                    "money": u["left"], "message": "unpaid",
                    "title": f"{money(u['left'])} از شهریه‌ی {u['name']} مانده است",
                    "detail": f"کلاس {u['course']}، شهریه {money(u['fee'])}، پرداخت‌شده {money(u['paid'])}. {u['days']} روز از ثبت‌نام گذشته است."})
    for w in waiting_new(c):
        out.append({"type": "placed", "tone": "info", "icon": "sparkles", "order": 2, "student_id": w["student_id"], "act": "enroll", "placed": w["placed"],
                    "title": f"{w['name']} {w['day_text']} آزمون تعیین سطح داد و هنوز کلاس ندارد",
                    "detail": f"سطح: {w['placed_name']}. کلاس‌های ترم بعد این سطح را ببینید و ثبت‌نامش کنید."})
    cu = term(c, "current")
    left = (date.fromisoformat(cu["end"]) - today()).days
    if role == "secretary" and 0 <= left <= RENEW_DAYS:
        n = len(renewals(c))
        if n:
            out.append({"type": "renew", "tone": "info", "icon": "users", "order": 4, "act": "renewals",
                        "title": f"{n} زبان‌آموز هنوز برای ترم بعد ثبت‌نام نکرده‌اند",
                        "detail": f"{left} روز تا پایان ترم مانده است. برای هر کدام پیام یادآوری آماده است."})
    return sorted(out, key=lambda a: (a["order"], -a.get("money", 0), a["title"]))

def office_stats(c):
    cu, nt = term(c, "current"), term(c, "next")
    active = c.execute("""SELECT COUNT(*) FROM enrollments e JOIN classes cl ON cl.id = e.class_id WHERE cl.term_id = ? AND e.status = 'active'""", (cu["id"],)).fetchone()[0]
    n_classes = c.execute("SELECT COUNT(*) FROM classes WHERE term_id = ?", (cu["id"],)).fetchone()[0]
    by_level = c.execute("""SELECT substr(cl.course, 1, instr(cl.course, '-') - 1) lv, COUNT(*) n FROM enrollments e JOIN classes cl ON cl.id = e.class_id
                            WHERE cl.term_id = ? AND e.status = 'active' GROUP BY lv""", (cu["id"],)).fetchall()
    counts = {r["lv"]: r["n"] for r in by_level}
    eligible = c.execute("""SELECT COUNT(*) FROM enrollments e JOIN classes cl ON cl.id = e.class_id WHERE cl.term_id = ? AND e.status = 'active' AND cl.course != ?""",
                         (cu["id"], cur.KEYS[-1])).fetchone()[0]
    continuing = eligible - len(renewals(c))
    regd = c.execute("""SELECT COUNT(*) FROM enrollments e JOIN classes cl ON cl.id = e.class_id WHERE cl.term_id = ? AND e.status = 'registered'""", (nt["id"],)).fetchone()[0]
    next_classes = classes(c, nt["id"])
    cap = sum(cl["capacity"] for cl in next_classes)
    owed = unpaid(c)
    left = (date.fromisoformat(cu["end"]) - today()).days
    return [
        {"label": "زبان‌آموزان این ترم", "value": str(active), "sub": f"در {n_classes} کلاس", "icon": "users", "tone": "primary",
         "how": [f"{cur.LEVEL[k]['fa']} ({cur.LEVEL[k]['cefr']}): {counts.get(k, 0)} نفر" for k, *_ in cur.LEVELS] + [f"= {active} زبان‌آموز در {n_classes} کلاس"]},
        {"label": "ثبت‌نام ترم بعد", "value": f"{continuing} از {eligible}", "sub": f"{round(100 * continuing / eligible) if eligible else 0} درصد · {left} روز تا پایان ترم",
         "icon": "calendar", "tone": "info",
         "how": [f"زبان‌آموزان این ترم که ترم بعدی دارند: {eligible}", f"ثبت‌نام کرده‌اند: {continuing}", f"هنوز ثبت‌نام نکرده‌اند: {eligible - continuing}",
                 f"همه‌ی ثبت‌نام‌های ترم بعد، با زبان‌آموزان جدید: {regd}"]},
        {"label": "پر بودن کلاس‌های ترم بعد", "value": f"{round(100 * regd / cap) if cap else 0} درصد", "sub": f"{regd} جا از {cap}", "icon": "chart", "tone": "success",
         "how": [f"{cl['course_name']} · {cl['pair_text']} {cl['time']} · {cl['room_name']}: {cl['seats']} از {cl['capacity']}" for cl in next_classes] + [f"= {regd} از {cap} جا"]},
        {"label": "شهریه‌ی مانده", "value": money(sum(u["left"] for u in owed)), "sub": f"{len(owed)} زبان‌آموز", "icon": "alert", "tone": "warning" if owed else "success",
         "how": [f"{u['name']}: شهریه {money(u['fee'])} − پرداخت {money(u['paid'])} = {money(u['left'])}" for u in owed] + [f"= جمع: {money(sum(u['left'] for u in owed))}"]},
    ]

def today_classes(c, teacher_id=None):
    cu = term(c, "current")
    t0 = today().isoformat()
    lk = lookups(c)
    rows = c.execute("SELECT * FROM classes WHERE term_id = ? ORDER BY time, room", (cu["id"],)).fetchall()
    out = [class_view(c, r, lk, cu) for r in rows if t0 in session_days(cu, r["pair"]) and (teacher_id is None or r["teacher_id"] == teacher_id)]
    for v in out:
        v["written"] = bool(c.execute("SELECT 1 FROM attendance WHERE class_id = ? AND day = ? LIMIT 1", (v["id"], t0)).fetchone())
        v["session_no"] = session_days(cu, v["pair"]).index(t0) + 1
    return out

def teacher_home(c, teacher_id):
    cu = term(c, "current")
    mine = [r["id"] for r in c.execute("SELECT id FROM classes WHERE term_id = ? AND teacher_id = ?", (cu["id"], teacher_id))]
    lk = lookups(c)
    my = [class_view(c, r, lk, cu) for r in c.execute("SELECT * FROM classes WHERE term_id = ? AND teacher_id = ? ORDER BY pair, time", (cu["id"], teacher_id))]
    alerts = []
    for cid, d in missing_attendance(c, set(mine)):
        v = next(x for x in my if x["id"] == cid)
        alerts.append({"type": "attendance", "tone": "warning", "icon": "check", "class_id": cid, "day": d, "act": "attendance", "order": 1,
                       "title": f"حضور و غیاب جلسه‌ی {jlong(d)} کلاس {v['course_name']} ثبت نشده است",
                       "detail": f"{v['pair_text']} ساعت {v['time']}، {v['room_name']}. چند ثانیه بیشتر طول نمی‌کشد."})
    for s in streaks(c, set(mine)):
        alerts.append({"type": "absent", "tone": "warning", "icon": "user", "class_id": s["class_id"], "student_id": s["student_id"], "act": "class", "order": 2,
                       "title": f"{s['name']} سه جلسه‌ی آخر کلاس {s['course_name']} نیامده است",
                       "detail": "دفتر آموزشگاه هم این را می‌بیند و تماس می‌گیرد. اگر از دلیلش خبر دارید، به دفتر بگویید."})
    for q in low_quizzes(c, set(mine)):
        alerts.append({"type": "quiz", "tone": "info", "icon": "chart", "class_id": q["class_id"], "act": "results", "exam_id": q["id"], "order": 3,
                       "title": f"میانگین آزمون «{q['title']}» {q['average']} از ۱۰۰ شد",
                       "detail": f"ضعیف‌ترین بخش {q['weakest']} است ({q['weakest_pct']} درصد درست). شاید یک جلسه مرور لازم باشد."})
    for e in c.execute(f"SELECT * FROM exams WHERE kind = 'quiz' AND class_id IN ({','.join('?' * len(mine)) or 'NULL'})", mine):
        v = exam_view(c, e)
        if v["open"]:
            alerts.append({"type": "open", "tone": "success", "icon": "sparkles", "class_id": e["class_id"], "act": "results", "exam_id": e["id"], "order": 4,
                           "title": f"آزمون «{e['title']}» باز است: {v['taken']} نفر از {v['of']} نفر داده‌اند",
                           "detail": f"تا {v['closes_word']} باز است. نمره‌ها را خود برنامه می‌دهد."})
    students = sum(v["seats"] for v in my)
    att = c.execute(f"SELECT status, COUNT(*) n FROM attendance WHERE class_id IN ({','.join('?' * len(mine)) or 'NULL'}) GROUP BY status", mine).fetchall()
    n = {r["status"]: r["n"] for r in att}
    total = sum(n.values())
    qa = c.execute(f"""SELECT AVG(a.score) FROM attempts a JOIN exams e ON e.id = a.exam_id WHERE e.class_id IN ({','.join('?' * len(mine)) or 'NULL'})
                       AND a.submitted IS NOT NULL""", mine).fetchone()[0]
    stats = [
        {"label": "کلاس‌های این ترم", "value": str(len(my)), "sub": f"{len(my) * 3} ساعت در هفته", "icon": "calendar", "tone": "primary",
         "how": [f"{v['course_name']} · {v['pair_text']} {v['time']} · {v['room_name']}" for v in my]},
        {"label": "زبان‌آموزان", "value": str(students), "sub": "در همه‌ی کلاس‌ها", "icon": "users", "tone": "info",
         "how": [f"{v['course_name']}: {v['seats']} نفر" for v in my]},
        {"label": "حضور در کلاس‌ها", "value": f"{round(100 * (n.get('present', 0) + n.get('late', 0)) / total) if total else 0} درصد", "sub": f"{n.get('absent', 0)} غیبت در این ترم",
         "icon": "check", "tone": "success", "how": [f"حاضر: {n.get('present', 0)}", f"با تأخیر: {n.get('late', 0)}", f"غایب: {n.get('absent', 0)}"]},
        {"label": "میانگین آزمون‌های آنلاین", "value": f"{round(qa) if qa is not None else 0} از ۱۰۰", "sub": "همه‌ی کلاس‌ها", "icon": "chart", "tone": "warning",
         "how": ["میانگین نمره‌ی همه‌ی آزمون‌های آنلاینی که زبان‌آموزان کلاس‌های شما داده‌اند"]},
    ]
    return {"classes": my, "today": today_classes(c, teacher_id), "alerts": sorted(alerts, key=lambda a: a["order"]), "stats": stats}

def overview(c, role):
    t = today().isoformat()
    cu = term(c, "current")
    return {"today": jfull(t), "today_long": jlong(t), "term": term_view(cu), "next_term": term_view(term(c, "next")),
            "stats": office_stats(c), "alerts": office_alerts(c, role), "classes_today": today_classes(c)}

def brief_facts(c):
    o = overview(c, "owner")
    lines = [f"امروز: {o['today_long']} {o['today']}", f"{o['term']['name']}: {o['term']['days_left']} روز تا پایان ترم"]
    lines += [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]]
    lines += ["کارهای امروز به ترتیب فوریت:"] + [f"{i + 1}. {a['title']}" for i, a in enumerate(o["alerts"][:6])]
    return "\n".join(lines), o

def events(c, after=0, limit=40, student_id=None):
    q, args = "SELECT * FROM events WHERE id > ?", [after]
    if student_id:
        q += " AND student_id = ?"; args.append(student_id)
    rows = c.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit)).fetchall()
    t = today().isoformat()
    return [{"id": e["id"], "kind": e["kind"], "text": e["text"], "who": e["who"], "role": e["role"], "today": e["at"][:10] == t,
             "day": jday(e["at"]), "time": e["at"][11:16], "student_id": e["student_id"]} for e in rows]
