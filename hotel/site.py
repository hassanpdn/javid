"""The hotel's website with its booking assistant: what a guest would see if the hotel had a site.

The guest writes in their own words; the assistant asks only what it needs (the dates, how many people, a child's
age), shows the room types free for every night of the stay with their price, and takes a name and a mobile number.
The model only reads what the guest wrote (read.py, every value checked against the message); rooms left and prices
are written by code. The booking it makes is tentative: it waits for its deposit like any other, and the panels get
a toast.
"""
import json, re, secrets
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from jalali import to_gregorian
from . import info, store, facts, read as reader
from .api import DESK, BookIn, make_booking

router = APIRouter(prefix="/hotel")

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

def _iso(j):
    y, m, d = (int(x) for x in j.split("/"))
    return to_gregorian(y, m, d).isoformat()

def _options(state):
    a, d = _iso(state["arrive"]), _iso(state["depart"])
    with store.conn() as c:
        av = facts.availability(c, a, d)
        out = []
        for t in facts.TYPES:
            q = facts.quote(c, t, a, d, state["adults"], state.get("ages", []), "BB")
            if q["fits"] and av[t]["free"] > 0:
                out.append({"type": t, "name": facts.type_name(t), "total": q["total"], "text": q["total_text"], "deposit": q["deposit"], "free": av[t]["free"]})
    return out

def reply(state, text):
    """One turn of the conversation: what the assistant says, the buttons under it, and the lines «پشت صحنه» shows."""
    got = reader.read(text)
    f, trace = got["fields"], []
    names = {"arrive": "ورود", "depart": "خروج", "nights": "شب", "adults": "بزرگسال", "children": "کودک", "ages": "سن کودک", "type": "اتاق",
             "board": "پذیرایی", "name": "نام", "phone": "تلفن"}
    shown = {"type": facts.type_name, "board": lambda v: facts.BOARDS[v], "ages": lambda v: "، ".join(str(x) for x in v)}
    said = [f"{names[k]} {shown.get(k, str)(v)}" for k, v in f.items() if v not in (None, [], "") and k in got["found"]]
    if said:
        trace.append("از پیام خوانده شد: " + "، ".join(said))
    for k in ("arrive", "depart", "adults", "children", "ages", "type", "name", "phone"):
        if f.get(k) not in (None, [], ""):
            state[k] = f[k]
    if state["step"] == "contact":
        if not state.get("phone"):
            return {"messages": ["لطفاً شماره‌ی همراه را به شکل ۰۹۱۲۱۲۳۴۵۶۷ بنویسید."], "chips": [], "trace": trace}
        if not state.get("name"):
            rest = " ".join(re.sub(r"[0-9۰-۹\-]+|سلام|هستم|اسمم|نام|من", " ", text).split())
            if len(rest) >= 5:
                state["name"] = rest
        if not state.get("name"):
            return {"messages": ["نام و نام خانوادگی را هم بنویسید."], "chips": [], "trace": trace}
        return {"done": True, "trace": trace}
    if state["step"] == "choose":
        opts = _options(state)
        pick = next((o for i, o in enumerate(opts) if text.strip().translate(reader.FA_DIGITS) == str(i + 1) or o["name"] in text), None)
        if not pick and state.get("type"):
            pick = next((o for o in opts if o["type"] == state["type"]), None)
        if not pick:
            return {"messages": ["کدام را انتخاب می‌کنید؟"], "chips": [o["name"] for o in opts], "trace": trace}
        state["type"], state["step"] = pick["type"], "contact"
        trace.append(f"انتخاب: {pick['name']}، {pick['text']}؛ بیعانه {facts.money(pick['deposit'])}")
        return {"messages": [f"{pick['name']}، {facts.stay_text({'arrive': _iso(state['arrive']), 'depart': _iso(state['depart'])})}، با صبحانه: {pick['text']}.",
                             "برای ثبت رزرو، نام و شماره‌ی همراهتان را بنویسید."], "chips": [], "trace": trace}
    if not state.get("arrive") or not state.get("depart"):
        return {"messages": ["برای چه تاریخی؟ مثلاً «۱۵ تا ۱۸ آبان» یا «از ۲۰ آذر دو شب»."], "chips": [], "trace": trace}
    if _iso(state["arrive"]) < store.today().isoformat() or _iso(state["depart"]) <= _iso(state["arrive"]):
        state.pop("arrive"); state.pop("depart")
        return {"messages": ["این تاریخ درست نیست یا گذشته است. تاریخ ورود و خروج را دوباره بنویسید."], "chips": [], "trace": trace}
    if not state.get("adults"):
        return {"messages": ["چند نفر هستید؟"], "chips": ["دو بزرگسال", "دو بزرگسال و یک کودک", "چهار نفر"], "trace": trace}
    if state.get("children") and len(state.get("ages") or []) < state["children"]:
        return {"messages": ["سن کودک چند سال است؟ کودکان زیر ۶ سال رایگان‌اند."], "chips": ["۳ ساله", "۸ ساله"], "trace": trace}
    opts = _options(state)
    a, d = _iso(state["arrive"]), _iso(state["depart"])
    trace.append(f"اتاق‌های خالی در همه‌ی شب‌های {facts.stay_text({'arrive': a, 'depart': d})} برای {state['adults']} بزرگسال" +
                 (f" و {state['children']} کودک" if state.get("children") else "") + ": " + ("، ".join(f"{o['name']} {o['free']}" for o in opts) or "هیچ"))
    if not opts:
        state.pop("arrive"); state.pop("depart")
        return {"messages": ["متأسفانه برای این شب‌ها اتاق خالی نداریم. تاریخ دیگری را امتحان کنید؟"], "chips": [], "trace": trace}
    state["step"] = "choose"
    msgs = [f"برای {facts.stay_text({'arrive': a, 'depart': d})} این اتاق‌ها خالی است (قیمت کل با صبحانه):"]
    msgs += [f"{i + 1}. {o['name']}: {o['text']}" for i, o in enumerate(opts)]
    if state.get("type") and any(o["type"] == state["type"] for o in opts):
        return reply(state, "")
    return {"messages": msgs, "chips": [o["name"] for o in opts], "trace": trace}

@router.post("/site/chat")
def site_chat(req: Say):
    if not info.is_set_up():
        raise HTTPException(status_code=404, detail="هتل هنوز راه‌اندازی نشده است")
    state = _load(req.chat) if req.chat else None
    if state is None or not req.text.strip():
        chat_id = secrets.token_urlsafe(12)
        _save(chat_id, {"step": "ask"})
        return {"chat": chat_id, "messages": [f"سلام، به {info.current()['name']} خوش آمدید.", "برای چه تاریخی و چند نفر اتاق می‌خواهید؟"],
                "chips": ["۱۵ تا ۱۸ آذر، دو بزرگسال", "سوئیت رو به دریا برای آخر هفته", "ویلا برای شش نفر"], "trace": [], "booking": None}
    out = reply(state, req.text)
    booking = None
    if out.get("done"):
        with store.conn() as c:
            body = BookIn(arrive=state["arrive"], depart=state["depart"], adults=state["adults"], ages=state.get("ages") or [], board="BB",
                          type=state["type"], name=state["name"], phone=state["phone"], source="site", status="tentative")
            try:
                bid = make_booking(c, body, None, "site")
            except HTTPException as e:
                state["step"] = "ask"
                _save(req.chat, state)
                return {"chat": req.chat, "messages": [e.detail, "تاریخ یا اتاق دیگری را امتحان کنید."], "chips": [], "trace": out["trace"], "booking": None}
            v = facts.booking_view(c, c.execute("SELECT * FROM bookings WHERE id = ?", (bid,)).fetchone())
            dep = facts.quote(c, v["type"], v["arrive"], v["depart"], v["adults"], v["ages"], "BB")["deposit"]
        state["step"] = "done"
        booking = {"id": bid, "guest": v["guest"]}
        out = {"messages": [f"رزرو شما با شماره‌ی {bid} ثبت شد: {v['type_text']}، {v['stay_text']}، {v['total_text']}.",
                            f"برای قطعی شدن، بیعانه‌ی {facts.money(dep)} تا {v['deposit_due_text']} لازم است. همکاران رزرو برای پرداخت با شما تماس می‌گیرند."],
               "chips": [], "trace": out["trace"] + [f"رزرو موقت {bid} ساخته شد و منتظر بیعانه است؛ در پنل رزرو و پذیرش خبر داده شد"]}
    _save(req.chat, state)
    return {"chat": req.chat, "messages": out["messages"], "chips": out.get("chips", []), "trace": out["trace"], "booking": booking}

@router.get("/site/new")
def new_from_site(after: int = 0, user: dict = Depends(DESK)):
    """Bookings the website made after this id: the panels' toast and badge."""
    with store.conn() as c:
        rows = [facts.booking_view(c, b) for b in c.execute("SELECT * FROM bookings WHERE source = 'site' AND id > ? ORDER BY id", (after,))]
        top = c.execute("SELECT MAX(id) FROM bookings").fetchone()[0] or 0
        waiting = c.execute("SELECT COUNT(*) FROM bookings WHERE source = 'site' AND status = 'tentative'").fetchone()[0]
    return {"new": [{"id": r["id"], "guest": r["guest"], "stay": r["stay_text"], "type": r["type_text"]} for r in rows], "last": top, "waiting": waiting}
