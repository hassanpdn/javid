"""The hotel's public website API, under /hotel/public: open to anyone, on the hotel's own address (HOTEL_HOST) and
past the site's door (app.py lets these paths through).

Visitors see the hotel, its room types with the price of a night, and, for their dates and people, which types are
free for every night with the stay's price (worked out by facts.quote, never by the model). Guests make an account
with a mobile number and a password of their own and book a room type: the booking is tentative and waits for its
deposit like any phone booking (24 hours, or until the day before arrival), the desk's panels get a toast. The guest
pays card to card and sends a photo of the receipt; a person at the desk looks at the bank and records the payment,
which confirms the booking. A guest can cancel by the hotel's rule (facts.refund) and sees only the bookings they made
on the website: the account comes from its token, never from the request. Requests from one address are limited per
minute, so a script cannot fill the hotel or try passwords.
"""
import json, re, time
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from lodge.api import save_image, image_data
from . import info, store, facts, read as reader
from .api import BookIn, make_booking, _stay

router = APIRouter(prefix="/hotel/public")
_hits = {}
LIMITS = {"login": 10, "register": 5, "book": 6, "write": 20, "search": 40}   # per minute, per address
CARD = "۰۰۰۰ ۰۰۰۰ ۰۰۰۰ ۰۰۰۰ (نمایشی؛ واریز نکنید)"
# what the website says about each room type (the demo's words; a real hotel writes its own)
ABOUT = {
    "dbl_garden": "اتاق آرام دوتخته با پنجره‌ای رو به باغ و درختان نارنج؛ برای دو نفر، با جای یک تخت اضافه.",
    "dbl_sea": "اتاق دوتخته با بالکن رو به دریا؛ صبح با صدای موج بیدار می‌شوید.",
    "triple": "اتاق بزرگ سه‌تخته در طبقه‌ی چهارم، مناسب خانواده‌ها.",
    "suite": "سوئیت با نشیمن جدا و پنجره‌های بلند رو به دریا؛ تا چهار نفر.",
    "villa": "ویلای ساحلی با حیاط و دسترسی مستقیم به ساحل؛ تا شش نفر، با جای دو تخت اضافه.",
}

def limit(request: Request, kind):
    key = (request.client.host if request.client else "", kind)
    now = time.time()
    _hits[key] = [x for x in _hits.get(key, []) if now - x < 60] + [now]
    if len(_hits[key]) > LIMITS[kind]:
        raise HTTPException(status_code=429, detail="درخواست‌ها زیاد بود. یک دقیقه دیگر دوباره امتحان کنید.")

def ready():
    if not info.is_set_up():
        raise HTTPException(status_code=404, detail="سایت هتل هنوز راه‌اندازی نشده است")

def current_account(authorization: str = Header(None)):
    a = store.account_by_token((authorization or "").removeprefix("Bearer ").strip())
    if not a:
        raise HTTPException(status_code=401, detail="لطفاً وارد حساب خود شوید")
    return a

def _phone(p):
    phone = re.sub(r"\D", "", (p or "").translate(reader.FA_DIGITS))
    if not re.fullmatch(r"09\d{9}", phone):
        raise HTTPException(status_code=422, detail="شماره‌ی همراه باید ۱۱ رقم و با ۰۹ شروع شود")
    return phone

# ---------- what anyone sees ----------

@router.get("/site")
def site():
    ready()
    s = info.current()
    with store.conn() as c:
        st = facts.settings(c)
        count = {t: c.execute("SELECT COUNT(*) FROM rooms WHERE type = ?", (t,)).fetchone()[0] for t in facts.TYPES}
    return {"name": s["name"], "place": s["place"], "manager": info.person("manager", s), "today": facts.jfull(store.today().isoformat()),
            "types": [{"key": k, "name": v[0], "beds": v[1], "most": v[2], "rooms": count[k], "about": ABOUT[k],
                       # «a night from»: the price in the quiet months, the lowest season (facts.season)
                       "price_text": facts.money(round(st["prices"][k] * 0.8 / 10_000) * 10_000)} for k, v in facts.TYPES.items()],
            "boards": facts.BOARDS, "board_prices": {"HB": facts.money(st["HB"]), "FB": facts.money(st["FB"])}, "extra_bed": facts.money(st["extra_bed"]),
            "check_in": facts.CHECK_IN, "check_out": facts.CHECK_OUT, "child_free": facts.CHILD_FREE, "deposit": st["deposit"],
            "refund_rule": "لغو بیش از ۷ روز پیش از ورود: ۹۰ درصد پرداختی برمی‌گردد؛ ۳ تا ۷ روز: ۵۰ درصد؛ کمتر از ۳ روز: هیچ."}

class SearchIn(BaseModel):
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)
    adults: int = Field(2, ge=1, le=8)
    ages: list[int] = Field(default_factory=list, max_length=6)
    board: str = "BB"

def _check_people(req):
    if any(a < 0 or a > 17 for a in req.ages):
        raise HTTPException(status_code=422, detail="سن کودک بین ۰ تا ۱۷ سال باشد")
    if req.board not in facts.BOARDS:
        raise HTTPException(status_code=422, detail="نوع پذیرایی را انتخاب کنید")

@router.post("/search")
def search(req: SearchIn, request: Request):
    """Every room type: free for every night or not, and the stay's price for these people, cheapest first."""
    ready(); limit(request, "search"); _check_people(req)
    a, d = _stay(req.arrive, req.depart)
    if a < store.today().isoformat():
        raise HTTPException(status_code=422, detail="تاریخ ورود گذشته است")
    with store.conn() as c:
        av = facts.availability(c, a, d)
        out = []
        for t in facts.TYPES:
            q = facts.quote(c, t, a, d, req.adults, req.ages, req.board)
            free = av[t]["free"] > 0
            out.append({"type": t, "name": facts.type_name(t), "about": ABOUT[t], "fits": q["fits"], "free": free,
                        "why": q.get("why", "") if not q["fits"] else "" if free else "برای همه‌ی این شب‌ها جای خالی ندارد",
                        "total": q.get("total", 0), "total_text": q.get("total_text", ""), "deposit_text": facts.money(q.get("deposit", 0)),
                        "how": q.get("how", []), "last": free and av[t]["free"] <= 2})
    out.sort(key=lambda o: (not (o["fits"] and o["free"]), o["total"]))
    return {"stay": facts.stay_text({"arrive": a, "depart": d}), "people": f"{req.adults} بزرگسال" + (f" و {len(req.ages)} کودک" if req.ages else ""),
            "options": out}

# ---------- guests' accounts ----------

class Register(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    phone: str = Field(max_length=20)
    password: str = Field(min_length=6, max_length=100)

@router.post("/register")
def register(req: Register, request: Request):
    ready(); limit(request, "register")
    phone, name = _phone(req.phone), " ".join(req.name.split())
    with store.conn() as c:
        if c.execute("SELECT 1 FROM site_accounts WHERE phone = ?", (phone,)).fetchone():
            raise HTTPException(status_code=409, detail="با این شماره قبلاً حساب ساخته شده است. وارد شوید.")
        aid = c.execute("INSERT INTO site_accounts (name, phone, password, created) VALUES (?,?,?,?)",
                        (name, phone, store.hash_password(req.password), store.today().isoformat())).lastrowid
        token = store.account_session(c, aid)
    return {"token": token, "guest": {"name": name, "phone": phone}}

class GuestLogin(BaseModel):
    phone: str = Field(max_length=20)
    password: str = Field(max_length=100)

@router.post("/login")
def guest_login(req: GuestLogin, request: Request):
    ready(); limit(request, "login")
    phone = _phone(req.phone)
    with store.conn() as c:
        a = c.execute("SELECT * FROM site_accounts WHERE phone = ?", (phone,)).fetchone()
        if not a or not store.check_password(req.password, a["password"]):
            raise HTTPException(status_code=401, detail="شماره یا رمز درست نیست")
        token = store.account_session(c, a["id"])
    return {"token": token, "guest": {"name": a["name"], "phone": a["phone"]}}

@router.post("/logout")
def guest_logout(authorization: str = Header(None)):
    store.logout((authorization or "").removeprefix("Bearer ").strip())
    return {"ok": True}

@router.get("/me")
def me(a: dict = Depends(current_account)):
    return {"name": a["name"], "phone": a["phone"]}

# ---------- the guest's own bookings ----------

def _mine(c, a, bid):
    b = c.execute("SELECT b.* FROM bookings b JOIN site_bookings s ON s.booking_id = b.id WHERE b.id = ? AND s.account_id = ?", (bid, a["id"])).fetchone()
    if not b:
        raise HTTPException(status_code=404, detail="این رزرو پیدا نشد")
    return dict(b)

def deposit_of(c, b):
    """The deposit this booking asks for (the hotel's percent of its total)."""
    return round((b["total"] or 0) * facts.settings(c)["deposit"] / 100 / 10_000) * 10_000

def _view(c, b):
    v = facts.booking_view(c, b)
    t = store.today().isoformat()
    paid = facts.paid(c, b["id"])
    r = c.execute("SELECT * FROM receipts WHERE booking_id = ? ORDER BY id DESC LIMIT 1", (b["id"],)).fetchone()
    waiting = bool(r and r["status"] == "waiting")
    out = {k: v[k] for k in ("id", "type", "type_text", "status", "status_text", "stay_text", "arrive_text", "depart_text", "people_text",
                             "board_text", "total_text", "deposit_due_text", "nights_count", "eta", "requests")}
    out["status_text"] = {"tentative": "منتظر بیعانه", "confirmed": "قطعی", "in_house": "در هتل", "out": "پایان اقامت"}.get(b["status"], v["status_text"])
    if b["status"] == "tentative" and waiting:
        out["status_text"] = "رسید در حال بررسی"
    out["deposit_text"] = facts.money(deposit_of(c, b))
    out["paid_text"] = facts.money(paid) if paid else ""
    out["can_pay"] = b["status"] == "tentative" and not waiting
    out["card"] = CARD if out["can_pay"] else ""
    out["room"] = v["room"] if b["status"] in ("in_house", "out") else None
    out["can_cancel"] = b["status"] in ("tentative", "confirmed") and b["arrive"] > t
    out["refund"] = facts.refund(c, b) if out["can_cancel"] else None
    out["receipt"] = {"status": r["status"], "data": image_data(r["file"], store.DIR)} if r else None
    out["late"] = b["status"] == "tentative" and not waiting and bool(b["deposit_due"]) and b["deposit_due"] < store.stamp()
    return out

@router.get("/my")
def my_bookings(a: dict = Depends(current_account)):
    with store.conn() as c:
        rows = c.execute("""SELECT b.* FROM bookings b JOIN site_bookings s ON s.booking_id = b.id WHERE s.account_id = ?
                            ORDER BY b.arrive DESC""", (a["id"],)).fetchall()
        return {"name": a["name"], "bookings": [_view(c, b) for b in rows]}

class BookReq(SearchIn):
    type: str
    eta: str = Field("14:00", pattern=r"^\d{2}:\d{2}$")
    requests: str = Field("", max_length=300)

@router.post("/bookings")
def book(req: BookReq, request: Request, a: dict = Depends(current_account)):
    """A tentative booking of a room type, checked against the rooms left like any other. Two waiting at most."""
    ready(); limit(request, "book"); _check_people(req)
    if req.type not in facts.TYPES:
        raise HTTPException(status_code=422, detail="نوع اتاق را انتخاب کنید")
    with store.conn() as c:
        if c.execute("""SELECT COUNT(*) FROM site_bookings s JOIN bookings b ON b.id = s.booking_id
                        WHERE s.account_id = ? AND b.status = 'tentative'""", (a["id"],)).fetchone()[0] >= 2:
            raise HTTPException(status_code=409, detail="دو رزرو شما هنوز منتظر بیعانه است؛ اول آن‌ها را قطعی یا لغو کنید")
        body = BookIn(arrive=req.arrive, depart=req.depart, adults=req.adults, ages=req.ages, board=req.board, type=req.type, name=a["name"],
                      phone=a["phone"], source="site", status="tentative", eta=req.eta, requests=req.requests.strip())
        bid = make_booking(c, body, None, "site")
        c.execute("INSERT INTO site_bookings (booking_id, account_id) VALUES (?, ?)", (bid, a["id"]))
        c.execute("UPDATE events SET who = ?, role = 'مهمان' WHERE booking_id = ? AND kind = 'book'", (a["name"], bid))   # make_booking logs «سایت هتل»
        return _view(c, c.execute("SELECT * FROM bookings WHERE id = ?", (bid,)).fetchone())

class ReceiptIn(BaseModel):
    data: str = Field(max_length=9_000_000)

@router.post("/bookings/{bid}/receipt")
def receipt(bid: int, req: ReceiptIn, request: Request, a: dict = Depends(current_account)):
    """A photo of the card-to-card receipt; the booking stays tentative until the desk records the payment."""
    limit(request, "write")
    with store.conn() as c:
        b = _mine(c, a, bid)
        if b["status"] != "tentative" or c.execute("SELECT 1 FROM receipts WHERE booking_id = ? AND status = 'waiting'", (bid,)).fetchone():
            raise HTTPException(status_code=409, detail="برای این رزرو رسید لازم نیست یا در حال بررسی است")
    name = save_image(req.data, f"receipt{bid}", store.DIR)
    with store.conn() as c:
        c.execute("INSERT INTO receipts (booking_id, at, file, status) VALUES (?,?,?, 'waiting')", (bid, store.stamp(), name))
        store.log(c, a, "receipt", "رسید بیعانه از سایت فرستاده شد", bid)
    return {"ok": True}

@router.post("/bookings/{bid}/cancel")
def cancel(bid: int, a: dict = Depends(current_account)):
    """Cancelled by the hotel's rule; what goes back is recorded as a refund, which the desk transfers."""
    with store.conn() as c:
        b = _mine(c, a, bid)
        if b["status"] not in ("tentative", "confirmed") or b["arrive"] <= store.today().isoformat():
            raise HTTPException(status_code=409, detail="این رزرو دیگر از این‌جا لغو نمی‌شود؛ با هتل تماس بگیرید")
        r = facts.refund(c, b)
        c.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (bid,))
        c.execute("UPDATE receipts SET status = 'rejected' WHERE booking_id = ? AND status = 'waiting'", (bid,))
        if r["amount"]:
            c.execute("INSERT INTO payments (booking_id, at, amount, method, kind) VALUES (?,?,?, 'transfer', 'refund')", (bid, store.stamp(), -r["amount"]))
        store.log(c, a, "cancel", "مهمان رزرو را از سایت لغو کرد" + (f"؛ {facts.money(r['amount'])} باید برگردد" if r["amount"] else ""), bid)
    return r
