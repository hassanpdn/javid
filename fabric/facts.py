"""Every number the fabric panels and the model use, computed by code from fabric.db.
The model only ever writes sentences around these numbers, and its sentences are checked against them.

Money is shown the way the bazaar says it ("۱۲۸ میلیون تومان"), always through money(), so a number the
model copies looks exactly like the number in its facts.
"""
import re
from collections import defaultdict
from datetime import date, timedelta
from jalali import to_jalali, to_gregorian, MONTHS
from . import store
from .excel import today, normal, FA_DIGITS

LOW_DAYS = 10        # stock that lasts fewer working days than this is "running out"
DEAD_DAYS = 90       # no sale for this many days: money sitting on the shelf
QUIET_DAYS = 45      # a regular customer silent this long gets a call
WINDOW = 7           # the cheque and cash window, in days

def money(v):
    """Toman in bazaar words: 1_280_000_000 -> '1 میلیارد و 280 میلیون تومان', 185_000 -> '185 هزار تومان'."""
    v = int(round(v or 0))
    sign = "منفی " if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000_000:
        b, m = divmod(round(v / 1_000_000), 1000)
        return f"{sign}{b} میلیارد" + (f" و {m} میلیون" if m else "") + " تومان"
    if v >= 1_000_000:
        return f"{sign}{round(v / 1_000_000)} میلیون تومان"
    if v >= 1000:
        return f"{sign}{round(v / 1000)} هزار تومان"
    return f"{sign}{v} تومان"

def jday(iso):
    """'2026-10-16' -> '24 مهر'"""
    y, m, d = to_jalali(date.fromisoformat(iso))
    return f"{d} {MONTHS[m - 1]}"

def days_ago(iso):
    return (today() - date.fromisoformat(iso)).days

def meters(m):
    m = round(m or 0, 1)
    return f"{int(m) if m == int(m) else m} متر"

# ---------- periods ----------

PERIODS = {"today": "امروز", "week": "این هفته", "month": "این ماه", "last_month": "ماه قبل", "last_30": "سی روز اخیر"}

def period_range(key):
    """(start, end) dates for a period, both included. Weeks start on Saturday; months are Persian months."""
    t = today()
    if key == "today":
        return t, t
    if key == "week":
        return t - timedelta(days=(t.weekday() - 5) % 7), t
    jy, jm, _ = to_jalali(t)
    month_start = to_gregorian(jy, jm, 1)
    if key == "month":
        return month_start, t
    if key == "last_month":
        py, pm = (jy, jm - 1) if jm > 1 else (jy - 1, 12)
        return to_gregorian(py, pm, 1), month_start - timedelta(days=1)
    return t - timedelta(days=29), t

def sales_between(c, start, end, code_like=None):
    """Sales total, meters and invoice count between two dates, optionally for products matching some codes."""
    q = """SELECT COALESCE(SUM(l.amount), 0) amount, COALESCE(SUM(l.meters), 0) meters, COUNT(DISTINCT i.id) invoices
           FROM invoices i JOIN invoice_lines l ON l.invoice_id = i.id WHERE i.date BETWEEN ? AND ?"""
    args = [start.isoformat(), end.isoformat()]
    if code_like is not None:
        if not code_like:
            return {"amount": 0, "meters": 0, "invoices": 0}
        q += f" AND l.product_code IN ({','.join('?' * len(code_like))})"
        args += list(code_like)
    return dict(c.execute(q, args).fetchone())

# ---------- products ----------

def products(c):
    """Every product with its stock, last 30 days' sales, days of stock left and last sale."""
    t = today()
    sold = {r["code"]: r["m"] for r in c.execute(
        """SELECT l.product_code code, SUM(l.meters) m FROM invoice_lines l JOIN invoices i ON i.id = l.invoice_id
           WHERE i.date >= ? GROUP BY l.product_code""", ((t - timedelta(days=29)).isoformat(),))}
    last = {r["code"]: r["d"] for r in c.execute(
        "SELECT l.product_code code, MAX(i.date) d FROM invoice_lines l JOIN invoices i ON i.id = l.invoice_id GROUP BY l.product_code")}
    out = []
    for p in c.execute("SELECT * FROM products ORDER BY code"):
        p = dict(p)
        p["title"] = f"{p['name']} {p['color']}".strip()
        p["sold_30"] = round(sold.get(p["code"], 0), 1)
        rate = p["sold_30"] / 26          # about 26 working days in 30 (Fridays closed)
        p["per_day"] = round(rate, 1)
        p["days_left"] = round(p["meters"] / rate) if rate else None
        p["last_sale"] = last.get(p["code"])
        p["idle_days"] = days_ago(p["last_sale"]) if p["last_sale"] else None
        p["low"] = p["days_left"] is not None and p["days_left"] < LOW_DAYS
        p["dead"] = p["meters"] > 0 and (p["idle_days"] is None or p["idle_days"] >= DEAD_DAYS)
        p["value"] = round(p["meters"] * p["buy_price"])
        out.append(p)
    return out

def words(text):
    return [w for w in re.split(r"[\s،,]+", normal(text).translate(FA_DIGITS)) if w]

def search_products(c, query, limit=8):
    """Products ranked by how many words of the query appear in their name, material, color and width."""
    q = words(query)
    if not q:
        return []
    scored = []
    for p in products(c):
        hay = f"{p['name']} {p['material']} {p['color']} {p['width']} {p['code']}"
        score = sum(1 for w in q if w in hay)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1]["code"]))
    return [p for _, p in scored[:limit]]

# ---------- customers ----------

def customers(c):
    """Every customer with what they owe, their open and bounced cheques, credit room and buying rhythm."""
    t = today()
    rows = {r["id"]: dict(r) for r in c.execute("SELECT * FROM customers")}
    credit = defaultdict(int); paid = defaultdict(int); open_q = defaultdict(int); bounced = defaultdict(int)
    for r in c.execute("SELECT customer_id, SUM(total) s FROM invoices WHERE payment = 'نسیه' GROUP BY customer_id"):
        credit[r["customer_id"]] = r["s"]
    for r in c.execute("SELECT customer_id, SUM(amount) s FROM receipts GROUP BY customer_id"):
        paid[r["customer_id"]] = r["s"]
    for r in c.execute("SELECT customer_id, status, SUM(amount) s FROM cheques_in GROUP BY customer_id, status"):
        if r["status"] == "در جریان":
            open_q[r["customer_id"]] = r["s"]
        elif r["status"] == "برگشتی":
            bounced[r["customer_id"]] = r["s"]
    dates = defaultdict(list)
    for r in c.execute("SELECT customer_id, date FROM invoices ORDER BY date"):
        dates[r["customer_id"]].append(r["date"])
    since = (t - timedelta(days=89)).isoformat()
    bought = {r["customer_id"]: r["s"] for r in c.execute(
        "SELECT customer_id, SUM(total) s FROM invoices WHERE date >= ? GROUP BY customer_id", (since,))}
    for cid, row in rows.items():
        debt = row["opening"] + credit[cid] - paid[cid] + bounced[cid]
        row.update(debt=max(debt, 0), open_cheques=open_q[cid], bounced=bounced[cid])
        row["exposure"] = row["debt"] + row["open_cheques"]
        row["room"] = row["credit_limit"] - row["exposure"]
        d = sorted(set(dates[cid]))
        row["invoices"] = len(dates[cid])
        row["last_buy"] = d[-1] if d else None
        gaps = [(date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(d, d[1:])]
        row["usual_gap"] = round(sum(gaps) / len(gaps)) if gaps else None
        row["silent_days"] = days_ago(d[-1]) if d else None
        row["quiet"] = bool(d) and len(d) >= 4 and row["silent_days"] >= QUIET_DAYS and (row["usual_gap"] or 99) <= 20
        row["bought_90"] = bought.get(cid, 0)
    return rows

def find_customer(c, text):
    """The customer a name means: the same name, or the only one whose name holds every word of it."""
    q = normal(text)
    rows = list(c.execute("SELECT id, name, shop, city FROM customers"))
    exact = [r for r in rows if r["name"] == q]
    if exact:
        return exact[0]["id"]
    hits = [r for r in rows if q and all(w in f"{r['name']} {r['shop']} {r['city']}" for w in q.split())]
    return hits[0]["id"] if len(hits) == 1 else None

def card(c, cid):
    """Everything the seller needs on screen while the customer is on the phone."""
    all_rows = customers(c)
    if cid not in all_rows:
        return None
    row = all_rows[cid]
    cheques = [dict(r) for r in c.execute(
        "SELECT number, bank, amount, due, status FROM cheques_in WHERE customer_id = ? AND status IN ('در جریان', 'برگشتی') ORDER BY due", (cid,))]
    for q in cheques:
        q["due_text"] = jday(q["due"])
        q["days"] = (date.fromisoformat(q["due"]) - today()).days
    recent = []
    for inv in c.execute("SELECT * FROM invoices WHERE customer_id = ? ORDER BY date DESC, id DESC LIMIT 5", (cid,)):
        lines = c.execute("""SELECT l.*, p.name, p.color FROM invoice_lines l LEFT JOIN products p ON p.code = l.product_code
                             WHERE l.invoice_id = ?""", (inv["id"],)).fetchall()
        recent.append({"id": inv["id"], "date": jday(inv["date"]), "payment": inv["payment"], "total": inv["total"],
                       "items": "، ".join(f"{l['name'] or l['product_code']} {l['color'] or ''}".strip() + f" ({meters(l['meters'])})" for l in lines)})
    usual = [dict(r) for r in c.execute(
        """SELECT l.product_code code, p.name, p.color, SUM(l.meters) m FROM invoice_lines l
           JOIN invoices i ON i.id = l.invoice_id LEFT JOIN products p ON p.code = l.product_code
           WHERE i.customer_id = ? GROUP BY l.product_code ORDER BY m DESC LIMIT 3""", (cid,))]
    return {**row, "cheques": cheques, "recent": recent,
            "usual": [{"code": u["code"], "title": f"{u['name']} {u['color']}", "meters": round(u["m"])} for u in usual],
            "warnings": customer_warnings(row, cheques)}

def customer_warnings(row, cheques=()):
    out = []
    for q in cheques:
        if q["status"] == "برگشتی":
            out.append({"tone": "danger", "text": f"چک {money(q['amount'])} او ({q['bank']}، سررسید {jday(q['due'])}) برگشت خورده و هنوز پرداخت نشده."})
    if row["room"] < 0:
        out.append({"tone": "danger", "text": f"از سقف اعتبارش ({money(row['credit_limit'])}) {money(-row['room'])} جلوتر است."})
    elif row["credit_limit"] and row["room"] < row["credit_limit"] * .15:
        out.append({"tone": "warning", "text": f"فقط {money(row['room'])} تا سقف اعتبارش مانده."})
    if row["quiet"]:
        out.append({"tone": "info", "text": f"معمولاً هر {row['usual_gap']} روز خرید می‌کرد؛ {row['silent_days']} روز است خریدی نکرده."})
    return out

# ---------- cheques and cash ----------

def money_week(c, days=WINDOW):
    """Cheques in and out over the next days, and whether the bank balance covers what goes out."""
    t = today()
    end = (t + timedelta(days=days)).isoformat()
    names = {r["id"]: r["name"] for r in c.execute("SELECT id, name FROM customers")}
    incoming = [dict(r, who=names.get(r["customer_id"], "")) for r in c.execute(
        "SELECT * FROM cheques_in WHERE status = 'در جریان' AND due BETWEEN ? AND ? ORDER BY due", (t.isoformat(), end))]
    outgoing = [dict(r, who=r["payee"]) for r in c.execute(
        "SELECT * FROM cheques_out WHERE status = 'در جریان' AND due BETWEEN ? AND ? ORDER BY due", (t.isoformat(), end))]
    for q in incoming + outgoing:
        q["due_text"] = jday(q["due"]); q["days"] = (date.fromisoformat(q["due"]) - t).days
    bank = int(float(store.get_meta("bank", 0) or 0))
    cin, cout = sum(q["amount"] for q in incoming), sum(q["amount"] for q in outgoing)
    return {"days": days, "bank": bank, "incoming": incoming, "outgoing": outgoing, "in_total": cin, "out_total": cout,
            "left": bank + cin - cout}

def bounced(c):
    names = {r["id"]: r["name"] for r in c.execute("SELECT id, name FROM customers")}
    rows = [dict(r, who=names.get(r["customer_id"], "")) for r in c.execute("SELECT * FROM cheques_in WHERE status = 'برگشتی' ORDER BY due")]
    for q in rows:
        q["due_text"] = jday(q["due"]); q["days_ago"] = days_ago(q["due"])
    return rows

# ---------- the owner's day ----------

def trend(c, days=14):
    """Sales per working day, oldest first, for the chart."""
    t = today()
    by_day = {r["date"]: r["s"] for r in c.execute(
        "SELECT date, SUM(total) s FROM invoices WHERE date >= ? GROUP BY date", ((t - timedelta(days=days * 2)).isoformat(),))}
    out, d = [], t
    while len(out) < days:
        if d.weekday() != 4:
            out.append({"date": d.isoformat(), "label": jday(d.isoformat()), "amount": by_day.get(d.isoformat(), 0)})
        d -= timedelta(days=1)
    return out[::-1]

def top(c, period="month", n=5):
    start, end = period_range(period)
    args = (start.isoformat(), end.isoformat())
    prods = [dict(r) for r in c.execute(
        """SELECT l.product_code code, p.name || ' ' || p.color title, SUM(l.meters) meters, SUM(l.amount) amount
           FROM invoice_lines l JOIN invoices i ON i.id = l.invoice_id LEFT JOIN products p ON p.code = l.product_code
           WHERE i.date BETWEEN ? AND ? GROUP BY l.product_code ORDER BY amount DESC LIMIT ?""", args + (n,))]
    custs = [dict(r) for r in c.execute(
        """SELECT cu.id, cu.name, cu.city, SUM(i.total) amount, COUNT(*) invoices FROM invoices i JOIN customers cu ON cu.id = i.customer_id
           WHERE i.date BETWEEN ? AND ? GROUP BY cu.id ORDER BY amount DESC LIMIT ?""", args + (n,))]
    return {"products": prods, "customers": custs}

def alerts(c):
    """What the owner should look at today, most urgent first. Each comes with the panel it opens."""
    out = []
    for q in bounced(c):
        out.append({"type": "bounced", "tone": "danger", "icon": "alert", "customer_id": q["customer_id"],
                    "title": f"چک برگشتی {q['who']}",
                    "detail": f"{money(q['amount'])}، {q['days_ago']} روز پیش برگشت خورد و هنوز پرداخت نشده."})
    w = money_week(c)
    if w["left"] < 0:
        out.append({"type": "cash", "tone": "danger", "icon": "calendar",
                    "title": f"کسری پول برای چک‌های {w['days']} روز آینده",
                    "detail": f"{money(w['out_total'])} چک باید پاس شود؛ موجودی بانک {money(w['bank'])} و چک‌های رسیدنی {money(w['in_total'])} است. {money(-w['left'])} کم است."})
    rows = customers(c)
    for r in sorted(rows.values(), key=lambda r: r["room"]):
        if r["room"] < 0:
            out.append({"type": "limit", "tone": "warning", "icon": "user", "customer_id": r["id"],
                        "title": f"{r['name']} از سقف اعتبار گذشته",
                        "detail": f"سقف {money(r['credit_limit'])}، بدهی و چک در جریان {money(r['exposure'])}."})
    for p in sorted((p for p in products(c) if p["low"]), key=lambda p: p["days_left"]):
        out.append({"type": "low", "tone": "warning", "icon": "chart", "code": p["code"],
                    "title": f"{p['title']} رو به تمام شدن است",
                    "detail": f"{p['rolls']} توپ ({meters(p['meters'])}) مانده؛ با فروش روزی {meters(p['per_day'])} حدود {p['days_left']} روز کار می‌دهد. تأمین‌کننده: {p['supplier']}."})
    for r in rows.values():
        if r["quiet"]:
            out.append({"type": "quiet", "tone": "info", "icon": "message", "customer_id": r["id"],
                        "title": f"{r['name']} ({r['city']}) مدتی است خرید نکرده",
                        "detail": f"معمولاً هر {r['usual_gap']} روز سفارش می‌داد؛ آخرین خرید {r['silent_days']} روز پیش بود."})
    dead = [p for p in products(c) if p["dead"]]
    if dead:
        out.append({"type": "dead", "tone": "info", "icon": "inbox",
                    "title": f"{len(dead)} جنس بیش از {DEAD_DAYS} روز فروش نرفته",
                    "detail": f"{money(sum(p['value'] for p in dead))} پول به قیمت خرید در انبار خوابیده: " + "، ".join(p["title"] for p in dead) + "."})
    return out

def overview(c):
    t = today()
    s_today = sales_between(c, *period_range("today"))
    s_month = sales_between(c, *period_range("month"))
    start, _ = period_range("last_month")
    s_prev = sales_between(c, start, start + (t - period_range("month")[0]))   # last month, the same number of days
    rows = customers(c)
    w = money_week(c)
    return {
        "today": jday(t.isoformat()),
        "sales_today": s_today, "sales_month": s_month, "sales_prev": s_prev,
        "receivable": sum(r["debt"] for r in rows.values()), "debtors": sum(1 for r in rows.values() if r["debt"] > 0),
        "week": {k: w[k] for k in ("days", "bank", "in_total", "out_total", "left")},
        "alerts": alerts(c), "trend": trend(c), "top": top(c),
        "notes": [r["note"] for r in c.execute("SELECT note FROM import_notes ORDER BY id")],
    }

def brief_facts(o):
    """The owner's morning in numbered lines, for the model to turn into two or three sentences."""
    lines = [f"تاریخ: {o['today']}",
             f"فروش امروز تا این ساعت: {money(o['sales_today']['amount'])} در {o['sales_today']['invoices']} فاکتور",
             f"فروش این ماه: {money(o['sales_month']['amount'])}؛ همین روزهای ماه قبل: {money(o['sales_prev']['amount'])}",
             f"طلب از مشتری‌ها: {money(o['receivable'])} از {o['debtors']} مشتری"]
    lines += [f"{i + 1}. {a['title']}: {a['detail']}" for i, a in enumerate(o["alerts"][:5])]
    return "\n".join(lines)
