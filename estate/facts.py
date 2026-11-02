"""Every number the agency's panels, the website and the model use, computed by code from estate.db.
The model only writes sentences around these numbers, and its sentences are checked against them.

Money is worded by money() (from the fabric assistant: «8 میلیارد و 450 میلیون تومان»), so a number the model copies
looks exactly like the number in its facts.
"""
from datetime import date, timedelta
from statistics import median
from jalali import to_jalali, MONTHS
from fabric.facts import money
from . import store

STALE_DAYS = 30      # no word with the owner this long: call to check the unit is still available
REPORT_DAYS = 30     # the owner has had no report this long
MISSED_DAYS = 3      # a match nobody called about this long is a missed chance
PRICE_FLAG = 20      # asking price this many percent off the neighbourhood's deals gets a flag
FEATURES = {"elevator": "آسانسور", "parking": "پارکینگ", "storage": "انباری"}
KINDS = {"sale": "فروش", "rent": "رهن و اجاره"}
STATUS = {"active": "فعال", "sold": "فروخته شد", "rented": "اجاره داده شد", "withdrawn": "مالک منصرف شد"}
REQ_STATUS = {"open": "در جستجو", "won": "معامله شد", "lost": "منصرف شد"}
# The agency's settings. The defaults follow what Tehran agencies commonly use; a real agency checks them against this
# year's tariff of its union (اتحادیه) and changes them in «تنظیمات».
DEFAULTS = {"rate": 3.0,       # a month's rent for each 100 toman of deposit (3: each 1 million toman of deposit = 30 thousand a month)
            "sale_fee": 0.5,   # sale: percent of the price, from each side
            "rent_fee": 25.0}  # rent: percent of one month's rent (with the deposit converted), from each side

def today():
    return store.today()

def jdate(iso):
    """'2026-10-16' -> '24 مهر'"""
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{d} {MONTHS[m - 1]}"

def jfull(iso):
    y, m, d = to_jalali(date.fromisoformat(iso[:10]))
    return f"{y}/{m:02d}/{d:02d}"

def days_ago(iso):
    return (today() - date.fromisoformat(iso[:10])).days

def ago_text(iso):
    n = days_ago(iso)
    return "امروز" if n <= 0 else "دیروز" if n == 1 else f"{n} روز پیش"

def when_text(at):
    """A visit's time: «امروز ساعت 17:30», «فردا ساعت 10:00» or «12 آبان ساعت 18:00»."""
    d = (date.fromisoformat(at[:10]) - today()).days
    day = {0: "امروز", 1: "فردا", -1: "دیروز"}.get(d, jdate(at))
    return f"{day} ساعت {at[11:16]}"

def settings(c):
    out = dict(DEFAULTS)
    for k in DEFAULTS:
        row = c.execute("SELECT value FROM meta WHERE key = ?", ("set_" + k,)).fetchone()
        if row:
            out[k] = float(row["value"])
    return out

def agents(c):
    """{user id: full name} of everyone who can be named on a listing (the owner works files too)."""
    return {r["id"]: r["full_name"] for r in c.execute("SELECT id, full_name FROM users ORDER BY id")}

# ---------- deposit and rent ----------

def equivalent(deposit, rent, rate):
    """The whole rent per month with the deposit turned into rent: rent + deposit × rate%."""
    return round((rent or 0) + (deposit or 0) * rate / 100)

def convert(deposit, rent, new_deposit, rate):
    """The same unit with another deposit: each toman of deposit less adds rate% a month to the rent."""
    eq = equivalent(deposit, rent, rate)
    new_rent = max(0, round(eq - new_deposit * rate / 100))
    return {"deposit": new_deposit, "rent": new_rent, "equivalent": eq,
            "text": f"ودیعه {money(new_deposit)} و اجاره‌ی ماهانه {money(new_rent)}",
            "how": [f"اجاره‌ی کامل ماهانه = {money(rent)} + {money(deposit)} × {_pct(rate)}٪ = {money(eq)}",
                    f"اجاره‌ی جدید = {money(eq)} − {money(new_deposit)} × {_pct(rate)}٪ = {money(new_rent)}"]}

def _pct(v):
    return f"{v:g}"

# ---------- a listing in words ----------

def title(l):
    return f"{l['area']} متر، {l['rooms']} خواب، {l['hood']}"

def price_text(l):
    if l["kind"] == "sale":
        return money(l["price"])
    return f"ودیعه {money(l['deposit'])}، اجاره {money(l['rent'])}" if l["rent"] else f"رهن کامل {money(l['deposit'])}"

def features(l):
    out = [f"طبقه {l['floor']}" + (f" از {l['floors']}" if l.get("floors") else ""), f"{l['age']} ساله" if l["age"] else "نوساز"]
    return out + [name for k, name in FEATURES.items() if l.get(k)]

def listing_view(l, names, extra=None):
    l = dict(l)
    return l | {"kind_text": KINDS[l["kind"]], "title": title(l), "price_text": price_text(l), "features": features(l),
                "agent": names.get(l["agent_id"], ""), "status_text": STATUS.get(l["status"], l["status"]),
                "contact_text": ago_text(l["last_contact"]) if l["last_contact"] else "", "created_text": jdate(l["created"])} | (extra or {})

def request_budget_text(r):
    if r["kind"] == "sale":
        return f"تا {money(r['budget'])}"
    return f"ودیعه تا {money(r['deposit'])}" + (f"، اجاره تا {money(r['rent'])}" if r["rent"] else "")

def request_view(r, names, extra=None):
    r = dict(r)
    needs = [FEATURES[n] for n in (r["needs"] or "").split(",") if n in FEATURES]
    want = [f"{r['rooms']} خواب" if r["rooms"] else "", f"از {r['area']} متر" if r["area"] else ""] + needs
    return r | {"kind_text": KINDS[r["kind"]], "hoods_list": (r["hoods"] or "").split(","), "budget_text": request_budget_text(r),
                "wants": [w for w in want if w], "agent": names.get(r["agent_id"], ""), "status_text": REQ_STATUS.get(r["status"], r["status"]),
                "created_text": jdate(r["created"]), "source_text": "سایت بنگاه" if r["source"] == "site" else "تلفن"} | (extra or {})

# ---------- matching ----------

def match(l, r, s):
    """How well a unit fits a request, by code: None when it does not fit, else {score, reasons, misses}.
    The neighbourhood is required; the budget may be passed by a little (room to bargain); a missing room, a smaller
    area or a missing feature lowers the score and is said in words."""
    if l["kind"] != r["kind"] or l["hood"] not in (r["hoods"] or "").split(","):
        return None
    reasons, misses, score = [], [], 100.0
    if l["kind"] == "sale":
        ratio = l["price"] / r["budget"] if r["budget"] else 1
    else:
        if r["deposit"] and l["deposit"] > r["deposit"] * 1.25:
            return None   # the deposit is cash in hand: far more than they have is no match
        want = equivalent(r["deposit"], r["rent"], s["rate"])
        ratio = equivalent(l["deposit"], l["rent"], s["rate"]) / want if want else 1
    if ratio > 1.08:
        return None
    gap = round(abs(1 - ratio) * 100)
    if ratio > 1:
        misses.append(f"{gap}٪ بالاتر از بودجه، جای مذاکره دارد")
        score -= gap * 3
    else:
        reasons.append(f"{gap}٪ زیر بودجه" if gap >= 2 else "در حد بودجه")
        score += min(gap, 15) / 3
    if r["rooms"]:
        if l["rooms"] < r["rooms"] - 1:
            return None
        if l["rooms"] < r["rooms"]:
            misses.append("یک خواب کمتر")
            score -= 20
        else:
            reasons.append(f"{l['rooms']} خواب")
    if r["area"]:
        if l["area"] < r["area"] * 0.85:
            return None
        if l["area"] < r["area"]:
            misses.append(f"{r['area'] - l['area']} متر کوچک‌تر")
            score -= 10
        else:
            reasons.append(f"{l['area']} متر")
    for n in (r["needs"] or "").split(","):
        if n in FEATURES:
            if l[n]:
                reasons.append(f"{FEATURES[n]} دارد")
            else:
                misses.append(f"{FEATURES[n]} ندارد")
                score -= 15
    if score < 45:
        return None
    return {"score": round(min(score, 100)), "reasons": reasons, "misses": misses}

def _since(l, r):
    return max(l["created"], r["created"])

def _calls(c):
    out = {}
    for row in c.execute("SELECT k.*, u.full_name FROM calls k LEFT JOIN users u ON u.id = k.user_id ORDER BY k.id"):
        out[(row["listing_id"], row["request_id"])] = {"at": row["at"], "who": row["full_name"], "outcome": row["outcome"],
                                                        "when": jdate(row["at"])}
    return out

def all_matches(c):
    """Every fitting pair of an active listing and an open request, with whether someone called about it."""
    s = settings(c)
    ls = [dict(r) for r in c.execute("SELECT * FROM listings WHERE status = 'active'")]
    rs = [dict(r) for r in c.execute("SELECT * FROM requests WHERE status = 'open'")]
    calls = _calls(c)
    out = []
    for l in ls:
        for r in rs:
            m = match(l, r, s)
            if m:
                since = _since(l, r)
                out.append(m | {"listing": l, "request": r, "since": since, "waiting": days_ago(since),
                                "called": calls.get((l["id"], r["id"]))})
    return out

def matches_for_listing(c, lid):
    return sorted((m for m in all_matches(c) if m["listing"]["id"] == lid), key=lambda m: -m["score"])

def matches_for_request(c, rid):
    return sorted((m for m in all_matches(c) if m["request"]["id"] == rid), key=lambda m: -m["score"])

# ---------- price check from the agency's own deals ----------

def per_m2(row, s):
    """Sale: price per square metre. Rent: the whole monthly rent (deposit converted) per square metre."""
    if row["kind"] == "sale":
        return row["price"] / row["area"]
    return equivalent(row["deposit"], row["rent"], s["rate"]) / row["area"]

def price_check(c, l):
    """The asking price against the deals this agency closed in the same neighbourhood in the last year (similar age
    when there are at least three such deals). None when there are fewer than three deals to compare with."""
    s = settings(c)
    since = (today() - timedelta(days=365)).isoformat()
    deals = [dict(r) for r in c.execute("SELECT * FROM deals WHERE kind = ? AND hood = ? AND date >= ? ORDER BY date DESC",
                                        (l["kind"], l["hood"], since))]
    near = [d for d in deals if abs((d["age"] or 0) - (l["age"] or 0)) <= 8]
    used, same_age = (near, True) if len(near) >= 3 else (deals, False)
    if len(used) < 3:
        return None
    values = [per_m2(d, s) for d in used]
    mid, mine = median(values), per_m2(l, s)
    diff = round((mine - mid) / mid * 100)
    verdict = "high" if diff >= PRICE_FLAG else "low" if diff <= -PRICE_FLAG else "fair"
    unit = "متری" if l["kind"] == "sale" else "اجاره‌ی کامل ماهانه‌ی هر متر"
    side = f"{abs(diff)}٪ {'بالاتر' if diff > 0 else 'پایین‌تر'} از میانه" if abs(diff) >= 2 else "هم‌اندازه‌ی میانه"
    text = (f"{unit} {money(mine)}؛ {len(used)} معامله‌ی {'هم‌سن ' if same_age else ''}{l['hood']} در یک سال اخیر "
            f"{unit} {money(min(values))} تا {money(max(values))} بوده است (میانه {money(mid)}). {side}.")
    how = [f"{jfull(d['date'])} · {d['area']} متر · {d['age']} ساله · {unit} {money(per_m2(d, s))}" for d in used]
    how += [f"= میانه‌ی {len(used)} معامله: {money(mid)}", f"= این فایل: {money(mine)} ({side})"]
    if l["kind"] == "rent":
        how.insert(0, f"اجاره‌ی کامل = اجاره + ودیعه × {_pct(s['rate'])}٪")
    return {"n": len(used), "low": round(min(values)), "mid": round(mid), "high": round(max(values)), "value": round(mine),
            "diff": diff, "verdict": verdict, "text": text, "how": how}

# ---------- commission ----------

def commission(kind, price, deposit, rent, s):
    """The agency's commission by its settings: from each side, and the total."""
    if kind == "sale":
        each = round((price or 0) * s["sale_fee"] / 100)
        how = [f"از هر طرف = {money(price)} × {_pct(s['sale_fee'])}٪ = {money(each)}"]
    else:
        eq = equivalent(deposit, rent, s["rate"])
        each = round(eq * s["rent_fee"] / 100)
        how = [f"اجاره‌ی کامل ماهانه = {money(rent)} + {money(deposit)} × {_pct(s['rate'])}٪ = {money(eq)}",
               f"از هر طرف = {money(eq)} × {_pct(s['rent_fee'])}٪ = {money(each)}"]
    return {"each": each, "total": each * 2, "how": how + [f"= جمع از دو طرف: {money(each * 2)}"]}

def split(total, ids):
    """The commission shared equally between the agents on the deal."""
    ids = [i for i in ids if i] or [None]
    part = total // len(ids)
    return {i: part for i in ids}

# ---------- what needs doing ----------

def duplicates(c):
    """Pairs of active listings that look like the same unit: same kind, neighbourhood, floor, nearly the same area,
    and the same owner phone or street."""
    ls = [dict(r) for r in c.execute("SELECT * FROM listings WHERE status = 'active' ORDER BY id")]
    out = []
    for i, a in enumerate(ls):
        for b in ls[i + 1:]:
            if (a["kind"], a["hood"], a["floor"]) == (b["kind"], b["hood"], b["floor"]) and abs(a["area"] - b["area"]) <= 3 \
                    and ((a["owner_phone"] and a["owner_phone"] == b["owner_phone"]) or (a["street"] and a["street"] == b["street"])):
                why = "شماره‌ی مالک یکی است" if a["owner_phone"] == b["owner_phone"] else "خیابان یکی است"
                out.append({"a": a, "b": b, "why": f"هر دو {a['hood']}، طبقه {a['floor']}، {a['area']} و {b['area']} متر؛ {why}"})
    return out

def report_due(l):
    base = l["last_report"] or l["created"]
    return l["status"] == "active" and days_ago(base) >= REPORT_DAYS

def alerts(c, agent_id=None):
    """Today's work: matches nobody called, visits not confirmed, stale listings, prices far from the deals, duplicates,
    owners with no report. agent_id: only this agent's listings and buyers (for the agent's own panel)."""
    names, out = agents(c), []
    mine = (lambda aid: aid == agent_id) if agent_id else (lambda aid: True)
    for m in sorted(all_matches(c), key=lambda m: -m["waiting"]):
        l, r = m["listing"], m["request"]
        if m["called"] or not (mine(r["agent_id"]) or mine(l["agent_id"])):
            continue
        if m["waiting"] >= MISSED_DAYS:
            out.append({"type": "missed", "tone": "danger", "icon": "alert", "listing_id": l["id"], "request_id": r["id"],
                        "title": f"{m['waiting']} روز است کسی فایل {l['id']} را به {r['name']} پیشنهاد نداده است",
                        "detail": f"{title(l)}، {price_text(l)}. {r['name']} {request_budget_text(r)} دنبال همین است. مشاور متقاضی: {names.get(r['agent_id'], '')}"})
        elif agent_id:
            out.append({"type": "new_match", "tone": "success", "icon": "sparkles", "listing_id": l["id"], "request_id": r["id"],
                        "title": f"فایل {l['id']} به درد {r['name']} می‌خورد",
                        "detail": f"{title(l)}، {price_text(l)}. {'، '.join(m['reasons'])}"})
    tomorrow = (today() + timedelta(days=1)).isoformat()
    for v in c.execute("""SELECT v.*, r.name, l.hood, l.area FROM visits v JOIN requests r ON r.id = v.request_id
                          JOIN listings l ON l.id = v.listing_id WHERE v.status = 'booked' AND v.at >= ? ORDER BY v.at""",
                       (today().isoformat(),)):
        if v["at"][:10] <= tomorrow and mine(v["agent_id"]):
            out.append({"type": "visit", "tone": "warning", "icon": "calendar", "visit_id": v["id"], "listing_id": v["listing_id"],
                        "title": f"بازدید {when_text(v['at'])} هنوز تأیید نشده است",
                        "detail": f"{v['name']}، فایل {v['listing_id']} ({v['area']} متر، {v['hood']}). مشاور: {names.get(v['agent_id'], '')}"})
    for l in c.execute("SELECT * FROM listings WHERE status = 'active' ORDER BY last_contact"):
        if not mine(l["agent_id"]):
            continue
        if days_ago(l["last_contact"]) >= STALE_DAYS:
            out.append({"type": "stale", "tone": "warning", "icon": "clock", "listing_id": l["id"],
                        "title": f"{days_ago(l['last_contact'])} روز است با مالک فایل {l['id']} تماسی نبوده است",
                        "detail": f"{title(l)}. شاید فروخته یا اجاره داده شده باشد؛ تا تماس گرفته نشود روی سایت نشان داده نمی‌شود."})
        if report_due(l):
            base = l["last_report"] or l["created"]
            out.append({"type": "report", "tone": "info", "icon": "message", "listing_id": l["id"],
                        "title": f"{days_ago(base)} روز است مالک فایل {l['id']} گزارشی نگرفته است",
                        "detail": f"{l['owner_name']}، {title(l)}. گزارش هفتگی را دستیار آماده می‌کند."})
        p = price_check(c, l)
        if p and p["verdict"] != "fair":
            out.append({"type": "price", "tone": "warning", "icon": "chart", "listing_id": l["id"],
                        "title": f"قیمت فایل {l['id']} از معامله‌های مشابه {abs(p['diff'])}٪ {'بالاتر' if p['diff'] > 0 else 'پایین‌تر'} است",
                        "detail": p["text"]})
    for d in duplicates(c):
        if mine(d["a"]["agent_id"]) or mine(d["b"]["agent_id"]):
            out.append({"type": "duplicate", "tone": "info", "icon": "layers", "listing_id": d["b"]["id"], "other_id": d["a"]["id"],
                        "title": f"فایل {d['b']['id']} احتمالاً همان فایل {d['a']['id']} است",
                        "detail": f"{d['why']}. ثبت‌کننده‌ها: {names.get(d['a']['agent_id'], '')} و {names.get(d['b']['agent_id'], '')}"})
    return out

# ---------- the owner's checks: what does not add up ----------

def checks(c):
    """Findings from numbers and dates alone. They say what does not add up and show the sum, never who did it."""
    s, names, out = settings(c), agents(c), []
    # a unit withdrawn soon after several visits by the same customer, whose request was closed as lost soon after:
    # the pattern a deal made outside the agency leaves
    for l in c.execute("SELECT * FROM listings WHERE status = 'withdrawn' AND closed IS NOT NULL"):
        rows = c.execute("""SELECT v.*, r.name, r.status AS rstatus, r.closed AS rclosed FROM visits v JOIN requests r ON r.id = v.request_id
                            WHERE v.listing_id = ? AND v.status = 'done' ORDER BY v.at""", (l["id"],)).fetchall()
        by = {}
        for v in rows:
            by.setdefault(v["request_id"], []).append(v)
        for rid, vs in by.items():
            last = vs[-1]
            gap = (date.fromisoformat(l["closed"]) - date.fromisoformat(last["at"][:10])).days
            if len(vs) >= 2 and 0 <= gap <= 7 and last["rstatus"] == "lost" and last["rclosed"]:
                lost = (date.fromisoformat(last["rclosed"]) - date.fromisoformat(l["closed"])).days
                if abs(lost) <= 7:
                    events = c.execute("SELECT * FROM events WHERE listing_id = ? OR request_id = ? ORDER BY at", (l["id"], rid)).fetchall()
                    out.append({"type": "outside", "tone": "danger", "listing_id": l["id"], "request_id": rid,
                                "title": f"فایل {l['id']} پس از {len(vs)} بازدید یک مشتری بسته شد و معامله‌ای ثبت نشد",
                                "detail": (f"{title(l)}. {last['name']} {len(vs)} بار این واحد را دید؛ {gap} روز پس از آخرین بازدید فایل با "
                                           f"«{STATUS['withdrawn']}» بسته شد و {abs(lost)} روز {'بعد' if lost >= 0 else 'قبل'} درخواست همین مشتری هم «منصرف شد» ثبت شد. "
                                           "این الگو می‌تواند اتفاقی باشد؛ تماس با مالک روشن می‌کند."),
                                "how": [f"بازدید {jfull(v['at'])} ساعت {v['at'][11:16]} · {names.get(v['agent_id'], '')}" for v in vs] +
                                       [f"{jfull(e['at'])} ساعت {e['at'][11:16]} · {e['who']}: {e['text']}" for e in events]})
    for d in c.execute("SELECT * FROM deals WHERE expected > 0 AND commission < expected * 0.9 ORDER BY date DESC"):
        gap = round((1 - d["commission"] / d["expected"]) * 100)
        who = "، ".join(names.get(int(i), "") for i in (d["agents"] or "").split(",") if i)
        how = commission(d["kind"], d["price"], d["deposit"], d["rent"], s)["how"]
        out.append({"type": "fee", "tone": "warning", "deal_id": d["id"],
                    "title": f"کمیسیون معامله‌ی {d['id']} از تعرفه‌ی بنگاه {gap}٪ کمتر ثبت شده است",
                    "detail": f"{KINDS[d['kind']]} در {d['hood']}، {jdate(d['date'])}. ثبت‌شده {money(d['commission'])}، با تعرفه {money(d['expected'])}. مشاور: {who}",
                    "how": how + [f"ثبت‌شده: {money(d['commission'])}", f"= کمتر: {money(d['expected'] - d['commission'])}"]})
    for d in duplicates(c):
        out.append({"type": "duplicate", "tone": "info", "listing_id": d["b"]["id"],
                    "title": f"فایل {d['a']['id']} و {d['b']['id']} احتمالاً یک واحدند",
                    "detail": f"{d['why']}. یک واحد با دو فایل، دو بار به مشتری پیشنهاد می‌شود و آمار را بالا می‌برد.",
                    "how": [f"فایل {x['id']}: {title(x)}، {price_text(x)}، {x['owner_name']} {x['owner_phone']}، ثبت {jfull(x['created'])} · {names.get(x['agent_id'], '')}"
                            for x in (d["a"], d["b"])]})
    return out

# ---------- dashboards ----------

def month_start():
    y, m, d = to_jalali(today())
    return (today() - timedelta(days=d - 1)).isoformat()

def overview(c):
    s, names, t = settings(c), agents(c), today()
    start, week = month_start(), (t + timedelta(days=7)).isoformat()
    active = c.execute("SELECT kind, COUNT(*) n FROM listings WHERE status = 'active' GROUP BY kind").fetchall()
    by_kind = {r["kind"]: r["n"] for r in active}
    open_r = c.execute("SELECT COUNT(*) FROM requests WHERE status = 'open'").fetchone()[0]
    site_r = c.execute("SELECT COUNT(*) FROM requests WHERE status = 'open' AND source = 'site'").fetchone()[0]
    deals = [dict(r) for r in c.execute("SELECT * FROM deals WHERE date >= ? ORDER BY date", (start,))]
    fee = sum(d["commission"] for d in deals)
    visits = c.execute("SELECT COUNT(*) FROM visits WHERE status != 'cancelled' AND at >= ? AND at < ?", (t.isoformat(), week)).fetchone()[0]
    matches = all_matches(c)
    missed = [m for m in matches if not m["called"] and m["waiting"] >= MISSED_DAYS]
    y, mo, _ = to_jalali(t)
    stats = [
        {"label": "فایل فعال", "value": f"{by_kind.get('sale', 0) + by_kind.get('rent', 0)}", "sub": f"{by_kind.get('sale', 0)} فروش، {by_kind.get('rent', 0)} رهن و اجاره",
         "icon": "file", "tone": "primary", "how": [f"فایل‌های با وضعیت «فعال»: {by_kind.get('sale', 0)} فروش + {by_kind.get('rent', 0)} رهن و اجاره"]},
        {"label": "متقاضی در جستجو", "value": f"{open_r}", "sub": f"{site_r} نفر از سایت بنگاه", "icon": "users", "tone": "info",
         "how": [f"درخواست‌های باز: {open_r - site_r} از تلفن + {site_r} از سایت"]},
        {"label": f"معامله‌های {MONTHS[mo - 1]}", "value": f"{len(deals)}", "sub": f"کمیسیون {money(fee)}", "icon": "check", "tone": "success",
         "how": [f"{jfull(d['date'])} · {KINDS[d['kind']]} {d['hood']} · {money(d['commission'])}" for d in deals] + [f"= جمع کمیسیون: {money(fee)}"]},
        {"label": "بازدید هفت روز آینده", "value": f"{visits}", "sub": f"{len(missed)} تطبیق بی‌تماس", "icon": "calendar",
         "tone": "danger" if missed else "warning", "how": [f"بازدیدهای ثبت‌شده از امروز تا {jdate(week)}: {visits}",
                                                              f"تطبیق‌هایی که {MISSED_DAYS} روز یا بیشتر کسی درباره‌شان تماس نگرفته: {len(missed)}"]},
    ]
    team = []
    for uid, name in names.items():
        team.append({"id": uid, "name": name,
                     "listings": c.execute("SELECT COUNT(*) FROM listings WHERE status = 'active' AND agent_id = ?", (uid,)).fetchone()[0],
                     "requests": c.execute("SELECT COUNT(*) FROM requests WHERE status = 'open' AND agent_id = ?", (uid,)).fetchone()[0],
                     "visits": c.execute("SELECT COUNT(*) FROM visits WHERE agent_id = ? AND status = 'done' AND at >= ?", (uid, start)).fetchone()[0],
                     "deals": sum(1 for d in deals if str(uid) in (d["agents"] or "").split(",")),
                     "fee": sum(v for d in deals for k, v in split(d["commission"], (d["agents"] or "").split(",")).items() if k == str(uid))})
    team = [m for m in team if m["listings"] or m["requests"] or m["deals"] or m["visits"]]
    return {"today": jfull(t.isoformat()), "stats": stats, "team": team, "alerts": alerts(c), "checks": len(checks(c)),
            "month": MONTHS[mo - 1], "settings": s}

def agent_today(c, user):
    t = today()
    end = (t + timedelta(days=2)).isoformat()
    visits = [dict(v) | {"when": when_text(v["at"])} for v in c.execute(
        """SELECT v.*, r.name, r.phone, l.hood, l.area, l.rooms, l.street FROM visits v JOIN requests r ON r.id = v.request_id
           JOIN listings l ON l.id = v.listing_id WHERE v.agent_id = ? AND v.status IN ('booked', 'confirmed') AND v.at >= ? AND v.at < ?
           ORDER BY v.at""", (user["id"], t.isoformat(), end))]
    mine = {"listings": c.execute("SELECT COUNT(*) FROM listings WHERE status = 'active' AND agent_id = ?", (user["id"],)).fetchone()[0],
            "requests": c.execute("SELECT COUNT(*) FROM requests WHERE status = 'open' AND agent_id = ?", (user["id"],)).fetchone()[0]}
    return {"today": jfull(t.isoformat()), "visits": visits, "alerts": alerts(c, user["id"]), "mine": mine}

def brief_facts(c):
    """What the owner's morning summary may say: plain lines with every number in them."""
    o = overview(c)
    lines = [f"تاریخ: {o['today']}"] + [f"{s['label']}: {s['value']} ({s['sub']})" for s in o["stats"]]
    lines += ["کارهای امروز به ترتیب اهمیت:"] + [f"{i + 1}. {a['title']}" for i, a in enumerate(o["alerts"][:6])]
    if o["checks"]:
        lines.append(f"موارد ناجور در «بررسی‌ها»: {o['checks']}")
    return "\n".join(lines), o

def ask_facts(c):
    """Everything the floating assistant may answer from, one fact per line."""
    s, t = settings(c), today()
    lines = [f"امروز {jfull(t.isoformat())} است."]
    for k, name in KINDS.items():
        n = c.execute("SELECT COUNT(*) FROM listings WHERE status = 'active' AND kind = ?", (k,)).fetchone()[0]
        lines.append(f"فایل فعال {name}: {n}")
    from .agency import HOODS
    since = (t - timedelta(days=365)).isoformat()
    for h in HOODS:
        n = c.execute("SELECT COUNT(*) FROM listings WHERE status = 'active' AND hood = ?", (h,)).fetchone()[0]
        sale = [per_m2(dict(d), s) for d in c.execute("SELECT * FROM deals WHERE kind = 'sale' AND hood = ? AND date >= ?", (h, since))]
        line = f"{h}: {n} فایل فعال"
        if sale:
            line += f"؛ میانه‌ی قیمت متری در معامله‌های فروش یک سال اخیر {money(median(sale))}"
        lines.append(line)
    open_r = c.execute("SELECT COUNT(*) FROM requests WHERE status = 'open'").fetchone()[0]
    lines.append(f"متقاضی در جستجو: {open_r}")
    start = month_start()
    deals = c.execute("SELECT COUNT(*) n, COALESCE(SUM(commission), 0) f FROM deals WHERE date >= ?", (start,)).fetchone()
    lines.append(f"معامله‌های این ماه: {deals['n']}، کمیسیون {money(deals['f'])}")
    for v in c.execute("""SELECT v.at, r.name, l.hood FROM visits v JOIN requests r ON r.id = v.request_id JOIN listings l ON l.id = v.listing_id
                          WHERE v.status IN ('booked', 'confirmed') AND v.at >= ? ORDER BY v.at LIMIT 6""", (t.isoformat(),)):
        lines.append(f"بازدید {when_text(v['at'])}: {v['name']}، {v['hood']}")
    lines.append(f"نرخ تبدیل ودیعه به اجاره: هر یک میلیون تومان ودیعه {money(1_000_000 * s['rate'] / 100)} در ماه")
    return "\n".join(lines)

def events(c, after=0, limit=40):
    rows = c.execute("SELECT * FROM events WHERE id > ? ORDER BY id DESC LIMIT ?", (after, limit)).fetchall()
    t = today().isoformat()
    return [{"id": e["id"], "kind": e["kind"], "text": e["text"], "who": e["who"], "role": e["role"], "today": e["at"][:10] == t,
             "day": jdate(e["at"]), "time": e["at"][11:16], "listing_id": e["listing_id"], "request_id": e["request_id"]} for e in rows]
