"""The language institute's endpoints, all under /lang. Logins, sessions and data are its own (lang.db); the site's
door and the card's login (access.py) cover these like every other path.

Roles: owner (مدیر) runs the timetable, the teachers and the classes, and sees the log and the morning summary;
secretary (منشی) registers learners, runs the placement test in the office, takes fees and calls; teacher (استاد)
sees only their own classes: attendance, marks and online tests; student (زبان‌آموز) sees only their own road, plan,
tests and fee. Every number is worked out by code (facts.py) and every test is marked by code; the model only writes
the morning summary, the learner's short note and the floating assistant's answers, whose numbers are checked, with a
code-written fallback. Nothing is sent to anyone from here: messages are drafts a person reads and sends.
"""
import json, re, threading, random
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from llm import ask_llm
from checks import only_known_numbers
from . import institute, store, demo, facts, curriculum as cur

router = APIRouter(prefix="/lang")
_lock = threading.Lock()
_cache = {}
FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def current_user(authorization: str = Header(None)):
    user = store.user_by_token((authorization or "").removeprefix("Bearer ").strip())
    if not user:
        raise HTTPException(status_code=401, detail="لطفا دوباره وارد شوید")
    return user

def require(*roles):
    def check(user: dict = Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="به این بخش دسترسی ندارید")
        return user
    return check

OWNER = require("owner")
OFFICE = require("owner", "secretary")
STAFF = require("owner", "secretary", "teacher")
TEACH = require("owner", "teacher")
STUDENT = require("student")
ANY = require("owner", "secretary", "teacher", "student")

class Login(BaseModel):
    username: str = Field(max_length=60)
    password: str = Field(max_length=200)

@router.post("/login")
def login(req: Login):
    result = store.login(req.username.strip(), req.password)
    if not result:
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    token, user = result
    with store.conn() as c:
        store.log(c, user, "login", "وارد شد")
    return {"token": token, "user": store.public_user(user)}

@router.get("/me")
def me(user: dict = Depends(current_user)):
    return store.public_user(user)

@router.post("/logout")
def logout(authorization: str = Header(None)):
    store.logout((authorization or "").removeprefix("Bearer ").strip())
    return {"ok": True}

def _people():
    with store.conn() as c:
        rows = {r["role"]: r["full_name"] for r in c.execute("SELECT role, full_name FROM users WHERE role IN ('teacher', 'student')")}
    return {"teacher": rows.get("teacher", ""), "student": rows.get("student", "")}

@router.get("/info")
def info():
    if not institute.is_set_up():
        return {"set_up": False}
    return {"set_up": True, "institute": institute.public(extra=_people()), "today": facts.jfull(store.today().isoformat()),
            "levels": list(cur.LEVEL.values()),
            "terms": [{k: v for k, v in t.items() if k != "topics"} | {"fee_text": facts.money(t["fee"]), "book_price_text": facts.money(t["book_price"]),
                                                                     "unit_topics": t["topics"][t["units"][0] - 1:t["units"][1]]} for t in cur.TERMS],
            "pairs": {k: v[0] for k, v in facts.PAIRS.items()}, "slots": facts.SLOTS, "rooms": facts.ROOMS, "skills": cur.SKILLS}

@router.get("/setup/default")
def setup_default():
    return {"institute": institute.DEFAULT}

class Setup(BaseModel):
    institute: dict

@router.post("/setup")
def setup(req: Setup):
    try:
        settings = institute.clean(req.institute)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with _lock:
        institute.save(settings)
        demo.build()
        _cache.clear()
    return {"ok": True, "institute": institute.public(extra=_people())}

def reset():
    with _lock:
        institute.forget()
        store.init()
        store.logout_all()
        _cache.clear()

def ensure_fresh():
    import os
    store.init()
    if institute.is_set_up() and store.get_meta("built_for") != store.today().isoformat() and os.getenv("KEEP_DB") != "1":
        demo.build()

ensure_fresh()

def _written(prompt, data, fallback, max_tokens=350):
    try:
        text = ask_llm(prompt, data, max_tokens=max_tokens).strip()
    except Exception:
        return fallback, None
    if not text or not only_known_numbers(text, data):
        return fallback, False
    return text, True

def _one(c, table, rid, what):
    row = c.execute(f"SELECT * FROM {table} WHERE id = ?", (rid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"این {what} پیدا نشد")
    return dict(row)

def _class(c, cid, user):
    """A class; a teacher may open only their own."""
    cl = _one(c, "classes", cid, "کلاس")
    if user["role"] == "teacher" and cl["teacher_id"] != user["ref_id"]:
        raise HTTPException(status_code=403, detail="این کلاس با شما نیست")
    return cl

def _term(c, kind):
    if kind not in ("current", "next"):
        raise HTTPException(status_code=422, detail="ترم را انتخاب کنید")
    return facts.term(c, kind)

def _sign():
    s = institute.current()
    return f"{institute.person('secretary', s)}، {s['name']}"

# ---------- the office ----------

@router.get("/today")
def today_view(user: dict = Depends(OFFICE)):
    with store.conn() as c:
        return facts.overview(c, user["role"])

@router.get("/brief")
def brief(user: dict = Depends(OWNER)):
    with store.conn() as c:
        key = f"{store.today()}|{c.execute('SELECT MAX(id) FROM events').fetchone()[0]}"
        if key in _cache:
            return _cache[key]
        data, o = facts.brief_facts(c)
    fallback = (f"امروز {len(o['alerts'])} کار منتظر آموزشگاه است. " + " ".join(f"{a['title']}." for a in o["alerts"][:2])) if o["alerts"] else "امروز کار فوری‌ای نیست."
    s = institute.current()
    text, checked = _written(
        f"تو دستیار {institute.person('owner', s)}، مدیر {s['name']} هستی. از روی اطلاعات زیر یک خلاصه‌ی صبحگاهی سه جمله‌ای به فارسی معیار، "
        "ساده و محترمانه بنویس. اول مشکل‌های جدول کلاس‌های ترم بعد را بگو، بعد ثبت‌نام ترم بعد و شهریه‌ی مانده را. "
        "عددها و مبلغ‌ها را دقیقاً همان‌طور که نوشته شده بنویس. عدد جدید نساز. سلام ننویس.", data, fallback)
    out = {"text": text, "checked": checked}
    if checked is not None:
        _cache[key] = out
    return out

@router.get("/events")
def events(after: int = 0, user: dict = Depends(OWNER)):
    with store.conn() as c:
        return facts.events(c, after)

@router.get("/timetable")
def timetable(term: str = "current", user: dict = Depends(OFFICE)):
    with store.conn() as c:
        t = _term(c, term)
        return {"term": facts.term_view(t), "classes": facts.classes(c, t["id"]), "problems": facts.problems(c, t)}

@router.get("/classes/{cid}")
def class_file(cid: int, user: dict = Depends(STAFF)):
    with store.conn() as c:
        cl = _class(c, cid, user)
        t = facts.term_by_id(c, cl["term_id"])
        v = facts.class_view(c, cl, t=t)
        days = facts.session_days(t, cl["pair"])
        written = {r[0] for r in c.execute("SELECT DISTINCT day FROM attendance WHERE class_id = ?", (cid,))}
        roster = []
        for e in facts.roster(c, cid):
            att = facts.attendance_of(c, e["student_id"], cid)
            qa = facts.quiz_avg(c, e["student_id"], cid)
            roster.append({"student_id": e["student_id"], "name": e["name"], "phone": e["phone"] if user["role"] != "teacher" else "", "status": e["status"],
                           "midterm": e["midterm"], "final": e["final"], "quiz": qa, "so_far": facts.so_far(e["midterm"], qa),
                           "absent": att["counts"]["absent"], "rate": att["rate"], "enrollment_id": e["id"],
                           "left": e["fee"] - facts.paid_of(c, e["id"]) if user["role"] != "teacher" else None})
        sessions = [{"n": i + 1, "day": d, "day_text": facts.jlong(d), "written": d in written, "past": d <= store.today().isoformat(),
                     "unit": (cur.TERM[cl["course"]]["units"][0] + u) if (u := cur.unit_of_session(i + 1)) is not None else None,
                     "exam": "میان‌ترم" if i + 1 == cur.MIDTERM else "پایان ترم" if i + 1 == cur.FINAL else None} for i, d in enumerate(days)]
        exams = [facts.exam_view(c, e) for e in c.execute("SELECT * FROM exams WHERE class_id = ? ORDER BY opens DESC", (cid,))]
        out = {"class": v, "term": facts.term_view(t), "roster": roster, "sessions": sessions, "exams": exams}
        if user["role"] == "owner":
            out["teachers"] = facts.teacher_options(c, cid)
        return out

@router.get("/classes/{cid}/moves")
def moves(cid: int, user: dict = Depends(OWNER)):
    with store.conn() as c:
        _class(c, cid, user)
        return facts.move_grid(c, cid)

class MoveIn(BaseModel):
    pair: str
    time: str
    room: int

def _move_text(c, cl, old):
    """The message to a class's learners when its hour or room changes, written by code."""
    s = institute.current()
    t = facts.term_by_id(c, cl["term_id"])
    when = lambda x: f"{facts.PAIRS[x['pair']][0]} ساعت {x['time']} در {facts.room_name(x['room'])}"
    return (f"زبان‌آموزان گرامی کلاس {cur.TERM[cl['course']]['name']}، سلام. کلاس شما در {t['name']} از {when(old)} به {when(cl)} منتقل شد"
            + (f" و از {facts.jlong(t['start'])} شروع می‌شود." if t["kind"] == "next" else ".") + f" اگر این ساعت برایتان ممکن نیست، با دفتر تماس بگیرید.\n{_sign()}")

@router.post("/classes/{cid}/move")
def move(cid: int, req: MoveIn, user: dict = Depends(OWNER)):
    if req.pair not in facts.PAIRS or req.time not in facts.SLOTS or req.room not in facts.ROOMS:
        raise HTTPException(status_code=422, detail="روز، ساعت یا اتاق درست نیست")
    with store.conn() as c:
        cl = _class(c, cid, user)
        why = facts.cell_reasons(c, cl, req.pair, req.time, req.room)
        if why:
            raise HTTPException(status_code=409, detail=why[0])
        c.execute("UPDATE classes SET pair = ?, time = ?, room = ? WHERE id = ?", (req.pair, req.time, req.room, cid))
        new = cl | {"pair": req.pair, "time": req.time, "room": req.room}
        store.log(c, user, "class", f"کلاس {cur.TERM[cl['course']]['name']} به {facts.PAIRS[req.pair][0]} ساعت {req.time}، {facts.room_name(req.room)} رفت", class_id=cid)
        n = len(facts.roster(c, cid))
        return {"class": facts.class_view(c, new), "message": _move_text(c, new, cl) if n else None, "learners": n}

class TeacherIn(BaseModel):
    teacher_id: int

@router.post("/classes/{cid}/teacher")
def set_teacher(cid: int, req: TeacherIn, user: dict = Depends(OWNER)):
    with store.conn() as c:
        cl = _class(c, cid, user)
        opt = next((o for o in facts.teacher_options(c, cid) if o["id"] == req.teacher_id), None)
        if not opt:
            raise HTTPException(status_code=404, detail="این استاد پیدا نشد")
        if not opt["ok"]:
            raise HTTPException(status_code=409, detail=f"{opt['name']}: {opt['why'][0]}")
        c.execute("UPDATE classes SET teacher_id = ? WHERE id = ?", (req.teacher_id, cid))
        store.log(c, user, "class", f"استاد کلاس {cur.TERM[cl['course']]['name']} ({facts.PAIRS[cl['pair']][0]} {cl['time']}): {opt['name']}", class_id=cid)
    return {"ok": True}

class ClassIn(BaseModel):
    term: str
    course: str
    teacher_id: int
    pair: str
    time: str
    room: int

@router.get("/cells")
def cells(term: str, teacher_id: int, user: dict = Depends(OWNER)):
    """Where a new class of this teacher could go in a term: the hours they come and are free, with the free rooms."""
    with store.conn() as c:
        t = _term(c, term)
        _one(c, "teachers", teacher_id, "استاد")
        lk = facts.lookups(c)
        out = []
        for pair in facts.PAIRS:
            for time in facts.SLOTS:
                rooms = [r for r in facts.ROOMS if not facts.cell_reasons(c, {"id": 0, "term_id": t["id"], "teacher_id": teacher_id}, pair, time, r, lk)]
                if rooms:
                    out.append({"pair": pair, "pair_text": facts.PAIRS[pair][0], "time": time, "rooms": [{"room": r, "seats": facts.ROOMS[r]} for r in rooms]})
        return out

@router.post("/classes")
def add_class(req: ClassIn, user: dict = Depends(OWNER)):
    if req.course not in cur.TERM or req.pair not in facts.PAIRS or req.time not in facts.SLOTS or req.room not in facts.ROOMS:
        raise HTTPException(status_code=422, detail="کتاب، روز، ساعت و اتاق را انتخاب کنید")
    with store.conn() as c:
        t = _term(c, req.term)
        teacher = _one(c, "teachers", req.teacher_id, "استاد")
        level = cur.TERM[req.course]["level"]
        if level not in teacher["levels"].split(","):
            raise HTTPException(status_code=409, detail=f"{teacher['name']} سطح {cur.LEVEL[level]['fa']} را درس نمی‌دهد")
        why = facts.cell_reasons(c, {"id": 0, "term_id": t["id"], "teacher_id": req.teacher_id}, req.pair, req.time, req.room)
        if why:
            raise HTTPException(status_code=409, detail=why[0])
        cid = c.execute("INSERT INTO classes (term_id, course, teacher_id, room, pair, time) VALUES (?,?,?,?,?,?)",
                        (t["id"], req.course, req.teacher_id, req.room, req.pair, req.time)).lastrowid
        store.log(c, user, "class", f"کلاس جدید {cur.TERM[req.course]['name']} برای {t['name']}: {facts.PAIRS[req.pair][0]} ساعت {req.time}، {teacher['name']}", class_id=cid)
        return facts.class_view(c, _one(c, "classes", cid, "کلاس"))

@router.post("/classes/{cid}/remove")
def remove_class(cid: int, user: dict = Depends(OWNER)):
    with store.conn() as c:
        cl = _class(c, cid, user)
        if c.execute("SELECT 1 FROM enrollments WHERE class_id = ? AND status != 'dropped'", (cid,)).fetchone():
            raise HTTPException(status_code=409, detail="این کلاس زبان‌آموز دارد؛ اول آن‌ها را به کلاس دیگری ببرید")
        c.execute("DELETE FROM classes WHERE id = ?", (cid,))
        store.log(c, user, "class", f"کلاس {cur.TERM[cl['course']]['name']} ({facts.PAIRS[cl['pair']][0]} {cl['time']}) حذف شد")
    return {"ok": True}

# ---------- teachers ----------

@router.get("/teachers")
def teachers(user: dict = Depends(OFFICE)):
    with store.conn() as c:
        cu, nt = facts.term(c, "current"), facts.term(c, "next")
        lk = facts.lookups(c)
        out = []
        for t in c.execute("SELECT * FROM teachers ORDER BY name"):
            mine = {k: [facts.class_view(c, r, lk, tt) for r in c.execute("SELECT * FROM classes WHERE term_id = ? AND teacher_id = ? ORDER BY pair, time", (tt["id"], t["id"]))]
                    for k, tt in (("current", cu), ("next", nt))}
            out.append({"id": t["id"], "name": t["name"], "phone": t["phone"], "levels": t["levels"].split(","), "avail": facts.avail(t),
                        "classes": mine, "hours": {k: len(v) * 3 for k, v in mine.items()}, "learners": sum(v["seats"] for v in mine["current"]),
                        "joined_text": facts.jfull(t["joined"])})
        return out

class TeacherNew(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    phone: str = Field(min_length=10, max_length=20)
    levels: list[str] = Field(min_length=1)

def _phone(raw):
    phone = re.sub(r"\D", "", raw.translate(FA_DIGITS))
    if not re.fullmatch(r"09\d{9}", phone):
        raise HTTPException(status_code=422, detail="شماره‌ی همراه باید ۱۱ رقم و با ۰۹ شروع شود")
    return phone

@router.post("/teachers")
def add_teacher(req: TeacherNew, user: dict = Depends(OWNER)):
    if not set(req.levels) <= set(cur.LEVEL):
        raise HTTPException(status_code=422, detail="سطح‌ها را انتخاب کنید")
    phone = _phone(req.phone)
    av = {p: facts.SLOTS[2:] for p in facts.PAIRS}
    with store.conn() as c:
        tid = c.execute("INSERT INTO teachers (name, phone, levels, avail, joined) VALUES (?,?,?,?,?)",
                        (" ".join(req.name.split()), phone, ",".join(k for k in cur.LEVEL if k in req.levels), json.dumps(av), store.today().isoformat())).lastrowid
        store.log(c, user, "teacher", f"استاد جدید: {' '.join(req.name.split())}")
    return {"id": tid}

class TeacherEdit(BaseModel):
    levels: list[str] | None = None
    avail: dict[str, list[str]] | None = None

@router.post("/teachers/{tid}")
def edit_teacher(tid: int, req: TeacherEdit, user: dict = Depends(OWNER)):
    with store.conn() as c:
        t = _one(c, "teachers", tid, "استاد")
        if req.levels is not None:
            if not req.levels or not set(req.levels) <= set(cur.LEVEL):
                raise HTTPException(status_code=422, detail="دست‌کم یک سطح را انتخاب کنید")
            c.execute("UPDATE teachers SET levels = ? WHERE id = ?", (",".join(k for k in cur.LEVEL if k in req.levels), tid))
        if req.avail is not None:
            if not set(req.avail) <= set(facts.PAIRS) or any(not set(v) <= set(facts.SLOTS) for v in req.avail.values()):
                raise HTTPException(status_code=422, detail="ساعت‌ها درست نیست")
            c.execute("UPDATE teachers SET avail = ? WHERE id = ?", (json.dumps({p: [s for s in facts.SLOTS if s in req.avail.get(p, [])] for p in facts.PAIRS}), tid))
        store.log(c, user, "teacher", f"سطح‌ها و ساعت‌های {t['name']} تغییر کرد")
    return {"ok": True}

# ---------- learners ----------

@router.get("/students")
def students(q: str = "", user: dict = Depends(OFFICE)):
    q = q.strip().translate(FA_DIGITS)
    with store.conn() as c:
        cu, nt = facts.term(c, "current"), facts.term(c, "next")
        rows = c.execute("SELECT * FROM students WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT 80", (f"%{q}%", f"%{q}%")).fetchall()
        out = []
        for s in rows:
            now = c.execute("""SELECT e.status, cl.course, cl.term_id FROM enrollments e JOIN classes cl ON cl.id = e.class_id WHERE e.student_id = ?
                               AND e.status IN ('active', 'registered')""", (s["id"],)).fetchall()
            act = next((r for r in now if r["term_id"] == cu["id"]), None)
            nxt = next((r for r in now if r["term_id"] == nt["id"]), None)
            out.append({"id": s["id"], "name": s["name"], "phone": s["phone"],
                        "now": cur.TERM[act["course"]]["name"] if act else None, "level": cur.TERM[(act or nxt)["course"]]["level"] if (act or nxt) else None,
                        "next": cur.TERM[nxt["course"]]["name"] if nxt else None})
        return out

@router.get("/students/{sid}")
def student_file(sid: int, user: dict = Depends(OFFICE)):
    with store.conn() as c:
        _one(c, "students", sid, "زبان‌آموز")
        road = facts.road(c, sid)
        pays = [dict(r) | {"date_text": facts.jfull(r["at"]), "amount_text": facts.money(r["amount"]), "method_text": facts.METHODS.get(r["method"], r["method"])}
                for r in c.execute("SELECT * FROM payments WHERE student_id = ? ORDER BY at DESC", (sid,))]
        enr = []
        for e in c.execute("""SELECT e.*, cl.course, t.name term_name, t.kind FROM enrollments e JOIN classes cl ON cl.id = e.class_id JOIN terms t ON t.id = cl.term_id
                              WHERE e.student_id = ? AND e.status IN ('active', 'registered') ORDER BY t.start""", (sid,)):
            paid = facts.paid_of(c, e["id"])
            enr.append({"id": e["id"], "course": cur.TERM[e["course"]]["name"], "term": e["term_name"], "status": e["status"], "fee": e["fee"],
                        "fee_text": facts.money(e["fee"]), "paid": paid, "left": e["fee"] - paid, "left_text": facts.money(e["fee"] - paid),
                        "how": [f"شهریه‌ی {cur.TERM[e['course']]['name']}: {facts.money(e['fee'])}", f"پرداخت‌شده: {facts.money(paid)}", f"= مانده: {facts.money(e['fee'] - paid)}"]})
        tests = [dict(r) | {"date_text": facts.jfull(r["submitted"]), "placed_name": cur.TERM[r["placed"]]["name"] if r["placed"] else None}
                 for r in c.execute("""SELECT a.id, a.score, a.submitted, a.placed, e.title, e.kind FROM attempts a JOIN exams e ON e.id = a.exam_id
                                       WHERE a.student_id = ? AND a.submitted IS NOT NULL ORDER BY a.submitted DESC""", (sid,))]
        contacts = [dict(r) | {"date_text": facts.jfull(r["at"])} for r in c.execute("SELECT * FROM contacts WHERE student_id = ? ORDER BY at DESC", (sid,))]
        return {"road": road, "enrollments": enr, "payments": pays, "tests": tests, "contacts": contacts, "history": facts.events(c, 0, 40, sid)}

class StudentIn(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    phone: str = Field(min_length=10, max_length=20)

@router.post("/students")
def add_student(req: StudentIn, user: dict = Depends(OFFICE)):
    phone = _phone(req.phone)
    with store.conn() as c:
        same = c.execute("SELECT * FROM students WHERE phone = ?", (phone,)).fetchone()
        if same:
            raise HTTPException(status_code=409, detail=f"این شماره برای «{same['name']}» ثبت شده است")
        sid = c.execute("INSERT INTO students (name, phone, created, start_key) VALUES (?,?,?, NULL)",
                        (" ".join(req.name.split()), phone, store.today().isoformat())).lastrowid
        store.log(c, user, "student", f"زبان‌آموز جدید: {' '.join(req.name.split())}", sid)
    return {"id": sid}

def _enrol(c, user, sid, class_id):
    """A learner into a class: active in the running term, registered for the next. One class a term."""
    s = _one(c, "students", sid, "زبان‌آموز")
    cl = _one(c, "classes", class_id, "کلاس")
    t = facts.term_by_id(c, cl["term_id"])
    if t["kind"] not in ("current", "next"):
        raise HTTPException(status_code=422, detail="این کلاس تمام شده است")
    if c.execute("""SELECT 1 FROM enrollments e JOIN classes x ON x.id = e.class_id WHERE e.student_id = ? AND x.term_id = ? AND e.status IN ('active', 'registered')""",
                 (sid, t["id"])).fetchone():
        raise HTTPException(status_code=409, detail=f"{s['name']} در {t['name']} کلاس دارد")
    v = facts.class_view(c, cl, t=t)
    if v["free"] <= 0:
        raise HTTPException(status_code=409, detail="این کلاس جای خالی ندارد")
    fee = cur.TERM[cl["course"]]["fee"]
    eid = c.execute("INSERT INTO enrollments (student_id, class_id, status, registered, fee) VALUES (?,?,?,?,?)",
                    (sid, class_id, "active" if t["kind"] == "current" else "registered", store.today().isoformat(), fee)).lastrowid
    if not s["start_key"]:
        c.execute("UPDATE students SET start_key = ? WHERE id = ?", (cl["course"], sid))
    store.log(c, user, "enroll", f"ثبت‌نام {s['name']} در {v['course_name']}، {t['name']} ({v['pair_text']} ساعت {v['time']})", sid, class_id)
    return {"enrollment_id": eid, "fee": fee, "fee_text": facts.money(fee), "class": v}

class EnrolIn(BaseModel):
    student_id: int
    class_id: int

@router.post("/enroll")
def enrol(req: EnrolIn, user: dict = Depends(OFFICE)):
    with store.conn() as c:
        return _enrol(c, user, req.student_id, req.class_id)

@router.get("/courses/{key}/classes")
def course_classes(key: str, user: dict = Depends(OFFICE)):
    """The classes of a station a new learner could join: this term's (only in its first weeks) and the next term's."""
    if key not in cur.TERM:
        raise HTTPException(status_code=404, detail="این ترم پیدا نشد")
    with store.conn() as c:
        cu, nt = facts.term(c, "current"), facts.term(c, "next")
        lk = facts.lookups(c)
        out = []
        for t in (cu, nt):
            if t["kind"] == "current" and facts.days_ago(t["start"]) > 14:
                continue
            out += [facts.class_view(c, r, lk, t) | {"term_name": t["name"]} for r in c.execute("SELECT * FROM classes WHERE term_id = ? AND course = ? ORDER BY pair, time", (t["id"], key))]
        return {"course": cur.TERM[key]["name"], "classes": out, "term": facts.term_view(nt)}

class PaymentIn(BaseModel):
    enrollment_id: int
    amount: int = Field(gt=0, le=500_000_000)
    method: str

@router.post("/students/{sid}/payments")
def pay(sid: int, req: PaymentIn, user: dict = Depends(OFFICE)):
    if req.method not in facts.METHODS:
        raise HTTPException(status_code=422, detail="روش پرداخت را انتخاب کنید")
    with store.conn() as c:
        e = c.execute("SELECT * FROM enrollments WHERE id = ? AND student_id = ?", (req.enrollment_id, sid)).fetchone()
        if not e:
            raise HTTPException(status_code=404, detail="این ثبت‌نام پیدا نشد")
        left = e["fee"] - facts.paid_of(c, e["id"])
        if req.amount > left:
            raise HTTPException(status_code=422, detail=f"مبلغ از مانده‌ی شهریه ({facts.money(left)}) بیشتر است")
        c.execute("INSERT INTO payments (student_id, enrollment_id, at, amount, method, user_id) VALUES (?,?,?,?,?,?)",
                  (sid, e["id"], store.stamp(), req.amount, req.method, user["id"]))
        store.log(c, user, "pay", f"پرداخت شهریه: {facts.money(req.amount)} ({facts.METHODS[req.method]})", sid)
        return {"left": left - req.amount, "left_text": facts.money(left - req.amount)}

@router.get("/renewals")
def renewals(user: dict = Depends(OFFICE)):
    with store.conn() as c:
        t = facts.term_view(facts.term(c, "current"))
        return {"term": t, "next_term": facts.term_view(facts.term(c, "next")), "rows": facts.renewals(c)}

MESSAGE_KINDS = ("absent", "unpaid", "renew", "placed")

@router.get("/students/{sid}/message")
def message(sid: int, kind: str, user: dict = Depends(OFFICE)):
    """A message to a learner, written by code from their own records; the secretary reads it and sends it."""
    if kind not in MESSAGE_KINDS:
        raise HTTPException(status_code=422, detail="نوع پیام درست نیست")
    with store.conn() as c:
        s = _one(c, "students", sid, "زبان‌آموز")
        hello = f"{s['name']} گرامی، سلام."
        if kind == "absent":
            st = next((x for x in facts.streaks(c) if x["student_id"] == sid), None)
            days = "، ".join(facts.jday(d) for d in st["days"]) if st else "این چند جلسه"
            course = st["course_name"] if st else ""
            text = f"{hello} در جلسه‌های {days} کلاس {course} شما را ندیدیم. اگر مشکلی پیش آمده، با دفتر آموزشگاه تماس بگیرید تا با هم راهی پیدا کنیم؛ درس این جلسه‌ها را هم می‌توانید از استاد بگیرید."
        elif kind == "unpaid":
            # the same balances the learner's file shows: this term's and the next term's, this term's first
            owed = []
            for e in c.execute("""SELECT e.*, cl.course, t.kind, t.start FROM enrollments e JOIN classes cl ON cl.id = e.class_id JOIN terms t ON t.id = cl.term_id
                                  WHERE e.student_id = ? AND e.status IN ('active', 'registered') ORDER BY t.start""", (sid,)):
                left = e["fee"] - facts.paid_of(c, e["id"])
                if left > 0:
                    owed.append((e, left))
            if not owed:
                raise HTTPException(status_code=409, detail="شهریه‌ی این زبان‌آموز مانده‌ای ندارد")
            e, left = owed[0]
            course = cur.TERM[e["course"]]["name"]
            if e["kind"] == "current":
                text = (f"{hello} از شهریه‌ی کلاس {course} ({facts.money(e['fee'])}) {facts.money(left)} مانده است. لطفاً در دفتر آموزشگاه بپردازید، "
                        "یا کارت به کارت کنید و رسید را برای ما بفرستید.")
            else:
                text = (f"{hello} جای شما در کلاس {course} ترم بعد نگه داشته شده است. ترم از {facts.jlong(e['start'])} شروع می‌شود و از شهریه‌ی آن "
                        f"({facts.money(e['fee'])}) {facts.money(left)} مانده است. لطفاً پیش از شروع ترم در دفتر آموزشگاه بپردازید، یا کارت به کارت کنید و رسید را برای ما بفرستید.")
        elif kind == "renew":
            r = next((x for x in facts.renewals(c) if x["student_id"] == sid), None)
            t, nt = facts.term_view(facts.term(c, "current")), facts.term_view(facts.term(c, "next"))
            if not r:
                raise HTTPException(status_code=409, detail="این زبان‌آموز برای ترم بعد ثبت‌نام کرده است")
            cl = r["class"]
            text = (f"{hello} {t['name']} {t['days_left']} روز دیگر تمام می‌شود. ترم بعد شما {r['next']} است"
                    + (f"، {cl['pair_text']} ساعت {cl['time']} با {cl['teacher']}" if cl else "") + f"؛ از {facts.jlong(nt['start'])} شروع می‌شود. "
                    "برای ثبت‌نام با دفتر تماس بگیرید یا در پنل زبان‌آموز جای خود را نگه دارید.")
        else:
            a = c.execute("""SELECT a.placed FROM attempts a JOIN exams e ON e.id = a.exam_id WHERE a.student_id = ? AND e.kind = 'placement' AND a.submitted IS NOT NULL
                             ORDER BY a.id DESC LIMIT 1""", (sid,)).fetchone()
            if not a:
                raise HTTPException(status_code=409, detail="این زبان‌آموز آزمون تعیین سطح نداده است")
            nt = facts.term(c, "next")
            opts = [facts.class_view(c, r, t=nt) for r in c.execute("SELECT * FROM classes WHERE term_id = ? AND course = ?", (nt["id"], a["placed"]))]
            opts = [o for o in opts if o["free"] > 0]
            text = (f"{hello} نتیجه‌ی آزمون تعیین سطح شما: {cur.TERM[a['placed']]['name']}. کلاس‌های این سطح از {facts.jlong(nt['start'])} شروع می‌شوند"
                    + (": " + "؛ ".join(f"{o['pair_text']} ساعت {o['time']}" for o in opts) if opts else "") + ". برای ثبت‌نام با دفتر تماس بگیرید.")
        return {"text": f"{text}\n{_sign()}", "phone": s["phone"], "name": s["name"]}

class ContactIn(BaseModel):
    kind: str
    text: str = Field("", max_length=300)

@router.post("/students/{sid}/contact")
def contact(sid: int, req: ContactIn, user: dict = Depends(OFFICE)):
    words = {"sent": "پیام فرستاده شد", "call": "تماس گرفته شد"}
    if req.kind not in words:
        raise HTTPException(status_code=422, detail="نتیجه را انتخاب کنید")
    with store.conn() as c:
        s = _one(c, "students", sid, "زبان‌آموز")
        c.execute("INSERT INTO contacts (student_id, at, user_id, kind, text) VALUES (?,?,?,?,?)", (sid, store.stamp(), user["id"], req.kind, req.text.strip() or words[req.kind]))
        store.log(c, user, "contact", f"{s['name']}: {words[req.kind]}" + (f" («{req.text.strip()}»)" if req.text.strip() else ""), sid)
    return {"ok": True}

# ---------- the teacher ----------

@router.get("/teacher/home")
def teacher_home(user: dict = Depends(require("teacher"))):
    with store.conn() as c:
        t = facts.today().isoformat()
        return facts.teacher_home(c, user["ref_id"]) | {"today_long": facts.jlong(t), "today_date": facts.jfull(t), "term": facts.term_view(facts.term(c, "current"))}

@router.get("/teacher/exams")
def teacher_exams(user: dict = Depends(require("teacher"))):
    """The online tests of the teacher's classes this term, newest first, each with its class."""
    with store.conn() as c:
        cu = facts.term(c, "current")
        lk = facts.lookups(c)
        mine = {r["id"]: facts.class_view(c, r, lk, cu) for r in c.execute("SELECT * FROM classes WHERE term_id = ? AND teacher_id = ?", (cu["id"], user["ref_id"]))}
        rows = c.execute(f"SELECT * FROM exams WHERE class_id IN ({','.join('?' * len(mine)) or 'NULL'}) ORDER BY opens DESC, id DESC", list(mine)).fetchall()
        return {"classes": list(mine.values()), "exams": [facts.exam_view(c, e) | {"class": mine[e["class_id"]]} for e in rows]}

@router.get("/classes/{cid}/attendance")
def attendance(cid: int, day: str | None = None, user: dict = Depends(TEACH)):
    with store.conn() as c:
        cl = _class(c, cid, user)
        t = facts.term_by_id(c, cl["term_id"])
        days = [d for d in facts.session_days(t, cl["pair"]) if d <= store.today().isoformat()]
        if not days:
            raise HTTPException(status_code=409, detail="این کلاس هنوز جلسه‌ای نداشته است")
        day = day if day in days else days[-1]
        marks = {r["student_id"]: r["status"] for r in c.execute("SELECT * FROM attendance WHERE class_id = ? AND day = ?", (cid, day))}
        return {"day": day, "day_text": facts.jlong(day), "n": facts.session_days(t, cl["pair"]).index(day) + 1, "written": bool(marks),
                "days": [{"day": d, "text": facts.jlong(d)} for d in days[-6:]],
                "rows": [{"student_id": e["student_id"], "name": e["name"], "status": marks.get(e["student_id"])} for e in facts.roster(c, cid) if e["status"] == "active"]}

class AttendanceIn(BaseModel):
    day: str = Field(max_length=10)
    marks: dict[int, str]

@router.post("/classes/{cid}/attendance")
def write_attendance(cid: int, req: AttendanceIn, user: dict = Depends(TEACH)):
    with store.conn() as c:
        cl = _class(c, cid, user)
        t = facts.term_by_id(c, cl["term_id"])
        if req.day not in facts.session_days(t, cl["pair"]) or req.day > store.today().isoformat():
            raise HTTPException(status_code=422, detail="این روز جلسه‌ی این کلاس نیست")
        members = {e["student_id"] for e in facts.roster(c, cid) if e["status"] == "active"}
        if set(req.marks) != members or not set(req.marks.values()) <= set(facts.ATT):
            raise HTTPException(status_code=422, detail="برای همه‌ی زبان‌آموزان حاضر، غایب یا با تأخیر را بزنید")
        c.executemany("INSERT OR REPLACE INTO attendance (class_id, student_id, day, status) VALUES (?,?,?,?)",
                      [(cid, sid, req.day, st) for sid, st in req.marks.items()])
        absent = sum(1 for v in req.marks.values() if v == "absent")
        store.log(c, user, "attendance", f"حضور و غیاب {cur.TERM[cl['course']]['name']}، {facts.jlong(req.day)}: {absent} غایب", class_id=cid)
    return {"ok": True, "absent": absent}

class ScoreIn(BaseModel):
    student_id: int
    midterm: int | None = Field(None, ge=0, le=100)
    final: int | None = Field(None, ge=0, le=100)

@router.post("/classes/{cid}/scores")
def scores(cid: int, req: ScoreIn, user: dict = Depends(TEACH)):
    with store.conn() as c:
        cl = _class(c, cid, user)
        e = c.execute("SELECT * FROM enrollments WHERE class_id = ? AND student_id = ? AND status = 'active'", (cid, req.student_id)).fetchone()
        if not e:
            raise HTTPException(status_code=404, detail="این زبان‌آموز در این کلاس نیست")
        c.execute("UPDATE enrollments SET midterm = ?, final = ? WHERE id = ?", (req.midterm, req.final, e["id"]))
        name = c.execute("SELECT name FROM students WHERE id = ?", (req.student_id,)).fetchone()[0]
        store.log(c, user, "score", f"نمره‌ی {name} در {cur.TERM[cl['course']]['name']} ثبت شد", req.student_id, cid)
        qa = facts.quiz_avg(c, req.student_id, cid)
    return {"so_far": facts.so_far(req.midterm, qa)}

class ExamIn(BaseModel):
    class_id: int
    title: str = Field(min_length=3, max_length=60)
    count: int = Field(8, ge=4, le=10)
    days: int = Field(3, ge=1, le=7)
    minutes: int = Field(15, ge=5, le=40)

@router.post("/exams")
def add_exam(req: ExamIn, user: dict = Depends(TEACH)):
    with store.conn() as c:
        cl = _class(c, req.class_id, user)
        if facts.term_by_id(c, cl["term_id"])["kind"] != "current":
            raise HTTPException(status_code=422, detail="آزمون آنلاین فقط برای کلاس‌های این ترم است")
        qids = cur.for_quiz(cur.TERM[cl["course"]]["level"], req.count, random.Random())
        t0 = store.today()
        eid = c.execute("INSERT INTO exams (class_id, kind, title, questions, opens, closes, minutes, created_by, created) VALUES (?, 'quiz', ?, ?, ?, ?, ?, ?, ?)",
                        (cl["id"], " ".join(req.title.split()), json.dumps(qids), t0.isoformat(), (t0 + timedelta(days=req.days)).isoformat(), req.minutes,
                         user["full_name"], store.stamp())).lastrowid
        store.log(c, user, "exam", f"آزمون آنلاین «{' '.join(req.title.split())}» برای {cur.TERM[cl['course']]['name']} باز شد", class_id=cl["id"])
        return facts.exam_view(c, _one(c, "exams", eid, "آزمون"))

@router.get("/exams/{eid}/results")
def results(eid: int, user: dict = Depends(TEACH)):
    with store.conn() as c:
        e = _one(c, "exams", eid, "آزمون")
        if not e["class_id"]:
            raise HTTPException(status_code=404, detail="این آزمون پیدا نشد")
        _class(c, e["class_id"], user)
        qids = json.loads(e["questions"])
        rows = c.execute("""SELECT a.*, s.name FROM attempts a JOIN students s ON s.id = a.student_id WHERE a.exam_id = ? AND a.submitted IS NOT NULL
                            ORDER BY a.score DESC""", (eid,)).fetchall()
        per_q = []
        for q in qids:
            qq = cur.QUESTIONS[q]
            right = sum(1 for a in rows if json.loads(a["answers"]).get(q) == qq["answer"])
            per_q.append({"id": q, "text": qq["text"], "skill": cur.SKILLS[qq["skill"]], "level": qq["level"], "right": right, "of": len(rows),
                          "pct": round(100 * right / len(rows)) if rows else 0, "answer": qq["options"][qq["answer"]]})
        skills = {}
        for a in rows:
            for k, (r, n) in json.loads(a["by_skill"]).items():
                s = skills.setdefault(k, [0, 0]); s[0] += r; s[1] += n
        members = {r["student_id"]: r["name"] for r in facts.roster(c, e["class_id"]) if r["status"] == "active"}
        took = {a["student_id"] for a in rows}
        return {"exam": facts.exam_view(c, e), "rows": [{"name": a["name"], "score": a["score"], "at": facts.jday(a["submitted"]) + " " + a["submitted"][11:16]} for a in rows],
                "missing": [n for sid, n in members.items() if sid not in took], "questions": per_q,
                "skills": [{"key": k, "name": cur.SKILLS[k], "pct": round(100 * r / n)} for k, (r, n) in skills.items()]}

# ---------- taking a test ----------

def _seconds_left(a, minutes):
    started = datetime.strptime(a["started"], "%Y-%m-%d %H:%M:%S") if len(a["started"]) > 16 else datetime.strptime(a["started"], "%Y-%m-%d %H:%M")
    now = datetime.strptime(f"{store.today().isoformat()} {datetime.now():%H:%M:%S}", "%Y-%m-%d %H:%M:%S")
    return int((started + timedelta(minutes=minutes) - now).total_seconds())

def _attempt(c, aid, user):
    """An attempt and its test; a learner opens only their own, the office only placement tests."""
    a = _one(c, "attempts", aid, "آزمون")
    e = _one(c, "exams", a["exam_id"], "آزمون")
    if user["role"] == "student" and a["student_id"] != user["ref_id"]:
        raise HTTPException(status_code=403, detail="این آزمون مال شما نیست")
    if user["role"] in ("owner", "secretary") and e["kind"] != "placement":
        raise HTTPException(status_code=403, detail="به این بخش دسترسی ندارید")
    if user["role"] == "teacher":
        raise HTTPException(status_code=403, detail="به این بخش دسترسی ندارید")
    return a, e

def _paper(a, e):
    """The test as the learner sees it: questions without their answers, the answers given so far, the time left."""
    qids = json.loads(e["questions"])
    qs = [{k: cur.QUESTIONS[q][k] for k in ("id", "text", "passage", "options", "skill", "level")} | {"skill_name": cur.SKILLS[cur.QUESTIONS[q]["skill"]]} for q in qids]
    return {"attempt_id": a["id"], "title": e["title"], "kind": e["kind"], "minutes": e["minutes"], "questions": qs,
            "answers": json.loads(a["answers"] or "{}"), "seconds_left": max(0, _seconds_left(a, e["minutes"]))}

def _result(c, a, e):
    qids = json.loads(e["questions"])
    answers = json.loads(a["answers"] or "{}")
    score, skills, wrong = facts.grade(qids, answers)
    out = {"score": score, "right": len(qids) - len(wrong), "of": len(qids), "kind": e["kind"], "title": e["title"],
           "skills": [{"key": k, "name": cur.SKILLS[k], "right": r, "of": n, "pct": round(100 * r / n)} for k, (r, n) in skills.items()],
           "review": [{"id": q, "text": cur.QUESTIONS[q]["text"], "passage": cur.QUESTIONS[q]["passage"], "yours": cur.QUESTIONS[q]["options"][answers[q]] if q in answers else None,
                       "answer": cur.QUESTIONS[q]["options"][cur.QUESTIONS[q]["answer"]], "skill_name": cur.SKILLS[cur.QUESTIONS[q]["skill"]]} for q in wrong]}
    if e["kind"] == "placement":
        placed = a["placed"] or facts.place(answers)
        nt = facts.term(c, "next")
        lk = facts.lookups(c)
        levels = []
        for key, *_ in cur.LEVELS:
            qs = [q for q in cur.PLACEMENT if q.startswith(key + "-")]
            levels.append({"key": key, "name": cur.LEVEL[key]["fa"], "cefr": cur.LEVEL[key]["cefr"], "right": sum(answers.get(q) == cur.QUESTIONS[q]["answer"] for q in qs), "of": len(qs)})
        out |= {"placed": placed, "placed_name": cur.TERM[placed]["name"], "placed_fa": cur.TERM[placed]["fa"], "book": cur.TERM[placed]["book"], "levels": levels,
                "student_id": a["student_id"],
                "classes": [facts.class_view(c, r, lk, nt) | {"term_name": nt["name"]} for r in c.execute("SELECT * FROM classes WHERE term_id = ? AND course = ? ORDER BY pair, time", (nt["id"], placed))]}
    return out

def _submit(c, a, e, user):
    if a["submitted"]:
        return
    qids = json.loads(e["questions"])
    answers = json.loads(a["answers"] or "{}")
    score, skills, _ = facts.grade(qids, answers)
    placed = facts.place(answers) if e["kind"] == "placement" else None
    c.execute("UPDATE attempts SET submitted = ?, score = ?, by_skill = ?, placed = ? WHERE id = ?", (store.stamp(), score, json.dumps(skills), placed, a["id"]))
    name = c.execute("SELECT name FROM students WHERE id = ?", (a["student_id"],)).fetchone()[0]
    store.log(c, user, "test", f"{e['title']}: {name}، نمره‌ی {score}" + (f"، سطح {cur.TERM[placed]['name']}" if placed else ""), a["student_id"], e["class_id"])

class PlacementIn(BaseModel):
    student_id: int

@router.post("/placement/start")
def placement_start(req: PlacementIn, user: dict = Depends(OFFICE)):
    with store.conn() as c:
        s = _one(c, "students", req.student_id, "زبان‌آموز")
        e = c.execute("SELECT * FROM exams WHERE kind = 'placement'").fetchone()
        aid = c.execute("INSERT INTO attempts (exam_id, student_id, started, answers) VALUES (?,?,?, '{}')",
                        (e["id"], s["id"], f"{store.today().isoformat()} {datetime.now():%H:%M:%S}")).lastrowid
        return _paper(_one(c, "attempts", aid, "آزمون"), dict(e))

@router.post("/exams/{eid}/start")
def exam_start(eid: int, user: dict = Depends(STUDENT)):
    with store.conn() as c:
        e = _one(c, "exams", eid, "آزمون")
        if e["kind"] != "quiz" or not c.execute("SELECT 1 FROM enrollments WHERE class_id = ? AND student_id = ? AND status = 'active'", (e["class_id"], user["ref_id"])).fetchone():
            raise HTTPException(status_code=403, detail="این آزمون برای کلاس شما نیست")
        v = facts.exam_view(c, e)
        if not v["open"]:
            raise HTTPException(status_code=409, detail="این آزمون باز نیست")
        a = c.execute("SELECT * FROM attempts WHERE exam_id = ? AND student_id = ? ORDER BY id DESC LIMIT 1", (eid, user["ref_id"])).fetchone()
        if a and a["submitted"]:
            raise HTTPException(status_code=409, detail="این آزمون را داده‌اید")
        if a and _seconds_left(dict(a), e["minutes"]) <= 0:
            _submit(c, dict(a), e, user)
            raise HTTPException(status_code=409, detail="وقت این آزمون تمام شده است")
        if not a:
            aid = c.execute("INSERT INTO attempts (exam_id, student_id, started, answers) VALUES (?,?,?, '{}')",
                            (eid, user["ref_id"], f"{store.today().isoformat()} {datetime.now():%H:%M:%S}")).lastrowid
            a = c.execute("SELECT * FROM attempts WHERE id = ?", (aid,)).fetchone()
        return _paper(dict(a), e)

class AnswerIn(BaseModel):
    question: str = Field(max_length=10)
    choice: int = Field(ge=0, le=3)

@router.post("/attempts/{aid}/answer")
def answer(aid: int, req: AnswerIn, user: dict = Depends(ANY)):
    with store.conn() as c:
        a, e = _attempt(c, aid, user)
        if a["submitted"]:
            raise HTTPException(status_code=409, detail="این آزمون تمام شده است")
        if req.question not in json.loads(e["questions"]):
            raise HTTPException(status_code=422, detail="این پرسش در آزمون نیست")
        if _seconds_left(a, e["minutes"]) < -30:      # a little grace for a slow connection
            _submit(c, a, e, user)
            raise HTTPException(status_code=409, detail="وقت آزمون تمام شد؛ پاسخ‌های قبلی ثبت شد")
        answers = json.loads(a["answers"] or "{}") | {req.question: req.choice}
        c.execute("UPDATE attempts SET answers = ? WHERE id = ?", (json.dumps(answers), aid))
    return {"ok": True, "answered": len(answers)}

@router.post("/attempts/{aid}/submit")
def submit(aid: int, user: dict = Depends(ANY)):
    with store.conn() as c:
        a, e = _attempt(c, aid, user)
        _submit(c, a, e, user)
        return _result(c, _one(c, "attempts", aid, "آزمون"), e)

@router.get("/attempts/{aid}/result")
def result(aid: int, user: dict = Depends(ANY)):
    with store.conn() as c:
        a, e = _attempt(c, aid, user)
        if not a["submitted"]:
            raise HTTPException(status_code=409, detail="این آزمون هنوز تمام نشده است")
        return _result(c, a, e)

# ---------- the learner ----------

@router.get("/me/home")
def my_home(user: dict = Depends(STUDENT)):
    sid = user["ref_id"]
    with store.conn() as c:
        road = facts.road(c, sid)
        plan = facts.week_plan(c, sid)
        exams = []
        if road["current"]:
            exams = [facts.exam_view(c, e, sid) for e in c.execute("SELECT * FROM exams WHERE class_id = ? ORDER BY opens DESC", (road["current"]["class"]["id"],))]
        skills = list(facts.skill_totals(c, sid).values())
        t = facts.today().isoformat()
        return {"road": road, "plan": plan, "exams": exams, "skills": skills, "today_long": facts.jlong(t), "today_date": facts.jfull(t)}

class TickIn(BaseModel):
    item: str = Field(max_length=40)
    done: bool

@router.post("/me/tick")
def tick(req: TickIn, user: dict = Depends(STUDENT)):
    with store.conn() as c:
        plan = facts.week_plan(c, user["ref_id"])
        if req.item not in {i["key"] for i in plan["items"]}:
            raise HTTPException(status_code=404, detail="این کار در برنامه‌ی این هفته نیست")
        if req.done:
            c.execute("INSERT OR IGNORE INTO ticks (student_id, week, item) VALUES (?,?,?)", (user["ref_id"], plan["week"], req.item))
        else:
            c.execute("DELETE FROM ticks WHERE student_id = ? AND week = ? AND item = ?", (user["ref_id"], plan["week"], req.item))
    return {"ok": True}

class ReserveIn(BaseModel):
    class_id: int

@router.post("/me/reserve")
def reserve(req: ReserveIn, user: dict = Depends(STUDENT)):
    """The learner keeps a seat in a class of their next station; the fee is paid at the office."""
    with store.conn() as c:
        road = facts.road(c, user["ref_id"])
        nx = road["next"]
        cl = _one(c, "classes", req.class_id, "کلاس")
        if not nx or nx["registered"] or cl["course"] != nx["key"] or facts.term_by_id(c, cl["term_id"])["kind"] != "next":
            raise HTTPException(status_code=409, detail="این کلاس برای ترم بعد شما نیست")
        return _enrol(c, user, user["ref_id"], req.class_id)

@router.get("/me/note")
def my_note(user: dict = Depends(STUDENT)):
    """A short note to the learner about where they are, from their own facts only; its numbers are checked."""
    sid = user["ref_id"]
    with store.conn() as c:
        road = facts.road(c, sid)
        skills = facts.skill_totals(c, sid)
    cu, nx = road["current"], road["next"]
    lines = [f"زبان‌آموز: {road['student']['name']}", f"پیشرفت در کل مسیر: {road['pct']} درصد"]
    if cu:
        lines += [f"ترم فعلی: {cu['class']['course_name']}، جلسه‌ی {cu['sessions']} از {cu['of']}", f"نمره تا این‌جا: {cu['so_far']}" if cu["so_far"] is not None else "نمره تا این‌جا: ندارد",
                  f"غیبت‌ها: {cu['attendance']['counts']['absent']}"]
    lines += [f"{v['name']}: {v['right']} از {v['of']} درست" for v in skills.values()]
    if nx:
        lines.append(f"ترم بعد: {nx['name']}" + ("، ثبت‌نام کرده است" if nx["registered"] else "، هنوز ثبت‌نام نکرده است"))
    data = "\n".join(lines)
    weak = [v["name"] for v in skills.values() if v["pct"] < 60]
    fallback = (f"تا این‌جا {road['pct']} درصد مسیر را آمده‌اید. " + (f"این هفته روی {weak[0]} بیشتر کار کنید؛ تمرینش در برنامه‌ی همین هفته هست." if weak else
                "همین‌طور ادامه دهید؛ برنامه‌ی این هفته را قدم به قدم جلو ببرید."))
    key = f"note|{store.today()}|{sid}|{data}"
    if key in _cache:
        return _cache[key]
    text, checked = _written(
        "تو دستیار آموزشی یک آموزشگاه زبان هستی. برای این زبان‌آموز دو جمله‌ی کوتاه، گرم و دقیق به فارسی معیار بنویس: کجای مسیر است و این هفته روی چه چیزی "
        "بیشتر کار کند. فقط از اطلاعات زیر استفاده کن، عدد جدید نساز، او را با کسی مقایسه نکن و سلام ننویس.", data, fallback, max_tokens=160)
    out = {"text": text, "checked": checked}
    if checked is not None:
        _cache[key] = out
    return out

# ---------- the floating assistant ----------

class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=500)

@router.post("/ask")
def ask(req: Ask, user: dict = Depends(ANY)):
    """Answers from the asker's own view only: a learner from their own road, a teacher from their own classes."""
    with store.conn() as c:
        if user["role"] == "student":
            road = facts.road(c, user["ref_id"])
            cu, nx = road["current"], road["next"]
            lines = [f"پیشرفت در کل مسیر: {road['pct']} درصد"]
            if cu:
                v = cu["class"]
                lines += [f"کلاس فعلی: {v['course_name']}، {v['pair_text']} ساعت {v['time']}، {v['room_name']}، استاد {v['teacher']}",
                          f"کتاب این ترم: {v['book']}، درس‌های {v['units'][0]} تا {v['units'][1]}", f"جلسه‌ی بعد: {v['next_text']}",
                          f"جلسه‌ها: {cu['sessions']} از {cu['of']}", f"غیبت‌ها: {cu['attendance']['counts']['absent']}"]
            if nx:
                lines += [f"ترم بعد: {nx['name']}، کتاب {nx['book']}" + ("، همان کتاب این ترم" if nx["same_book"] else f"، کتاب جدید با قیمت {nx['book_price_text']}"),
                          f"شروع ترم بعد: {nx['term']['start_long']}" if nx["term"] else ""]
            if road.get("finish"):
                lines.append(f"پایان مسیر اگر بی‌وقفه ادامه دهد: {road['finish']['month']}")
        elif user["role"] == "teacher":
            h = facts.teacher_home(c, user["ref_id"])
            lines = [f"{s['label']}: {s['value']} ({s['sub']})" for s in h["stats"]] + [a["title"] for a in h["alerts"]]
            lines += [f"کلاس {v['course_name']}: {v['pair_text']} ساعت {v['time']}، {v['room_name']}، {v['seats']} نفر، جلسه‌ی بعد {v['next_text']}" for v in h["classes"]]
        else:
            o = facts.overview(c, user["role"])
            lines = [f"امروز {o['today_long']} {o['today']} است.", f"{o['term']['name']}: {o['term']['days_left']} روز تا پایان"]
            lines += [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]] + [a["title"] for a in o["alerts"]]
            lines += [f"کلاس امروز: {v['course_name']} ساعت {v['time']}، {v['room_name']}، {v['teacher']}" for v in o["classes_today"]]
    lines = [l for l in lines if l]
    data = "\n".join(lines)
    words = [w for w in re.findall(r"[؀-ۿ‌]{3,}", req.question) if w not in ("چقدر", "چند", "کدام", "است", "داریم", "چه", "کجا", "کی")]
    hits = [l for l in lines if any(w in l for w in words)]
    fallback = "\n".join(hits[:6]) if hits else "پاسخ این سؤال در اطلاعات آموزشگاه پیدا نشد. درباره‌ی کلاس‌ها، ترم بعد، آزمون‌ها و شهریه بپرسید."
    text, checked = _written(
        f"تو دستیار {institute.current()['name']} هستی. به سؤال زیر فقط از روی «اطلاعات» جواب بده، کوتاه، حداکثر سه جمله، فارسی معیار. "
        "ساعت‌ها، عددها و مبلغ‌ها را دقیقاً همان‌طور که در اطلاعات آمده بنویس. اگر جواب در اطلاعات نیست، همین را بگو.",
        f"سؤال: {req.question}\n\nاطلاعات:\n{data}", fallback)
    return {"answer": text, "checked": checked}
