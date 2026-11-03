"""The eco-lodge's public website API, under /lodge/public: open to anyone, on the lodge's own address and past the
site's door (app.py lets these paths through).

Visitors see the lodge, its active units with prices and free nights, and the reviews the host chose to show. Guests
make an account with a mobile number and a password of their own, ask for a booking (the host approves it), send a
photo of the deposit receipt, cancel by the lodge's rule, write to the host, and after the stay leave a review once.
A guest sees only their own bookings: the guest comes from their token, never from the request. Requests from one
address are limited per minute, so a script cannot fill the calendar or try passwords.
"""
import json, os, re, time
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import info, store, facts
from .api import iso_date, stay, save_image, image_data, FA_DIGITS

router = APIRouter(prefix="/lodge/public")
_hits = {}
LIMITS = {"login": 10, "register": 5, "book": 6, "write": 20}   # per minute, per address

def limit(request: Request, kind):
    key = (request.client.host if request.client else "", kind)
    now = time.time()
    _hits[key] = [x for x in _hits.get(key, []) if now - x < 60] + [now]
    if len(_hits[key]) > LIMITS[kind]:
        raise HTTPException(status_code=429, detail="درخواست‌ها زیاد بود. یک دقیقه دیگر دوباره امتحان کنید.")

def ready():
    if not info.is_set_up():
        raise HTTPException(status_code=404, detail="سایت هنوز راه‌اندازی نشده است")

def current_guest(authorization: str = Header(None)):
    g = store.guest_by_token((authorization or "").removeprefix("Bearer ").strip())
    if not g:
        raise HTTPException(status_code=401, detail="لطفاً وارد حساب خود شوید")
    return g

def _phone(p):
    phone = re.sub(r"\D", "", (p or "").translate(FA_DIGITS))
    if not re.fullmatch(r"09\d{9}", phone):
        raise HTTPException(status_code=422, detail="شماره‌ی همراه باید ۱۱ رقم و با ۰۹ شروع شود")
    return phone

# ---------- what anyone sees ----------

@router.get("/site")
def site():
    ready()
    s = info.current()
    with store.conn() as c:
        units = [facts.unit_view(c, u) for u in c.execute("SELECT * FROM units WHERE active = 1 ORDER BY sort, id")]
        reviews = [facts.review_view(c, r) for r in c.execute("SELECT * FROM reviews WHERE status = 'shown' ORDER BY at DESC LIMIT 9")]
        return {"name": s["name"], "place": s["place"], "host": info.person("host", s), "words": info.site(), "units": units, "reviews": reviews,
                "rating": facts.rating(c), "today": facts.jfull(store.today().isoformat()), "rules": facts.settings(c)}

@router.get("/units/{uid}")
def unit(uid: int, start: str | None = None):
    ready()
    with store.conn() as c:
        u = c.execute("SELECT * FROM units WHERE id = ? AND active = 1", (uid,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="این اتاق در حال حاضر رزرو نمی‌شود")
        begin = iso_date(start, "تاریخ") if start else store.today().isoformat()
        begin = max(begin, store.today().isoformat())
        return {"unit": facts.unit_view(c, u), "calendar": facts.calendar(c, dict(u), begin, 42),
                "reviews": [facts.review_view(c, r) for r in c.execute("SELECT * FROM reviews WHERE unit_id = ? AND status = 'shown' ORDER BY at DESC LIMIT 6", (uid,))]}

class SearchIn(BaseModel):
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)
    people: int = Field(2, ge=1, le=30)
    unit_id: int | None = None

@router.post("/search")
def search(req: SearchIn):
    """The units free for every night, cheapest first; or one unit's price and why it may not be booked."""
    ready()
    a, d = stay(req.arrive, req.depart)
    with store.conn() as c:
        if req.unit_id:
            u = c.execute("SELECT * FROM units WHERE id = ? AND active = 1", (req.unit_id,)).fetchone()
            if not u:
                raise HTTPException(status_code=404, detail="این اتاق در حال حاضر رزرو نمی‌شود")
            why = facts.busy(c, u["id"], a, d)
            q = facts.quote(c, dict(u), a, d, req.people)
            return {"stay": facts.stay_text({"arrive": a, "depart": d}), "free": not why and q["ok"], "why": why or q.get("why", ""), "quote": q if q["ok"] else None}
        return {"stay": facts.stay_text({"arrive": a, "depart": d}), "units": facts.search(c, a, d, req.people)}

@router.get("/photo/{name}")
def photo(name: str):
    """A unit's photo, only if it is one of the units' photos (never a receipt)."""
    with store.conn() as c:
        if not c.execute("SELECT 1 FROM photos WHERE file = ?", (name,)).fetchone():
            raise HTTPException(status_code=404)
    path = os.path.join(store.DIR, os.path.basename(name))
    if not os.path.isfile(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=604800"})

# ---------- guests' accounts ----------

class Register(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    phone: str = Field(max_length=20)
    password: str = Field(min_length=6, max_length=100)

@router.post("/register")
def register(req: Register, request: Request):
    """A new account; a mobile the host entered from a phone booking (no password yet) is taken over, so the guest
    sees that booking too."""
    ready(); limit(request, "register")
    phone = _phone(req.phone)
    with store.conn() as c:
        g = c.execute("SELECT * FROM guests WHERE phone = ?", (phone,)).fetchone()
        if g and g["password"]:
            raise HTTPException(status_code=409, detail="با این شماره قبلاً حساب ساخته شده است. وارد شوید.")
        if g:
            c.execute("UPDATE guests SET password = ?, name = ? WHERE id = ?", (store.hash_password(req.password), " ".join(req.name.split()), g["id"]))
            gid = g["id"]
        else:
            gid = c.execute("INSERT INTO guests (name, phone, password, created) VALUES (?,?,?,?)",
                            (" ".join(req.name.split()), phone, store.hash_password(req.password), store.today().isoformat())).lastrowid
        token = store.guest_session(c, gid)
    return {"token": token, "guest": {"name": " ".join(req.name.split()), "phone": phone}}

class GuestLogin(BaseModel):
    phone: str = Field(max_length=20)
    password: str = Field(max_length=100)

@router.post("/login")
def guest_login(req: GuestLogin, request: Request):
    ready(); limit(request, "login")
    phone = _phone(req.phone)
    with store.conn() as c:
        g = c.execute("SELECT * FROM guests WHERE phone = ?", (phone,)).fetchone()
        if not g or not g["password"] or not store.check_password(req.password, g["password"]):
            raise HTTPException(status_code=401, detail="شماره یا رمز درست نیست")
        token = store.guest_session(c, g["id"])
    return {"token": token, "guest": {"name": g["name"], "phone": g["phone"]}}

@router.post("/logout")
def guest_logout(authorization: str = Header(None)):
    store.logout((authorization or "").removeprefix("Bearer ").strip())
    return {"ok": True}

@router.get("/me")
def me(g: dict = Depends(current_guest)):
    return {"name": g["name"], "phone": g["phone"]}

def _mine(c, g, bid):
    b = c.execute("SELECT * FROM bookings WHERE id = ? AND guest_id = ?", (bid, g["id"])).fetchone()
    if not b:
        raise HTTPException(status_code=404, detail="این رزرو پیدا نشد")
    return dict(b)

def _guest_view(c, b):
    v = facts.booking_view(c, b)
    t = store.today().isoformat()
    w = info.site()
    out = {k: v[k] for k in ("id", "unit", "art", "status", "status_text", "stay_text", "arrive_text", "depart_text", "adults", "total_text", "deposit_text",
                             "deposit_due_text", "over", "nights_count")}
    out["can_pay"] = b["status"] == "approved"
    out["card"] = w["card"] if b["status"] == "approved" else ""
    out["can_cancel"] = b["status"] in ("requested", "approved", "paid", "confirmed") and b["arrive"] > t
    out["can_review"] = b["status"] == "confirmed" and b["depart"] <= t and not v["review"]
    out["review"] = {k: v["review"][k] for k in ("stars", "text", "status", "reply")} if v["review"] else None
    out["refund"] = facts.refund(c, b) if out["can_cancel"] else None
    out["receipt"] = {"status": v["receipt"]["status"], "data": image_data(v["receipt"]["file"])} if v["receipt"] else None
    out["messages"] = [{"side": m["side"], "text": m["text"], "day": facts.jday(m["at"]), "time": m["at"][11:16]}
                       for m in c.execute("SELECT * FROM messages WHERE booking_id = ? ORDER BY id", (b["id"],))]
    return out

@router.get("/my")
def my_bookings(g: dict = Depends(current_guest)):
    with store.conn() as c:
        rows = c.execute("SELECT * FROM bookings WHERE guest_id = ? ORDER BY arrive DESC", (g["id"],)).fetchall()
        return {"name": g["name"], "bookings": [_guest_view(c, b) for b in rows]}

class BookIn(BaseModel):
    unit_id: int
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)
    people: int = Field(2, ge=1, le=30)
    note: str = Field("", max_length=300)

@router.post("/bookings")
def book(req: BookIn, request: Request, g: dict = Depends(current_guest)):
    """A request: it holds the unit's nights until the host answers. Two open requests per guest at most."""
    ready(); limit(request, "book")
    a, d = stay(req.arrive, req.depart)
    with store.conn() as c:
        if c.execute("SELECT COUNT(*) FROM bookings WHERE guest_id = ? AND status = 'requested'", (g["id"],)).fetchone()[0] >= 2:
            raise HTTPException(status_code=409, detail="دو درخواست شما هنوز منتظر جواب میزبان است")
        u = c.execute("SELECT * FROM units WHERE id = ? AND active = 1", (req.unit_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="این اتاق در حال حاضر رزرو نمی‌شود")
        why = facts.busy(c, u["id"], a, d)
        q = facts.quote(c, dict(u), a, d, req.people)
        if why or not q["ok"]:
            raise HTTPException(status_code=409, detail=why or q["why"])
        bid = c.execute("""INSERT INTO bookings (guest_id, unit_id, arrive, depart, adults, children, status, source, nights, total, deposit, note, created)
                           VALUES (?,?,?,?,?,0,'requested','site',?,?,?,?,?)""",
                        (g["id"], u["id"], a, d, req.people, json.dumps(q["nights"]), q["total"], q["deposit"], req.note.strip(), store.stamp())).lastrowid
        store.log(c, g, "book", f"درخواست از سایت: {u['name']}، {facts.stay_text({'arrive': a, 'depart': d})}، {q['total_text']}", bid)
        return _guest_view(c, c.execute("SELECT * FROM bookings WHERE id = ?", (bid,)).fetchone())

class ReceiptIn(BaseModel):
    data: str = Field(max_length=9_000_000)

@router.post("/bookings/{bid}/receipt")
def receipt(bid: int, req: ReceiptIn, request: Request, g: dict = Depends(current_guest)):
    limit(request, "write")
    with store.conn() as c:
        b = _mine(c, g, bid)
        if b["status"] != "approved":
            raise HTTPException(status_code=409, detail="رسید فقط پس از تأیید میزبان و پیش از قطعی شدن فرستاده می‌شود")
    name = save_image(req.data, f"receipt{bid}")
    with store.conn() as c:
        c.execute("INSERT INTO receipts (booking_id, at, file, status) VALUES (?,?,?, 'waiting')", (bid, store.stamp(), name))
        c.execute("UPDATE bookings SET status = 'paid' WHERE id = ?", (bid,))
        store.log(c, g, "receipt", "رسید بیعانه فرستاده شد", bid)
    return {"ok": True}

@router.post("/bookings/{bid}/cancel")
def cancel(bid: int, g: dict = Depends(current_guest)):
    with store.conn() as c:
        b = _mine(c, g, bid)
        if b["status"] not in ("requested", "approved", "paid", "confirmed") or b["arrive"] <= store.today().isoformat():
            raise HTTPException(status_code=409, detail="این رزرو دیگر از این‌جا لغو نمی‌شود؛ با میزبان تماس بگیرید")
        r = facts.refund(c, b)
        c.execute("UPDATE bookings SET status = 'cancelled', decided = ? WHERE id = ?", (store.stamp(), bid))
        store.log(c, g, "cancel", "مهمان رزرو را لغو کرد" + (f"؛ {facts.money(r['amount'])} باید برگردد" if r["amount"] else ""), bid)
    return r

class TextIn(BaseModel):
    text: str = Field(min_length=2, max_length=500)

@router.post("/bookings/{bid}/message")
def message(bid: int, req: TextIn, request: Request, g: dict = Depends(current_guest)):
    limit(request, "write")
    with store.conn() as c:
        _mine(c, g, bid)
        c.execute("INSERT INTO messages (booking_id, at, side, text, seen) VALUES (?,?, 'guest', ?, 0)", (bid, store.stamp(), req.text.strip()))
        store.log(c, g, "message", "پیام مهمان", bid)
    return {"ok": True}

class ReviewIn(BaseModel):
    stars: int = Field(ge=1, le=5)
    text: str = Field(min_length=10, max_length=800)

@router.post("/bookings/{bid}/review")
def review(bid: int, req: ReviewIn, request: Request, g: dict = Depends(current_guest)):
    """Once per stay, after its last day. It waits for the host before it is shown."""
    limit(request, "write")
    with store.conn() as c:
        b = _mine(c, g, bid)
        if b["status"] != "confirmed" or b["depart"] > store.today().isoformat():
            raise HTTPException(status_code=409, detail="نظر پس از پایان اقامت نوشته می‌شود")
        if c.execute("SELECT 1 FROM reviews WHERE booking_id = ?", (bid,)).fetchone():
            raise HTTPException(status_code=409, detail="برای این سفر نظر داده‌اید")
        c.execute("INSERT INTO reviews (booking_id, guest_id, unit_id, stars, text, at, status) VALUES (?,?,?,?,?,?, 'waiting')",
                  (bid, g["id"], b["unit_id"], req.stars, req.text.strip(), store.stamp()))
        store.log(c, g, "review", f"نظر {req.stars} ستاره نوشته شد", bid)
    return {"ok": True}
