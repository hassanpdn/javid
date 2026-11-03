"""The hotel's endpoints, all under /hotel. Logins, sessions and data are its own (hotel.db); the site's door and the
card's login (access.py) cover these like every other path.

Roles: manager (مدیر هتل) sees everything, including the checks, the report, the settings and the log; reservation
(رزرو) takes and changes bookings; reception (پذیرش) checks guests in and out, the folio and closing the day;
housekeeping (خانه‌داری) only the rooms' state, repairs and guests' requests, on a page made for a phone.
Every number is worked out by code (facts.py). The model reads pasted text (read.py) and writes the manager's morning
summary, whose numbers are checked, with a code-written fallback. Messages to guests are built by code and sent by a
person. Nothing is confirmed, cancelled or charged by the assistant: it suggests, the operator decides.
"""
import json, re, threading
from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from llm import ask_llm
from checks import only_known_numbers
from jalali import to_gregorian
from . import info, store, demo, facts, read as reader

router = APIRouter(prefix="/hotel")
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

ALL = require("manager", "reservation", "reception", "housekeeping")
DESK = require("manager", "reservation", "reception")
FRONT = require("manager", "reception")
MANAGER = require("manager")
ROOMS = require("manager", "reception", "housekeeping")

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
def info_():
    if not info.is_set_up():
        return {"set_up": False}
    with store.conn() as c:
        s = facts.settings(c)
        agencies = [dict(a) for a in c.execute("SELECT id, name, kind, discount FROM agencies ORDER BY id")]
    return {"set_up": True, "hotel": info.public(), "today": facts.jfull(store.today().isoformat()),
            "types": [{"key": k, "name": v[0], "beds": v[1], "most": v[2], "price": s["prices"][k]} for k, v in facts.TYPES.items()],
            "boards": facts.BOARDS, "sources": facts.SOURCES, "charges": facts.CHARGES, "methods": facts.METHODS, "agencies": agencies,
            "max_discount": s["max_discount"], "check_in": facts.CHECK_IN, "check_out": facts.CHECK_OUT}

@router.get("/setup/default")
def setup_default():
    return {"hotel": info.DEFAULT}

class Setup(BaseModel):
    hotel: dict

@router.post("/setup")
def setup(req: Setup):
    try:
        settings = info.clean(req.hotel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with _lock:
        info.save(settings)
        demo.build()
        _cache.clear()
    return {"ok": True, "hotel": info.public()}

def reset():
    with _lock:
        info.forget()
        store.init()
        store.logout_all()
        _cache.clear()

def ensure_fresh():
    import os
    store.init()
    if info.is_set_up() and store.get_meta("built_for") != store.today().isoformat() and os.getenv("KEEP_DB") != "1":
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

def _iso(s, what):
    """«1405/08/10» → ISO, or 422 with a plain message."""
    try:
        y, m, d = (int(x) for x in re.split(r"[/\-]", str(s).translate(reader.FA_DIGITS).strip()))
        assert 1300 < y < 1500 and 1 <= m <= 12 and 1 <= d <= 31
        return to_gregorian(y, m, d).isoformat()
    except Exception:
        raise HTTPException(status_code=422, detail=f"{what} درست نیست")

def _stay(arrive, depart):
    a, d = _iso(arrive, "تاریخ ورود"), _iso(depart, "تاریخ خروج")
    if d <= a:
        raise HTTPException(status_code=422, detail="تاریخ خروج باید بعد از تاریخ ورود باشد")
    if len(facts.nights_of(a, d)) > 30:
        raise HTTPException(status_code=422, detail="بیش از ۳۰ شب را جداگانه رزرو کنید")
    return a, d

def _booking(c, bid):
    row = c.execute("SELECT * FROM bookings WHERE id = ?", (bid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این رزرو پیدا نشد")
    return dict(row)

def _room(c, rid):
    row = c.execute("SELECT * FROM rooms WHERE id = ?", (rid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این اتاق پیدا نشد")
    return dict(row)

def _set_status(c, user, room_id, status):
    c.execute("UPDATE rooms SET status = ? WHERE id = ?", (status, room_id))
    c.execute("INSERT INTO room_log (room_id, at, status, user_id) VALUES (?,?,?,?)", (room_id, store.stamp(), status, user["id"] if user else None))

# ---------- dashboards ----------

@router.get("/today")
def today_view(user: dict = Depends(DESK)):
    with store.conn() as c:
        o = facts.overview(c)
        if user["role"] == "manager":
            o["checks"] = len(facts.checks(c))
        return o

@router.get("/brief")
def brief(user: dict = Depends(MANAGER)):
    with store.conn() as c:
        key = f"{store.today()}|{c.execute('SELECT MAX(id) FROM events').fetchone()[0]}"
        if key in _cache:
            return _cache[key]
        data, o = facts.brief_facts(c)
    fallback = (f"امروز {len(o['alerts'])} کار منتظر هتل است. " + " ".join(f"{a['title']}." for a in o["alerts"][:2])) if o["alerts"] else "امروز کار فوری‌ای نیست."
    s = info.current()
    text, checked = _written(
        f"تو دستیار {info.person('manager', s)}، مدیر {s['name']} هستی. از روی اطلاعات زیر یک خلاصه‌ی صبحگاهی سه جمله‌ای به فارسی معیار، "
        "ساده و محترمانه بنویس: اول اشغال امشب و ورود و خروج امروز، بعد فوری‌ترین کارها با نام. "
        "عددها را دقیقاً همان‌طور که نوشته شده بنویس. عدد جدید نساز. سلام ننویس.", data, fallback)
    out = {"text": text, "checked": checked}
    if checked is not None:
        _cache[key] = out
    return out

@router.get("/checks")
def checks(user: dict = Depends(MANAGER)):
    with store.conn() as c:
        return facts.checks(c)

@router.get("/events")
def events(after: int = 0, user: dict = Depends(MANAGER)):
    with store.conn() as c:
        return facts.events(c, after)

@router.get("/report")
def report(user: dict = Depends(MANAGER)):
    with store.conn() as c:
        return facts.report(c)

@router.get("/peak")
def peak(user: dict = Depends(DESK)):
    with store.conn() as c:
        return facts.peak(c)

@router.get("/grid")
def grid(d: str | None = None, days: int = 14, user: dict = Depends(DESK)):
    start = _iso(d, "تاریخ") if d else store.today().isoformat()
    with store.conn() as c:
        return facts.grid(c, start, max(7, min(days, 21)))

# ---------- quotes and new bookings ----------

class QuoteIn(BaseModel):
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)
    adults: int = Field(2, ge=1, le=12)
    ages: list[int] = Field([], max_length=6)
    board: str = "BB"
    discount: float = Field(0, ge=0, le=100)
    agency_id: int | None = None

def _discount(c, req, user):
    if req.agency_id:
        a = c.execute("SELECT discount FROM agencies WHERE id = ?", (req.agency_id,)).fetchone()
        if not a:
            raise HTTPException(status_code=422, detail="آژانس را از فهرست انتخاب کنید")
        return a["discount"]
    return req.discount

@router.post("/quote")
def quote(req: QuoteIn, user: dict = Depends(DESK)):
    """Every room type for these dates: how many are left on the fullest night, and the price, night by night."""
    if req.board not in facts.BOARDS:
        raise HTTPException(status_code=422, detail="نوع پذیرایی را انتخاب کنید")
    a, d = _stay(req.arrive, req.depart)
    with store.conn() as c:
        disc = _discount(c, req, user)
        av = facts.availability(c, a, d)
        out = []
        for t, (name, beds, most) in facts.TYPES.items():
            q = facts.quote(c, t, a, d, req.adults, req.ages, req.board, disc)
            out.append({"type": t, "name": name, "free": av[t]["free"], "rooms": av[t]["rooms"], "tight": facts.jlong(av[t]["tight"]) if av[t]["tight"] else ""} | q)
        waiting = c.execute("SELECT COUNT(*) FROM waitlist WHERE status = 'waiting' AND arrive < ? AND depart > ?", (d, a)).fetchone()[0]
    return {"stay": facts.stay_text({"arrive": a, "depart": d}), "options": out, "discount": disc, "waiting": waiting}

class ReadIn(BaseModel):
    text: str = Field(min_length=5, max_length=3000)

def _guest_card(c, g):
    stays = [facts.booking_view(c, b) for b in c.execute("SELECT * FROM bookings WHERE guest_id = ? ORDER BY arrive DESC LIMIT 8", (g["id"],))]
    spent = c.execute("""SELECT COALESCE(SUM(ch.amount), 0) FROM charges ch JOIN bookings b ON b.id = ch.booking_id WHERE b.guest_id = ?""", (g["id"],)).fetchone()[0]
    return dict(g) | {"stays": stays, "visits": sum(1 for s in stays if s["status"] == "out"), "noshows": sum(1 for s in stays if s["status"] == "noshow"),
                      "spent_text": facts.money(spent)}

@router.post("/read")
def read_text(req: ReadIn, user: dict = Depends(DESK)):
    out = reader.read(req.text)
    with store.conn() as c:
        g = c.execute("SELECT * FROM guests WHERE phone = ? ORDER BY id DESC LIMIT 1", (out["fields"]["phone"],)).fetchone() if out["fields"]["phone"] else None
        out["guest"] = _guest_card(c, g) if g else None
    return out

@router.get("/guests")
def guests(q: str = "", user: dict = Depends(DESK)):
    q = q.strip().translate(reader.FA_DIGITS)
    if len(q) < 2:
        return []
    with store.conn() as c:
        return [_guest_card(c, g) for g in c.execute("SELECT * FROM guests WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC LIMIT 12", (f"%{q}%", f"%{q}%"))]

class BookIn(QuoteIn):
    type: str
    guest_id: int | None = None
    name: str = Field("", max_length=60)
    phone: str = Field("", max_length=20)
    source: str = "phone"
    status: str = "tentative"                 # tentative (waits for its deposit) or confirmed (paid now)
    paid: int = Field(0, ge=0, le=5_000_000_000)
    method: str = "card"
    eta: str = Field("14:00", pattern=r"^\d{2}:\d{2}$")
    requests: str = Field("", max_length=300)
    room_id: int | None = None
    over: bool = False                        # the manager sells beyond the rooms on purpose

def new_guest(c, name, phone):
    phone = re.sub(r"\D", "", (phone or "").translate(reader.FA_DIGITS))
    if not re.fullmatch(r"09\d{9}", phone):
        raise HTTPException(status_code=422, detail="شماره‌ی همراه باید ۱۱ رقم و با ۰۹ شروع شود")
    g = c.execute("SELECT id FROM guests WHERE phone = ? ORDER BY id DESC LIMIT 1", (phone,)).fetchone()
    if g:
        return g["id"]
    name = " ".join((name or "").split())
    if len(name) < 3:
        raise HTTPException(status_code=422, detail="نام مهمان را بنویسید")
    return c.execute("INSERT INTO guests (name, phone, vip, notes, created) VALUES (?,?,0,'',?)", (name, phone, store.today().isoformat())).lastrowid

def make_booking(c, req: BookIn, user, source=None):
    """A booking checked against the rooms left: tentative ones wait for their deposit 24 hours (or until the day
    before arrival); a discount over the limit needs the manager."""
    if req.type not in facts.TYPES or req.board not in facts.BOARDS or (source or req.source) not in facts.SOURCES:
        raise HTTPException(status_code=422, detail="نوع اتاق، پذیرایی و راه رزرو را انتخاب کنید")
    if req.status not in ("tentative", "confirmed"):
        raise HTTPException(status_code=422, detail="وضعیت رزرو درست نیست")
    a, d = _stay(req.arrive, req.depart)
    if a < store.today().isoformat():
        raise HTTPException(status_code=422, detail="تاریخ ورود گذشته است")
    s = facts.settings(c)
    disc = _discount(c, req, user) if user else 0
    if not req.agency_id and disc > s["max_discount"] and (not user or user["role"] != "manager"):
        raise HTTPException(status_code=403, detail=f"تخفیف بیش از {s['max_discount']} درصد را فقط مدیر ثبت می‌کند")
    q = facts.quote(c, req.type, a, d, req.adults, req.ages, req.board, disc)
    if not q["fits"]:
        raise HTTPException(status_code=422, detail=q["why"])
    if facts.availability(c, a, d)[req.type]["free"] < 1 and not (req.over and user and user["role"] == "manager"):
        raise HTTPException(status_code=409, detail=f"{facts.type_name(req.type)} برای همه‌ی این شب‌ها جا ندارد")
    if req.room_id and not facts.room_free(c, _room(c, req.room_id), a, d):
        raise HTTPException(status_code=409, detail="این اتاق در این شب‌ها آزاد نیست")
    gid = req.guest_id or new_guest(c, req.name, req.phone)
    status = "confirmed" if req.paid >= q["deposit"] and req.paid > 0 else req.status
    if status == "confirmed" and req.paid < q["deposit"]:
        raise HTTPException(status_code=422, detail=f"برای رزرو قطعی، دست‌کم بیعانه‌ی {q['deposit']:,} تومان را ثبت کنید")
    due = None
    if status == "tentative":
        tomorrow = facts.add(store.today().isoformat(), 1)
        due = f"{min(tomorrow, facts.add(a, -1)) if a > store.today().isoformat() else store.today().isoformat()} {store.now_time() if a > tomorrow else '23:59'}"
    bid = c.execute("""INSERT INTO bookings (guest_id, room_id, type, arrive, depart, adults, children, board, source, agency_id, status, deposit_due,
                       nights, total, discount, eta, requests, created, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (gid, req.room_id, req.type, a, d, req.adults, ",".join(str(x) for x in req.ages), req.board, source or req.source, req.agency_id,
                     status, due, json.dumps(q["nights"]), q["total"], disc, req.eta, req.requests.strip(), store.stamp(), user["id"] if user else None)).lastrowid
    if req.paid:
        if req.method not in facts.METHODS:
            raise HTTPException(status_code=422, detail="روش پرداخت را انتخاب کنید")
        c.execute("INSERT INTO payments (booking_id, at, amount, method, kind, user_id) VALUES (?,?,?,?, 'deposit', ?)", (bid, store.stamp(), req.paid, req.method, user["id"] if user else None))
    store.log(c, user, "book", f"رزرو {facts.STATUS[status]} {facts.type_name(req.type)}، {facts.stay_text({'arrive': a, 'depart': d})}، {q['total_text']}", bid)
    return bid

@router.post("/bookings")
def add_booking(req: BookIn, user: dict = Depends(DESK)):
    with store.conn() as c:
        bid = make_booking(c, req, user)
        return facts.booking_view(c, _booking(c, bid))

@router.get("/bookings")
def bookings(q: str = "", when: str = "upcoming", user: dict = Depends(DESK)):
    t = store.today().isoformat()
    cond = {"upcoming": ("status IN ('tentative', 'confirmed') AND arrive >= ?", (t,)), "house": ("status = 'in_house'", ()),
            "tentative": ("status = 'tentative'", ()), "past": ("depart < ?", (t,))}.get(when, ("1", ()))
    q = q.strip().translate(reader.FA_DIGITS)
    sql = f"SELECT b.* FROM bookings b LEFT JOIN guests g ON g.id = b.guest_id WHERE {cond[0]}"
    args = list(cond[1])
    if q:
        sql += " AND (g.name LIKE ? OR g.phone LIKE ? OR b.ref LIKE ? OR CAST(b.id AS TEXT) = ?)"
        args += [f"%{q}%", f"%{q}%", f"%{q}%", q]
    sql += " ORDER BY b.arrive" + (" DESC" if when == "past" else "") + " LIMIT 80"
    with store.conn() as c:
        return [facts.booking_view(c, b) | {"balance": facts.balance(c, b["id"])} for b in c.execute(sql, args)]

@router.get("/bookings/{bid}")
def booking(bid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        b = _booking(c, bid)
        v = facts.booking_view(c, b)
        out = {"booking": v, "folio": facts.folio(c, bid), "history": facts.events(c, 0, 60, bid),
               "tasks": [dict(k) for k in c.execute("SELECT * FROM tasks WHERE booking_id = ? ORDER BY created DESC", (bid,))],
               "price_how": facts.quote(c, b["type"], b["arrive"], b["depart"], b["adults"], v["ages"], b["board"], b["discount"] or 0).get("how", [])}
        if b["status"] in facts.ACTIVE:
            out["suggest"] = [x for x in facts.suggest_rooms(c, b["type"], b["arrive"], b["depart"], b["guest_id"], ignore=bid, limit=4) if x["room_id"] != b["room_id"]][:3]
            out["refund"] = facts.refund(c, b)
        if b["guest_id"]:
            g = c.execute("SELECT * FROM guests WHERE id = ?", (b["guest_id"],)).fetchone()
            out["guest"] = _guest_card(c, g)
        return out

class RoomIn(BaseModel):
    room_id: int

@router.post("/bookings/{bid}/room")
def give_room(bid: int, req: RoomIn, user: dict = Depends(DESK)):
    with store.conn() as c:
        b, r = _booking(c, bid), _room(c, req.room_id)
        if b["status"] not in facts.ACTIVE:
            raise HTTPException(status_code=409, detail="این رزرو دیگر فعال نیست")
        start = max(b["arrive"], store.today().isoformat()) if b["status"] == "in_house" else b["arrive"]
        if not facts.room_free(c, r, start, b["depart"], ignore=bid):
            raise HTTPException(status_code=409, detail=f"اتاق {r['number']} در این شب‌ها آزاد نیست")
        old = c.execute("SELECT number FROM rooms WHERE id = ?", (b["room_id"],)).fetchone() if b["room_id"] else None
        c.execute("UPDATE bookings SET room_id = ?, type = ? WHERE id = ?", (r["id"], r["type"], bid))   # an upgrade takes a room of the other type; the price stays
        if b["status"] == "in_house" and old:
            _set_status(c, user, b["room_id"], "dirty")
        upgrade = r["type"] != b["type"]
        store.log(c, user, "room", (f"از اتاق {old['number']} به " if old else "") + f"اتاق {r['number']}" + (" (ارتقا، با همان قیمت)" if upgrade else ""), bid)
    return {"ok": True, "upgrade": upgrade}

@router.post("/assign/tomorrow")
def assign_tomorrow(user: dict = Depends(DESK)):
    """Gives tomorrow's arrivals without a room the room the assistant suggests, one by one (each suggestion is worked
    out again after the one before has taken its room)."""
    done = []
    with store.conn() as c:
        for b in c.execute("SELECT * FROM bookings WHERE arrive = ? AND status IN ('confirmed', 'tentative') AND room_id IS NULL ORDER BY id",
                           (facts.add(store.today().isoformat(), 1),)).fetchall():
            s = facts.suggest_rooms(c, b["type"], b["arrive"], b["depart"], b["guest_id"], ignore=b["id"], limit=1)
            if s:
                c.execute("UPDATE bookings SET room_id = ? WHERE id = ?", (s[0]["room_id"], b["id"]))
                store.log(c, user, "room", f"اتاق {s[0]['number']} برای ورود فردا ({s[0]['why'][0]})", b["id"])
                done.append(s[0]["number"])
    return {"assigned": done}

class CheckIn(BaseModel):
    national_id: str = Field("", max_length=12)
    plate: str = Field("", max_length=20)
    docs: bool = False
    force: bool = False                       # the room is not ready, the desk gives it anyway (seen in the checks)

@router.post("/bookings/{bid}/checkin")
def checkin(bid: int, req: CheckIn, user: dict = Depends(FRONT)):
    with store.conn() as c:
        b = _booking(c, bid)
        t = store.today().isoformat()
        if b["status"] not in ("confirmed", "tentative") or b["arrive"] > t:
            raise HTTPException(status_code=409, detail="این رزرو امروز ورود ندارد")
        if b["status"] == "tentative":
            raise HTTPException(status_code=409, detail="بیعانه‌ی این رزرو هنوز ثبت نشده است")
        if not b["room_id"]:
            raise HTTPException(status_code=409, detail="اول اتاق را انتخاب کنید")
        nid = re.sub(r"\D", "", req.national_id.translate(reader.FA_DIGITS))
        if len(nid) != 10:
            raise HTTPException(status_code=422, detail="کد ملی ۱۰ رقم است")
        r = _room(c, b["room_id"])
        if r["status"] == "dirty" and not req.force:
            raise HTTPException(status_code=409, detail=f"اتاق {r['number']} هنوز تمیز نشده است")
        busy = c.execute("SELECT 1 FROM bookings WHERE room_id = ? AND status = 'in_house' AND id != ?", (r["id"], bid)).fetchone()
        if busy:
            raise HTTPException(status_code=409, detail=f"مهمان قبلی اتاق {r['number']} هنوز تسویه نکرده است")
        c.execute("UPDATE bookings SET status = 'in_house', checked_in = ?, plate = ?, docs = ? WHERE id = ?", (store.stamp(), req.plate.strip(), int(req.docs), bid))
        c.execute("UPDATE guests SET national_id = ? WHERE id = ?", (nid, b["guest_id"]))
        store.log(c, user, "checkin", f"تحویل اتاق {r['number']}" + (" (اتاق هنوز کثیف بود)" if r["status"] == "dirty" else ""), bid)
    return {"ok": True}

@router.post("/bookings/{bid}/checkout")
def checkout(bid: int, user: dict = Depends(FRONT)):
    with store.conn() as c:
        b = _booking(c, bid)
        if b["status"] != "in_house":
            raise HTTPException(status_code=409, detail="این مهمان مقیم نیست")
        t = store.today().isoformat()
        for n in json.loads(b["nights"] or "[]"):             # nights not yet posted (leaving early posts nothing more)
            if n["date"] < t and not c.execute("SELECT 1 FROM charges WHERE booking_id = ? AND kind = 'room' AND day = ?", (bid, n["date"])).fetchone():
                c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?, 'room', ?, 'شب اقامت', ?)",
                          (bid, n["date"], store.stamp(), n["amount"], user["id"]))
        bal = facts.balance(c, bid)
        if bal > 0:
            raise HTTPException(status_code=409, detail=f"{facts.money(bal)} از صورت‌حساب مانده است")
        c.execute("UPDATE bookings SET status = 'out', checked_out = ?, depart = CASE WHEN depart > ? THEN ? ELSE depart END WHERE id = ?",
                  (store.stamp(), t, t, bid))
        _set_status(c, user, b["room_id"], "dirty")
        store.log(c, user, "checkout", "تسویه و خروج" + (f"؛ {facts.money(-bal)} بستانکار ماند" if bal < 0 else ""), bid)
    return {"ok": True, "credit": -bal}

class ChargeIn(BaseModel):
    kind: str
    amount: int = Field(gt=0, le=500_000_000)
    note: str = Field("", max_length=120)

@router.post("/bookings/{bid}/charge")
def charge(bid: int, req: ChargeIn, user: dict = Depends(DESK)):
    if req.kind not in facts.CHARGES or req.kind == "room":
        raise HTTPException(status_code=422, detail="نوع هزینه را انتخاب کنید")
    with store.conn() as c:
        b = _booking(c, bid)
        if b["status"] != "in_house":
            raise HTTPException(status_code=409, detail="هزینه فقط روی صورت‌حساب مهمان مقیم ثبت می‌شود")
        c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?,?,?,?,?)",
                  (bid, store.today().isoformat(), store.stamp(), req.kind, req.amount, req.note.strip(), user["id"]))
        store.log(c, user, "charge", f"{facts.CHARGES[req.kind]}: {facts.money(req.amount)}", bid)
        return facts.folio(c, bid)

class PayIn(BaseModel):
    amount: int = Field(gt=0, le=5_000_000_000)
    method: str

@router.post("/bookings/{bid}/pay")
def pay(bid: int, req: PayIn, user: dict = Depends(DESK)):
    if req.method not in facts.METHODS:
        raise HTTPException(status_code=422, detail="روش پرداخت را انتخاب کنید")
    with store.conn() as c:
        b = _booking(c, bid)
        if b["status"] in ("cancelled", "noshow"):
            raise HTTPException(status_code=409, detail="این رزرو بسته شده است")
        c.execute("INSERT INTO payments (booking_id, at, amount, method, kind, user_id) VALUES (?,?,?,?, 'payment', ?)",
                  (bid, store.stamp(), req.amount, req.method, user["id"]))
        msg = f"پرداخت {facts.money(req.amount)} ({facts.METHODS[req.method]})"
        if b["status"] == "tentative" and facts.paid(c, bid) >= facts.quote(c, b["type"], b["arrive"], b["depart"], b["adults"], [], b["board"], b["discount"] or 0).get("deposit", 0):
            c.execute("UPDATE bookings SET status = 'confirmed', deposit_due = NULL WHERE id = ?", (bid,))
            msg += "؛ رزرو قطعی شد"
        store.log(c, user, "pay", msg, bid)
        return facts.folio(c, bid) | {"status": c.execute("SELECT status FROM bookings WHERE id = ?", (bid,)).fetchone()[0]}

@router.post("/bookings/{bid}/cancel")
def cancel(bid: int, user: dict = Depends(DESK)):
    """Cancelled by the hotel's rule: what goes back depends on how many days are left (facts.refund)."""
    with store.conn() as c:
        b = _booking(c, bid)
        if b["status"] not in ("tentative", "confirmed"):
            raise HTTPException(status_code=409, detail="فقط رزروی که هنوز شروع نشده لغو می‌شود")
        r = facts.refund(c, b)
        c.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (bid,))
        if r["amount"]:
            c.execute("INSERT INTO payments (booking_id, at, amount, method, kind, user_id) VALUES (?,?,?, 'transfer', 'refund', ?)", (bid, store.stamp(), -r["amount"], user["id"]))
        store.log(c, user, "cancel", "رزرو لغو شد" + (f"؛ {facts.money(r['amount'])} برگشت داده می‌شود" if r["amount"] else ""), bid)
    return r

@router.post("/bookings/{bid}/noshow")
def noshow(bid: int, user: dict = Depends(FRONT)):
    with store.conn() as c:
        b = _booking(c, bid)
        if b["status"] not in ("tentative", "confirmed") or b["arrive"] > store.today().isoformat():
            raise HTTPException(status_code=409, detail="این رزرو هنوز روز ورودش نرسیده است")
        c.execute("UPDATE bookings SET status = 'noshow' WHERE id = ?", (bid,))
        first = json.loads(b["nights"] or "[]")[:1]
        kept = min(first[0]["amount"], facts.paid(c, bid)) if first else 0
        if kept:
            c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?, 'other', ?, 'جریمه‌ی نیامدن (شب اول)', ?)",
                      (bid, b["arrive"], store.stamp(), kept, user["id"]))
        store.log(c, user, "noshow", "مهمان نیامد" + (f"؛ {facts.money(kept)} جریمه از بیعانه" if kept else ""), bid)
    return {"ok": True, "kept": kept}

class DatesIn(BaseModel):
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)

@router.post("/bookings/{bid}/dates")
def change_dates(bid: int, req: DatesIn, user: dict = Depends(DESK)):
    """A longer or shorter stay, priced again night by night; nights already posted stay as they are."""
    with store.conn() as c:
        b = _booking(c, bid)
        if b["status"] not in facts.ACTIVE:
            raise HTTPException(status_code=409, detail="این رزرو دیگر فعال نیست")
        a, d = _stay(req.arrive, req.depart)
        if b["status"] == "in_house":
            a = b["arrive"]
            if d <= store.today().isoformat():
                raise HTTPException(status_code=422, detail="برای خروج امروز «تسویه و خروج» را بزنید")
        ages = [int(x) for x in (b["children"] or "").split(",") if x]
        if facts.availability(c, a, d, ignore=bid)[b["type"]]["free"] < 1:
            raise HTTPException(status_code=409, detail=f"{facts.type_name(b['type'])} برای همه‌ی این شب‌ها جا ندارد")
        if b["room_id"] and not facts.room_free(c, _room(c, b["room_id"]), max(a, store.today().isoformat()), d, ignore=bid):
            raise HTTPException(status_code=409, detail="اتاق فعلی در این شب‌ها آزاد نیست؛ اول اتاق را عوض کنید")
        q = facts.quote(c, b["type"], a, d, b["adults"], ages, b["board"], b["discount"] or 0)
        c.execute("UPDATE bookings SET arrive = ?, depart = ?, nights = ?, total = ? WHERE id = ?", (a, d, json.dumps(q["nights"]), q["total"], bid))
        store.log(c, user, "dates", f"تاریخ‌ها: {facts.stay_text({'arrive': a, 'depart': d})}، جمع جدید {q['total_text']}", bid)
        return facts.booking_view(c, _booking(c, bid)) | {"how": q["how"]}

@router.get("/bookings/{bid}/message")
def message(bid: int, kind: str = "confirm", user: dict = Depends(DESK)):
    """The confirmation (or the thank-you after leaving), written by code from the booking itself."""
    s = info.current()
    with store.conn() as c:
        v = facts.booking_view(c, _booking(c, bid))
        got = facts.paid(c, bid)
        dep = facts.quote(c, v["type"], v["arrive"], v["depart"], v["adults"], v["ages"], v["board"], v["discount"] or 0).get("deposit", 0)
    sign = f"{info.person('reservation', s)}، {s['name']}"
    if kind == "thanks":
        text = (f"{v['guest']} گرامی، سلام. از این‌که {s['name']} را برای اقامت انتخاب کردید سپاسگزاریم. اگر از اقامتتان نکته‌ای دارید، "
                f"خوشحال می‌شویم با پاسخ به همین پیام آن را بنویسید.\n{sign}")
    else:
        lines = [f"{v['guest']} گرامی، سلام. رزرو شما در {s['name']} {'ثبت شد' if v['status'] == 'tentative' else 'قطعی است'}:",
                 f"شماره‌ی رزرو: {v['id']}", f"{v['type_text']}، {v['people_text']}، {v['board_text']}",
                 f"ورود: {v['arrive_text']} از ساعت {facts.CHECK_IN} · خروج: {v['depart_text']} تا ساعت {facts.CHECK_OUT}",
                 f"مبلغ کل: {v['total_text']}" + (f" · پرداخت‌شده: {facts.money(got)} · مانده: {facts.money(v['total'] - got)}" if got else "")]
        if v["status"] == "tentative":
            lines.append(f"برای قطعی شدن رزرو، بیعانه‌ی {facts.money(dep)} را تا {v['deposit_due_text']} پرداخت کنید؛ پس از آن، رزرو آزاد می‌شود.")
        lines += ["هنگام ورود کارت ملی همه‌ی بزرگسالان لازم است.", sign]
        text = "\n".join(lines)
    return {"text": text, "phone": v["phone"]}

# ---------- rooms, housekeeping, requests ----------

@router.get("/rooms")
def room_list(user: dict = Depends(ALL)):
    """Every room with its state, who is in it, who leaves or arrives today, and open requests. Housekeeping's list:
    departures first (a guest is waiting for them), then rooms with a guest arriving, then stayovers."""
    t = store.today().isoformat()
    with store.conn() as c:
        out = []
        who = {g["id"]: g["name"] for g in c.execute("SELECT id, name FROM guests")}
        for r in facts.rooms(c).values():
            stay = c.execute("SELECT * FROM bookings WHERE room_id = ? AND status = 'in_house'", (r["id"],)).fetchone()
            arr = c.execute("SELECT * FROM bookings WHERE room_id = ? AND arrive = ? AND status IN ('confirmed', 'tentative')", (r["id"], t)).fetchone()
            tasks = [dict(k) for k in c.execute("SELECT * FROM tasks WHERE room_id = ? AND status = 'open' ORDER BY created", (r["id"],))]
            ooo = facts.ooo_on(r, t)
            leaving = bool(stay and stay["depart"] <= t)
            prio = 0 if (leaving or (arr and not stay)) and r["status"] == "dirty" and arr else 1 if leaving else 2 if arr else 3 if stay else 4
            out.append(r | {"status_text": facts.ROOM_STATUS[r["status"]], "type_text": facts.type_name(r["type"]), "ooo": ooo,
                            "guest": who.get(stay["guest_id"], "") if stay else "", "leaving": leaving, "booking_id": stay["id"] if stay else None,
                            "arriving": (who.get(arr["guest_id"], "") + f"، ساعت {arr['eta'] or facts.CHECK_IN}") if arr else "", "arrive_id": arr["id"] if arr else None,
                            "vip": bool(arr and c.execute("SELECT vip FROM guests WHERE id = ?", (arr["guest_id"],)).fetchone()[0]),
                            "tasks": tasks, "priority": prio, "ooo_to_text": facts.jfull(r["ooo_to"]) if r["ooo_to"] else ""})
        return sorted(out, key=lambda r: (r["priority"], not r["vip"], r["number"]))

class StatusIn(BaseModel):
    status: str

@router.post("/rooms/{rid}/status")
def room_status(rid: int, req: StatusIn, user: dict = Depends(ROOMS)):
    if req.status not in facts.ROOM_STATUS:
        raise HTTPException(status_code=422, detail="وضعیت درست نیست")
    if req.status == "inspected" and user["role"] not in ("housekeeping", "manager"):
        raise HTTPException(status_code=403, detail="بازرسی را سرپرست خانه‌داری ثبت می‌کند")
    with store.conn() as c:
        r = _room(c, rid)
        _set_status(c, user, rid, req.status)
        store.log(c, user, "room", f"اتاق {r['number']}: {facts.ROOM_STATUS[req.status]}")
    return {"ok": True}

class OooIn(BaseModel):
    until: str | None = Field(None, max_length=12)      # Jalali; empty = the repair is done
    note: str = Field("", max_length=120)

@router.post("/rooms/{rid}/ooo")
def room_ooo(rid: int, req: OooIn, user: dict = Depends(ROOMS)):
    with store.conn() as c:
        r = _room(c, rid)
        if req.until:
            to = _iso(req.until, "تاریخ پایان تعمیر")
            c.execute("UPDATE rooms SET ooo_from = ?, ooo_to = ?, ooo_note = ? WHERE id = ?", (store.today().isoformat(), to, req.note.strip() or "تعمیر", rid))
            store.log(c, user, "ooo", f"اتاق {r['number']} تا {facts.jfull(to)} از فروش بیرون رفت: {req.note.strip() or 'تعمیر'}")
        else:
            c.execute("UPDATE rooms SET ooo_from = NULL, ooo_to = NULL, ooo_note = NULL WHERE id = ?", (rid,))
            store.log(c, user, "ooo", f"تعمیر اتاق {r['number']} تمام شد و دوباره فروختنی است")
    return {"ok": True}

class TaskIn(BaseModel):
    room_id: int
    kind: str = "request"
    text: str = Field(min_length=2, max_length=200)

@router.post("/tasks")
def add_task(req: TaskIn, user: dict = Depends(ALL)):
    if req.kind not in ("request", "repair"):
        raise HTTPException(status_code=422, detail="نوع کار درست نیست")
    with store.conn() as c:
        r = _room(c, req.room_id)
        stay = c.execute("SELECT id FROM bookings WHERE room_id = ? AND status = 'in_house'", (r["id"],)).fetchone()
        tid = c.execute("INSERT INTO tasks (room_id, booking_id, kind, text, created, status) VALUES (?,?,?,?,?, 'open')",
                        (r["id"], stay["id"] if stay else None, req.kind, req.text.strip(), store.stamp())).lastrowid
        store.log(c, user, "task", f"اتاق {r['number']}: {req.text.strip()}", stay["id"] if stay else None)
    return {"id": tid}

@router.post("/tasks/{tid}/done")
def task_done(tid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        k = c.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
        if not k:
            raise HTTPException(status_code=404)
        c.execute("UPDATE tasks SET status = 'done', done_at = ?, done_by = ? WHERE id = ?", (store.stamp(), user["id"], tid))
        store.log(c, user, "task", f"انجام شد: {k['text']}", k["booking_id"])
    return {"ok": True}

@router.get("/tasks")
def tasks(user: dict = Depends(ALL)):
    with store.conn() as c:
        rm = facts.rooms(c)
        return [dict(k) | {"room": rm.get(k["room_id"], {}).get("number", ""), "time": k["created"][11:16], "day": facts.day_word(k["created"])}
                for k in c.execute("SELECT * FROM tasks WHERE status = 'open' ORDER BY created")]

# ---------- agencies, allotments, the waiting list ----------

@router.get("/agencies")
def agencies(user: dict = Depends(DESK)):
    t = store.today().isoformat()
    with store.conn() as c:
        out = []
        for a in c.execute("SELECT * FROM agencies ORDER BY kind, id"):
            stays = c.execute("""SELECT COUNT(*) n, COALESCE(SUM(total), 0) s FROM bookings WHERE agency_id = ? AND status IN ('confirmed', 'in_house', 'out')
                                 AND arrive >= ?""", (a["id"], facts.add(t, -30))).fetchone()
            blocks = []
            for al in c.execute("SELECT * FROM allotments WHERE agency_id = ? AND depart > ? ORDER BY arrive", (a["id"], t)):
                named = c.execute("""SELECT COUNT(*) FROM bookings b JOIN groups g ON g.id = b.group_id WHERE g.allotment_id = ? AND b.status IN ('tentative', 'confirmed')""",
                                  (al["id"],)).fetchone()[0]
                blocks.append(dict(al) | {"type_text": facts.type_name(al["type"]), "named": named, "stay": facts.stay_text(al), "release_text": facts.day_word(al["release"])})
            out.append(dict(a) | {"kind_text": {"agency": "آژانس", "ota": "سایت رزرو", "company": "شرکت"}[a["kind"]], "stays": stays["n"], "amount_text": facts.money(stays["s"]),
                                  "blocks": blocks})
        return out

class NamesIn(BaseModel):
    text: str = Field(min_length=3, max_length=3000)

@router.post("/allotments/{aid}/names")
def allotment_names(aid: int, req: NamesIn, user: dict = Depends(DESK)):
    """An agency's list of guests, one per line («نام، شماره‌ی همراه»): each line becomes a booking in the block,
    up to the rooms left in it."""
    with store.conn() as c:
        al = c.execute("SELECT * FROM allotments WHERE id = ?", (aid,)).fetchone()
        if not al:
            raise HTTPException(status_code=404)
        grp = c.execute("SELECT id FROM groups WHERE allotment_id = ?", (aid,)).fetchone()
        named = c.execute("SELECT COUNT(*) FROM bookings WHERE group_id = ? AND status IN ('tentative', 'confirmed')", (grp["id"],)).fetchone()[0]
        left, made, skipped = al["rooms"] - named, [], []
        for line in [l.strip() for l in req.text.translate(reader.FA_DIGITS).splitlines() if l.strip()]:
            phone = re.search(r"09\d{9}", re.sub(r"[\s\-]", "", line))
            name = " ".join(re.sub(r"[\d\-،,:.]+", " ", line).split())
            if not phone or len(name) < 3 or len(made) >= left:
                skipped.append(line)
                continue
            gid = new_guest(c, name, phone[0])
            q = facts.quote(c, al["type"], al["arrive"], al["depart"], facts.TYPES[al["type"]][1], [], "BB",
                            c.execute("SELECT discount FROM agencies WHERE id = ?", (al["agency_id"],)).fetchone()[0])
            bid = c.execute("""INSERT INTO bookings (guest_id, type, arrive, depart, adults, children, board, source, agency_id, group_id, status, nights, total, discount, eta, created, created_by)
                               VALUES (?,?,?,?,?, '', 'BB', 'agency', ?, ?, 'confirmed', ?, ?, ?, '14:00', ?, ?)""",
                            (gid, al["type"], al["arrive"], al["depart"], facts.TYPES[al["type"]][1], al["agency_id"], grp["id"], json.dumps(q["nights"]), q["total"],
                             c.execute("SELECT discount FROM agencies WHERE id = ?", (al["agency_id"],)).fetchone()[0], store.stamp(), user["id"])).lastrowid
            store.log(c, user, "book", f"از فهرست آژانس: {name}", bid)
            made.append(name)
    return {"made": made, "skipped": skipped}

@router.get("/waitlist")
def waitlist(user: dict = Depends(DESK)):
    with store.conn() as c:
        out = []
        for w in c.execute("SELECT * FROM waitlist WHERE status = 'waiting' AND depart > ? ORDER BY arrive", (store.today().isoformat(),)):
            g = c.execute("SELECT name, phone FROM guests WHERE id = ?", (w["guest_id"],)).fetchone()
            free = facts.availability(c, w["arrive"], w["depart"])[w["type"]]["free"]
            out.append(dict(w) | {"guest": g["name"], "phone": g["phone"], "type_text": facts.type_name(w["type"]), "stay": facts.stay_text(w), "free": free})
        return out

class WaitIn(BaseModel):
    name: str = Field("", max_length=60)
    phone: str = Field(max_length=20)
    type: str
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)
    adults: int = Field(2, ge=1, le=12)
    note: str = Field("", max_length=200)

@router.post("/waitlist")
def add_wait(req: WaitIn, user: dict = Depends(DESK)):
    if req.type not in facts.TYPES:
        raise HTTPException(status_code=422, detail="نوع اتاق را انتخاب کنید")
    a, d = _stay(req.arrive, req.depart)
    with store.conn() as c:
        gid = new_guest(c, req.name, req.phone)
        wid = c.execute("INSERT INTO waitlist (guest_id, type, arrive, depart, adults, note, added, status) VALUES (?,?,?,?,?,?,?, 'waiting')",
                        (gid, req.type, a, d, req.adults, req.note.strip(), store.today().isoformat())).lastrowid
        store.log(c, user, "wait", f"فهرست انتظار: {facts.type_name(req.type)}، {facts.stay_text({'arrive': a, 'depart': d})}")
    return {"id": wid}

@router.post("/waitlist/{wid}/done")
def wait_done(wid: int, user: dict = Depends(DESK)):
    with store.conn() as c:
        c.execute("UPDATE waitlist SET status = 'done' WHERE id = ?", (wid,))
    return {"ok": True}

# ---------- guests' registration, closing the day ----------

@router.get("/police")
def police(user: dict = Depends(FRONT)):
    """Today's check-ins with what the police's guest registration asks for, to copy into it (it is on the internet;
    the program does not send it)."""
    t = store.today().isoformat()
    with store.conn() as c:
        rows = []
        for b in c.execute("SELECT * FROM bookings WHERE status IN ('in_house', 'out') AND substr(checked_in, 1, 10) = ? ORDER BY checked_in", (t,)):
            v = facts.booking_view(c, b)
            g = c.execute("SELECT national_id FROM guests WHERE id = ?", (b["guest_id"],)).fetchone()
            rows.append({"id": v["id"], "guest": v["guest"], "national_id": g["national_id"] if g else "", "room": v["room"], "people": v["people_text"],
                         "arrive": facts.jfull(v["arrive"]), "depart": facts.jfull(v["depart"]), "plate": v["plate"] or "", "docs": bool(v["docs"]), "time": v["checked_in"][11:16]})
        return rows

@router.get("/close")
def close_status(user: dict = Depends(FRONT)):
    t = store.today().isoformat()
    with store.conn() as c:
        done = c.execute("SELECT * FROM closes WHERE day = ?", (t,)).fetchone()
        house = c.execute("SELECT * FROM bookings WHERE status = 'in_house' AND arrive <= ? AND depart > ?", (t, t)).fetchall()
        to_post = sum(n["amount"] for b in house for n in json.loads(b["nights"] or "[]") if n["date"] == t)
        cash = c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE method = 'cash' AND substr(at, 1, 10) = ?", (t,)).fetchone()[0]
        last = c.execute("SELECT * FROM closes ORDER BY day DESC LIMIT 1").fetchone()
        return {"done": dict(done) if done else None, "rooms": len(house), "to_post": to_post, "to_post_text": facts.money(to_post), "cash": cash,
                "cash_text": facts.money(cash), "last": facts.jlong(last["day"]) if last else ""}

class CloseIn(BaseModel):
    cash_counted: int = Field(ge=0, le=10_000_000_000)
    note: str = Field("", max_length=200)

@router.post("/close")
def close_day(req: CloseIn, user: dict = Depends(FRONT)):
    """Closing the day: tonight's price goes on the folio of every room in the house, and the cash counted is set
    beside the cash payments of the day. A difference is kept and shown in the manager's checks."""
    t = store.today().isoformat()
    with store.conn() as c:
        if c.execute("SELECT 1 FROM closes WHERE day = ?", (t,)).fetchone():
            raise HTTPException(status_code=409, detail="امروز قبلاً بسته شده است")
        posted = 0
        for b in c.execute("SELECT * FROM bookings WHERE status = 'in_house' AND arrive <= ? AND depart > ?", (t, t)).fetchall():
            n = next((x for x in json.loads(b["nights"] or "[]") if x["date"] == t), None)
            if n and not c.execute("SELECT 1 FROM charges WHERE booking_id = ? AND kind = 'room' AND day = ?", (b["id"], t)).fetchone():
                c.execute("INSERT INTO charges (booking_id, day, at, kind, amount, note, user_id) VALUES (?,?,?, 'room', ?, 'شب اقامت', ?)",
                          (b["id"], t, store.stamp(), n["amount"], user["id"]))
                posted += 1
        cash = c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE method = 'cash' AND substr(at, 1, 10) = ?", (t,)).fetchone()[0]
        c.execute("INSERT INTO closes (day, at, user_id, posted, cash_expected, cash_counted, note) VALUES (?,?,?,?,?,?,?)",
                  (t, store.stamp(), user["id"], posted, cash, req.cash_counted, req.note.strip()))
        diff = req.cash_counted - cash
        store.log(c, user, "close", f"روز بسته شد: {posted} شب ثبت شد" + (f"؛ صندوق {facts.money(abs(diff))} {'کم' if diff < 0 else 'زیاد'}" if diff else "؛ صندوق درست بود"))
    return {"posted": posted, "diff": diff, "diff_text": facts.money(abs(diff))}

# ---------- settings ----------

class Settings(BaseModel):
    prices: dict[str, int]
    extra_bed: int = Field(ge=0, le=100_000_000)
    HB: int = Field(ge=0, le=100_000_000)
    FB: int = Field(ge=0, le=100_000_000)
    deposit: int = Field(ge=0, le=100)
    max_discount: int = Field(ge=0, le=60)

@router.get("/settings")
def get_settings(user: dict = Depends(DESK)):
    with store.conn() as c:
        return facts.settings(c) | {"types": {k: v[0] for k, v in facts.TYPES.items()}}

@router.post("/settings")
def set_settings(req: Settings, user: dict = Depends(MANAGER)):
    if set(req.prices) != set(facts.TYPES) or any(not 100_000 <= v <= 1_000_000_000 for v in req.prices.values()):
        raise HTTPException(status_code=422, detail="قیمت همه‌ی نوع اتاق‌ها را درست بنویسید")
    with store.conn() as c:
        store.set_meta(c, "settings", json.dumps(req.model_dump()))
        store.log(c, user, "settings", "قیمت‌ها و قاعده‌ها تغییر کرد؛ برای رزروهای جدید")
        return facts.settings(c)

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
        for k in range(0, 8):
            d = facts.add(t, k)
            av = facts.availability(c, d, facts.add(d, 1))
            lines.append(f"شب {facts.jlong(d)}: " + "، ".join(f"{facts.type_name(tp)} {max(0, v['free'])} اتاق خالی" for tp, v in av.items()))
        for b in c.execute("SELECT * FROM bookings WHERE (arrive = ? OR depart = ?) AND status IN ('confirmed', 'tentative', 'in_house') ORDER BY eta", (t, t)):
            v = facts.booking_view(c, b)
            lines.append(f"{'ورود' if v['arrive'] == t else 'خروج'} امروز: {v['guest']}، {v['type_text']}" + (f"، اتاق {v['room']}" if v["room"] else "، بی‌اتاق") +
                         f"، {v['status_text']}" + (f"، بیعانه تا {v['deposit_due_text']}" if v["status"] == "tentative" else ""))
        for r in facts.rooms(c).values():
            stay = c.execute("SELECT depart FROM bookings WHERE room_id = ? AND status = 'in_house'", (r["id"],)).fetchone()
            lines.append(f"اتاق {r['number']}: {facts.ROOM_STATUS[r['status']]}" + (f"، مقیم تا {facts.jlong(stay['depart'])}" if stay else "، خالی"))
    data = "\n".join(lines)
    words = [w for w in re.findall(r"[؀-ۿ‌]{3,}", req.question) if w not in ("چقدر", "چند", "کدام", "است", "داریم", "امشب", "اتاق")]
    nums = re.findall(r"\d{3}", req.question.translate(reader.FA_DIGITS))
    hits = [l for l in lines if any(f"اتاق {n}" in l for n in nums)] or [l for l in lines if any(w in l for w in words)]
    fallback = "\n".join(hits[:6]) if hits else "پاسخ این سؤال در اطلاعات هتل پیدا نشد. درباره‌ی اتاق‌های خالی، ورود و خروج امروز و رزروها بپرسید."
    text, checked = _written(
        f"تو دستیار {info.current()['name']} هستی. به سؤال زیر فقط از روی «اطلاعات» جواب بده، کوتاه، حداکثر سه جمله، فارسی معیار. "
        "عددها، ساعت‌ها و شماره‌ی اتاق‌ها را دقیقاً همان‌طور که در اطلاعات آمده بنویس. اگر جواب در اطلاعات نیست، همین را بگو.",
        f"سؤال: {req.question}\n\nاطلاعات:\n{data}", fallback)
    return {"answer": text, "checked": checked}
