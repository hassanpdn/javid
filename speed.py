"""How fast the site really is for its visitors, measured in their own browsers (lib/rum.js) behind the site's door.

Each time someone opens the assistants page or an assistant's panel, their browser sends one line: which screen, how
many milliseconds until it was usable (from the page load, or from the click that opened it), the first paint, KB
downloaded, how many requests failed on the way, phone or computer, and the connection type when the browser tells it.
Lines live in access.db (kept 90 days, like the login log), so resets and reseeding keep them. Only the permanent
account sees them, summarised by code: per screen the median, the slowest tenth and the worst, with failures.

POST /speed passes the site's door and the assistants' logins in app.py like every API call, so only people who got
past the door are measured. Automated browsers (tests, perf-check) send nothing.
"""
import re, time
from statistics import median
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
import access

router = APIRouter()
KEEP_DAYS = 90
SCREENS = {   # screen key -> words on the page
    "hub": "صفحه‌ی دستیارها",
    "school:manager": "مدرسه، مدیر", "school:staff": "مدرسه، دفتر", "school:counselor": "مدرسه، مشاور", "school:parent": "مدرسه، ولی",
    "school:teacher": "مدرسه، آموزگار", "school:student": "مدرسه، دانش‌آموز",
    "fabric:owner": "پارچه‌فروشی، صاحب کار", "fabric:seller": "پارچه‌فروشی، فروشنده", "fabric:accountant": "پارچه‌فروشی، حسابدار", "fabric:warehouse": "پارچه‌فروشی، انباردار",
    "estate:owner": "بنگاه، مدیر", "estate:agent": "بنگاه، مشاور", "deed": "استخراج سند",
    "law:owner": "وکالت، وکیل", "law:associate": "وکالت، همکار وکیل", "law:secretary": "وکالت، منشی",
    "dental:owner": "دندان‌پزشکی، دندان‌پزشک", "dental:secretary": "دندان‌پزشکی، منشی",
    "hotel:manager": "هتل، مدیر", "hotel:reservation": "هتل، رزرو", "hotel:reception": "هتل، پذیرش", "hotel:housekeeping": "هتل، خانه‌داری",
    "lodge:host": "بوم‌گردی، میزبان", "lodge:helper": "بوم‌گردی، همکار",
}
KINDS = {"load": "باز شدن سایت", "open": "باز شدن از داخل سایت"}

def _conn():
    c = access._conn()
    c.execute("""CREATE TABLE IF NOT EXISTS speed (
        id INTEGER PRIMARY KEY, at INTEGER NOT NULL, screen TEXT NOT NULL, kind TEXT NOT NULL, ms INTEGER NOT NULL, fcp INTEGER,
        kb INTEGER, failed INTEGER NOT NULL, device TEXT NOT NULL, net TEXT NOT NULL, who TEXT NOT NULL)""")
    return c

class Report(BaseModel):
    screen: str
    kind: str
    ms: int = Field(ge=0, le=600_000)
    fcp: int | None = Field(None, ge=0, le=600_000)
    kb: int | None = Field(None, ge=0, le=200_000)
    failed: int = Field(0, ge=0, le=100)
    phone: bool = False
    net: str = Field("", max_length=10)

# A browser that sends too much is ignored: at most this many lines a minute from one address.
_sent, PER_MINUTE = {}, 30

@router.post("/speed")
def report(req: Report, request: Request):
    ip = request.client.host if request.client else ""
    now = time.time()
    _sent[ip] = [t for t in _sent.get(ip, []) if now - t < 60]
    if req.screen not in SCREENS or req.kind not in KINDS or len(_sent[ip]) >= PER_MINUTE:
        return {"ok": False}
    _sent[ip].append(now)
    h = access.holder(request) if access.ON else None
    who = (access.ADMIN_NAME if h["admin"] else h["name"]) if h else ""
    net = req.net if re.fullmatch(r"(slow-)?[234]g|wifi|", req.net) else ""
    with _conn() as c:
        c.execute("INSERT INTO speed (at, screen, kind, ms, fcp, kb, failed, device, net, who) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (int(now), req.screen, req.kind, req.ms, req.fcp, req.kb, req.failed, "phone" if req.phone else "desktop", net, who))
        c.execute("DELETE FROM speed WHERE at < ?", (int(now) - KEEP_DAYS * 86400,))
    return {"ok": True}

def _slowest_tenth(values):
    """The time below which nine in ten visits were ready (the 90th percentile)."""
    v = sorted(values)
    return v[min(len(v) - 1, int(len(v) * 0.9))]

def summary(rows):
    """Per screen: how many visits, the median, the slowest tenth, the worst, and visits with a failed request."""
    out = {}
    for r in rows:
        out.setdefault(r["screen"], []).append(r)
    lines = []
    for screen, rs in out.items():
        ms = [r["ms"] for r in rs]
        lines.append({"screen": screen, "label": SCREENS[screen], "count": len(rs), "median": round(median(ms)), "p90": _slowest_tenth(ms),
                      "worst": max(ms), "failed": sum(1 for r in rs if r["failed"]),
                      "kb": round(median([r["kb"] for r in rs if r["kb"] is not None])) if any(r["kb"] is not None for r in rs) else None})
    return sorted(lines, key=lambda l: -l["median"])

@router.get("/speed")
def view(request: Request, days: int = 7, device: str = ""):
    """The permanent account's view: the summary per screen, and the latest visits."""
    access._admin(request)
    days = days if days in (1, 7, 30, 90) else 7
    since = int(time.time()) - days * 86400
    q, args = "SELECT * FROM speed WHERE at >= ?", [since]
    if device in ("phone", "desktop"):
        q += " AND device = ?"; args.append(device)
    with _conn() as c:
        rows = [dict(r) for r in c.execute(q + " ORDER BY id DESC", args)]
    latest = [{"id": r["id"], "at": access.when(r["at"]), "label": SCREENS[r["screen"]], "kind": KINDS[r["kind"]], "ms": r["ms"], "kb": r["kb"],
               "failed": r["failed"], "device": r["device"], "net": r["net"], "who": r["who"]} for r in rows[:30]]
    return {"days": days, "count": len(rows), "screens": summary(rows), "latest": latest}
