"""The shop's website assistant: what an end customer would see if the wholesaler had a website with an agent.

The customer writes in their own words; the assistant answers in short sentences, asks only what it needs
(which colour, how many rolls, a mobile number), checks the stock file, and takes the order. The order gets
a number, goes into the sales file as «پرداخت نشده», and the owner and seller are told in their panel.
Later the seller turns it into an invoice once it is paid (POST /fabric/web-orders/{id}/invoice).

The model only reads what the customer wrote (which fabrics, how many). Every price, stock figure and total
the customer sees is written by code from the stock file, so a number can never be made up.
"""
import json, re, secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from llm import ask_json
from checks import numbers
from . import business, store, excel, facts
from .facts import money, meters, toman
from .api import DESK, _lock, make_invoice, price_lines, UNITS
from .excel import FA_DIGITS, normal

router = APIRouter(prefix="/fabric")
YES = ("بله", "آره", "اره", "باشه", "ثبت", "حتما", "حتماً", "اوکی", "درسته", "تایید", "تأیید", "بفرست", "همین")
NO = ("نه", "خیر", "لغو", "نمی‌خوام", "نمیخوام", "منصرف")
DONE = ("همین", "کافی", "تمام", "نه", "دیگه نه", "چیز دیگه‌ای نه")
STATUS_WAIT, STATUS_DONE, STATUS_OFF = "پرداخت نشده", "فاکتور شد", "لغو شد"

def _plain(text):
    return normal(text).translate(FA_DIGITS)

def _has(text, words):
    t = _plain(text)
    return any(w in t for w in words)

# ---------- reading what the customer wrote ----------

def _items(text):
    """[{text, qty or None, unit}] from a message. The model reads it first; its quantities must be in the
    message, otherwise a plain reading is used (and words without a number become an item with no quantity)."""
    try:
        data = ask_json('مشتری یک عمده‌فروشی پارچه پیام داده. اقلامی را که می‌خواهد دربیاور. اگر تعداد نگفته، qty را null بگذار. '
                        'خروجی: {"items": [{"qty": عدد یا null, "unit": "توپ" یا "متر", "text": "جنس و رنگ"}]}', text, max_tokens=300)
    except Exception:
        data = None
    out, said = [], numbers(text)
    for it in (data or {}).get("items") or []:
        q = it.get("qty")
        try:
            q = None if q in (None, "", "null") else float(str(q).translate(FA_DIGITS))
        except ValueError:
            out = []; break
        if q is not None and str(int(q) if q == int(q) else q) not in said:
            out = []; break
        if str(it.get("text") or "").strip():
            out.append({"text": str(it["text"]).strip(), "qty": q, "unit": UNITS.get(str(it.get("unit")), "roll")})
    if out:
        return out
    t = _plain(text)
    found = []
    for part in re.split(r"[،,;؛]|\s+و\s+", t):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(توپ|طاقه|رول|متر)?\s*(.*)", part)
        if m and m.group(3).strip():
            found.append({"text": m.group(3).strip(), "qty": float(m.group(1)), "unit": UNITS.get(m.group(2) or "توپ")})
        elif part.strip():
            found.append({"text": part.strip(), "qty": None, "unit": "roll"})
    return found

def _qty(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(توپ|طاقه|رول|متر)?", _plain(text))
    if not m:
        words = {"یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "ده": 10}
        for w, n in words.items():
            if re.search(rf"(^|\s){w}(\s|$)", _plain(text)):
                return n, "meter" if "متر" in text else "roll"
        return None, "roll"
    return float(m.group(1)), UNITS.get(m.group(2) or "توپ")

def _match(c, text):
    """The products a customer's words point to: [best] when clear, several when it is a matter of colour or kind."""
    hits = facts.search_products(c, text, limit=6)
    if not hits:
        return []
    words = facts.words(text)
    score = lambda p: sum(1 for w in words if w in f"{p['name']} {p['material']} {p['color']} {p['width']}")
    best = score(hits[0])
    top = [p for p in hits if score(p) == best and p["meters"] > 0]
    return top or hits[:1]

# ---------- the conversation ----------

def _summary(items):
    total = sum(i["amount"] for i in items)
    lines = [f"• {i['title']}: {i['rolls']} توپ ({meters(i['meters'])})" if i["rolls"] else f"• {i['title']}: {meters(i['meters'])}" for i in items]
    return "\n".join(lines) + f"\nجمع: {toman(total)}", total

def _ask_qty(p):
    return f"{p['title']}، متری {money(p['sell_price'])}. چند توپ؟ (هر توپ {p['roll_meters']} متر)"

def _add(c, state, code, qty, unit, out, trace):
    """Put a line in the cart if the stock has it; otherwise say what there is and ask again."""
    p = next(x for x in facts.products(c) if x["code"] == code)
    m = qty * p["roll_meters"] if unit == "roll" else qty
    trace.append(f"انبار › {p['title']}: {p['rolls']} توپ ({meters(p['meters'])}) موجود")
    if m > p["meters"]:
        state["pending"] = {"code": code}
        out.append(f"از {p['title']} فقط {p['rolls']} توپ داریم. چند توپ بفرستیم؟")
        return False
    lines, _ = price_lines(c, [{"code": code, "rolls": int(qty) if unit == "roll" else 0, "meters": 0 if unit == "roll" else m}])
    l = lines[0]
    state["items"].append({k: l[k] for k in ("code", "title", "rolls", "meters", "price", "amount")})
    trace.append(f"قیمت از انبار › قیمت فروش: متری {money(p['sell_price'])}")
    out.append(f"✓ {l['title']}، {int(qty)} {'توپ' if unit == 'roll' else 'متر'}: {toman(l['amount'])}")
    return True

def _next(c, state, out, chips, trace):
    """After a step: take the next queued item, or show the cart and ask what is left."""
    while state["queue"] and not state.get("pending"):
        it = state["queue"].pop(0)
        hits = _match(c, it["text"])
        if not hits:
            out.append(f"«{it['text']}» نداریم.")
            continue
        if len(hits) > 1:
            state["pending"] = {"options": [h["code"] for h in hits], "qty": it["qty"], "unit": it["unit"]}
            out.append("کدام یکی؟")
            chips += [h["title"] for h in hits]
            return
        if it["qty"] is None:
            state["pending"] = {"code": hits[0]["code"]}
            out.append(_ask_qty(hits[0]))
            chips += ["۱ توپ", "۲ توپ", "۳ توپ", "۵ توپ"]
            return
        if not _add(c, state, hits[0]["code"], it["qty"], it["unit"], out, trace):
            return
    if state.get("pending"):
        return
    if state["items"]:
        text, _ = _summary(state["items"])
        out.append(text)
        out.append("چیز دیگری لازم دارید؟")
        chips += ["همین کافی است", "یک جنس دیگر"]
        state["step"] = "more"

FAQ = [
    (("ارسال", "باربری", "پست", "شهرستان"), "به همه‌ی شهرها با باربری می‌فرستیم. کرایه با خریدار است."),
    (("آدرس", "کجا", "مغازه"), "{place}. ساعت ۹ تا ۱۸، جمعه‌ها تعطیل."),
    (("ساعت", "باز", "تعطیل"), "شنبه تا پنجشنبه ۹ تا ۱۸. جمعه تعطیل."),
    (("پرداخت", "کارت", "واریز", "چک"), "بعد از ثبت سفارش، همکاران ما برای پرداخت تماس می‌گیرند. واریز، کارت یا چک."),
    (("نمونه", "رنگ‌بندی", "عکس"), "عکس و نمونه‌ی رنگ را همکاران ما در واتساپ می‌فرستند."),
]

def reply(state, text):
    """One turn: the customer's text in, short messages, quick-reply chips and a behind-the-scenes trace out."""
    out, chips, trace, order = [], [], [], None
    t = _plain(text)
    with store.conn() as c:
        # questions that do not change the order: answer and stay where we were
        for words, answer in FAQ:
            if _has(t, words) and not (state["step"] == "confirm" and _has(t, YES)) and not re.search(r"\d", t):
                out.append(answer.format(place=business.current()["place"]))
                trace.append("جواب از اطلاعات فروشگاه، بدون عدد ساختگی")
                break
        else:
            pending = state.get("pending")
            if state["step"] == "done":
                state.update(step="items", items=[], queue=[], pending=None, order=None)
            if pending and pending.get("options"):
                opts = [p for p in facts.products(c) if p["code"] in pending["options"]]
                pick = [p for p in opts if p["color"] and p["color"] in normal(text)] or [p for p in opts if normal(text) in p["title"]]
                if len(pick) == 1:
                    state["pending"] = None
                    state["queue"].insert(0, {"text": pick[0]["title"], "qty": pending.get("qty"), "unit": pending.get("unit", "roll")})
                    _next(c, state, out, chips, trace)
                else:
                    out.append("کدام یکی؟"); chips += [p["title"] for p in opts]
            elif pending and pending.get("code"):
                q, unit = _qty(t)
                if q:
                    state["pending"] = None
                    if _add(c, state, pending["code"], q, unit, out, trace):
                        _next(c, state, out, chips, trace)
                else:
                    out.append("چند توپ؟ مثلاً «۲ توپ».")
                    chips += ["۱ توپ", "۲ توپ", "۳ توپ"]
            elif state["step"] == "more" and _has(t, DONE) and not re.search(r"\d", t):
                state["step"] = "phone"
                out.append("شماره موبایل‌تان؟")
            elif state["step"] == "more" and _has(t, ("دیگر", "دیگه", "اضافه")) and not re.search(r"\d", t):
                state["step"] = "items"
                out.append("چه جنسی؟")
                chips += ["کتان", "مخمل", "کرپ", "چادری"]
            elif state["step"] == "phone":
                m = re.search(r"09\d{9}", t.replace(" ", "").replace("-", ""))
                if not m:
                    out.append("شماره را به شکل ۰۹۱۲۱۲۳۴۵۶۷ بنویسید.")
                else:
                    state["phone"] = m.group(0)
                    row = c.execute("SELECT id, name FROM customers WHERE phone = ?", (state["phone"],)).fetchone()
                    trace.append("حسابداری › مشتریان: " + (f"این شماره متعلق به {row['name']} است" if row else "مشتری جدید"))
                    if row:
                        state.update(customer_id=row["id"], name=row["name"], step="confirm")
                        out.append(f"{row['name']} عزیز، خوش آمدید.")
                    else:
                        state["step"] = "name"
                        out.append("به چه نامی ثبت کنم؟")
                if state["step"] == "confirm":
                    text_, total = _summary(state["items"])
                    out += [text_, "ثبت کنم؟"]; chips += ["بله، ثبت کن", "نه"]
            elif state["step"] == "name":
                name = " ".join(text.split())[:40]
                if len(name) < 2:
                    out.append("نام و نام خانوادگی؟")
                else:
                    state.update(name=name, step="confirm")
                    text_, total = _summary(state["items"])
                    out += [text_, "ثبت کنم؟"]; chips += ["بله، ثبت کن", "نه"]
            elif state["step"] == "confirm":
                if _has(t, YES):
                    order = place_order(c, state, trace)
                    out += [f"سفارش شما ثبت شد. شماره سفارش: {order['id']}",
                            f"مبلغ {toman(order['total'])}. هنوز پرداخت نشده؛ همکاران ما برای پرداخت و ارسال تماس می‌گیرند."]
                    state["step"] = "done"
                elif _has(t, NO):
                    state.update(step="items", items=[], queue=[], pending=None)
                    out.append("ثبت نشد. چیز دیگری لازم دارید؟")
                else:
                    out.append("ثبت کنم؟"); chips += ["بله، ثبت کن", "نه"]
            else:
                asked = _items(text)
                priceq = _has(t, ("قیمت", "چنده", "چند است", "موجود", "دارید", "داری"))
                if priceq and all(i["qty"] is None for i in asked):
                    hits = []
                    for i in asked:
                        hits += _match(c, i["text"])
                    if not hits:
                        out.append("این جنس را نداریم. کتان، مخمل، کرپ، حریر، لینن، چادری و فاستونی داریم.")
                    else:
                        for p in hits[:3]:
                            trace.append(f"انبار › {p['title']}: {p['rolls']} توپ، متری {money(p['sell_price'])}")
                            out.append(f"{p['title']}: متری {money(p['sell_price'])}، " + (f"{p['rolls']} توپ موجود." if p["rolls"] else "تمام شده."))
                        if len(hits) == 1 and hits[0]["rolls"]:
                            state["pending"] = {"code": hits[0]["code"]}
                            out.append("چند توپ بفرستیم؟"); chips += ["۱ توپ", "۲ توپ", "۳ توپ"]
                        else:
                            chips += [p["title"] for p in hits[:3]]
                elif asked:
                    state["step"] = "items"
                    state["queue"] += asked
                    _next(c, state, out, chips, trace)
                    if not out:
                        out.append("چه جنسی و چند توپ؟ مثلاً «۲ توپ کتان کش مشکی».")
                else:
                    out.append("چه جنسی و چند توپ؟ مثلاً «۲ توپ کتان کش مشکی».")
    return {"messages": out, "chips": chips[:6], "trace": trace, "order": order}

def place_order(c, state, trace):
    """The order: a row in web_orders, rows in the sales file (not paid), a line in the event log."""
    no = max(c.execute("SELECT COALESCE(MAX(id), 1000) FROM web_orders").fetchone()[0], 1000) + 1
    lines, _ = price_lines(c, [{"code": i["code"], "rolls": i["rolls"], "meters": i["meters"]} for i in state["items"]])
    total = sum(l["amount"] for l in lines)
    stamp = store.stamp()
    c.execute("INSERT INTO web_orders (id, at, customer_id, name, phone, items, total, status) VALUES (?,?,?,?,?,?,?,?)",
              (no, stamp, state.get("customer_id"), state["name"], state["phone"],
               json.dumps([{k: l[k] for k in ("code", "title", "rolls", "meters", "price", "amount")} for l in lines], ensure_ascii=False),
               total, STATUS_WAIT))
    store.log(c, {"full_name": f"{state['name']} (سایت)", "role": "web"}, "web_order",
              f"سفارش {no} از سایت · {toman(total)} · {STATUS_WAIT}", {"files": ["فروش"], "order": no})
    trace += [f"فروش › برگه سفارش‌های سایت: {len(lines)} ردیف با وضعیت «{STATUS_WAIT}»", "به صاحب کار و فروشنده خبر داده شد"]
    state["order"] = no
    return {"id": no, "total": total, "lines": lines, "at": stamp}

# ---------- endpoints: the website side (no staff login: this is what a visitor would use) ----------

class Say(BaseModel):
    chat: str = Field(default="", max_length=40)
    text: str = Field(default="", max_length=400)

def _load(chat_id):
    with store.conn() as c:
        row = c.execute("SELECT state FROM web_chats WHERE id = ?", (chat_id,)).fetchone()
    return json.loads(row["state"]) if row else None

def _save(chat_id, state):
    with store.conn() as c:
        c.execute("INSERT OR REPLACE INTO web_chats (id, state, updated) VALUES (?,?,?)", (chat_id, json.dumps(state, ensure_ascii=False), store.stamp()))

@router.post("/shop/chat")
def shop_chat(req: Say):
    if not business.is_set_up():
        raise HTTPException(status_code=404, detail="فروشگاه هنوز راه‌اندازی نشده است")
    state = _load(req.chat) if req.chat else None
    if state is None or not req.text.strip():
        chat_id = secrets.token_urlsafe(12)
        state = {"step": "items", "items": [], "queue": [], "pending": None}
        _save(chat_id, state)
        s = business.current()
        return {"chat": chat_id, "messages": [f"سلام، به {s['name']} خوش آمدید.", "چه پارچه‌ای لازم دارید؟"],
                "chips": ["قیمت کتان کش", "۲ توپ مخمل", "ارسال به شهرستان"], "trace": [], "order": None}
    if req.text.strip():
        with _lock:   # the order and the sales file are written together
            out = reply(state, req.text)
            _save(req.chat, state)
            if out["order"]:
                o = out["order"]
                excel.add_web_order(o["id"], excel.today(), o["at"][11:16], state["name"], state["phone"], o["lines"], STATUS_WAIT)
                out["order"] = {"id": o["id"], "total": o["total"]}
    return {"chat": req.chat} | out

# ---------- endpoints: the shop's side ----------

@router.get("/shop/demo-phones")
def demo_phones(user: dict = Depends(DESK)):
    """For the demo only: two customers' numbers, so the presenter can show a returning customer being recognised."""
    with store.conn() as c:
        rows = facts.customers(c)
    pick = sorted(rows.values(), key=lambda r: (-r["bounced"], -r["bought_90"]))[:2]
    return [{"name": r["name"], "phone": r["phone"], "note": "چک برگشتی دارد" if r["bounced"] else "مشتری پرخرید"} for r in pick]

def _orders(c, status=None):
    names = {r["id"]: r for r in c.execute("SELECT id, name, city FROM customers")}
    rows = c.execute("SELECT * FROM web_orders" + (" WHERE status = ?" if status else "") + " ORDER BY id DESC", (status,) if status else ()).fetchall()
    all_c = facts.customers(c)
    out = []
    for r in rows:
        cust = all_c.get(r["customer_id"]) if r["customer_id"] else None
        back = [dict(q) for q in c.execute("SELECT number, bank, amount, due, status FROM cheques_in WHERE customer_id = ? AND status = 'برگشتی'",
                                           (r["customer_id"],))] if cust else []
        warn = facts.customer_warnings(cust, back) if cust else []
        out.append({"id": r["id"], "at": r["at"], "time": r["at"][11:16], "name": r["name"], "phone": r["phone"],
                    "known": bool(cust), "city": cust["city"] if cust else "", "items": json.loads(r["items"]), "total": r["total"],
                    "status": r["status"], "invoice_id": r["invoice_id"], "warnings": [w for w in warn if w["tone"] != "info"]})
    return out

@router.get("/web-orders")
def web_orders(user: dict = Depends(DESK)):
    with store.conn() as c:
        return _orders(c)

@router.get("/web-orders/new")
def web_orders_new(after: int = 0, user: dict = Depends(DESK)):
    """For the panel's notice: orders newer than `after` and how many are still waiting for payment."""
    with store.conn() as c:
        waiting = c.execute("SELECT COUNT(*) FROM web_orders WHERE status = ?", (STATUS_WAIT,)).fetchone()[0]
        new = [o for o in _orders(c) if o["id"] > after]
    return {"waiting": waiting, "new": new}

class Pay(BaseModel):
    payment: str
    cheque_days: int = Field(default=45, ge=0, le=365)

@router.post("/web-orders/{oid}/invoice")
def web_order_invoice(oid: int, req: Pay, user: dict = Depends(DESK)):
    """Paid (or agreed): the website order becomes a normal invoice in all three files. A new customer is added
    to the accounts file first."""
    with _lock:
        with store.conn() as c:
            o = c.execute("SELECT * FROM web_orders WHERE id = ?", (oid,)).fetchone()
            if not o or o["status"] != STATUS_WAIT:
                raise HTTPException(status_code=400, detail="این سفارش منتظر پرداخت نیست")
            cid = o["customer_id"]
            if not cid:
                cid = (c.execute("SELECT MAX(id) FROM customers").fetchone()[0] or 0) + 1
                c.execute("INSERT INTO customers (id, name, shop, city, phone, credit_limit, opening) VALUES (?,?,?,?,?,0,0)",
                          (cid, o["name"], "مشتری سایت", "", o["phone"]))
                store.log(c, user, "customer", f"{o['name']} از سفارش سایت {oid} به مشتری‌ها اضافه شد", {"files": ["حسابداری"]})
                new_customer = True
            else:
                new_customer = False
        if new_customer:
            wb = excel.openpyxl.load_workbook(excel.path("accounts"))
            wb["مشتریان"].append([cid, o["name"], "مشتری سایت", "", o["phone"], 0, 0])
            wb.save(excel.path("accounts"))
        items = json.loads(o["items"])
        result = make_invoice(user, cid, [{"code": i["code"], "rolls": i["rolls"], "meters": i["meters"]} for i in items],
                              req.payment, req.cheque_days, origin=f"از سفارش سایت {oid}")
        with store.conn() as c:
            c.execute("UPDATE web_orders SET status = ?, invoice_id = ?, customer_id = ? WHERE id = ?", (STATUS_DONE, result["invoice"], cid, oid))
        excel.set_web_order_status(oid, f"{STATUS_DONE} ({result['invoice']})")
    return result | {"new_customer": new_customer}

@router.post("/web-orders/{oid}/cancel")
def web_order_cancel(oid: int, user: dict = Depends(DESK)):
    with _lock:
        with store.conn() as c:
            o = c.execute("SELECT status FROM web_orders WHERE id = ?", (oid,)).fetchone()
            if not o or o["status"] != STATUS_WAIT:
                raise HTTPException(status_code=400, detail="این سفارش منتظر پرداخت نیست")
            c.execute("UPDATE web_orders SET status = ? WHERE id = ?", (STATUS_OFF, oid))
            store.log(c, user, "web_order", f"سفارش سایت {oid} لغو شد", {"files": ["فروش"], "order": oid})
        excel.set_web_order_status(oid, STATUS_OFF)
    return {"ok": True}
