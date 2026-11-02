"""The real estate agency's endpoints, all under /estate. Logins, sessions and data are its own (estate.db); the
site's door (gate.py) and the card's login (access.py) cover these like every other path.

Roles: owner (مدیر بنگاه) sees everything, including the checks, the log and the settings; agent (مشاور املاک) works
listings, buyers, visits and deals (every listing and buyer is shared; «مال من» filters to their own). The model reads
pasted text and writes sentences; every number it writes is checked against facts computed by code, with a
code-written fallback. Nothing leaves the agency without a person: messages are drafts the agent sends.
"""
import re, threading
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from llm import ask_llm
from checks import only_known_numbers
from jalali import to_gregorian
from fabric.facts import money
from . import agency, store, demo, facts, read as reader

router = APIRouter(prefix="/estate")
_lock = threading.Lock()   # setup rebuilds everything at once
_cache = {}                # model texts, per day and data version

# ---------- logins ----------

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

ALL = require("owner", "agent")
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

# ---------- the agency this demo is for ----------

LOGINS = ["modir", "moshaver1", "moshaver2"]

@router.get("/info")
def info():
    """Public, before login: the setup and login pages. Nothing is given out before the first setup."""
    if not agency.is_set_up():
        return {"set_up": False}
    return {"set_up": True, "agency": agency.public(), "logins": LOGINS, "today": facts.jfull(store.today().isoformat())}

@router.get("/setup/default")
def setup_default():
    return {"agency": agency.DEFAULT}

class Setup(BaseModel):
    agency: dict

@router.post("/setup")
def setup(req: Setup):
    """Set up the demo for an agency: save the names and build six months of its work."""
    try:
        settings = agency.clean(req.agency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with _lock:
        agency.save(settings)
        demo.build()
        _cache.clear()
    return {"ok": True, "agency": agency.public()}

def reset():
    """The live demo starts every visit fresh (RESET_ON_LOAD): forget the agency and log everyone out."""
    with _lock:
        agency.forget()
        store.init()
        store.logout_all()
        _cache.clear()

def ensure_fresh():
    """On startup: the demo follows the real date, so data made on another day is rebuilt (KEEP_DB=1 keeps it)."""
    import os
    store.init()
    if agency.is_set_up() and store.get_meta("built_for") != store.today().isoformat() and os.getenv("KEEP_DB") != "1":
        demo.build()

ensure_fresh()

def _version():
    with store.conn() as c:
        n = c.execute("SELECT MAX(id) FROM events").fetchone()[0]
    return f"{store.today()}|{n}"

def _written(prompt, data, fallback, max_tokens=350):
    """Model text from computed facts, kept only if every number in it is in the facts.
    checked: True (the model's text passed), False (it failed the check), None (no model answer)."""
    try:
        text = ask_llm(prompt, data, max_tokens=max_tokens).strip()
    except Exception:
        return fallback, None
    if not text or not only_known_numbers(text, data):
        return fallback, False
    return text, True

def _agency():
    return agency.current()

# ---------- dashboards ----------

@router.get("/overview")
def overview(user: dict = Depends(OWNER)):
    with store.conn() as c:
        return facts.overview(c)

@router.get("/today")
def today_view(user: dict = Depends(ALL)):
    with store.conn() as c:
        return facts.agent_today(c, user)

@router.get("/brief")
def brief(user: dict = Depends(OWNER)):
    key = "brief|" + _version()
    if key in _cache:
        return _cache[key]
    with store.conn() as c:
        data, o = facts.brief_facts(c)
    fallback = (f"امروز {len(o['alerts'])} کار منتظر شماست. " + " ".join(f"{a['title']}." for a in o["alerts"][:2])) if o["alerts"] else "امروز مورد فوری نیست."
    s = _agency()
    text, checked = _written(
        f"تو دستیار {agency.person('owner', s)}، مدیر {s['name']} (بنگاه املاک) هستی. از روی اطلاعات زیر یک خلاصه‌ی صبحگاهی "
        "سه جمله‌ای به فارسی معیار، ساده و محترمانه بنویس (رسمی، نه محاوره‌ای).\n"
        "- جمله‌ی اول وضعیت فایل‌ها، متقاضیان و معامله‌های این ماه را بگوید.\n"
        "- جمله‌ی دوم و سوم مهم‌ترین کارهای شماره‌دار را با شماره‌ی فایل یا نام شخص بگوید.\n"
        "- عددها و مبلغ‌ها را دقیقاً همان‌طور که نوشته شده بنویس. عدد جدید نساز. سلام ننویس.",
        data, fallback)
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

@router.get("/agents")
def agents(user: dict = Depends(ALL)):
    with store.conn() as c:
        return [{"id": k, "name": v} for k, v in facts.agents(c).items()]

# ---------- settings and the deposit and rent tool ----------

class Settings(BaseModel):
    rate: float = Field(gt=0, le=10)
    sale_fee: float = Field(gt=0, le=5)
    rent_fee: float = Field(gt=0, le=100)

@router.get("/settings")
def get_settings(user: dict = Depends(ALL)):
    with store.conn() as c:
        return facts.settings(c)

@router.post("/settings")
def set_settings(req: Settings, user: dict = Depends(OWNER)):
    with store.conn() as c:
        for k, v in req.model_dump().items():
            store.set_meta(c, "set_" + k, v)
        store.log(c, user, "settings", f"تنظیمات تغییر کرد: نرخ تبدیل {req.rate:g}٪، کمیسیون فروش {req.sale_fee:g}٪، کمیسیون اجاره {req.rent_fee:g}٪")
        return facts.settings(c)

class Convert(BaseModel):
    deposit: int = Field(ge=0, le=10**12)
    rent: int = Field(ge=0, le=10**10)
    new_deposit: int = Field(ge=0, le=10**12)

@router.post("/convert")
def convert(req: Convert, user: dict = Depends(ALL)):
    with store.conn() as c:
        s = facts.settings(c)
    return facts.convert(req.deposit, req.rent, req.new_deposit, s["rate"])

# ---------- listings ----------

def _listing(c, lid):
    row = c.execute("SELECT * FROM listings WHERE id = ?", (lid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این فایل پیدا نشد")
    return dict(row)

def _flags(c, l, dups, called_missing):
    out = []
    if l["status"] == "active":
        if facts.days_ago(l["last_contact"]) >= facts.STALE_DAYS:
            out.append("بی‌تماس")
        if facts.report_due(l):
            out.append("گزارش مالک")
        if l["id"] in dups:
            out.append("تکراری؟")
        if l["id"] in called_missing:
            out.append("تطبیق بی‌تماس")
    return out

@router.get("/listings")
def listings(kind: str = "", hood: str = "", status: str = "active", mine: bool = False, user: dict = Depends(ALL)):
    q, args = "SELECT * FROM listings WHERE 1", []
    if kind in facts.KINDS:
        q += " AND kind = ?"; args.append(kind)
    if hood in agency.HOODS:
        q += " AND hood = ?"; args.append(hood)
    if status == "active":
        q += " AND status = 'active'"
    elif status == "closed":
        q += " AND status != 'active'"
    if mine:
        q += " AND agent_id = ?"; args.append(user["id"])
    with store.conn() as c:
        names = facts.agents(c)
        matches = facts.all_matches(c)
        count = {}
        for m in matches:
            count[m["listing"]["id"]] = count.get(m["listing"]["id"], 0) + 1
        missing = {m["listing"]["id"] for m in matches if not m["called"] and m["waiting"] >= facts.MISSED_DAYS}
        dups = {x["id"] for d in facts.duplicates(c) for x in (d["a"], d["b"])}
        rows = [dict(r) for r in c.execute(q + " ORDER BY created DESC, id DESC", args)]
        return [facts.listing_view(l, names, {"matches": count.get(l["id"], 0), "flags": _flags(c, l, dups, missing)}) for l in rows]

def _match_view(m, names, side):
    other = m["request"] if side == "listing" else m["listing"]
    head = ({"request_id": other["id"], "name": other["name"], "budget_text": facts.request_budget_text(other), "phone": other["phone"],
             "agent": names.get(other["agent_id"], "")} if side == "listing" else
            {"listing_id": other["id"], "title": facts.title(other), "price_text": facts.price_text(other), "agent": names.get(other["agent_id"], "")})
    return head | {"score": m["score"], "reasons": m["reasons"], "misses": m["misses"], "called": m["called"],
                   "waiting": m["waiting"], "listing_id": m["listing"]["id"], "request_id": m["request"]["id"]}

@router.get("/listings/{lid}")
def listing(lid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        names = facts.agents(c)
        l = _listing(c, lid)
        visits = [dict(v) | {"when": facts.when_text(v["at"]), "agent": names.get(v["agent_id"], "")} for v in c.execute(
            "SELECT v.*, r.name FROM visits v JOIN requests r ON r.id = v.request_id WHERE v.listing_id = ? ORDER BY v.at DESC", (lid,))]
        history = facts.events(c, 0, 400)
        dup = next((d for d in facts.duplicates(c) if lid in (d["a"]["id"], d["b"]["id"])), None)
        last = c.execute("SELECT * FROM reports WHERE listing_id = ? ORDER BY id DESC LIMIT 1", (lid,)).fetchone()
        return {"listing": facts.listing_view(l, names), "price": facts.price_check(c, l),
                "matches": [_match_view(m, names, "listing") for m in facts.matches_for_listing(c, lid)] if l["status"] == "active" else [],
                "visits": visits, "history": [e for e in history if e["listing_id"] == lid],
                "duplicate": {"other": dup["a"]["id"] if dup["b"]["id"] == lid else dup["b"]["id"], "why": dup["why"]} if dup else None,
                "report": {"due": facts.report_due(l), "last": facts.jdate(l["last_report"]) if l["last_report"] else None,
                           "text": last["text"] if last else None}}

HOOD_ERR = "محله را از فهرست انتخاب کنید"

class ListingIn(BaseModel):
    kind: str
    hood: str
    street: str = Field("", max_length=60)
    area: int = Field(ge=15, le=2000)
    rooms: int = Field(ge=0, le=10)
    floor: int = Field(ge=-2, le=60)
    floors: int | None = Field(None, ge=1, le=60)
    age: int = Field(ge=0, le=80)
    elevator: bool = False
    parking: bool = False
    storage: bool = False
    price: int = Field(0, ge=0, le=10**13)
    deposit: int = Field(0, ge=0, le=10**12)
    rent: int = Field(0, ge=0, le=10**10)
    owner_name: str = Field(min_length=2, max_length=60)
    owner_phone: str = Field("", max_length=20)
    note: str = Field("", max_length=500)

def _check_listing(req):
    if req.kind not in facts.KINDS:
        raise HTTPException(status_code=422, detail="نوع فایل را انتخاب کنید")
    if req.hood not in agency.HOODS:
        raise HTTPException(status_code=422, detail=HOOD_ERR)
    if req.kind == "sale" and req.price <= 0:
        raise HTTPException(status_code=422, detail="قیمت فروش را بنویسید")
    if req.kind == "rent" and req.deposit <= 0 and req.rent <= 0:
        raise HTTPException(status_code=422, detail="ودیعه یا اجاره را بنویسید")

@router.post("/listings")
def add_listing(req: ListingIn, user: dict = Depends(ALL)):
    _check_listing(req)
    t = store.today().isoformat()
    with store.conn() as c:
        cur = c.execute("""INSERT INTO listings (kind, hood, street, area, rooms, floor, floors, age, elevator, parking, storage, price, deposit, rent,
                           owner_name, owner_phone, note, agent_id, status, created, last_contact, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,'app')""",
                        (req.kind, req.hood, req.street.strip(), req.area, req.rooms, req.floor, req.floors, req.age, int(req.elevator), int(req.parking),
                         int(req.storage), req.price if req.kind == "sale" else 0, req.deposit if req.kind == "rent" else 0, req.rent if req.kind == "rent" else 0,
                         req.owner_name.strip(), re.sub(r"\D", "", req.owner_phone), req.note.strip(), user["id"], t, t))
        lid = cur.lastrowid
        l = _listing(c, lid)
        store.log(c, user, "listing", f"فایل {lid} ثبت شد: {facts.KINDS[req.kind]}، {facts.title(l)}، {facts.price_text(l)}", lid)
        n = len(facts.matches_for_listing(c, lid))
    return {"id": lid, "matches": n}

PRICE_WORDS = {"price": "قیمت", "deposit": "ودیعه", "rent": "اجاره"}

class Contact(BaseModel):
    status: str
    price: int | None = Field(None, ge=0, le=10**13)
    deposit: int | None = Field(None, ge=0, le=10**12)
    rent: int | None = Field(None, ge=0, le=10**10)
    note: str = Field("", max_length=300)

@router.post("/listings/{lid}/contact")
def contact(lid: int, req: Contact, user: dict = Depends(ALL)):
    """The agent called the owner: still available (maybe at a new price), sold, rented, or withdrawn."""
    if req.status not in facts.STATUS:
        raise HTTPException(status_code=422, detail="وضعیت را انتخاب کنید")
    t = store.today().isoformat()
    with store.conn() as c:
        l = _listing(c, lid)
        if l["status"] != "active":
            raise HTTPException(status_code=409, detail="این فایل بسته شده است")
        note = f" («{req.note.strip()}»)" if req.note.strip() else ""
        if req.status == "active":
            changes = []
            for k in ("price", "deposit", "rent"):
                v = getattr(req, k)
                if v is not None and v != l[k] and (l["kind"] == "sale") == (k == "price"):
                    changes.append(f"{PRICE_WORDS[k]} از {money(l[k])} به {money(v)}")
                    c.execute(f"UPDATE listings SET {k} = ? WHERE id = ?", (v, lid))
            c.execute("UPDATE listings SET last_contact = ? WHERE id = ?", (t, lid))
            store.log(c, user, "contact", f"فایل {lid}: مالک تأیید کرد هنوز {'برای فروش' if l['kind'] == 'sale' else 'برای اجاره'} است" +
                      (f"؛ {'، '.join(changes)}" if changes else "") + note, lid)
        else:
            c.execute("UPDATE listings SET status = ?, closed = ?, last_contact = ? WHERE id = ?", (req.status, t, t, lid))
            store.log(c, user, "status", f"فایل {lid}: {facts.STATUS[req.status]}{note}", lid)
    return {"ok": True}

@router.post("/listings/{lid}/report/draft")
def report_draft(lid: int, user: dict = Depends(ALL)):
    """The weekly report for the owner: numbers by code, sentences by the model, sent by the agent."""
    s = _agency()
    since = (store.today() - timedelta(days=30)).isoformat()
    with store.conn() as c:
        l = _listing(c, lid)
        ms = facts.matches_for_listing(c, lid)
        called = [m for m in ms if m["called"]]
        visits = [dict(v) for v in c.execute("SELECT * FROM visits WHERE listing_id = ? AND status = 'done' AND at >= ? ORDER BY at", (lid, since))]
        price = facts.price_check(c, l)
    lines = [f"فایل: {facts.title(l)}، {facts.price_text(l)}", f"مالک: {l['owner_name']}",
             f"متقاضیانی که با این واحد جور بودند: {len(ms)}", f"متقاضیانی که واحد به آن‌ها پیشنهاد شد: {len(called)}",
             f"بازدیدهای سی روز اخیر: {len(visits)}"]
    lines += [f"بازدید {facts.jdate(v['at'])}: {v['outcome']}" for v in visits if v["outcome"]]
    if price:
        lines.append(f"مقایسه‌ی قیمت: {price['text']}")
    data = "\n".join(lines)
    fallback = (f"{l['owner_name']} گرامی، سلام. گزارش فایل شما ({facts.title(l)}) در سی روز اخیر: واحد شما با {len(ms)} متقاضی جور بود، "
                f"به {len(called)} نفر پیشنهاد شد و {len(visits)} بازدید داشت."
                + (f" نظر بازدیدکنندگان: {'؛ '.join(v['outcome'] for v in visits if v['outcome'])}." if any(v["outcome"] for v in visits) else "")
                + f"\n{s['name']}")
    text, checked = _written(
        f"تو مشاور {s['name']} (بنگاه املاک) هستی. برای مالک این واحد یک پیام کوتاه گزارش بنویس: چند متقاضی پیدا شد، به چند نفر پیشنهاد شد، "
        "چند بازدید داشت و بازدیدکنندگان چه گفتند. اگر مقایسه‌ی قیمت آمده، یک جمله‌ی محترمانه درباره‌ی آن بگو. حداکثر پنج جمله، فارسی معیار و محترمانه. "
        f"با «{l['owner_name']} گرامی، سلام» شروع کن و با «{s['name']}» تمام کن. فقط از اطلاعات داده‌شده استفاده کن و عدد جدید نساز.",
        data, fallback)
    return {"text": text, "checked": checked, "data": lines}

class Sent(BaseModel):
    text: str = Field(min_length=5, max_length=3000)

@router.post("/listings/{lid}/report")
def report_sent(lid: int, req: Sent, user: dict = Depends(ALL)):
    t = store.today().isoformat()
    with store.conn() as c:
        _listing(c, lid)
        c.execute("INSERT INTO reports (listing_id, at, user_id, text) VALUES (?,?,?,?)", (lid, store.stamp(), user["id"], req.text.strip()))
        c.execute("UPDATE listings SET last_report = ? WHERE id = ?", (t, lid))
        store.log(c, user, "report", f"گزارش فایل {lid} برای مالک فرستاده شد", lid)
    return {"ok": True}

# ---------- reading pasted text ----------

class ReadIn(BaseModel):
    kind: str
    text: str = Field(min_length=5, max_length=3000)

@router.post("/read")
def read_text(req: ReadIn, user: dict = Depends(ALL)):
    if req.kind not in ("listing", "request"):
        raise HTTPException(status_code=422)
    out = reader.read(req.kind, req.text)
    f = out["fields"]
    if req.kind == "listing" and f.get("hood"):
        with store.conn() as c:
            names = facts.agents(c)
            like = []
            for l in c.execute("SELECT * FROM listings WHERE status = 'active' AND hood = ?", (f["hood"],)):
                same_phone = f.get("owner_phone") and l["owner_phone"] == f["owner_phone"]
                same_unit = f.get("area") and abs(l["area"] - f["area"]) <= 3 and (f.get("floor") is None or l["floor"] == f["floor"])
                if same_phone or same_unit:
                    like.append({"id": l["id"], "title": facts.title(dict(l)), "price_text": facts.price_text(dict(l)),
                                 "agent": names.get(l["agent_id"], ""), "why": "شماره‌ی مالک یکی است" if same_phone else "محله، متراژ و طبقه یکی است"})
        out["duplicates"] = like
    return out

# ---------- requests (buyers and renters) ----------

def _request(c, rid):
    row = c.execute("SELECT * FROM requests WHERE id = ?", (rid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این متقاضی پیدا نشد")
    return dict(row)

@router.get("/requests")
def requests(status: str = "open", mine: bool = False, kind: str = "", user: dict = Depends(ALL)):
    q, args = "SELECT * FROM requests WHERE 1", []
    if status == "open":
        q += " AND status = 'open'"
    elif status == "closed":
        q += " AND status != 'open'"
    if kind in facts.KINDS:
        q += " AND kind = ?"; args.append(kind)
    if mine:
        q += " AND agent_id = ?"; args.append(user["id"])
    with store.conn() as c:
        names = facts.agents(c)
        ms = facts.all_matches(c)
        count, waiting = {}, set()
        for m in ms:
            rid = m["request"]["id"]
            count[rid] = count.get(rid, 0) + 1
            if not m["called"]:
                waiting.add(rid)
        rows = [dict(r) for r in c.execute(q + " ORDER BY created DESC, id DESC", args)]
        return [facts.request_view(r, names, {"matches": count.get(r["id"], 0), "uncalled": r["id"] in waiting}) for r in rows]

@router.get("/requests/{rid}")
def request_detail(rid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        names = facts.agents(c)
        r = _request(c, rid)
        visits = [dict(v) | {"when": facts.when_text(v["at"]), "agent": names.get(v["agent_id"], "")} for v in c.execute(
            "SELECT v.*, l.hood, l.area, l.rooms FROM visits v JOIN listings l ON l.id = v.listing_id WHERE v.request_id = ? ORDER BY v.at DESC", (rid,))]
        return {"request": facts.request_view(r, names), "visits": visits,
                "matches": [_match_view(m, names, "request") for m in facts.matches_for_request(c, rid)] if r["status"] == "open" else [],
                "history": [e for e in facts.events(c, 0, 400) if e["request_id"] == rid]}

class RequestIn(BaseModel):
    kind: str
    name: str = Field(min_length=2, max_length=60)
    phone: str = Field("", max_length=20)
    hoods: list[str] = Field(min_length=1)
    budget: int = Field(0, ge=0, le=10**13)
    deposit: int = Field(0, ge=0, le=10**12)
    rent: int = Field(0, ge=0, le=10**10)
    rooms: int = Field(0, ge=0, le=10)
    area: int = Field(0, ge=0, le=2000)
    needs: list[str] = []
    note: str = Field("", max_length=500)

def add_request(c, req: RequestIn, agent_id, source, user):
    if req.kind not in facts.KINDS:
        raise HTTPException(status_code=422, detail="خرید یا اجاره را انتخاب کنید")
    hoods = [h for h in req.hoods if h in agency.HOODS]
    if not hoods:
        raise HTTPException(status_code=422, detail=HOOD_ERR)
    if req.kind == "sale" and req.budget <= 0:
        raise HTTPException(status_code=422, detail="سقف بودجه را بنویسید")
    if req.kind == "rent" and req.deposit <= 0 and req.rent <= 0:
        raise HTTPException(status_code=422, detail="سقف ودیعه یا اجاره را بنویسید")
    t = store.today().isoformat()
    cur = c.execute("""INSERT INTO requests (kind, name, phone, hoods, budget, deposit, rent, rooms, area, needs, note, agent_id, status, created, source)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'open',?,?)""",
                    (req.kind, req.name.strip(), re.sub(r"\D", "", req.phone), ",".join(hoods), req.budget if req.kind == "sale" else 0,
                     req.deposit if req.kind == "rent" else 0, req.rent if req.kind == "rent" else 0, req.rooms, req.area,
                     ",".join(n for n in req.needs if n in facts.FEATURES), req.note.strip(), agent_id, t, source))
    rid = cur.lastrowid
    r = _request(c, rid)
    store.log(c, user, "request" if source != "site" else "site", f"متقاضی جدید{' از سایت' if source == 'site' else ''}: {r['name']}، "
              f"{'خرید' if r['kind'] == 'sale' else 'اجاره'} در {'، '.join(hoods)}، {facts.request_budget_text(r)}", request_id=rid)
    return rid

@router.post("/requests")
def new_request(req: RequestIn, user: dict = Depends(ALL)):
    with store.conn() as c:
        rid = add_request(c, req, user["id"], "phone", user)
        n = len(facts.matches_for_request(c, rid))
    return {"id": rid, "matches": n}

class Close(BaseModel):
    status: str
    note: str = Field("", max_length=300)

@router.post("/requests/{rid}/close")
def close_request(rid: int, req: Close, user: dict = Depends(ALL)):
    if req.status not in ("lost",):
        raise HTTPException(status_code=422, detail="معامله را از «ثبت معامله» ثبت کنید")
    with store.conn() as c:
        r = _request(c, rid)
        if r["status"] != "open":
            raise HTTPException(status_code=409, detail="این درخواست بسته شده است")
        c.execute("UPDATE requests SET status = 'lost', closed = ? WHERE id = ?", (store.today().isoformat(), rid))
        store.log(c, user, "status", f"درخواست {r['name']} بسته شد: منصرف شد" + (f" («{req.note.strip()}»)" if req.note.strip() else ""), request_id=rid)
    return {"ok": True}

class Call(BaseModel):
    listing_id: int
    request_id: int
    outcome: str = Field("پیشنهاد شد", max_length=200)

@router.post("/calls")
def call(req: Call, user: dict = Depends(ALL)):
    """The agent offered this unit to this buyer (by phone or message)."""
    with store.conn() as c:
        l, r = _listing(c, req.listing_id), _request(c, req.request_id)
        c.execute("INSERT INTO calls (listing_id, request_id, at, user_id, outcome) VALUES (?,?,?,?,?)",
                  (l["id"], r["id"], store.stamp(), user["id"], req.outcome.strip()))
        store.log(c, user, "call", f"فایل {l['id']} به {r['name']} پیشنهاد شد: {req.outcome.strip()}", l["id"], r["id"])
    return {"ok": True}

# ---------- visits ----------

class VisitIn(BaseModel):
    listing_id: int
    request_id: int
    date: str = Field(pattern=r"^\d{4}/\d{1,2}/\d{1,2}$")   # Jalali «1405/08/12», from the date picker
    time: str = Field(pattern=r"^\d{1,2}:\d{2}$")

def _drafts(c, v):
    """The two confirmation messages, built by code: time, place without the exact address for the customer, and the
    customer's name for the owner. The agent sends them."""
    s = _agency()
    l, r = _listing(c, v["listing_id"]), _request(c, v["request_id"])
    agent = facts.agents(c).get(v["agent_id"], "")
    when = facts.when_text(v["at"])
    return {"customer": f"{r['name']} گرامی، سلام. بازدید واحد {facts.title(l)} ({l['street'] or l['hood']}) {when} هماهنگ شد. "
                        f"لطفاً اگر برنامه‌تان تغییر کرد خبر بدهید. {agent}، {s['name']}",
            "owner": f"{l['owner_name']} گرامی، سلام. برای واحد شما {when} بازدید هماهنگ شده است. بازدیدکننده: {r['name']}. "
                     f"{agent}، {s['name']}",
            "customer_phone": r["phone"], "owner_phone": l["owner_phone"]}

@router.get("/visits")
def visits(when: str = "upcoming", mine: bool = False, user: dict = Depends(ALL)):
    t = store.today().isoformat()
    q = """SELECT v.*, r.name, r.phone, l.hood, l.area, l.rooms, l.street, l.kind FROM visits v JOIN requests r ON r.id = v.request_id
           JOIN listings l ON l.id = v.listing_id WHERE """ + ("v.at >= ? AND v.status != 'cancelled'" if when == "upcoming" else "v.at < ?")
    args = [t]
    if mine:
        q += " AND v.agent_id = ?"; args.append(user["id"])
    q += " ORDER BY v.at" + ("" if when == "upcoming" else " DESC LIMIT 60")
    with store.conn() as c:
        names = facts.agents(c)
        return [dict(v) | {"when": facts.when_text(v["at"]), "agent": names.get(v["agent_id"], ""), "day": v["at"][:10]} for v in c.execute(q, args)]

@router.post("/visits")
def book_visit(req: VisitIn, user: dict = Depends(ALL)):
    try:
        y, m, d = (int(x) for x in req.date.split("/"))
        hour, minute = (int(x) for x in req.time.split(":"))
        at = datetime.combine(to_gregorian(y, m, d), datetime.min.time()).replace(hour=hour, minute=minute)
    except ValueError:
        raise HTTPException(status_code=422, detail="زمان بازدید درست نیست")
    when = at.strftime("%Y-%m-%d %H:%M")
    if at.date() < store.today():
        raise HTTPException(status_code=422, detail="زمان بازدید گذشته است")
    with store.conn() as c:
        l, r = _listing(c, req.listing_id), _request(c, req.request_id)
        if l["status"] != "active":
            raise HTTPException(status_code=409, detail="این فایل فعال نیست")
        cur = c.execute("INSERT INTO visits (listing_id, request_id, at, agent_id, status) VALUES (?,?,?,?, 'booked')",
                        (l["id"], r["id"], when, user["id"]))
        v = dict(c.execute("SELECT * FROM visits WHERE id = ?", (cur.lastrowid,)).fetchone())
        if not c.execute("SELECT 1 FROM calls WHERE listing_id = ? AND request_id = ?", (l["id"], r["id"])).fetchone():
            c.execute("INSERT INTO calls (listing_id, request_id, at, user_id, outcome) VALUES (?,?,?,?, 'بازدید هماهنگ شد')",
                      (l["id"], r["id"], store.stamp(), user["id"]))
        store.log(c, user, "visit", f"بازدید فایل {l['id']} برای {r['name']} {facts.when_text(when)} ثبت شد", l["id"], r["id"])
        return {"id": v["id"], "when": facts.when_text(when), "drafts": _drafts(c, v)}

def _visit(c, vid):
    row = c.execute("SELECT * FROM visits WHERE id = ?", (vid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="این بازدید پیدا نشد")
    return dict(row)

@router.get("/visits/{vid}/drafts")
def visit_drafts(vid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        return _drafts(c, _visit(c, vid))

@router.post("/visits/{vid}/confirm")
def confirm_visit(vid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        v = _visit(c, vid)
        c.execute("UPDATE visits SET status = 'confirmed' WHERE id = ?", (vid,))
        store.log(c, user, "visit", f"بازدید {facts.when_text(v['at'])} با مشتری و مالک تأیید شد", v["listing_id"], v["request_id"])
    return {"ok": True}

@router.post("/visits/{vid}/cancel")
def cancel_visit(vid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        v = _visit(c, vid)
        c.execute("UPDATE visits SET status = 'cancelled' WHERE id = ?", (vid,))
        store.log(c, user, "visit", f"بازدید {facts.when_text(v['at'])} لغو شد", v["listing_id"], v["request_id"])
    return {"ok": True}

class Outcome(BaseModel):
    text: str = Field(min_length=2, max_length=500)

def _outcome_by_code(text):
    """Without the model: the agent's own words as the note, and a next step from a few plain words in them."""
    t = text
    m = re.search(r"(شنبه|یکشنبه|دوشنبه|سه‌شنبه|سه شنبه|چهارشنبه|پنجشنبه|پنج‌شنبه|جمعه|فردا|پس‌فردا|هفته‌ی بعد|هفته بعد)", t)
    if re.search(r"پیشنهاد|قیمت|چانه|تخفیف", t):
        step = "پیشنهاد مشتری را به مالک بگویید"
    elif re.search(r"دوباره|دوم|همسر|خانواده|پدر|مادر", t):
        step = "بازدید دوم را هماهنگ کنید"
    elif re.search(r"نپسندید|کم|کوچک|تاریک|بد", t):
        step = "فایل‌های دیگر را به مشتری پیشنهاد دهید"
    else:
        step = "با مشتری تماس بگیرید"
    return text.strip(), step + (f" ({m[1]})" if m else "")

@router.post("/visits/{vid}/outcome")
def visit_outcome(vid: int, req: Outcome, user: dict = Depends(ALL)):
    """One line from the agent after the visit; the model turns it into a short note and a next step."""
    with store.conn() as c:
        v = _visit(c, vid)
    note, step = _outcome_by_code(req.text)
    try:
        out = ask_llm("یک مشاور املاک پس از بازدید یک خط نوشته است. دو خط فارسی معیار بنویس: خط اول «یادداشت:» و یک جمله‌ی کوتاه از آنچه گذشت، "
                      "خط دوم «گام بعد:» و یک کار مشخص با زمانش اگر گفته شده. فقط از همین متن استفاده کن و عدد یا مبلغ جدید نساز.", req.text, max_tokens=120)
        mn, ms = re.search(r"یادداشت:\s*(.+)", out), re.search(r"گام بعد:\s*(.+)", out)
        if mn and ms and only_known_numbers(out, req.text):
            note, step = mn[1].strip(), ms[1].strip()
    except Exception:
        pass
    with store.conn() as c:
        c.execute("UPDATE visits SET status = 'done', outcome = ?, note = ?, next_step = ? WHERE id = ?", (req.text.strip(), note, step, vid))
        r = _request(c, v["request_id"])
        store.log(c, user, "visit", f"نتیجه‌ی بازدید فایل {v['listing_id']} با {r['name']}: {note}", v["listing_id"], v["request_id"])
    return {"note": note, "next_step": step}

# ---------- deals ----------

class Preview(BaseModel):
    kind: str
    price: int = Field(0, ge=0, le=10**13)
    deposit: int = Field(0, ge=0, le=10**12)
    rent: int = Field(0, ge=0, le=10**10)
    agents: list[int] = []

@router.post("/deals/preview")
def preview(req: Preview, user: dict = Depends(ALL)):
    if req.kind not in facts.KINDS:
        raise HTTPException(status_code=422)
    with store.conn() as c:
        s, names = facts.settings(c), facts.agents(c)
    fee = facts.commission(req.kind, req.price, req.deposit, req.rent, s)
    parts = facts.split(fee["total"], req.agents)
    return fee | {"split": [{"id": k, "name": names.get(k, ""), "amount": v, "text": money(v)} for k, v in parts.items() if k],
                  "total_text": money(fee["total"]), "each_text": money(fee["each"])}

class DealIn(BaseModel):
    listing_id: int
    request_id: int | None = None
    buyer: str = Field(min_length=2, max_length=60)
    price: int = Field(0, ge=0, le=10**13)
    deposit: int = Field(0, ge=0, le=10**12)
    rent: int = Field(0, ge=0, le=10**10)
    agents: list[int] = Field(min_length=1)
    commission: int = Field(ge=0, le=10**11)

@router.post("/deals")
def close_deal(req: DealIn, user: dict = Depends(ALL)):
    t = store.today().isoformat()
    with store.conn() as c:
        l = _listing(c, req.listing_id)
        if l["status"] != "active":
            raise HTTPException(status_code=409, detail="این فایل فعال نیست")
        if l["kind"] == "sale" and req.price <= 0:
            raise HTTPException(status_code=422, detail="قیمت نهایی را بنویسید")
        if l["kind"] == "rent" and req.deposit <= 0 and req.rent <= 0:
            raise HTTPException(status_code=422, detail="ودیعه و اجاره‌ی نهایی را بنویسید")
        names = facts.agents(c)
        ids = [a for a in req.agents if a in names]
        if not ids:
            raise HTTPException(status_code=422, detail="مشاوران معامله را انتخاب کنید")
        expected = facts.commission(l["kind"], req.price, req.deposit, req.rent, facts.settings(c))["total"]
        cur = c.execute("""INSERT INTO deals (kind, listing_id, request_id, date, hood, area, age, price, deposit, rent, buyer, seller, agents, commission, expected)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (l["kind"], l["id"], req.request_id, t, l["hood"], l["area"], l["age"], req.price if l["kind"] == "sale" else 0,
                         req.deposit if l["kind"] == "rent" else 0, req.rent if l["kind"] == "rent" else 0, req.buyer.strip(), l["owner_name"],
                         ",".join(map(str, ids)), req.commission, expected))
        c.execute("UPDATE listings SET status = ?, closed = ? WHERE id = ?", ("sold" if l["kind"] == "sale" else "rented", t, l["id"]))
        if req.request_id:
            c.execute("UPDATE requests SET status = 'won', closed = ? WHERE id = ? AND status = 'open'", (t, req.request_id))
        price = money(req.price) if l["kind"] == "sale" else f"ودیعه {money(req.deposit)}، اجاره {money(req.rent)}"
        store.log(c, user, "deal", f"معامله‌ی فایل {l['id']} ثبت شد: {req.buyer.strip()}، {price}، کمیسیون {money(req.commission)}", l["id"], req.request_id)
    return {"id": cur.lastrowid, "below_tariff": req.commission < expected * 0.9}

@router.get("/deals")
def deals(user: dict = Depends(ALL)):
    with store.conn() as c:
        names = facts.agents(c)
        rows = [dict(d) for d in c.execute("SELECT * FROM deals ORDER BY date DESC, id DESC LIMIT 80")]
        start = facts.month_start()
        month = [d for d in rows if d["date"] >= start]
    def view(d):
        price = money(d["price"]) if d["kind"] == "sale" else f"ودیعه {money(d['deposit'])}، اجاره {money(d['rent'])}"
        return d | {"kind_text": facts.KINDS[d["kind"]], "date_text": facts.jdate(d["date"]), "price_text": price, "fee_text": money(d["commission"]),
                    "agents_text": "، ".join(names.get(int(i), "") for i in (d["agents"] or "").split(",") if i),
                    "below": bool(d["expected"]) and d["commission"] < d["expected"] * 0.9}
    total = sum(d["commission"] for d in month)
    return {"items": [view(d) for d in rows], "month": {"count": len(month), "fee": total, "fee_text": money(total),
                                                        "how": [f"{facts.jfull(d['date'])} · فایل {d['listing_id'] or '-'} · {money(d['commission'])}" for d in month]
                                                        + [f"= جمع: {money(total)}"]}}

# ---------- the floating assistant ----------

class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=500)

@router.post("/ask")
def ask(req: Ask, user: dict = Depends(ALL)):
    with store.conn() as c:
        data = facts.ask_facts(c)
    words = [w for w in re.findall(r"[؀-ۿ‌]{3,}", req.question) if w not in ("چقدر", "چند", "است", "کدام", "داریم", "هست")]
    hits = [l for l in data.splitlines() if any(w in l for w in words)]
    fallback = "\n".join(hits[:4]) if hits else "پاسخ این سؤال در اطلاعات بنگاه پیدا نشد. سؤال را درباره‌ی فایل‌ها، محله‌ها، متقاضیان، بازدیدها یا معامله‌ها بپرسید."
    text, checked = _written(
        f"تو دستیار {_agency()['name']} (بنگاه املاک) هستی. به سؤال زیر فقط از روی «اطلاعات» جواب بده، کوتاه و ساده، حداکثر سه جمله، فارسی معیار. "
        "عددها و مبلغ‌ها را دقیقاً همان‌طور که در اطلاعات آمده بنویس. اگر جواب در اطلاعات نیست، همین را بگو.",
        f"سؤال: {req.question}\n\nاطلاعات:\n{data}", fallback)
    return {"answer": text, "checked": checked}
