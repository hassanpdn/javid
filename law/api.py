"""The law office's endpoints, all under /law. Logins, sessions and data are its own (law.db); the site's door and the
card's login (access.py) cover these like every other path.

Roles: owner (وکیل، صاحب دفتر) sees everything, including the checks, the log and the settings; associate (همکار وکیل)
works the cases, with «مال من» for their own; secretary (منشی) enters notices and opens cases. Deadlines are worked out
by code (facts.deadline); the model only reads pasted text and writes the client's report, whose dates and numbers
are checked against the case's facts, with a code-written fallback. Nothing is sent to a client from here: reports
are drafts the lawyer reads and sends.
"""
import re, threading
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from llm import ask_llm
from checks import only_known_numbers
from jalali import to_gregorian
from . import office, store, demo, facts, read as reader

router = APIRouter(prefix="/law")
_lock = threading.Lock()
_cache = {}

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

ALL = require("owner", "associate", "secretary")
LAWYERS = require("owner", "associate")
OWNER = require("owner")

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

LOGINS = ["vakil", "hamkar", "monshi"]

@router.get("/info")
def info():
    if not office.is_set_up():
        return {"set_up": False}
    return {"set_up": True, "office": office.public(), "logins": LOGINS, "today": facts.jfull(store.today().isoformat())}

@router.get("/setup/default")
def setup_default():
    return {"office": office.DEFAULT}

class Setup(BaseModel):
    office: dict

@router.post("/setup")
def setup(req: Setup):
    try:
        settings = office.clean(req.office)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with _lock:
        office.save(settings)
        demo.build()
        _cache.clear()
    return {"ok": True, "office": office.public()}

def reset():
    with _lock:
        office.forget()
        store.init()
        store.logout_all()
        _cache.clear()

def ensure_fresh():
    import os
    store.init()
    if office.is_set_up() and store.get_meta("built_for") != store.today().isoformat() and os.getenv("KEEP_DB") != "1":
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

def _jalali(s, what):
    """«1405/08/10» → ISO, or 422 with a plain message."""
    try:
        y, m, d = (int(x) for x in re.split(r"[/\-]", s.translate(reader.FA_DIGITS).strip()))
        assert 1300 < y < 1500 and 1 <= m <= 12 and 1 <= d <= 31
        return to_gregorian(y, m, d).isoformat()
    except Exception:
        raise HTTPException(status_code=422, detail=f"{what} درست نیست")

# ---------- dashboards ----------

@router.get("/overview")
def overview(user: dict = Depends(OWNER)):
    with store.conn() as c:
        return facts.overview(c)

@router.get("/today")
def today_view(user: dict = Depends(ALL)):
    with store.conn() as c:
        o = facts.overview(c)
        mine = facts.alerts(c, user["id"]) if user["role"] == "associate" else o["alerts"]
        return {"today": o["today"], "today_long": o["today_long"], "alerts": mine, "stats": o["stats"]}

@router.get("/brief")
def brief(user: dict = Depends(OWNER)):
    with store.conn() as c:
        key = f"{store.today()}|{c.execute('SELECT MAX(id) FROM events').fetchone()[0]}"
        if key in _cache:
            return _cache[key]
        data, o = facts.brief_facts(c)
    fallback = (f"امروز {len(o['alerts'])} کار منتظر دفتر است. " + " ".join(f"{a['title']}." for a in o["alerts"][:2])) if o["alerts"] else "امروز کار فوری‌ای نیست."
    s = office.current()
    text, checked = _written(
        f"تو دستیار {office.person('owner', s)}، وکیل و صاحب {s['name']} هستی. از روی اطلاعات زیر یک خلاصه‌ی صبحگاهی سه جمله‌ای به فارسی معیار، "
        "ساده و محترمانه بنویس. اول فوری‌ترین مهلت یا مهلت گذشته را با نام پرونده بگو، بعد جلسه‌های نزدیک و بعد بقیه را. "
        "تاریخ‌ها و عددها را دقیقاً همان‌طور که نوشته شده بنویس. عدد یا تاریخ جدید نساز. سلام ننویس.", data, fallback)
    out = {"text": text, "checked": checked}
    if checked is not None:
        _cache[key] = out
    return out

@router.get("/checks")
def checks(user: dict = Depends(OWNER)):
    with store.conn() as c:
        return facts.checks(c)

@router.get("/events")
def events(after: int = 0, user: dict = Depends(OWNER)):
    with store.conn() as c:
        return facts.events(c, after)

@router.get("/lawyers")
def lawyers(user: dict = Depends(ALL)):
    with store.conn() as c:
        return [{"id": r["id"], "name": r["full_name"]} for r in c.execute("SELECT * FROM users WHERE role != 'secretary' ORDER BY id")]

# ---------- cases ----------

def _case(c, cid):
    row = c.execute("SELECT * FROM cases WHERE id = ?", (cid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این پرونده پیدا نشد")
    return dict(row)

def _client(c, cs):
    row = c.execute("SELECT * FROM clients WHERE id = ?", (cs["client_id"],)).fetchone()
    return dict(row) if row else None

@router.get("/cases")
def cases(status: str = "open", mine: bool = False, user: dict = Depends(ALL)):
    q, args = "SELECT * FROM cases WHERE 1", []
    if status in ("open", "closed"):
        q += " AND status = ?"; args.append(status)
    if mine:
        q += " AND lawyer_id = ?"; args.append(user["id"])
    with store.conn() as c:
        names = facts.users(c)
        out = []
        for cs in c.execute(q + " ORDER BY id DESC", args):
            nxt = c.execute("""SELECT * FROM notices WHERE case_id = ? AND status = 'open' ORDER BY COALESCE(deadline, substr(hearing, 1, 10)) LIMIT 1""",
                            (cs["id"],)).fetchone()
            out.append(facts.case_view(cs, names, _client(c, cs)) | {"next": facts.notice_view(nxt) if nxt else None})
        return out

@router.get("/cases/{cid}")
def case_detail(cid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        names, cs = facts.users(c), _case(c, cid)
        off = facts.holidays(c)
        days = facts.settings(c)["days"]
        notices = []
        for n in c.execute("SELECT * FROM notices WHERE case_id = ? ORDER BY served DESC, id DESC", (cid,)):
            v = facts.notice_view(n, cs, names) | {"done_by_name": names.get(n["done_by"], "")}
            if n["deadline"]:
                last, moved = facts.deadline(n["served"], days.get(n["kind"], 0) or 0, off)
                v["how"] = facts.deadline_how(n["served"], days.get(n["kind"], 0), n["deadline"], moved if last == n["deadline"] else "")
            notices.append(v)
        last = c.execute("SELECT * FROM reports WHERE case_id = ? ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
        return {"case": facts.case_view(cs, names, _client(c, cs)), "notices": notices, "history": facts.events(c, 0, 200, cid),
                "report": {"last": facts.jfull(cs["last_report"]) if cs["last_report"] else None, "text": last["text"] if last else None}}

class CaseIn(BaseModel):
    topic: str = Field(min_length=2, max_length=80)
    client: str = Field(min_length=2, max_length=60)
    phone: str = Field("", max_length=20)
    opponent: str = Field("", max_length=80)
    field: str
    court: str = Field("", max_length=80)
    branch: str = Field("", max_length=10)
    number: str = Field("", max_length=24)
    archive: str = Field("", max_length=12)
    lawyer_id: int

@router.post("/cases")
def add_case(req: CaseIn, user: dict = Depends(ALL)):
    if req.field not in facts.FIELDS:
        raise HTTPException(status_code=422, detail="نوع پرونده را انتخاب کنید")
    t = store.today().isoformat()
    with store.conn() as c:
        if req.lawyer_id not in facts.users(c):
            raise HTTPException(status_code=422, detail="وکیل مسئول را انتخاب کنید")
        client = c.execute("INSERT INTO clients (name, phone) VALUES (?,?)", (req.client.strip(), re.sub(r"\D", "", req.phone))).lastrowid
        title = f"{req.topic.strip()}، {req.client.strip()}"
        cid = c.execute("""INSERT INTO cases (title, client_id, opponent, side, field, court, branch, number, archive, stage, lawyer_id, status, created)
                           VALUES (?,?,?,'خواهان',?,?,?,?,?,'first',?,'open',?)""",
                        (title, client, req.opponent.strip(), req.field, req.court.strip(), req.branch.strip(), re.sub(r"\D", "", req.number),
                         re.sub(r"\D", "", req.archive), req.lawyer_id, t)).lastrowid
        store.log(c, user, "case", f"پرونده‌ی «{title}» باز شد", cid)
    return {"id": cid}

# ---------- notices ----------

class ReadIn(BaseModel):
    text: str = Field(min_length=10, max_length=4000)

@router.post("/read")
def read_text(req: ReadIn, user: dict = Depends(ALL)):
    out = reader.read(req.text)
    f = out["fields"]
    with store.conn() as c:
        names, found = facts.users(c), []
        for cs in c.execute("SELECT * FROM cases WHERE status = 'open'"):
            why = ("شماره‌ی پرونده یکی است" if f["number"] and cs["number"] == f["number"] else
                   "شماره‌ی بایگانی یکی است" if f["archive"] and (cs["archive"] or "").lstrip("0") == f["archive"].lstrip("0") else "")
            if why:
                found.append(facts.case_view(cs, names, _client(c, cs)) | {"why": why})
    return out | {"cases": found}

@router.get("/sample")
def sample(user: dict = Depends(ALL)):
    """For the demo: a notice as the courts' system would send it, for one of the office's open cases with nothing
    pending, served today, so the presenter can paste it and watch it be read and matched to its case."""
    with store.conn() as c:
        cs = c.execute("""SELECT * FROM cases k WHERE status = 'open' AND field = 'civil' AND number != ''
                          AND NOT EXISTS (SELECT 1 FROM notices n WHERE n.case_id = k.id AND n.status = 'open') ORDER BY id LIMIT 1""").fetchone()
        client = _client(c, cs) if cs else None
    if not cs:
        raise HTTPException(status_code=404)
    t = facts.jfull(store.today().isoformat())
    return {"text": f"ابلاغیه\nشماره پرونده: {cs['number']}\nشماره بایگانی پرونده: {cs['archive']}\nمخاطب: {client['name'] if client else ''}\n"
                    f"نوع ابلاغ: ابلاغ دادنامه\nتاریخ ابلاغ: {t}\nمحتوای ابلاغ: دادنامه صادره از شعبه {cs['branch']} {cs['court']}، پیوست ابلاغیه"}

class NoticeIn(BaseModel):
    case_id: int
    kind: str
    served: str = Field(max_length=12)           # Jalali «1405/08/10»
    hearing_date: str | None = Field(None, max_length=12)
    hearing_time: str | None = Field(None, pattern=r"^\d{1,2}:\d{2}$")
    text: str = Field("", max_length=4000)

@router.post("/notices")
def add_notice(req: NoticeIn, user: dict = Depends(ALL)):
    """A notice entered in the office: its last day is worked out here, from the settings and the holidays."""
    if req.kind not in facts.KINDS:
        raise HTTPException(status_code=422, detail="نوع ابلاغیه را انتخاب کنید")
    served = _jalali(req.served, "تاریخ ابلاغ")
    if served > store.today().isoformat():
        raise HTTPException(status_code=422, detail="تاریخ ابلاغ نمی‌تواند بعد از امروز باشد")
    hearing = None
    if req.kind == "hearing":
        if not (req.hearing_date and req.hearing_time):
            raise HTTPException(status_code=422, detail="تاریخ و ساعت جلسه را بنویسید")
        hearing = f"{_jalali(req.hearing_date, 'تاریخ جلسه')} {req.hearing_time.zfill(5)}"
    with store.conn() as c:
        cs = _case(c, req.case_id)
        days = facts.settings(c)["days"][req.kind]
        last, moved = (facts.deadline(served, days, facts.holidays(c)) if days else (None, ""))
        nid = c.execute("""INSERT INTO notices (case_id, kind, served, deadline, hearing, text, status, entered_by, entered)
                           VALUES (?,?,?,?,?,?,'open',?,?)""", (cs["id"], req.kind, served, last, hearing, req.text.strip(), user["id"], store.stamp())).lastrowid
        name, todo, _ = facts.KINDS[req.kind]
        store.log(c, user, "notice", f"ابلاغیه ثبت شد: {name}" + (f"؛ روز آخر {todo} {facts.jfull(last)}" if last else "") +
                  (f"؛ جلسه {facts.jfull(hearing)} ساعت {hearing[11:]}" if hearing else ""), cs["id"])
        n = c.execute("SELECT * FROM notices WHERE id = ?", (nid,)).fetchone()
        v = facts.notice_view(n, cs, facts.users(c))
        if last:
            v["how"] = facts.deadline_how(served, days, last, moved)
        return v

class Done(BaseModel):
    note: str = Field("", max_length=300)

@router.post("/notices/{nid}/done")
def done(nid: int, req: Done, user: dict = Depends(LAWYERS)):
    """The lawyer did what the notice asked (filed the appeal, corrected the petition, attended the hearing)."""
    with store.conn() as c:
        n = c.execute("SELECT * FROM notices WHERE id = ?", (nid,)).fetchone()
        if not n:
            raise HTTPException(status_code=404)
        if n["status"] != "open":
            raise HTTPException(status_code=409, detail="این مورد قبلاً بسته شده است")
        c.execute("UPDATE notices SET status = 'done', done_at = ?, done_by = ?, note = ? WHERE id = ?", (store.stamp(), user["id"], req.note.strip(), nid))
        late = n["deadline"] and n["deadline"] < store.today().isoformat()
        store.log(c, user, "done", f"{facts.KINDS[n['kind']][1]} انجام شد" + (f" («{req.note.strip()}»)" if req.note.strip() else "") +
                  ("؛ پس از روز آخر مهلت" if late else ""), n["case_id"])
    return {"ok": True, "late": bool(late)}

@router.get("/deadlines")
def deadlines(mine: bool = False, user: dict = Depends(ALL)):
    """Every open deadline and hearing, soonest first, in groups: passed, this week, later."""
    with store.conn() as c:
        names = facts.users(c)
        cases = {r["id"]: dict(r) for r in c.execute("SELECT * FROM cases")}
        out = {"overdue": [], "week": [], "later": []}
        rows = c.execute("SELECT * FROM notices WHERE status = 'open' ORDER BY COALESCE(deadline, substr(hearing, 1, 10))").fetchall()
        for n in rows:
            cs = cases.get(n["case_id"])
            if not cs or (mine and cs["lawyer_id"] != user["id"]):
                continue
            v = facts.notice_view(n, cs, names)
            group = "overdue" if v["left"] < 0 else "week" if v["left"] <= 7 else "later"
            out[group].append(v)
        return out

# ---------- the client's report ----------

@router.post("/cases/{cid}/report/draft")
def report_draft(cid: int, user: dict = Depends(LAWYERS)):
    s = office.current()
    with store.conn() as c:
        cs = _case(c, cid)
        client = _client(c, cs)
        notices = [facts.notice_view(n) for n in c.execute("SELECT * FROM notices WHERE case_id = ? ORDER BY served DESC LIMIT 4", (cid,))]
    lines = [f"پرونده: {cs['title']}", f"مرجع: {cs['court']}، شعبه‌ی {cs['branch']}", f"مرحله: {facts.STAGES.get(cs['stage'], '')}"]
    for n in notices:
        line = f"{n['kind_text']}، ابلاغ {n['served_text']}"
        if n.get("deadline_text"):
            line += f"؛ مهلت {n['todo']} تا {n['deadline_text']}" + ("؛ انجام شد" if n["status"] == "done" else "")
        if n.get("hearing_text"):
            line += f"؛ جلسه {n['hearing_text']}" + ("؛ برگزار شد" if n["status"] == "done" else "")
        lines.append(line)
    data = "\n".join(lines)
    name = client["name"] if client else "موکل"
    fallback = f"{name} گرامی، سلام. آخرین وضعیت پرونده‌ی شما ({cs['title']}):\n" + "\n".join(lines[3:]) + f"\n{office.person('owner', s)}، {s['name']}"
    text, checked = _written(
        f"تو منشی {s['name']} هستی. برای موکل یک پیام کوتاه وضعیت پرونده بنویس: آخرین اتفاق پرونده، کاری که دفتر انجام داده یا انجام می‌دهد، و قدم بعد با تاریخش. "
        f"حداکثر پنج جمله، فارسی معیار و محترمانه، بدون اصطلاحات پیچیده‌ی حقوقی و بدون وعده درباره‌ی نتیجه‌ی پرونده. با «{name} گرامی، سلام» شروع کن و با "
        f"«{office.person('owner', s)}، {s['name']}» تمام کن. تاریخ‌ها و عددها را دقیقاً همان‌طور که در اطلاعات آمده بنویس و چیز جدیدی نساز.",
        data, fallback)
    return {"text": text, "checked": checked, "phone": client["phone"] if client else ""}

class Sent(BaseModel):
    text: str = Field(min_length=5, max_length=3000)

@router.post("/cases/{cid}/report")
def report_sent(cid: int, req: Sent, user: dict = Depends(LAWYERS)):
    with store.conn() as c:
        _case(c, cid)
        c.execute("INSERT INTO reports (case_id, at, user_id, text) VALUES (?,?,?,?)", (cid, store.stamp(), user["id"], req.text.strip()))
        c.execute("UPDATE cases SET last_report = ? WHERE id = ?", (store.today().isoformat(), cid))
        store.log(c, user, "report", "گزارش وضعیت برای موکل فرستاده شد", cid)
    return {"ok": True}

# ---------- settings ----------

class Settings(BaseModel):
    days: dict[str, int]
    holidays: list[str] = []

@router.get("/settings")
def get_settings(user: dict = Depends(ALL)):
    with store.conn() as c:
        s = facts.settings(c)
    return s | {"kinds": [{"key": k, "name": v[0], "todo": v[1], "default": v[2]} for k, v in facts.KINDS.items() if v[2]]}

@router.post("/settings")
def set_settings(req: Settings, user: dict = Depends(OWNER)):
    for k, v in req.days.items():
        if k not in facts.KINDS or not facts.KINDS[k][2] or not 1 <= v <= 120:
            raise HTTPException(status_code=422, detail="تعداد روز مهلت‌ها درست نیست")
    clean = []
    for h in req.holidays:
        h = h.translate(reader.FA_DIGITS).strip()
        if h:
            _jalali(h, f"تعطیلی «{h}»")
            clean.append(h)
    with store.conn() as c:
        for k, v in req.days.items():
            store.set_meta(c, "days_" + k, v)
        store.set_meta(c, "holidays", ",".join(clean))
        store.log(c, user, "settings", "مدت مهلت‌ها و تعطیلات تغییر کرد")
        return facts.settings(c)

# ---------- the floating assistant ----------

class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=500)

@router.post("/ask")
def ask(req: Ask, user: dict = Depends(ALL)):
    t = store.today()
    with store.conn() as c:
        names = facts.users(c)
        lines = [f"امروز {facts.jlong(t.isoformat())} {facts.jfull(t.isoformat())} است."]
        for n in c.execute("""SELECT n.*, k.title, k.lawyer_id FROM notices n JOIN cases k ON k.id = n.case_id WHERE n.status = 'open'
                              ORDER BY COALESCE(n.deadline, substr(n.hearing, 1, 10)) LIMIT 25"""):
            v = facts.notice_view(n)
            if v.get("deadline_text"):
                lines.append(f"مهلت {v['todo']}، پرونده‌ی «{n['title']}»: روز آخر {v['deadline_text']} ({v['left_text']})، مسئول {names.get(n['lawyer_id'], '')}")
            elif v.get("hearing_text"):
                lines.append(f"جلسه‌ی پرونده‌ی «{n['title']}»: {v['hearing_text']} ({v['left_text']})، مسئول {names.get(n['lawyer_id'], '')}")
        lines.append(f"پرونده‌های باز: {c.execute('SELECT COUNT(*) FROM cases WHERE status = ?', ('open',)).fetchone()[0]}")
    data = "\n".join(lines)
    words = [w for w in re.findall(r"[؀-ۿ‌]{3,}", req.question) if w not in ("چقدر", "چند", "کدام", "است", "داریم")]
    hits = [l for l in lines if any(w in l for w in words)]
    fallback = "\n".join(hits[:5]) if hits else "پاسخ این سؤال در اطلاعات دفتر پیدا نشد. درباره‌ی مهلت‌ها، جلسه‌ها و پرونده‌ها بپرسید."
    text, checked = _written(
        f"تو دستیار {office.current()['name']} هستی. به سؤال زیر فقط از روی «اطلاعات» جواب بده، کوتاه، حداکثر سه جمله، فارسی معیار. "
        "تاریخ‌ها را دقیقاً همان‌طور که در اطلاعات آمده بنویس. اگر جواب در اطلاعات نیست، همین را بگو.",
        f"سؤال: {req.question}\n\nاطلاعات:\n{data}", fallback)
    return {"answer": text, "checked": checked}
