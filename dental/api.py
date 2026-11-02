"""The dental clinic's endpoints, all under /dental. Logins, sessions and data are its own (dental.db); the site's door
and the card's login (access.py) cover these like every other path.

Roles: owner (دندان‌پزشک، صاحب مطب) sees everything, including the checks, the log and the morning summary, and is the
only one who marks a treatment done; secretary (منشی) books, confirms, takes payments and follows up plans. Every
number is worked out by code (facts.py); the model only writes the morning summary and the plan follow-up message,
whose numbers are checked against the facts, with a code-written fallback. Nothing is sent to a patient from here:
messages are drafts the secretary reads and sends.
"""
import re, threading
from datetime import date, datetime
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from llm import ask_llm
from checks import only_known_numbers
from jalali import to_gregorian
from . import clinic, store, demo, facts

router = APIRouter(prefix="/dental")
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

ALL = require("owner", "secretary")
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

@router.get("/info")
def info():
    if not clinic.is_set_up():
        return {"set_up": False}
    return {"set_up": True, "clinic": clinic.public(), "today": facts.jfull(store.today().isoformat()),
            "services": [{"key": k, "name": v[0], "minutes": v[1], "price": v[2], "price_text": facts.money(v[2])} for k, v in facts.SERVICES.items()]}

@router.get("/setup/default")
def setup_default():
    return {"clinic": clinic.DEFAULT}

class Setup(BaseModel):
    clinic: dict

@router.post("/setup")
def setup(req: Setup):
    try:
        settings = clinic.clean(req.clinic)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with _lock:
        clinic.save(settings)
        demo.build()
        _cache.clear()
    return {"ok": True, "clinic": clinic.public()}

def reset():
    with _lock:
        clinic.forget()
        store.init()
        store.logout_all()
        _cache.clear()

def ensure_fresh():
    import os
    store.init()
    if clinic.is_set_up() and store.get_meta("built_for") != store.today().isoformat() and os.getenv("KEEP_DB") != "1":
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
        y, m, d = (int(x) for x in re.split(r"[/\-]", s.translate(FA_DIGITS).strip()))
        assert 1300 < y < 1500 and 1 <= m <= 12 and 1 <= d <= 31
        return to_gregorian(y, m, d).isoformat()
    except Exception:
        raise HTTPException(status_code=422, detail=f"{what} درست نیست")

def _patient(c, pid):
    row = c.execute("SELECT * FROM patients WHERE id = ?", (pid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این بیمار پیدا نشد")
    return dict(row)

def _appt(c, aid):
    row = c.execute("SELECT * FROM appointments WHERE id = ?", (aid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این نوبت پیدا نشد")
    return dict(row)

# ---------- dashboards ----------

@router.get("/today")
def today_view(user: dict = Depends(ALL)):
    with store.conn() as c:
        o = facts.overview(c)
        if user["role"] == "owner":
            o["checks"] = len(facts.checks(c))
        return o

@router.get("/brief")
def brief(user: dict = Depends(OWNER)):
    with store.conn() as c:
        key = f"{store.today()}|{c.execute('SELECT MAX(id) FROM events').fetchone()[0]}"
        if key in _cache:
            return _cache[key]
        data, o = facts.brief_facts(c)
    fallback = (f"امروز {len(o['alerts'])} کار منتظر مطب است. " + " ".join(f"{a['title']}." for a in o["alerts"][:2])) if o["alerts"] else "امروز کار فوری‌ای نیست."
    s = clinic.current()
    text, checked = _written(
        f"تو دستیار {clinic.person('owner', s)}، دندان‌پزشک و صاحب {s['name']} هستی. از روی اطلاعات زیر یک خلاصه‌ی صبحگاهی سه جمله‌ای به فارسی معیار، "
        "ساده و محترمانه بنویس. اول نوبت‌های تأییدنشده و وقت‌های خالی روز کاری بعد را بگو، بعد طرح‌های درمانی که منتظر تماس‌اند با مبلغشان. "
        "عددها و مبلغ‌ها را دقیقاً همان‌طور که نوشته شده بنویس. عدد جدید نساز. سلام ننویس.", data, fallback)
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

# ---------- schedule ----------

@router.get("/day")
def day(d: str | None = None, user: dict = Depends(ALL)):
    iso = _jalali(d, "تاریخ") if d else store.today().isoformat()
    with store.conn() as c:
        return facts.schedule(c, iso)

@router.get("/free")
def free(d: str, minutes: int = 30, user: dict = Depends(ALL)):
    """The times an appointment this long can start on a day."""
    iso = _jalali(d, "تاریخ")
    with store.conn() as c:
        times = [s for s in facts.SLOTS if facts.fits(c, iso, s, minutes)] if iso >= store.today().isoformat() else []
        if iso == date.today().isoformat():      # today: not the hours already gone
            now = datetime.now().strftime("%H:%M")
            times = [s for s in times if s > now]
        return {"date_text": facts.jlong(iso) + " " + facts.jfull(iso), "closed": not facts.open_day(date.fromisoformat(iso)), "times": times}

class BookIn(BaseModel):
    patient_id: int
    service: str
    date: str = Field(max_length=12)                 # Jalali «1405/08/10»
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    plan_item_id: int | None = None
    waitlist_id: int | None = None

@router.post("/appointments")
def book(req: BookIn, user: dict = Depends(ALL)):
    if req.service not in facts.SERVICES:
        raise HTTPException(status_code=422, detail="خدمت را انتخاب کنید")
    iso = _jalali(req.date, "تاریخ نوبت")
    if iso < store.today().isoformat():
        raise HTTPException(status_code=422, detail="تاریخ نوبت گذشته است")
    name, minutes, price = facts.SERVICES[req.service]
    with store.conn() as c:
        p = _patient(c, req.patient_id)
        if req.plan_item_id:
            item = c.execute("SELECT i.* FROM plan_items i JOIN plans p ON p.id = i.plan_id WHERE i.id = ? AND p.patient_id = ?",
                             (req.plan_item_id, p["id"])).fetchone()
            if not item:
                raise HTTPException(status_code=422, detail="این مرحله در طرح درمان این بیمار نیست")
            price = item["price"]
            c.execute("UPDATE plans SET status = 'accepted' WHERE id = ? AND status = 'proposed'", (item["plan_id"],))
        if not facts.fits(c, iso, req.time, minutes):
            raise HTTPException(status_code=409, detail="این وقت دیگر خالی نیست")
        aid = c.execute("""INSERT INTO appointments (patient_id, at, minutes, service, price, plan_item_id, status, created, changed)
                           VALUES (?,?,?,?,?,?, 'confirmed', ?, ?)""", (p["id"], f"{iso} {req.time}", minutes, req.service, price, req.plan_item_id,
                                                                     store.stamp(), store.stamp())).lastrowid
        if req.waitlist_id:
            c.execute("UPDATE waitlist SET status = 'booked' WHERE id = ? AND patient_id = ?", (req.waitlist_id, p["id"]))
        store.log(c, user, "book", f"نوبت {name} برای {facts.jlong(iso)} ساعت {req.time}" + ("، از فهرست انتظار" if req.waitlist_id else ""), p["id"])
        return facts.appt_view(_appt(c, aid), {p["id"]: p["name"]})

class StatusIn(BaseModel):
    status: str

@router.post("/appointments/{aid}/status")
def set_status(aid: int, req: StatusIn, user: dict = Depends(ALL)):
    """confirmed (the patient said they will come), done (the dentist only), noshow, cancelled."""
    if req.status not in ("confirmed", "done", "noshow", "cancelled"):
        raise HTTPException(status_code=422, detail="وضعیت درست نیست")
    if req.status == "done" and user["role"] != "owner":
        raise HTTPException(status_code=403, detail="انجام درمان را دندان‌پزشک ثبت می‌کند")
    with store.conn() as c:
        a = _appt(c, aid)
        if a["status"] in ("done", "noshow", "cancelled"):
            raise HTTPException(status_code=409, detail="وضعیت این نوبت قبلاً ثبت شده است")
        if req.status in ("done", "noshow") and a["at"][:10] > store.today().isoformat():
            raise HTTPException(status_code=422, detail="این نوبت هنوز نرسیده است")
        c.execute("UPDATE appointments SET status = ?, changed = ? WHERE id = ?", (req.status, store.stamp(), aid))
        if req.status == "done" and a["plan_item_id"]:
            c.execute("UPDATE plan_items SET status = 'done', done_on = ? WHERE id = ?", (store.today().isoformat(), a["plan_item_id"]))
        store.log(c, user, req.status, f"نوبت {facts.service_name(a['service'])} {facts.jday(a['at'])} ساعت {a['at'][11:16]}: {facts.STATUS[req.status]}", a["patient_id"])
    return {"ok": True}

@router.get("/appointments/{aid}/reminder")
def reminder(aid: int, user: dict = Depends(ALL)):
    """The reminder message for an appointment, written by code from the appointment itself."""
    s = clinic.current()
    with store.conn() as c:
        a = _appt(c, aid)
        p = _patient(c, a["patient_id"])
    text = (f"{p['name']} گرامی، سلام. نوبت شما در {s['name']} برای {facts.service_name(a['service'])}، "
            f"{facts.jlong(a['at'])} ساعت {a['at'][11:16]} است. لطفاً با یک پیام کوتاه آمدنتان را تأیید کنید؛ اگر نمی‌توانید بیایید، "
            f"خبر بدهید تا این وقت را به بیمار دیگری بدهیم.\n{clinic.person('secretary', s)}، {s['name']}")
    return {"text": text, "phone": p["phone"]}

# ---------- patients ----------

@router.get("/patients")
def patients(q: str = "", user: dict = Depends(ALL)):
    q = q.strip().translate(FA_DIGITS)
    with store.conn() as c:
        rows = c.execute("SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT 60", (f"%{q}%", f"%{q}%")).fetchall()
        out = []
        for p in rows:
            owed, paid = facts.balance(c, p["id"])
            nxt = c.execute("""SELECT * FROM appointments WHERE patient_id = ? AND status IN ('booked', 'confirmed') AND substr(at, 1, 10) >= ?
                               ORDER BY at LIMIT 1""", (p["id"], store.today().isoformat())).fetchone()
            last = c.execute("SELECT MAX(at) FROM appointments WHERE patient_id = ? AND status = 'done'", (p["id"],)).fetchone()[0]
            out.append(dict(p) | {"left": owed - paid, "left_text": facts.money(owed - paid), "next": facts.appt_view(nxt) if nxt else None,
                                  "last_text": facts.jfull(last) if last else ""})
        return out

@router.get("/patients/{pid}")
def patient(pid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        p = _patient(c, pid)
        owed, paid = facts.balance(c, pid)
        who = {pid: p["name"]}
        appts = [facts.appt_view(a, who) for a in c.execute("SELECT * FROM appointments WHERE patient_id = ? ORDER BY at DESC LIMIT 30", (pid,))]
        pays = [dict(r) | {"date_text": facts.jfull(r["at"]), "amount_text": facts.money(r["amount"]), "method_text": facts.METHODS.get(r["method"], r["method"])}
                for r in c.execute("SELECT * FROM payments WHERE patient_id = ? ORDER BY at DESC LIMIT 30", (pid,))]
        plans = [facts.plan_view(c, pl, who) for pl in c.execute("SELECT * FROM plans WHERE patient_id = ? ORDER BY created DESC", (pid,))]
        contacts = [dict(r) | {"date_text": facts.jfull(r["at"])} for r in c.execute("SELECT * FROM contacts WHERE patient_id = ? ORDER BY at DESC", (pid,))]
        wait = [dict(r) | {"service_text": facts.service_name(r["service"])} for r in c.execute("SELECT * FROM waitlist WHERE patient_id = ? AND status = 'waiting'", (pid,))]
        noshows = sum(1 for a in appts if a["status"] == "noshow")
        return {"patient": p | {"created_text": facts.jfull(p["created"])}, "appointments": appts, "payments": pays, "plans": plans, "contacts": contacts,
                "waiting": wait, "noshows": noshows,
                "balance": {"owed": owed, "paid": paid, "left": owed - paid, "left_text": facts.money(owed - paid),
                            "how": [f"درمان‌های انجام‌شده: {facts.money(owed)}", f"پرداخت‌شده: {facts.money(paid)}", f"= مانده: {facts.money(owed - paid)}"]},
                "history": facts.events(c, 0, 60, pid)}

class PatientIn(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    phone: str = Field(min_length=10, max_length=20)

@router.post("/patients")
def add_patient(req: PatientIn, user: dict = Depends(ALL)):
    phone = re.sub(r"\D", "", req.phone.translate(FA_DIGITS))
    if not re.fullmatch(r"09\d{9}", phone):
        raise HTTPException(status_code=422, detail="شماره‌ی همراه باید ۱۱ رقم و با ۰۹ شروع شود")
    with store.conn() as c:
        same = c.execute("SELECT * FROM patients WHERE phone = ?", (phone,)).fetchone()
        if same:
            raise HTTPException(status_code=409, detail=f"این شماره برای «{same['name']}» ثبت شده است")
        pid = c.execute("INSERT INTO patients (name, phone, created) VALUES (?,?,?)", (" ".join(req.name.split()), phone, store.today().isoformat())).lastrowid
        store.log(c, user, "patient", "پرونده‌ی بیمار باز شد", pid)
    return {"id": pid}

class PaymentIn(BaseModel):
    amount: int = Field(gt=0, le=2_000_000_000)
    method: str

@router.post("/patients/{pid}/payments")
def pay(pid: int, req: PaymentIn, user: dict = Depends(ALL)):
    if req.method not in facts.METHODS:
        raise HTTPException(status_code=422, detail="روش پرداخت را انتخاب کنید")
    with store.conn() as c:
        _patient(c, pid)
        c.execute("INSERT INTO payments (patient_id, at, amount, method, user_id) VALUES (?,?,?,?,?)", (pid, store.stamp(), req.amount, req.method, user["id"]))
        store.log(c, user, "pay", f"پرداخت {facts.money(req.amount)} ({facts.METHODS[req.method]})", pid)
        owed, paid = facts.balance(c, pid)
    return {"left": owed - paid, "left_text": facts.money(owed - paid)}

# ---------- treatment plans ----------

@router.get("/plans")
def plans(user: dict = Depends(ALL)):
    with store.conn() as c:
        out = facts.plans(c)
        return out | {"follow_days": facts.FOLLOW_DAYS}

class PlanIn(BaseModel):
    patient_id: int
    title: str = Field(min_length=2, max_length=60)
    items: list[dict] = Field(min_length=1, max_length=12)     # [{service, tooth}]

@router.post("/plans")
def add_plan(req: PlanIn, user: dict = Depends(OWNER)):
    with store.conn() as c:
        p = _patient(c, req.patient_id)
        items = []
        for i in req.items:
            if i.get("service") not in facts.SERVICES:
                raise HTTPException(status_code=422, detail="خدمت هر مرحله را انتخاب کنید")
            items.append((i["service"], str(i.get("tooth", ""))[:6], facts.SERVICES[i["service"]][2]))
        plid = c.execute("INSERT INTO plans (patient_id, title, created, status) VALUES (?,?,?, 'proposed')", (p["id"], req.title.strip(), store.today().isoformat())).lastrowid
        for srv, tooth, price in items:
            c.execute("INSERT INTO plan_items (plan_id, service, tooth, price, status) VALUES (?,?,?,?, 'planned')", (plid, srv, tooth, price))
        store.log(c, user, "plan", f"طرح درمان «{req.title.strip()}» پیشنهاد شد ({facts.money(sum(x[2] for x in items))})", p["id"])
    return {"id": plid}

def _plan(c, plid):
    row = c.execute("SELECT * FROM plans WHERE id = ?", (plid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این طرح درمان پیدا نشد")
    return row

@router.post("/plans/{plid}/followup/draft")
def followup_draft(plid: int, user: dict = Depends(ALL)):
    """A short message to a patient whose plan has not started: the model writes it from the plan's facts, with no price,
    no pressure and no medical claim; its numbers are checked; a code-written text replaces it otherwise."""
    s = clinic.current()
    with store.conn() as c:
        v = facts.plan_view(c, _plan(c, plid))
        p = _patient(c, v["patient_id"])
    steps = "، ".join(dict.fromkeys(i["service_text"] for i in v["items"]))
    data = "\n".join([f"بیمار: {p['name']}", f"طرح درمان: {v['title']} ({steps})", f"تاریخ معاینه و پیشنهاد طرح: {v['created_text']}",
                      f"مطب: {s['name']}", f"منشی: {clinic.person('secretary', s)}"])
    fallback = (f"{p['name']} گرامی، سلام. از {s['name']} پیام می‌دهیم. طرح درمانی که در معاینه‌ی {v['created_text']} برایتان نوشته شد ({steps}) "
                f"هنوز شروع نشده است. اگر سؤالی درباره‌ی مراحل یا هزینه دارید، یا می‌خواهید نوبت بگیرید، با همین شماره تماس بگیرید.\n"
                f"{clinic.person('secretary', s)}، {s['name']}")
    text, checked = _written(
        f"تو منشی {s['name']} هستی. برای بیماری که طرح درمانش هنوز شروع نشده، یک پیام کوتاه و دوستانه بنویس: یادآوری طرح، این‌که اگر سؤالی دارد "
        f"می‌تواند تماس بگیرد، و پیشنهاد گرفتن نوبت. حداکثر چهار جمله، فارسی معیار و محترمانه. مبلغ ننویس، عجله نینداز، درباره‌ی بیماری یا خطر "
        f"چیزی نگو. با «{p['name']} گرامی، سلام» شروع کن و با «{clinic.person('secretary', s)}، {s['name']}» تمام کن. تاریخ را دقیقاً همان‌طور که "
        "در اطلاعات آمده بنویس و عدد جدید نساز.", data, fallback)
    return {"text": text, "checked": checked, "phone": p["phone"]}

class ContactIn(BaseModel):
    kind: str                       # sent (the message went), call (talked on the phone), declined (the patient does not want it)
    text: str = Field("", max_length=300)

@router.post("/plans/{plid}/contact")
def contact(plid: int, req: ContactIn, user: dict = Depends(ALL)):
    if req.kind not in ("sent", "call", "declined"):
        raise HTTPException(status_code=422, detail="نتیجه‌ی تماس را انتخاب کنید")
    words = {"sent": "پیام پیگیری فرستاده شد", "call": "تماس گرفته شد", "declined": "بیمار فعلاً طرح را نمی‌خواهد"}
    with store.conn() as c:
        pl = _plan(c, plid)
        c.execute("INSERT INTO contacts (patient_id, plan_id, at, user_id, kind, text) VALUES (?,?,?,?,?,?)",
                  (pl["patient_id"], plid, store.stamp(), user["id"], req.kind, req.text.strip() or words[req.kind]))
        if req.kind == "declined":
            c.execute("UPDATE plans SET status = 'declined' WHERE id = ?", (plid,))
        store.log(c, user, "contact", f"طرح «{pl['title']}»: {words[req.kind]}" + (f" («{req.text.strip()}»)" if req.text.strip() else ""), pl["patient_id"])
    return {"ok": True}

# ---------- waiting list ----------

@router.get("/waitlist")
def waitlist(user: dict = Depends(ALL)):
    with store.conn() as c:
        who = facts.names(c)
        phones = {r["id"]: r["phone"] for r in c.execute("SELECT id, phone FROM patients")}
        return [dict(r) | {"patient": who.get(r["patient_id"], ""), "phone": phones.get(r["patient_id"], ""), "service_text": facts.service_name(r["service"]),
                           "minutes": facts.SERVICES[r["service"]][1], "added_text": facts.jfull(r["added"]), "days": facts.days_ago(r["added"])}
                for r in c.execute("SELECT * FROM waitlist WHERE status = 'waiting' ORDER BY added")]

class WaitIn(BaseModel):
    patient_id: int
    service: str
    note: str = Field("", max_length=200)

@router.post("/waitlist")
def add_wait(req: WaitIn, user: dict = Depends(ALL)):
    if req.service not in facts.SERVICES:
        raise HTTPException(status_code=422, detail="خدمت را انتخاب کنید")
    with store.conn() as c:
        _patient(c, req.patient_id)
        wid = c.execute("INSERT INTO waitlist (patient_id, service, added, note, status) VALUES (?,?,?,?, 'waiting')",
                        (req.patient_id, req.service, store.today().isoformat(), req.note.strip())).lastrowid
        store.log(c, user, "wait", f"به فهرست انتظار اضافه شد: {facts.service_name(req.service)}", req.patient_id)
    return {"id": wid}

# ---------- the floating assistant ----------

class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=500)

@router.post("/ask")
def ask(req: Ask, user: dict = Depends(ALL)):
    t = store.today().isoformat()
    with store.conn() as c:
        o = facts.overview(c)
        lines = [f"امروز {o['today_long']} {o['today']} است."] + [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]]
        lines += [a["title"] for a in o["alerts"]]
        who = facts.names(c)
        nxt = facts.next_workday().isoformat()
        for a in c.execute("SELECT * FROM appointments WHERE substr(at, 1, 10) IN (?, ?) AND status != 'cancelled' ORDER BY at", (t, nxt)):
            lines.append(f"نوبت {facts.day_word(a['at'])} ساعت {a['at'][11:16]}: {who.get(a['patient_id'], '')}، {facts.service_name(a['service'])}، {facts.STATUS[a['status']]}")
    data = "\n".join(lines)
    words = [w for w in re.findall(r"[؀-ۿ‌]{3,}", req.question) if w not in ("چقدر", "چند", "کدام", "است", "داریم", "چه")]
    hits = [l for l in lines if any(w in l for w in words)]
    fallback = "\n".join(hits[:6]) if hits else "پاسخ این سؤال در اطلاعات مطب پیدا نشد. درباره‌ی نوبت‌ها، طرح‌های درمان و پرداخت‌ها بپرسید."
    text, checked = _written(
        f"تو دستیار {clinic.current()['name']} هستی. به سؤال زیر فقط از روی «اطلاعات» جواب بده، کوتاه، حداکثر سه جمله، فارسی معیار. "
        "ساعت‌ها و مبلغ‌ها را دقیقاً همان‌طور که در اطلاعات آمده بنویس. اگر جواب در اطلاعات نیست، همین را بگو.",
        f"سؤال: {req.question}\n\nاطلاعات:\n{data}", fallback)
    return {"answer": text, "checked": checked}
