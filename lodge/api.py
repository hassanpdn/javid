"""The eco-lodge host's panel, all under /lodge (the public website's API is public.py, under /lodge/public). Logins,
sessions and data are its own (lodge.db); the site's door and the card's login (access.py) cover these paths.

Roles: host (میزبان) does everything, including the units, prices, the website's words and the setup; helper (همکار)
answers requests, checks receipts and replies to guests. Every number comes from facts.py. The model writes only the
host's morning summary (checked by only_known_numbers, with a code-built fallback); messages to guests are built by
code and sent by the host. A booking is never confirmed without the host: approving a request and confirming a
receipt are buttons a person presses.
"""
import base64, io, json, os, re, secrets, threading
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from llm import ask_llm
from checks import only_known_numbers
from jalali import to_gregorian
from . import info, store, demo, facts

router = APIRouter(prefix="/lodge")
_lock = threading.Lock()
_cache = {}
FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
MAX_IMAGE = 6 * 1024 * 1024

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

ALL = require("host", "helper")
HOST = require("host")

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
    return {"set_up": True, "lodge": info.public(), "site": info.site(), "today": facts.jfull(store.today().isoformat()),
            "kinds": facts.KINDS, "sources": facts.SOURCES, "site_url": os.getenv("LODGE_URL") or "/eco"}

@router.get("/setup/default")
def setup_default():
    return {"lodge": info.DEFAULT}

class Setup(BaseModel):
    lodge: dict

@router.post("/setup")
def setup(req: Setup):
    try:
        settings = info.clean(req.lodge)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with _lock:
        info.save(settings)
        demo.build()
        _cache.clear()
    return {"ok": True, "lodge": info.public()}

store.init()

def _written(prompt, data, fallback, max_tokens=350):
    try:
        text = ask_llm(prompt, data, max_tokens=max_tokens).strip()
    except Exception:
        return fallback, None
    if not text or not only_known_numbers(text, data):
        return fallback, False
    return text, True

def iso_date(s, what):
    """«1405/08/10» → ISO, or 422 with a plain message."""
    try:
        y, m, d = (int(x) for x in re.split(r"[/\-]", str(s).translate(FA_DIGITS).strip()))
        assert 1300 < y < 1500 and 1 <= m <= 12 and 1 <= d <= 31
        return to_gregorian(y, m, d).isoformat()
    except Exception:
        raise HTTPException(status_code=422, detail=f"{what} درست نیست")

def stay(arrive, depart):
    a, d = iso_date(arrive, "تاریخ ورود"), iso_date(depart, "تاریخ خروج")
    if d <= a:
        raise HTTPException(status_code=422, detail="تاریخ خروج باید بعد از تاریخ ورود باشد")
    if len(facts.nights_of(a, d)) > 21:
        raise HTTPException(status_code=422, detail="بیش از ۲۱ شب را با میزبان هماهنگ کنید")
    if a < store.today().isoformat():
        raise HTTPException(status_code=422, detail="تاریخ ورود گذشته است")
    return a, d

def save_image(data_url, prefix, folder=None):
    """A photo sent as a data URL: only JPEG or PNG (by its first bytes), at most 6 MB, made at most 1600 px wide and
    saved as JPEG in folder (the lodge's own by default; the hotel's website uses it for receipts). Returns the file name."""
    from PIL import Image
    try:
        raw = base64.b64decode(data_url.split(",", 1)[-1], validate=True)
    except Exception:
        raise HTTPException(status_code=422, detail="فایل عکس خوانده نشد")
    if len(raw) > MAX_IMAGE:
        raise HTTPException(status_code=413, detail="عکس بیش از ۶ مگابایت است")
    if not (raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail="فقط عکس JPG یا PNG")
    try:
        im = Image.open(io.BytesIO(raw))
        im.thumbnail((1600, 1600))
        name = f"{prefix}-{secrets.token_hex(8)}.jpg"
        im.convert("RGB").save(os.path.join(folder or store.DIR, name), "JPEG", quality=82)
    except Exception:
        raise HTTPException(status_code=422, detail="فایل عکس خوانده نشد")
    return name

def image_data(name, folder=None):
    try:
        with open(os.path.join(folder or store.DIR, os.path.basename(name)), "rb") as f:
            raw = f.read()
    except OSError:
        return None
    kind = "png" if raw[:4] == b"\x89PNG" else "jpeg"
    return f"data:image/{kind};base64," + base64.b64encode(raw).decode()

def _booking(c, bid):
    row = c.execute("SELECT * FROM bookings WHERE id = ?", (bid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این رزرو پیدا نشد")
    return dict(row)

def _unit(c, uid):
    row = c.execute("SELECT * FROM units WHERE id = ?", (uid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این واحد پیدا نشد")
    return dict(row)

# ---------- today ----------

@router.get("/today")
def today_view(user: dict = Depends(ALL)):
    with store.conn() as c:
        return facts.overview(c)

@router.get("/brief")
def brief(user: dict = Depends(HOST)):
    with store.conn() as c:
        key = f"{store.today()}|{c.execute('SELECT MAX(id) FROM events').fetchone()[0]}"
        if key in _cache:
            return _cache[key]
        data, o = facts.brief_facts(c)
    fallback = (f"امروز {len(o['alerts'])} کار منتظر شماست. " + " ".join(f"{a['title']}." for a in o["alerts"][:2])) if o["alerts"] else "امروز کار فوری‌ای نیست."
    s = info.current()
    text, checked = _written(
        f"تو دستیار {info.person('host', s)}، میزبان {s['name']} هستی. از روی اطلاعات زیر یک خلاصه‌ی صبحگاهی سه جمله‌ای، گرم و ساده، به فارسی معیار بنویس: "
        "اول درخواست‌ها و رسیدهای منتظر، بعد مهمان‌های امروز و فردا، بعد بقیه. عددها را دقیقاً همان‌طور که نوشته شده بنویس و عدد جدید نساز. سلام ننویس.", data, fallback)
    out = {"text": text, "checked": checked}
    if checked is not None:
        _cache[key] = out
    return out

@router.get("/events")
def events(after: int = 0, user: dict = Depends(ALL)):
    with store.conn() as c:
        return facts.events(c, after)

# ---------- units ----------

@router.get("/units")
def units(user: dict = Depends(ALL)):
    with store.conn() as c:
        out = []
        for u in c.execute("SELECT * FROM units ORDER BY sort, id"):
            v = facts.unit_view(c, u)
            v["photo_ids"] = [dict(p) for p in c.execute("SELECT id, file FROM photos WHERE unit_id = ? ORDER BY sort, id", (u["id"],))]
            v["blocks"] = [dict(b) | {"text": f"{facts.jday(b['start'])} تا {facts.jday(b['end'])}"} for b in
                           c.execute("SELECT * FROM blocks WHERE unit_id = ? AND end > ? ORDER BY start", (u["id"], store.today().isoformat()))]
            v["next"] = c.execute("SELECT COUNT(*) FROM bookings WHERE unit_id = ? AND status IN ('requested', 'approved', 'paid', 'confirmed') AND depart > ?",
                                  (u["id"], store.today().isoformat())).fetchone()[0]
            out.append(v)
        return out

class UnitIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    kind: str
    beds: int = Field(ge=1, le=20)
    capacity: int = Field(ge=1, le=30)
    price: int = Field(ge=100_000, le=500_000_000)
    weekend_price: int = Field(ge=100_000, le=500_000_000)
    description: str = Field("", max_length=400)
    amenities: str = Field("", max_length=300)
    art: str = "dome"

def _check_unit(req):
    if req.kind not in facts.KINDS or req.art not in facts.ARTS:
        raise HTTPException(status_code=422, detail="نوع واحد را انتخاب کنید")
    if req.capacity < req.beds:
        raise HTTPException(status_code=422, detail="ظرفیت نمی‌تواند کمتر از تخت‌ها باشد")

@router.post("/units")
def add_unit(req: UnitIn, user: dict = Depends(HOST)):
    _check_unit(req)
    with store.conn() as c:
        n = c.execute("SELECT COUNT(*) FROM units").fetchone()[0]
        if n >= 20:
            raise HTTPException(status_code=409, detail="این نسخه برای حداکثر ۲۰ واحد است")
        uid = c.execute("INSERT INTO units (name, kind, beds, capacity, price, weekend_price, description, amenities, art, active, sort) VALUES (?,?,?,?,?,?,?,?,?,1,?)",
                        (req.name.strip(), req.kind, req.beds, req.capacity, req.price, req.weekend_price, req.description.strip(), req.amenities.strip(), req.art, n)).lastrowid
        store.log(c, user, "unit", f"واحد جدید: {req.name.strip()}")
    return {"id": uid}

@router.post("/units/{uid}")
def edit_unit(uid: int, req: UnitIn, user: dict = Depends(HOST)):
    """Prices change for new bookings only: a booking keeps the price of each of its nights."""
    _check_unit(req)
    with store.conn() as c:
        _unit(c, uid)
        c.execute("UPDATE units SET name = ?, kind = ?, beds = ?, capacity = ?, price = ?, weekend_price = ?, description = ?, amenities = ?, art = ? WHERE id = ?",
                  (req.name.strip(), req.kind, req.beds, req.capacity, req.price, req.weekend_price, req.description.strip(), req.amenities.strip(), req.art, uid))
        store.log(c, user, "unit", f"واحد {req.name.strip()} ویرایش شد")
    return {"ok": True}

class ActiveIn(BaseModel):
    active: bool

@router.post("/units/{uid}/active")
def unit_active(uid: int, req: ActiveIn, user: dict = Depends(HOST)):
    """A unit switched off is not shown on the website and cannot be booked; its bookings stay as they are."""
    with store.conn() as c:
        u = _unit(c, uid)
        c.execute("UPDATE units SET active = ? WHERE id = ?", (int(req.active), uid))
        store.log(c, user, "unit", f"{u['name']} {'دوباره فعال شد' if req.active else 'از سایت و فروش بیرون رفت'}")
        left = c.execute("SELECT COUNT(*) FROM bookings WHERE unit_id = ? AND status IN ('requested', 'approved', 'paid', 'confirmed') AND depart > ?",
                         (uid, store.today().isoformat())).fetchone()[0]
    return {"ok": True, "bookings_left": left}

class PhotoIn(BaseModel):
    data: str = Field(max_length=9_000_000)

@router.post("/units/{uid}/photos")
def add_photo(uid: int, req: PhotoIn, user: dict = Depends(HOST)):
    with store.conn() as c:
        _unit(c, uid)
        if c.execute("SELECT COUNT(*) FROM photos WHERE unit_id = ?", (uid,)).fetchone()[0] >= 8:
            raise HTTPException(status_code=409, detail="هر واحد حداکثر ۸ عکس")
    name = save_image(req.data, f"unit{uid}")
    with store.conn() as c:
        pid = c.execute("INSERT INTO photos (unit_id, file, sort) VALUES (?,?,?)", (uid, name, 0)).lastrowid
    return {"id": pid, "url": f"/lodge/public/photo/{name}"}

@router.post("/photos/{pid}/delete")
def delete_photo(pid: int, user: dict = Depends(HOST)):
    with store.conn() as c:
        p = c.execute("SELECT * FROM photos WHERE id = ?", (pid,)).fetchone()
        if not p:
            raise HTTPException(status_code=404)
        c.execute("DELETE FROM photos WHERE id = ?", (pid,))
    try:
        os.remove(os.path.join(store.DIR, p["file"]))
    except OSError:
        pass
    return {"ok": True}

class BlockIn(BaseModel):
    start: str = Field(max_length=12)
    end: str = Field(max_length=12)
    note: str = Field("", max_length=80)

@router.post("/units/{uid}/blocks")
def add_block(uid: int, req: BlockIn, user: dict = Depends(HOST)):
    """Close nights of a unit (repairs, the family's own guests). Nights already booked cannot be closed."""
    a, d = iso_date(req.start, "تاریخ شروع"), iso_date(req.end, "تاریخ پایان")
    if d <= a:
        raise HTTPException(status_code=422, detail="تاریخ پایان باید بعد از شروع باشد")
    with store.conn() as c:
        u = _unit(c, uid)
        why = facts.busy(c, uid, a, d)
        if why:
            raise HTTPException(status_code=409, detail=why)
        c.execute("INSERT INTO blocks (unit_id, start, end, note) VALUES (?,?,?,?)", (uid, a, d, req.note.strip()))
        store.log(c, user, "block", f"{u['name']}: {facts.jday(a)} تا {facts.jday(d)} بسته شد" + (f" ({req.note.strip()})" if req.note.strip() else ""))
    return {"ok": True}

@router.post("/blocks/{bid}/delete")
def delete_block(bid: int, user: dict = Depends(HOST)):
    with store.conn() as c:
        c.execute("DELETE FROM blocks WHERE id = ?", (bid,))
    return {"ok": True}

@router.get("/calendar")
def calendar(d: str | None = None, user: dict = Depends(ALL)):
    """Every unit, three weeks: each night free, booked (by whom, in what state) or closed."""
    start = iso_date(d, "تاریخ") if d else store.today().isoformat()
    end = facts.add(start, 21)
    with store.conn() as c:
        cols = [{"date": n, "day": facts.jday(n), "weekday": facts.WEEKDAYS[__import__("datetime").date.fromisoformat(n).weekday()], "weekend": facts.weekend(n),
                 "today": n == store.today().isoformat()} for n in facts.nights_of(start, end)]
        rows = []
        for u in c.execute("SELECT * FROM units ORDER BY sort, id"):
            bars = []
            for b in c.execute("SELECT * FROM bookings WHERE unit_id = ? AND status IN ('requested', 'approved', 'paid', 'confirmed') AND arrive < ? AND depart > ?", (u["id"], end, start)):
                a, z = max(b["arrive"], start), min(b["depart"], end)
                g = c.execute("SELECT name FROM guests WHERE id = ?", (b["guest_id"],)).fetchone()
                bars.append({"id": b["id"], "from": len(facts.nights_of(start, a)), "span": len(facts.nights_of(a, z)), "guest": g["name"] if g else "", "status": b["status"]})
            for k in c.execute("SELECT * FROM blocks WHERE unit_id = ? AND start < ? AND end > ?", (u["id"], end, start)):
                a, z = max(k["start"], start), min(k["end"], end)
                bars.append({"id": None, "from": len(facts.nights_of(start, a)), "span": len(facts.nights_of(a, z)), "guest": k["note"] or "بسته", "status": "closed"})
            rows.append({"id": u["id"], "name": u["name"], "active": bool(u["active"]), "bars": bars})
        return {"cols": cols, "rows": rows}

# ---------- bookings ----------

@router.get("/bookings")
def bookings(when: str = "open", q: str = "", user: dict = Depends(ALL)):
    t = store.today().isoformat()
    cond = {"open": ("status IN ('requested', 'approved', 'paid')", ()), "coming": ("status = 'confirmed' AND depart > ?", (t,)),
            "past": ("depart <= ? AND status = 'confirmed'", (t,)), "closed": ("status IN ('rejected', 'cancelled')", ())}.get(when, ("1", ()))
    sql = f"SELECT b.* FROM bookings b JOIN guests g ON g.id = b.guest_id WHERE {cond[0]}"
    args = list(cond[1])
    q = q.strip().translate(FA_DIGITS)
    if q:
        sql += " AND (g.name LIKE ? OR g.phone LIKE ? OR CAST(b.id AS TEXT) = ?)"
        args += [f"%{q}%", f"%{q}%", q]
    sql += " ORDER BY b.arrive" + (" DESC" if when in ("past", "closed") else "") + " LIMIT 80"
    with store.conn() as c:
        return [facts.booking_view(c, b) for b in c.execute(sql, args)]

@router.get("/bookings/{bid}")
def booking(bid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        b = _booking(c, bid)
        c.execute("UPDATE messages SET seen = 1 WHERE booking_id = ? AND side = 'guest'", (bid,))
        v = facts.booking_view(c, b)
        u = _unit(c, b["unit_id"])
        g = c.execute("SELECT * FROM guests WHERE id = ?", (b["guest_id"],)).fetchone()
        stays = [facts.booking_view(c, x) for x in c.execute("SELECT * FROM bookings WHERE guest_id = ? AND id != ? ORDER BY arrive DESC LIMIT 6", (b["guest_id"], bid))]
        return {"booking": v | {"receipt_data": image_data(v["receipt"]["file"]) if v["receipt"] else None},
                "messages": [dict(m) | {"day": facts.jday(m["at"]), "time": m["at"][11:16]} for m in c.execute("SELECT * FROM messages WHERE booking_id = ? ORDER BY id", (bid,))],
                "price_how": facts.quote(c, u | {"capacity": 99}, b["arrive"], b["depart"], b["adults"]).get("how", []), "refund": facts.refund(c, b),
                "stays": stays, "history": facts.events(c, 0, 40, bid), "conflict": facts.busy(c, b["unit_id"], b["arrive"], b["depart"], ignore=bid) if b["status"] == "requested" else ""}

def _move(c, user, bid, frm, to, text):
    b = _booking(c, bid)
    if b["status"] not in frm:
        raise HTTPException(status_code=409, detail="وضعیت این رزرو عوض شده است؛ صفحه را دوباره باز کنید")
    return b

@router.post("/bookings/{bid}/approve")
def approve(bid: int, user: dict = Depends(ALL)):
    """Yes to a request: the deposit is due within the deposit hours (or before arrival, whichever is first)."""
    with store.conn() as c:
        b = _move(c, user, bid, ("requested",), "approved", "")
        why = facts.busy(c, b["unit_id"], b["arrive"], b["depart"], ignore=bid)
        if why:
            raise HTTPException(status_code=409, detail=why)
        hours = facts.settings(c)["deposit_hours"]
        from datetime import datetime, timedelta
        due = min(datetime.fromisoformat(store.stamp()) + timedelta(hours=hours), datetime.fromisoformat(b["arrive"] + " 12:00"))
        c.execute("UPDATE bookings SET status = 'approved', deposit_due = ?, decided = ? WHERE id = ?", (due.strftime("%Y-%m-%d %H:%M"), store.stamp(), bid))
        store.log(c, user, "approve", f"درخواست تأیید شد؛ بیعانه تا {facts.jlong(due.isoformat())} ساعت {due:%H:%M}", bid)
    return {"ok": True}

class NoteIn(BaseModel):
    text: str = Field("", max_length=300)

@router.post("/bookings/{bid}/reject")
def reject(bid: int, req: NoteIn, user: dict = Depends(ALL)):
    with store.conn() as c:
        _move(c, user, bid, ("requested",), "rejected", "")
        c.execute("UPDATE bookings SET status = 'rejected', decided = ? WHERE id = ?", (store.stamp(), bid))
        if req.text.strip():
            c.execute("INSERT INTO messages (booking_id, at, side, text, seen) VALUES (?,?, 'host', ?, 1)", (bid, store.stamp(), req.text.strip()))
        store.log(c, user, "reject", "درخواست تأیید نشد" + (f": {req.text.strip()}" if req.text.strip() else ""), bid)
    return {"ok": True}

@router.post("/bookings/{bid}/confirm")
def confirm(bid: int, user: dict = Depends(ALL)):
    """The receipt was checked against the account (or the deposit came another way): the booking is confirmed."""
    with store.conn() as c:
        _move(c, user, bid, ("paid", "approved"), "confirmed", "")
        c.execute("UPDATE bookings SET status = 'confirmed', deposit_due = NULL WHERE id = ?", (bid,))
        c.execute("UPDATE receipts SET status = 'ok' WHERE booking_id = ? AND status = 'waiting'", (bid,))
        store.log(c, user, "confirm", "بیعانه رسید؛ رزرو قطعی شد", bid)
    return {"ok": True}

@router.post("/bookings/{bid}/receipt-wrong")
def receipt_wrong(bid: int, req: NoteIn, user: dict = Depends(ALL)):
    """The receipt does not match a deposit: back to waiting for the deposit, with a word to the guest."""
    with store.conn() as c:
        _move(c, user, bid, ("paid",), "approved", "")
        c.execute("UPDATE bookings SET status = 'approved' WHERE id = ?", (bid,))
        c.execute("UPDATE receipts SET status = 'rejected' WHERE booking_id = ? AND status = 'waiting'", (bid,))
        c.execute("INSERT INTO messages (booking_id, at, side, text, seen) VALUES (?,?, 'host', ?, 1)",
                  (bid, store.stamp(), req.text.strip() or "واریزی با این رسید در حساب پیدا نشد. لطفاً رسید درست را بفرستید یا تماس بگیرید."))
        store.log(c, user, "receipt", "رسید با واریزی جور نبود؛ از مهمان رسید درست خواسته شد", bid)
    return {"ok": True}

@router.post("/bookings/{bid}/cancel")
def cancel(bid: int, req: NoteIn, user: dict = Depends(ALL)):
    with store.conn() as c:
        b = _move(c, user, bid, ("requested", "approved", "paid", "confirmed"), "cancelled", "")
        r = facts.refund(c, b)
        c.execute("UPDATE bookings SET status = 'cancelled', decided = ? WHERE id = ?", (store.stamp(), bid))
        if req.text.strip():
            c.execute("INSERT INTO messages (booking_id, at, side, text, seen) VALUES (?,?, 'host', ?, 1)", (bid, store.stamp(), req.text.strip()))
        store.log(c, user, "cancel", "رزرو را میزبان لغو کرد" + (f"؛ {facts.money(r['amount'])} برگشت داده شود" if r["amount"] else ""), bid)
    return r

@router.post("/bookings/{bid}/message")
def reply(bid: int, req: NoteIn, user: dict = Depends(ALL)):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="متن پیام را بنویسید")
    with store.conn() as c:
        _booking(c, bid)
        c.execute("INSERT INTO messages (booking_id, at, side, text, seen) VALUES (?,?, 'host', ?, 1)", (bid, store.stamp(), req.text.strip()))
        store.log(c, user, "message", "پاسخ به مهمان", bid)
    return {"ok": True}

@router.get("/bookings/{bid}/feedback")
def feedback_text(bid: int, user: dict = Depends(ALL)):
    """The message that asks a guest how the stay was, built by code; the host sends it from the lodge's phone."""
    s, site_url = info.current(), os.getenv("LODGE_URL") or "سایت اقامتگاه"
    with store.conn() as c:
        v = facts.booking_view(c, _booking(c, bid))
    text = (f"{v['guest']} عزیز، سلام. امیدواریم روزهای {v['unit']} به شما خوش گذشته باشد. اگر چند دقیقه وقت دارید، "
            f"نظرتان را درباره‌ی اقامتتان در {site_url} (بخش «سفرهای من») بنویسید؛ برای ما و مهمان‌های بعدی ارزش زیادی دارد.\n"
            f"{info.person('host', s)}، {s['name']}")
    return {"text": text, "phone": v["phone"], "has_account": v["has_account"]}

@router.post("/bookings/{bid}/feedback")
def feedback_sent(bid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        _booking(c, bid)
        c.execute("UPDATE bookings SET feedback_asked = ? WHERE id = ?", (store.stamp(), bid))
        store.log(c, user, "feedback", "از مهمان نظر خواسته شد", bid)
    return {"ok": True}

class ManualIn(BaseModel):
    unit_id: int
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)
    adults: int = Field(2, ge=1, le=30)
    name: str = Field(min_length=3, max_length=60)
    phone: str = Field(max_length=20)
    source: str = "whatsapp"
    note: str = Field("", max_length=300)

@router.post("/bookings")
def add_booking(req: ManualIn, user: dict = Depends(ALL)):
    """A booking that came by phone, WhatsApp or Instagram, entered by the host: approved at once (waiting for its
    deposit), like a request the host said yes to. The guest can later make an account with the same mobile."""
    if req.source not in facts.SOURCES or req.source == "site":
        raise HTTPException(status_code=422, detail="راه رزرو را انتخاب کنید")
    a, d = stay(req.arrive, req.depart)
    phone = re.sub(r"\D", "", req.phone.translate(FA_DIGITS))
    if not re.fullmatch(r"09\d{9}", phone):
        raise HTTPException(status_code=422, detail="شماره‌ی همراه باید ۱۱ رقم و با ۰۹ شروع شود")
    with store.conn() as c:
        u = _unit(c, req.unit_id)
        why = facts.busy(c, u["id"], a, d)
        q = facts.quote(c, u, a, d, req.adults)
        if why or not q["ok"]:
            raise HTTPException(status_code=409, detail=why or q["why"])
        g = c.execute("SELECT id FROM guests WHERE phone = ?", (phone,)).fetchone()
        gid = g["id"] if g else c.execute("INSERT INTO guests (name, phone, created) VALUES (?,?,?)", (" ".join(req.name.split()), phone, store.today().isoformat())).lastrowid
        from datetime import datetime, timedelta
        due = min(datetime.fromisoformat(store.stamp()) + timedelta(hours=facts.settings(c)["deposit_hours"]), datetime.fromisoformat(a + " 12:00"))
        bid = c.execute("""INSERT INTO bookings (guest_id, unit_id, arrive, depart, adults, children, status, source, nights, total, deposit, deposit_due, note, created, decided)
                           VALUES (?,?,?,?,?,0,'approved',?,?,?,?,?,?,?,?)""",
                        (gid, u["id"], a, d, req.adults, req.source, json.dumps(q["nights"]), q["total"], q["deposit"], due.strftime("%Y-%m-%d %H:%M"),
                         req.note.strip(), store.stamp(), store.stamp())).lastrowid
        store.log(c, user, "book", f"رزرو از {facts.SOURCES[req.source]}: {u['name']}، {facts.stay_text({'arrive': a, 'depart': d})}، {q['total_text']}", bid)
    return {"id": bid}

class QuoteIn(BaseModel):
    arrive: str = Field(max_length=12)
    depart: str = Field(max_length=12)
    adults: int = Field(2, ge=1, le=30)

@router.post("/free")
def free(req: QuoteIn, user: dict = Depends(ALL)):
    a, d = stay(req.arrive, req.depart)
    with store.conn() as c:
        return facts.search(c, a, d, req.adults)

# ---------- reviews, guests, the website's words ----------

@router.get("/reviews")
def reviews(user: dict = Depends(ALL)):
    with store.conn() as c:
        return {"reviews": [facts.review_view(c, r) for r in c.execute("SELECT * FROM reviews ORDER BY status = 'waiting' DESC, at DESC LIMIT 60")],
                "rating": facts.rating(c), "feedback": facts.feedback_due(c)}

class ReviewIn(BaseModel):
    status: str
    reply: str = Field("", max_length=400)

@router.post("/reviews/{rid}")
def review_decide(rid: int, req: ReviewIn, user: dict = Depends(ALL)):
    """Show or hide a review on the website, with the host's reply. A hidden review stays in the panel."""
    if req.status not in ("shown", "hidden"):
        raise HTTPException(status_code=422, detail="وضعیت درست نیست")
    with store.conn() as c:
        r = c.execute("SELECT * FROM reviews WHERE id = ?", (rid,)).fetchone()
        if not r:
            raise HTTPException(status_code=404)
        c.execute("UPDATE reviews SET status = ?, reply = ? WHERE id = ?", (req.status, req.reply.strip() or None, rid))
        store.log(c, user, "review", f"نظر {r['stars']} ستاره {'در سایت نمایش داده شد' if req.status == 'shown' else 'پنهان شد'}" + (" با پاسخ میزبان" if req.reply.strip() else ""), r["booking_id"])
    return {"ok": True}

@router.get("/guests")
def guests(q: str = "", user: dict = Depends(ALL)):
    q = q.strip().translate(FA_DIGITS)
    with store.conn() as c:
        out = []
        for g in c.execute("SELECT * FROM guests WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC LIMIT 60", (f"%{q}%", f"%{q}%")):
            n = c.execute("SELECT COUNT(*) n, MAX(depart) last FROM bookings WHERE guest_id = ? AND status = 'confirmed'", (g["id"],)).fetchone()
            out.append({"id": g["id"], "name": g["name"], "phone": g["phone"], "account": bool(g["password"]), "stays": n["n"], "last": facts.jfull(n["last"]) if n["last"] else ""})
        return out

class SiteIn(BaseModel):
    tagline: str = Field(max_length=120)
    story: str = Field(max_length=1200)
    rules: str = Field(max_length=800)
    phone: str = Field(max_length=20)
    payment: str = Field(max_length=300)
    card: str = Field(max_length=60)
    extra_person: int = Field(ge=0, le=50_000_000)
    deposit: int = Field(ge=0, le=100)
    deposit_hours: int = Field(ge=1, le=96)
    min_weekend: int = Field(ge=1, le=7)

@router.get("/site")
def get_site(user: dict = Depends(ALL)):
    with store.conn() as c:
        return info.site() | facts.settings(c)

@router.post("/site")
def set_site(req: SiteIn, user: dict = Depends(HOST)):
    words = {k: getattr(req, k).strip() for k in ("tagline", "story", "rules", "phone", "payment", "card")}
    info.save(info.current(), words)
    with store.conn() as c:
        store.set_meta(c, "settings", json.dumps({k: getattr(req, k) for k in ("extra_person", "deposit", "deposit_hours", "min_weekend")}))
        store.log(c, user, "site", "متن سایت و قاعده‌های رزرو تغییر کرد")
    return {"ok": True}

# ---------- the floating assistant ----------

class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=500)

@router.post("/ask")
def ask(req: Ask, user: dict = Depends(ALL)):
    t = store.today().isoformat()
    with store.conn() as c:
        o = facts.overview(c)
        lines = [f"امروز {o['today_long']} {o['today']} است."] + [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]] + [a["title"] for a in o["alerts"]]
        for k in range(0, 7):
            n = facts.add(t, k)
            free_units = [u["name"] for u in c.execute("SELECT * FROM units WHERE active = 1") if not facts.busy(c, u["id"], n, facts.add(n, 1))]
            lines.append(f"شب {facts.jlong(n)}: {len(free_units)} واحد خالی" + (f" ({'، '.join(free_units)})" if free_units else ""))
    data = "\n".join(lines)
    words = [w for w in re.findall(r"[؀-ۿ‌]{3,}", req.question) if w not in ("چقدر", "چند", "کدام", "است", "داریم", "امشب")]
    hits = [l for l in lines if any(w in l for w in words)]
    fallback = "\n".join(hits[:6]) if hits else "پاسخ این سؤال در اطلاعات اقامتگاه پیدا نشد. درباره‌ی رزروها، شب‌های خالی و نظرها بپرسید."
    text, checked = _written(f"تو دستیار {info.current()['name']} هستی. به سؤال زیر فقط از روی «اطلاعات» جواب بده، کوتاه، حداکثر سه جمله، فارسی معیار. "
                             "عددها را دقیقاً همان‌طور که در اطلاعات آمده بنویس. اگر جواب در اطلاعات نیست، همین را بگو.", f"سؤال: {req.question}\n\nاطلاعات:\n{data}", fallback)
    return {"answer": text, "checked": checked}
