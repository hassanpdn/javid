"""The agency's website with its assistant: what someone looking for a home would see if the agency had a site.

The visitor writes in their own words; the assistant asks only what it needs (buy or rent, which neighbourhood, how
much), shows the units that fit, and takes a mobile number. The model only reads what the visitor wrote (through
read.py, every value checked against the message); every unit, price and count shown is written by code from the
agency's listings. No owner name, phone or exact address ever reaches the site. Listings nobody has confirmed with
their owner in the last 30 days are not shown. The number becomes a request for an agent, with a toast in the panels.
"""
import json, re, secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from fabric.facts import money
from . import agency, store, facts, read as reader
from .api import ALL, RequestIn, add_request

router = APIRouter(prefix="/estate")

class Say(BaseModel):
    chat: str = Field("", max_length=40)
    text: str = Field("", max_length=500)

def _load(chat_id):
    with store.conn() as c:
        row = c.execute("SELECT state FROM web_chats WHERE id = ?", (chat_id,)).fetchone()
    return json.loads(row["state"]) if row else None

def _save(chat_id, state):
    with store.conn() as c:
        c.execute("INSERT OR REPLACE INTO web_chats (id, state, updated) VALUES (?,?,?)", (chat_id, json.dumps(state, ensure_ascii=False), store.stamp()))

def _shown(c, want, s):
    """The units that fit, best first, only those confirmed with their owner lately."""
    r = {"kind": want["kind"], "hoods": ",".join(want["hoods"]), "budget": want.get("budget") or 0, "deposit": want.get("deposit") or 0,
         "rent": want.get("rent") or 0, "rooms": want.get("rooms") or 0, "area": want.get("area") or 0,
         "needs": ",".join(k for k in facts.FEATURES if want.get(k))}
    out = []
    for l in c.execute("SELECT * FROM listings WHERE status = 'active' AND kind = ?", (want["kind"],)):
        l = dict(l)
        if facts.days_ago(l["last_contact"]) >= facts.STALE_DAYS:
            continue
        m = facts.match(l, r, s)
        if m:
            out.append((m["score"], l, m))
    return sorted(out, key=lambda x: -x[0])

def _unit_line(n, l, m):
    return f"{n}. {facts.title(l)}، {', '.join(facts.features(l)[:3])}، {facts.price_text(l)}" + (f" ({m['reasons'][0]})" if m["reasons"] else "")

def reply(state, text):
    """One turn of the conversation: what the assistant says, the buttons under it, and the lines «پشت صحنه» shows."""
    got = reader.read("request", text)
    f, trace = got["fields"], []
    if got["found"]:
        trace.append("از پیام خوانده شد: " + "، ".join(_said(k, v) for k, v in f.items() if v not in (None, [], "") and k in got["found"]))
    phone = re.sub(r"\D", "", (text or "").translate(reader.FA_DIGITS))
    if state["step"] == "phone":
        if re.fullmatch(r"09\d{9}", phone):
            return {"done": phone, "trace": trace}
        return {"messages": ["لطفاً شماره‌ی همراه را به شکل ۰۹۱۲۱۲۳۴۵۶۷ بنویسید."], "chips": [], "trace": trace}
    for k in ("kind", "rooms", "area", "budget", "deposit", "rent", "parking", "elevator", "storage", "name"):
        if f.get(k) not in (None, ""):
            state[k] = f[k]
    if f.get("hoods"):
        state["hoods"] = f["hoods"]
    if re.search(r"خرید|بخرم|فروشی", text):
        state["kind"] = "sale"
    if re.search(r"اجاره|رهن", text):
        state["kind"] = "rent"
    if not state.get("kind"):
        return {"messages": ["برای خرید دنبال خانه هستید یا اجاره؟"], "chips": ["خرید", "رهن و اجاره"], "trace": trace}
    if not state.get("hoods"):
        return {"messages": ["کدام محله را در نظر دارید؟ ما در این محله‌ها فایل داریم:"], "chips": agency.HOODS, "trace": trace}
    if state["kind"] == "sale" and not state.get("budget"):
        return {"messages": ["سقف بودجه‌ی شما چقدر است؟ مثلاً «تا ۸ میلیارد»."], "chips": ["تا ۶ میلیارد", "تا ۱۰ میلیارد", "تا ۱۵ میلیارد"], "trace": trace}
    if state["kind"] == "rent" and not (state.get("deposit") or state.get("rent")):
        return {"messages": ["چه مقدار ودیعه و اجاره‌ی ماهانه در نظر دارید؟ مثلاً «رهن ۵۰۰ میلیون، اجاره ۱۵ میلیون»."],
                "chips": ["رهن ۵۰۰ میلیون، اجاره ۱۵ میلیون", "رهن کامل ۲ میلیارد"], "trace": trace}
    with store.conn() as c:
        s = facts.settings(c)
        units = _shown(c, state, s)
    hoods = "، ".join(state["hoods"])
    budget = facts.request_budget_text({"kind": state["kind"], "budget": state.get("budget") or 0, "deposit": state.get("deposit") or 0, "rent": state.get("rent") or 0})
    trace.append(f"فایل‌های فعال {facts.KINDS[state['kind']]} در {hoods} {budget}: {len(units)} واحد جور است (فایل‌های تأییدنشده در سی روز اخیر کنار گذاشته شد)")
    state["step"] = "phone"
    if not units:
        return {"messages": [f"در حال حاضر فایلی با این مشخصات در {hoods} نداریم.",
                             "شماره‌ی همراهتان را بنویسید تا هر وقت فایل مناسبی آمد، مشاور ما با شما تماس بگیرد."], "chips": [], "trace": trace}
    top = units[:3]
    trace += [f"فایل {l['id']}: {facts.title(l)}، {facts.price_text(l)} · امتیاز تطبیق {m['score']}" for _, l, m in top]
    state["shown"] = [l["id"] for _, l, _ in top]
    msgs = [f"{len(units)} واحد با خواسته‌ی شما جور است. {'سه' if len(top) == 3 else len(top)} مورد مناسب‌تر:"]
    msgs += [_unit_line(i + 1, l, m) for i, (_, l, m) in enumerate(top)]
    msgs.append("برای دیدن نشانی و هماهنگی بازدید، شماره‌ی همراهتان را بنویسید تا مشاور ما تماس بگیرد.")
    return {"messages": msgs, "chips": [], "trace": trace}

def _said(k, v):
    names = {"kind": "نوع", "hoods": "محله", "budget": "بودجه", "deposit": "ودیعه", "rent": "اجاره", "rooms": "خواب", "area": "متراژ",
             "parking": "پارکینگ", "elevator": "آسانسور", "storage": "انباری", "name": "نام", "phone": "تلفن"}
    if k == "kind":
        v = facts.KINDS[v]
    elif k == "hoods":
        v = "، ".join(v)
    elif k in ("budget", "deposit", "rent"):
        v = money(v)
    elif v is True:
        v = "لازم دارد"
    return f"{names.get(k, k)} {v}"

@router.post("/site/chat")
def site_chat(req: Say):
    if not agency.is_set_up():
        raise HTTPException(status_code=404, detail="بنگاه هنوز راه‌اندازی نشده است")
    state = _load(req.chat) if req.chat else None
    if state is None or not req.text.strip():
        chat_id = secrets.token_urlsafe(12)
        _save(chat_id, {"step": "ask"})
        return {"chat": chat_id, "messages": [f"سلام، به سایت {agency.current()['name']} خوش آمدید.", "دنبال چه خانه‌ای هستید؟"],
                "chips": ["آپارتمان دو خواب برای خرید در پونک", "اجاره در سعادت‌آباد", "رهن کامل تا ۲ میلیارد"], "trace": [], "lead": None}
    out = reply(state, req.text)
    lead = None
    if out.get("done"):
        with store.conn() as c:
            n = c.execute("SELECT COUNT(*) FROM requests WHERE source = 'site'").fetchone()[0]
            agents = [r["id"] for r in c.execute("SELECT id FROM users WHERE role = 'agent' ORDER BY id")]
            agent = agents[n % len(agents)] if agents else None
            body = RequestIn(kind=state["kind"], name=state.get("name") or "بازدیدکننده‌ی سایت", phone=out["done"], hoods=state["hoods"],
                             budget=state.get("budget") or 0, deposit=state.get("deposit") or 0, rent=state.get("rent") or 0,
                             rooms=state.get("rooms") or 0, area=state.get("area") or 0,
                             needs=[k for k in facts.FEATURES if state.get(k)], note="از گفت‌وگوی سایت")
            rid = add_request(c, body, agent, "site", None)
            name = facts.agents(c).get(agent, "")
        state["step"] = "done"
        lead = {"id": rid, "agent": name}
        out = {"messages": [f"ممنون. درخواست شما با شماره‌ی {rid} ثبت شد و {name} به‌زودی با شما تماس می‌گیرد."], "chips": [],
               "trace": out["trace"] + [f"درخواست {rid} ساخته شد و به {name} سپرده شد؛ در پنل مشاور و مدیر خبر داده شد"]}
    _save(req.chat, state)
    return {"chat": req.chat, "messages": out["messages"], "chips": out.get("chips", []), "trace": out["trace"], "lead": lead}

@router.get("/site/leads")
def leads(after: int = 0, user: dict = Depends(ALL)):
    """Requests the website made after this id: the panels' toast and badge."""
    with store.conn() as c:
        rows = c.execute("SELECT id, name, hoods, kind FROM requests WHERE source = 'site' AND id > ? ORDER BY id", (after,)).fetchall()
        top = c.execute("SELECT MAX(id) FROM requests").fetchone()[0] or 0
        waiting = c.execute("""SELECT COUNT(*) FROM requests q WHERE q.source = 'site' AND q.status = 'open'
                               AND NOT EXISTS (SELECT 1 FROM calls k WHERE k.request_id = q.id)""").fetchone()[0]
    return {"new": [dict(r) for r in rows], "last": top, "waiting": waiting}
