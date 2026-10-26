"""The fabric assistant's endpoints, all under /fabric. Logins, sessions and data are its own (fabric.db);
the site's door (gate.py) covers these like every other path.

Roles: owner (صاحب کار) sees everything; seller (فروشنده) works the phone desk and the stock;
accountant (حسابدار) works cheques, debts and reminder messages. The model writes text only: every
number in what it writes is checked against facts computed by code, with a code-written fallback.
"""
import base64, io, json, os, re, shutil, threading
from datetime import date, timedelta
from urllib.parse import quote
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from llm import ask_llm, ask_json
from checks import only_known_numbers, numbers
from . import business, store, excel, facts
from .facts import money, meters, jday

router = APIRouter(prefix="/fabric")
_lock = threading.Lock()          # setup, upload and invoices change files and data together
_cache = {}                       # model texts, per day and data version

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

ALL = require("owner", "seller", "accountant")
OWNER = require("owner")
DESK = require("owner", "seller")
BOOKS = require("owner", "accountant")

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

# ---------- the business this demo is for ----------

LOGINS = ["sahebkar", "forooshande", "hesabdar"]

@router.get("/info")
def info():
    """Public, before login: the setup and login pages. Nothing is given out before the first setup."""
    if not business.is_set_up():
        return {"set_up": False}
    return {"set_up": True, "business": business.public(), "logins": LOGINS}

@router.get("/setup/default")
def setup_default():
    return {"business": business.DEFAULT}

class Setup(BaseModel):
    business: dict

@router.post("/setup")
def setup(req: Setup):
    """Set up the demo for a wholesaler: save the names, make the three Excel files and read them in."""
    try:
        settings = business.clean(req.business)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with _lock:
        business.save(settings)
        result = excel.build()
        _cache.clear()
    return {"ok": True, "business": business.public(), "read": result}

def reset():
    """The live demo starts every visit fresh (RESET_ON_LOAD): forget the business and log everyone out."""
    with _lock:
        business.forget()
        store.init()
        store.logout_all()
        _cache.clear()

def ensure_fresh():
    """On startup: the demo follows the real date, so data made on another day is rebuilt (KEEP_DB=1 keeps it)."""
    store.init()
    if not business.is_set_up():
        return
    stale = store.get_meta("built_for") != excel.today().isoformat() and os.getenv("KEEP_DB") != "1"
    if stale or not all(os.path.exists(excel.path(k)) for k in excel.FILES):
        excel.build()

ensure_fresh()

def _version():
    with store.conn() as c:
        n = c.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    return f"{excel.today()}|{store.get_meta('imported_at')}|{n}"

def _written(prompt, data, fallback, max_tokens=350):
    """Model text from computed facts, kept only if every number in it is in the facts.
    checked: True (the model's text passed), False (it failed the check), None (the model did not answer)."""
    try:
        text = ask_llm(prompt, data, max_tokens=max_tokens).strip()
    except Exception:
        return fallback, None
    if not text or not only_known_numbers(text, data):
        return fallback, False
    return text, True

# ---------- owner ----------

@router.get("/overview")
def overview(user: dict = Depends(OWNER)):
    with store.conn() as c:
        o = facts.overview(c)
        return o | {"how": facts.overview_how(c, o)}

@router.get("/brief")
def brief(user: dict = Depends(OWNER)):
    key = "brief|" + _version()
    if key not in _cache:
        with store.conn() as c:
            o = facts.overview(c)
        data = facts.brief_facts(o)
        fallback = " ".join(f"{a['title']}." for a in o["alerts"][:3]) or "امروز مورد فوری نیست."
        s = business.current()
        _cache[key] = _written(
            f"تو دستیار {business.person('owner', s)}، صاحب {s['name']} (عمده‌فروشی پارچه) هستی. از روی اطلاعات زیر یک خلاصه صبحگاهی "
            "سه جمله‌ای به فارسی ساده و محاوره‌ی محترمانه بنویس.\n"
            "- جمله اول فروش امروز و این ماه را با ماه قبل مقایسه کند.\n"
            "- جمله دوم و سوم مهم‌ترین موردهای شماره‌دار را با اسم شخص یا جنس بگوید.\n"
            "- مبلغ‌ها را دقیقاً همان‌طور که نوشته شده بنویس (مثلاً «۱۲۸ میلیون تومان»). عدد جدید نساز. سلام ننویس.",
            data, fallback)
    text, checked = _cache[key]
    return {"text": text, "checked": checked}

# ---------- customers and the phone desk ----------

@router.get("/customers")
def customer_list(q: str = "", user: dict = Depends(ALL)):
    with store.conn() as c:
        rows = facts.customers(c).values()
    words = facts.words(q)
    rows = [r for r in rows if all(w in f"{r['name']} {r['shop']} {r['city']} {r['phone']}" for w in words)]
    rows.sort(key=lambda r: (-r["bought_90"], r["name"]))
    return [{k: r[k] for k in ("id", "name", "shop", "city", "phone", "debt", "open_cheques", "bounced", "credit_limit",
                               "room", "last_buy", "silent_days", "quiet")} for r in rows[:40]]

@router.get("/customers/{cid}")
def customer(cid: int, user: dict = Depends(ALL)):
    with store.conn() as c:
        card = facts.card(c, cid)
    if not card:
        raise HTTPException(status_code=404, detail="این مشتری پیدا نشد")
    return card

UNITS = {"توپ": "roll", "طاقه": "roll", "رول": "roll", "متر": "meter"}
QTY = r"(\d+(?:\.\d+)?)"

def parse_note(note):
    """'3 توپ کتان آبی و 20 متر مخمل زرشکی' -> [{qty: 3, unit: roll, text: 'کتان آبی'}, ...]
    The seller types what they hear on the phone; this reads it without the model."""
    text = note.translate(excel.FA_DIGITS).replace("\n", "،")
    parts = re.split(r"[،,;؛]|\s+و\s+(?=\d)|\s+(?=\d+\s*(?:توپ|طاقه|رول|متر)\b)", text)
    items = []
    for part in parts:
        m = re.search(QTY + r"\s*(توپ|طاقه|رول|متر)?\s*(.*)", part.strip())
        if not m or not m.group(3).strip():
            continue
        items.append({"qty": float(m.group(1)), "unit": UNITS.get(m.group(2) or "توپ"), "text": m.group(3).strip()})
    return items

def read_order(note):
    """The model reads the order first (it copes with free wording); its quantities must be in the note,
    otherwise the plain reading above is used."""
    try:
        data = ask_json('از متن سفارش تلفنی پارچه، اقلام را دربیاور. خروجی: {"items": [{"qty": عدد, "unit": "توپ" یا "متر", "text": "شرح جنس و رنگ و عرض"}]}', note, max_tokens=400)
    except Exception:
        data = None
    items = []
    for it in (data or {}).get("items") or []:
        try:
            qty = float(str(it.get("qty")).translate(excel.FA_DIGITS))
        except (TypeError, ValueError):
            return parse_note(note), False
        if str(int(qty) if qty == int(qty) else qty) not in numbers(note) or not str(it.get("text") or "").strip():
            return parse_note(note), False
        items.append({"qty": qty, "unit": UNITS.get(str(it.get("unit")), "roll"), "text": str(it["text"]).strip()})
    return (items, True) if items else (parse_note(note), False)

class Order(BaseModel):
    customer_id: int
    note: str = Field(min_length=1, max_length=1000)

def price_lines(c, wanted):
    """[{code, rolls?, meters?}] -> priced lines from the stock file's prices, with stock checks."""
    prods = {p["code"]: p for p in facts.products(c)}
    lines, warnings = [], []
    for w in wanted:
        p = prods.get(w["code"])
        if not p:
            continue
        rolls = int(w.get("rolls") or 0)
        m = rolls * p["roll_meters"] if rolls else float(w.get("meters") or 0)
        if m <= 0:
            continue
        amount = int(round(m * p["sell_price"] / 1000) * 1000)
        line = {"code": p["code"], "title": p["title"], "rolls": rolls, "meters": m, "price": p["sell_price"], "amount": amount,
                "stock_meters": p["meters"], "stock_rolls": p["rolls"], "short": m > p["meters"]}
        if line["short"]:
            warnings.append({"tone": "danger", "text": f"از {p['title']} فقط {p['rolls']} توپ ({meters(p['meters'])}) موجود است."})
        elif p["meters"] - m <= 0:
            warnings.append({"tone": "warning", "text": f"این سفارش همه‌ی {p['title']} انبار را می‌برد. وقت سفارش به {p['supplier']} است."})
        elif p["meters"] - m < p["per_day"] * 3 and p["per_day"]:
            warnings.append({"tone": "warning", "text": f"بعد از این سفارش از {p['title']} فقط {meters(p['meters'] - m)} می‌ماند. وقت سفارش به {p['supplier']} است."})
        lines.append(line)
    return lines, warnings

def credit_warnings(c, cid, total):
    row = facts.customers(c)[cid]
    out = facts.customer_warnings(row, [dict(r) for r in c.execute(
        "SELECT number, bank, amount, due, status FROM cheques_in WHERE customer_id = ? AND status = 'برگشتی'", (cid,))])
    if row["room"] >= 0 and total > row["room"]:
        out.append({"tone": "warning", "text": f"با این فاکتور ({money(total)}) از سقف اعتبارش {money(total - row['room'])} جلو می‌زند، اگر نقد نخرد."})
    return [w for w in out if w["tone"] != "info"]

@router.post("/order/read")
def order_read(req: Order, user: dict = Depends(DESK)):
    """The seller's note -> a draft invoice: each item matched to a product in stock, priced, checked."""
    with store.conn() as c:
        if not c.execute("SELECT 1 FROM customers WHERE id = ?", (req.customer_id,)).fetchone():
            raise HTTPException(status_code=404, detail="این مشتری پیدا نشد")
        items, by_model = read_order(req.note)
        wanted, unmatched = [], []
        for it in items:
            hits = facts.search_products(c, it["text"], limit=4)
            if not hits:
                unmatched.append({"text": it["text"], "options": []})
                continue
            p = hits[0]
            if it["unit"] == "roll":
                wanted.append({"code": p["code"], "rolls": int(it["qty"]), "asked": it["text"],
                               "options": [{"code": h["code"], "title": h["title"]} for h in hits]})
            else:
                wanted.append({"code": p["code"], "meters": it["qty"], "asked": it["text"],
                               "options": [{"code": h["code"], "title": h["title"]} for h in hits]})
        lines, warnings = price_lines(c, wanted)
        for line, w in zip(lines, wanted):
            line["asked"], line["options"] = w["asked"], w["options"]
        total = sum(l["amount"] for l in lines)
        warnings = credit_warnings(c, req.customer_id, total) + warnings
    return {"lines": lines, "unmatched": unmatched, "total": total, "warnings": warnings, "by_model": by_model}

class ConfirmLine(BaseModel):
    code: str
    rolls: int = Field(default=0, ge=0, le=500)
    meters: float = Field(default=0, ge=0, le=50000)

class Confirm(BaseModel):
    customer_id: int
    lines: list[ConfirmLine] = Field(min_length=1, max_length=30)
    payment: str
    cheque_days: int = Field(default=45, ge=0, le=365)
    cheque_bank: str = Field(default="", max_length=30)
    cheque_number: str = Field(default="", max_length=20)

@router.post("/order/confirm")
def order_confirm(req: Confirm, user: dict = Depends(DESK)):
    """The seller approved the draft: one invoice in the database and in all three Excel files."""
    with _lock:
        return make_invoice(user, req.customer_id, [l.model_dump() for l in req.lines], req.payment,
                            req.cheque_days, req.cheque_bank, req.cheque_number)

def make_invoice(user, customer_id, wanted, payment, cheque_days=45, cheque_bank="", cheque_number="", origin=""):
    """One invoice in the database and in all three Excel files (call with _lock held). Used by the phone desk
    and by a website order once it is paid. Prices and stock are worked out here from the stock data, never
    taken from the browser. origin: a few words for the event log, e.g. «از سفارش سایت ۱۰۰۱»."""
    if payment not in ("نقد", "چک", "نسیه"):
        raise HTTPException(status_code=400, detail="نوع پرداخت را انتخاب کنید")
    with store.conn() as c:
        cust = c.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not cust:
            raise HTTPException(status_code=404, detail="این مشتری پیدا نشد")
        lines, _ = price_lines(c, wanted)
        if not lines:
            raise HTTPException(status_code=400, detail="فاکتور قلمی ندارد")
        short = [l["title"] for l in lines if l["short"]]
        if short:
            raise HTTPException(status_code=400, detail=f"موجودی {short[0]} کافی نیست")
        d = excel.today()
        no = (c.execute("SELECT MAX(id) FROM invoices").fetchone()[0] or 1400) + 1
        total = sum(l["amount"] for l in lines)
        seller = business.current()["seller_name"]
        c.execute("INSERT INTO invoices (id, date, customer_id, seller, payment, total, source) VALUES (?,?,?,?,?,?, 'app')",
                  (no, d.isoformat(), cust["id"], seller, payment, total))
        for l in lines:
            c.execute("INSERT INTO invoice_lines (invoice_id, product_code, rolls, meters, price, amount) VALUES (?,?,?,?,?,?)",
                      (no, l["code"], l["rolls"], l["meters"], l["price"], l["amount"]))
            c.execute("UPDATE products SET meters = MAX(0, meters - ?), rolls = MAX(0, rolls - ?) WHERE code = ?",
                      (l["meters"], l["rolls"], l["code"]))
        cheque = None
        if payment == "چک":
            cheque = {"number": cheque_number.strip() or "ثبت نشده", "bank": cheque_bank.strip() or "نامشخص",
                      "amount": total, "due": d + timedelta(days=cheque_days)}
            c.execute("INSERT INTO cheques_in (number, bank, customer_id, amount, due, status) VALUES (?,?,?,?,?, 'در جریان')",
                      (cheque["number"], cheque["bank"], cust["id"], total, cheque["due"].isoformat()))
    excel.add_invoice(no, d, cust["name"], lines, payment, seller, cheque)
    # what changed where, one line per file: shown to the seller now and kept in the event log
    rolls = sum(l["rolls"] for l in lines)
    steps = [{"file": "فروش", "text": f"{len(lines)} ردیف برای فاکتور {no} اضافه شد"},
             {"file": "انبار", "text": (f"{rolls} توپ، " if rolls else "") + f"{meters(sum(l['meters'] for l in lines))} از موجودی کم شد"}]
    if cheque:
        steps.append({"file": "حسابداری", "text": f"چک {money(total)} با سررسید {jday(cheque['due'].isoformat())} ثبت شد"})
    with store.conn() as c:
        store.log(c, user, "invoice", f"فاکتور {no} برای {cust['name']} ثبت شد · {money(total)} · {payment}" + (f" · {origin}" if origin else ""),
                  {"files": [x["file"] for x in steps], "steps": steps})
    _cache.clear()
    return {"invoice": no, "total": total, "files": [x["file"] for x in steps], "steps": steps}

# ---------- stock ----------

@router.get("/stock")
def stock(q: str = "", user: dict = Depends(ALL)):
    with store.conn() as c:
        rows = facts.search_products(c, q, limit=60) if q.strip() else facts.products(c)
    rows.sort(key=lambda p: (not p["low"], not p["dead"], p["days_left"] if p["days_left"] is not None else 9999))
    return rows

# ---------- money: cheques, debts, reminders ----------

@router.get("/money")
def money_view(user: dict = Depends(BOOKS)):
    with store.conn() as c:
        week = facts.money_week(c)
        month = facts.money_week(c, 30)
        rows = facts.customers(c)
        debtors = sorted((r for r in rows.values() if r["debt"] > 0 or r["bounced"]), key=lambda r: (-r["bounced"], -r["debt"]))
        sent = {r["customer_id"]: r["sent_at"] for r in c.execute("SELECT customer_id, MAX(sent_at) sent_at FROM reminders GROUP BY customer_id")}
        return {"week": week, "month": {k: month[k] for k in ("in_total", "out_total", "left", "days")}, "bounced": facts.bounced(c),
                "debtors": [{k: r[k] for k in ("id", "name", "shop", "city", "phone", "debt", "bounced", "open_cheques", "credit_limit", "room", "last_buy")}
                            | {"reminded": sent.get(r["id"])} for r in debtors[:20]]}

class Reminder(BaseModel):
    customer_id: int

def _reminder_facts(c, cid):
    """The facts for one reminder, and the same facts as plain sentences for the code-written fallback."""
    row = facts.customers(c).get(cid)
    if not row:
        raise HTTPException(status_code=404, detail="این مشتری پیدا نشد")
    lines, said = [f"مشتری: {row['name']}، {row['shop']}، {row['city']}"], []
    for q in facts.bounced(c):
        if q["customer_id"] == cid:
            lines.append(f"چک برگشتی: {money(q['amount'])}، بانک {q['bank']}، سررسید {q['due_text']}")
            said.append(f"چک {money(q['amount'])} شما (بانک {q['bank']}، سررسید {q['due_text']}) برگشت خورده است")
    if row["debt"] - row["bounced"] > 0:
        lines.append(f"مانده‌ی حساب نسیه: {money(row['debt'] - row['bounced'])}")
        said.append(f"مانده‌ی حساب نسیه‌ی شما {money(row['debt'] - row['bounced'])} است")
    return row, "\n".join(lines), said

@router.post("/reminders/draft")
def reminder_draft(req: Reminder, user: dict = Depends(BOOKS)):
    """A polite payment reminder (SMS) for the accountant to read and send. Numbers are checked."""
    with store.conn() as c:
        row, data, said = _reminder_facts(c, req.customer_id)
    s = business.current()
    fallback = f"{row['name']} عزیز، سلام. " + "؛ ".join(said) + f". لطفاً برای تسویه با ما تماس بگیرید. با احترام، {s['name']}"
    text, checked = _written(
        f"تو حسابدار {s['name']} (عمده‌فروشی پارچه در {s['place']}) هستی. یک پیامک کوتاه (حداکثر سه جمله) و بسیار محترمانه "
        "برای یادآوری پرداخت به این مشتری بنویس. لحن دوستانه‌ی بازاری، بدون تهدید. مبلغ‌ها را دقیقاً همان‌طور که نوشته شده بیاور. "
        f"در پایان بنویس: با احترام، {s['name']}",
        data, fallback, max_tokens=250)
    return {"text": text, "checked": checked}

class ReminderSent(BaseModel):
    customer_id: int
    text: str = Field(min_length=1, max_length=1000)

@router.post("/reminders")
def reminder_sent(req: ReminderSent, user: dict = Depends(BOOKS)):
    """The accountant sent it (the demo sends nothing out); we note when, so the list shows it."""
    with store.conn() as c:
        c.execute("INSERT INTO reminders (customer_id, text, sent_at) VALUES (?,?,?)", (req.customer_id, req.text, store.stamp()))
        who = c.execute("SELECT name FROM customers WHERE id = ?", (req.customer_id,)).fetchone()
        store.log(c, user, "reminder", f"پیامک یادآوری برای {who['name'] if who else 'مشتری'} فرستاد")
    return {"ok": True}

# ---------- the three Excel files ----------

@router.get("/files")
def files(user: dict = Depends(ALL)):
    out = []
    for key, (disk, name) in excel.FILES.items():
        p = excel.path(key)
        st = os.stat(p) if os.path.exists(p) else None
        out.append({"key": key, "name": name, "size": st.st_size if st else 0,
                    "sheets": [{"name": s["name"], "total": s["total"]} for s in excel.preview(key, 0)] if st else []})
    with store.conn() as c:
        notes = [r["note"] for r in c.execute("SELECT note FROM import_notes ORDER BY id")]
    return {"files": out, "notes": notes, "imported_at": store.get_meta("imported_at")}

def _key(key):
    if key not in excel.FILES:
        raise HTTPException(status_code=404, detail="این فایل وجود ندارد")
    return key

@router.get("/files/{key}/preview")
def file_preview(key: str, user: dict = Depends(ALL)):
    return excel.preview(_key(key))

@router.get("/files/{key}/download")
def file_download(key: str, user: dict = Depends(ALL)):
    return FileResponse(excel.path(_key(key)), filename=excel.FILES[key][1],
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

class Upload(BaseModel):
    data: str = Field(max_length=8_000_000)   # the file, base64; about 6 MB at most

@router.post("/files/{key}")
def file_upload(key: str, req: Upload, user: dict = Depends(require("owner", "accountant"))):
    """Replace one workbook with the person's own version and read everything again. If it can't be read,
    the old file comes back and nothing changes."""
    _key(key)
    try:
        raw = base64.b64decode(req.data, validate=True)
    except ValueError:
        raise HTTPException(status_code=400, detail="فایل خراب است")
    if not raw.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="فقط فایل اکسل (xlsx) قبول می‌شود")
    p = excel.path(key)
    tables = {"products": "جنس", "invoices": "فاکتور", "customers": "مشتری", "receipts": "دریافتی",
              "cheques_in": "چک دریافتی", "cheques_out": "چک پرداختی", "stock_in": "ورود کالا", "cash_deposits": "واریز صندوق"}
    def counts():
        with store.conn() as c:
            return {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    with _lock:
        before = counts()
        shutil.copy(p, p + ".bak")
        with open(p, "wb") as f:
            f.write(raw)
        try:
            result = excel.import_all()
        except Exception as e:
            shutil.move(p + ".bak", p)
            raise HTTPException(status_code=400, detail=str(e) if isinstance(e, ValueError) else "این فایل خوانده نشد")
        os.remove(p + ".bak")
        after = counts()
        changes = [f"{tables[t]}: {before[t]} ← {after[t]}" for t in tables if before[t] != after[t]]
        name = excel.FILES[key][1].replace(".xlsx", "")
        with store.conn() as c:
            store.log(c, user, "upload", f"فایل {name} را با نسخه‌ی خودش عوض کرد" + ("" if changes else " (تعداد ردیف‌ها همان ماند)"),
                      {"files": [name], "changes": changes})
        _cache.clear()
    return result | {"changes": changes}

# ---------- do the files agree, who did what, reports ----------

@router.get("/reconcile")
def reconcile(user: dict = Depends(BOOKS)):
    with store.conn() as c:
        return facts.reconcile(c)

@router.get("/events")
def events(after: int = 0, user: dict = Depends(OWNER)):
    """The event log, newest first. after: only events newer than this id (the dashboard asks every few seconds)."""
    with store.conn() as c:
        rows = c.execute("SELECT * FROM events WHERE id > ? ORDER BY id DESC LIMIT 60", (after,)).fetchall()
    out = []
    for r in rows:
        day, _, time = r["at"].partition(" ")
        out.append({"id": r["id"], "time": time, "day": jday(day), "today": day == excel.today().isoformat() or day == store.stamp()[:10],
                    "who": r["who"], "role": store.ROLE_NAMES.get(r["role"], ""), "kind": r["kind"], "text": r["text"],
                    "detail": json.loads(r["detail"]) if r["detail"] else None})
    return out

def _period(period):
    if period not in facts.PERIODS:
        raise HTTPException(status_code=400, detail="دوره‌ی گزارش درست نیست")
    return period

@router.get("/report")
def report(period: str = "month", user: dict = Depends(BOOKS)):
    with store.conn() as c:
        return facts.report(c, _period(period))

@router.get("/report/download")
def report_download(period: str = "month", user: dict = Depends(BOOKS)):
    """The same report as an Excel file: a summary sheet with where each figure comes from, and the invoices."""
    with store.conn() as c:
        r = facts.report(c, _period(period))
        checks = facts.reconcile(c)
    wb = excel.openpyxl.Workbook()
    ws = wb.active; ws.title = "خلاصه"
    rows = [[business.current()["name"], f"گزارش {r['label']}", r["span"]], []]
    for sec in r["sections"]:
        rows.append([sec["title"]])
        rows += [[row["label"], row["value"], row["how"]] for row in sec["rows"]]
        rows.append([])
    rows.append(["تطبیق سه فایل"])
    rows += [[ch["title"], "جور است" if ch["ok"] else "مغایرت دارد", ch["text"]] for ch in checks["checks"]]
    rows += [["مغایرت", i["title"], " | ".join(i["how"])] for i in checks["issues"]]
    excel._sheet(ws, ["عنوان", "مقدار", "از کجا آمده"], [(r + ["", "", ""])[:3] for r in rows])
    excel._sheet(wb.create_sheet("فاکتورها"), ["شماره فاکتور", "تاریخ", "مشتری", "شهر", "نوع پرداخت", "مبلغ"],
                 [[i["id"], jday(i["date"]), i["customer"], i["city"], i["payment"], i["total"]] for i in r["invoices"]])
    for cell in wb["فاکتورها"]["F"][1:]:
        cell.number_format = "#,##0"
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    name = f"گزارش {r['label']}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})

# ---------- questions about the business ----------

TOOLS = {
    "stock": "موجودی یک جنس",
    "sales": "فروش یک دوره (و اگر جنسی گفته شد، فروش همان جنس)",
    "customer": "وضعیت حساب یک مشتری",
    "top_customers": "بهترین مشتری‌ها در یک دوره",
    "top_products": "پرفروش‌ترین جنس‌ها در یک دوره",
    "cheques": "چک‌های دریافتی و پرداختی روزهای آینده و کسری پول",
    "debtors": "بدهکارها و چک‌های برگشتی",
    "low_stock": "جنس‌هایی که رو به تمام شدن‌اند",
    "dead_stock": "جنس‌هایی که فروش نمی‌روند",
}

def route(question):
    """Which computation a question needs. The model picks; when it can't, plain keywords decide."""
    try:
        data = ask_json("سؤال صاحب یک عمده‌فروشی پارچه را به یکی از این ابزارها بفرست:\n" +
                        "\n".join(f"- {k}: {v}" for k, v in TOOLS.items()) +
                        '\nخروجی: {"tool": نام ابزار, "product": شرح جنس یا null, "customer": نام مشتری یا null, '
                        '"period": یکی از today, week, month, last_month, last_30}', question)
    except Exception:
        data = None
    if data and data.get("tool") in TOOLS:
        period = data.get("period") if data.get("period") in facts.PERIODS else "month"
        return data["tool"], data.get("product") or "", data.get("customer") or "", period
    q = question
    period = ("today" if "امروز" in q else "week" if "هفته" in q else "last_month" if "ماه قبل" in q or "ماه پیش" in q
              else "last_30" if "سی روز" in q or "۳۰ روز" in q else "month")
    if "چک" in q and ("برگشت" in q or "بدهکار" in q):
        return "debtors", "", "", period
    if "چک" in q or "کسری" in q or "پول" in q:
        return "cheques", "", "", period
    if "بدهکار" in q or "طلب" in q:
        return "debtors", "", "", period
    if "تمام" in q or "کم شده" in q:
        return "low_stock", "", "", period
    if "فروش نمی" in q or "خوابیده" in q or "نمی‌فروشه" in q:
        return "dead_stock", "", "", period
    if "مشتری" in q and ("بهترین" in q or "بیشترین" in q):
        return "top_customers", "", "", period
    if "پرفروش" in q:
        return "top_products", "", "", period
    with store.conn() as c:
        cid = next((r["id"] for r in c.execute("SELECT id, name FROM customers") if r["name"].split()[-1] in q), None)
    if cid:
        return "customer", "", str(cid), period
    if "فروش" in q:
        return "sales", q, "", period
    return "stock", q, "", period

def tool_facts(c, tool, product, customer, period):
    """The facts for one question, as short lines that also read well on their own."""
    label = facts.PERIODS[period]
    if tool == "stock":
        hits = facts.search_products(c, product, limit=5) if product.strip() else []
        if not hits:
            return "این جنس در انبار پیدا نشد."
        return "\n".join(f"{p['title']} (عرض {p['width']}): {p['rolls']} توپ، {meters(p['meters'])}، قیمت فروش {money(p['sell_price'])} هر متر"
                         + (f"، حدود {p['days_left']} روز کار می‌دهد" if p["days_left"] is not None else "، اخیراً فروشی نداشته") for p in hits)
    if tool == "sales":
        start, end = facts.period_range(period)
        # a product counts only when the question names a kind of fabric; "فروش این ماه" alone means everything
        kinds = {p["material"] for p in facts.products(c)} | {p["name"].split()[0] for p in facts.products(c)}
        codes = [p["code"] for p in facts.search_products(c, product, limit=10)] if any(k in product for k in kinds) else None
        s = facts.sales_between(c, start, end, codes)
        what = "این جنس" if codes else "کل"
        line = f"فروش {what} در {label}: {money(s['amount'])}، {meters(s['meters'])} در {s['invoices']} فاکتور"
        if period == "month":
            ps, _ = facts.period_range("last_month")
            prev = facts.sales_between(c, ps, ps + (end - start), codes)
            line += f"\nهمین روزهای ماه قبل: {money(prev['amount'])}، {meters(prev['meters'])}"
        return line
    if tool == "customer":
        cid = int(customer) if str(customer).isdigit() else facts.find_customer(c, customer)
        k = facts.card(c, cid) if cid else None
        if not k:
            return "این مشتری پیدا نشد."
        lines = [f"{k['name']}، {k['shop']}، {k['city']}", f"بدهی: {money(k['debt'])}؛ چک در جریان: {money(k['open_cheques'])}",
                 f"سقف اعتبار: {money(k['credit_limit'])}"]
        if k["last_buy"]:
            lines.append(f"آخرین خرید: {jday(k['last_buy'])}")
        return "\n".join(lines + [w["text"] for w in k["warnings"]])
    if tool in ("top_customers", "top_products"):
        t = facts.top(c, period)
        if tool == "top_customers":
            rows = [f"{i + 1}. {r['name']} ({r['city']}): {money(r['amount'])}" for i, r in enumerate(t["customers"])]
        else:
            rows = [f"{i + 1}. {r['title']}: {meters(r['meters'])}، {money(r['amount'])}" for i, r in enumerate(t["products"])]
        return f"{label}:\n" + ("\n".join(rows) or "فروشی ثبت نشده.")
    if tool == "cheques":
        w = facts.money_week(c)
        lines = [f"چک‌های رسیدنی {w['days']} روز آینده: {money(w['in_total'])}", f"چک‌های پرداختی {w['days']} روز آینده: {money(w['out_total'])}",
                 f"موجودی بانک: {money(w['bank'])}"]
        lines.append(f"کسری: {money(-w['left'])}" if w["left"] < 0 else f"بعد از پاس شدن همه می‌ماند: {money(w['left'])}")
        lines += [f"پرداختی {q['due_text']}: {money(q['amount'])} به {q['who']}" for q in w["outgoing"]]
        return "\n".join(lines)
    if tool == "debtors":
        rows = sorted(facts.customers(c).values(), key=lambda r: -r["debt"])[:5]
        lines = [f"چک برگشتی {q['who']}: {money(q['amount'])}، {q['days_ago']} روز پیش" for q in facts.bounced(c)]
        return "\n".join(lines + [f"{r['name']} ({r['city']}): بدهی {money(r['debt'])}" for r in rows])
    if tool == "low_stock":
        rows = [p for p in facts.products(c) if p["low"]]
        return "\n".join(f"{p['title']}: {p['rolls']} توپ، حدود {p['days_left']} روز" for p in rows) or "فعلاً جنسی رو به تمام شدن نیست."
    rows = [p for p in facts.products(c) if p["dead"]]
    return "\n".join(f"{p['title']}: {p['rolls']} توپ، {money(p['value'])} به قیمت خرید" for p in rows) or "جنس خوابیده‌ای نیست."

class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=500)

@router.post("/ask")
def ask(req: Ask, user: dict = Depends(ALL)):
    tool, product, customer, period = route(req.question)
    if user["role"] == "seller" and tool in ("cheques",):
        return {"answer": "اطلاعات چک‌ها و بانک فقط برای صاحب کار و حسابدار است.", "checked": True}
    with store.conn() as c:
        data = tool_facts(c, tool, product, customer, period)
    text, checked = _written(
        f"تو دستیار {business.current()['name']} (عمده‌فروشی پارچه) هستی. به سؤال زیر فقط از روی «اطلاعات» جواب بده، "
        "کوتاه و ساده، حداکثر سه جمله. مبلغ‌ها و عددها را دقیقاً همان‌طور که در اطلاعات آمده بنویس. اگر جواب در اطلاعات نیست، همین را بگو.",
        f"سؤال: {req.question}\n\nاطلاعات:\n{data}", data)
    return {"answer": text, "checked": checked}
