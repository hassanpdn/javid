"""From the pages' text to the deed's fields, page by page, then one result for the whole deed.

Two ways to read a page, with the same output (fields.PageData):
- rules: code that knows the fixed wording of a deed («پلاک ... فرعی از ... اصلی», «به مساحت», «شمالاً ...»).
  Nothing leaves the server. Used whenever the assistant's AI switch is off (the live site's default).
- the model, through llm.py (Ollama on a local machine, AvalAI on the live server when the switch is on). Its answer
  is checked against the schema, asked once more if it does not fit, then given up with a clear message.

Whichever read it, code then looks for every value in the page's own text: a value that is not there is dropped
(null; the model may not guess), and one that is there gets that line as its source and a confidence from how
surely the OCR read that line. Pages that disagree keep both values for the reviewer.
"""
import math, re
from pydantic import ValidationError
from llm import ask_json, ModelOff, ModelDown
from . import fields as F
from .fields import clean, SCALARS, BOUNDARIES

MODEL_TIMEOUT = 90   # seconds for one model answer

class ExtractError(Exception):
    """The model gave no usable answer twice; the message is for the reviewer."""

# ---------- rules ----------

FA = r"[؀-ۿ‌]+"   # one Persian word (letters and the half-space)
DATE = r"\d{4}/\d{1,2}/\d{1,2}"

def _first(pattern, text, group=1):
    m = re.search(pattern, text)
    return m.group(group) if m else None

def rules(text):
    """One page read by its fixed wording. Only what is written is taken; the rest stays None."""
    lines = [clean(l) or "" for l in text.splitlines()]
    flat = " ".join(lines)
    d = {
        "deed_number": _first(r"شماره\s*سند\s*[:：]?\s*(\d+)", flat) or _first(r"سند\s*شماره\s*(\d+)", flat),
        "book": _first(r"دفتر\s*(?:شماره\s*)?(\d+)\s*[،,]?\s*صفحه\s*\d+", flat),
        "page": _first(r"دفتر\s*(?:شماره\s*)?\d+\s*[،,]?\s*صفحه\s*(\d+)", flat),
        "issue_date": _first(rf"تاریخ\s*(?:صدور|ثبت)?\s*[:：]?\s*({DATE})", flat),
        "sub_plate": _first(r"(\d+)\s*فرعی\s*از\s*\d+\s*اصلی", flat),
        "main_plate": _first(r"(\d+)\s*اصلی", flat),
        "section": None, "area": None, "area_unit": None,
    }
    m = re.search(rf"بخش\s*(\d+)(?:\s+(?:ثبت\s+)?(?!و\b)({FA}))?", flat)
    if m:
        d["section"] = m.group(1) + (" " + m.group(2) if m.group(2) else "")
    m = re.search(r"مساحت\s*(\d+(?:\.\d+)?)\s*(متر\s*مربع|هکتار)", flat)
    if m:
        d["area"], d["area_unit"] = m.group(1), m.group(2).replace(" ", "")
    sides = {}
    for line in lines:
        m = re.match(r"^(شمال|شرق|جنوب|غرب)ا?ً?\s+(.+)$", line)
        if m:
            sides[{"شمال": "north", "شرق": "east", "جنوب": "south", "غرب": "west"}[m.group(1)]] = m.group(2)
    owners = [{"name": m["name"], "father_name": m["father"], "national_id": m["nid"], "share": m["share"]}
              for m in re.finditer(rf"(?:آقای|خانم)\s+(?P<name>{FA}(?:\s+{FA}){{0,3}}?)\s+فرزند\s+(?P<father>{FA})\s+"
                                   rf"(?:به\s+)?(?:شماره|کد)\s*ملی\s*[:：]?\s*(?P<nid>\d{{10}})"
                                   rf"(?:\s+نسبت\s+به\s+(?P<share>.{{1,20}}?\s*دانگ))?", flat)]
    transfers = [{"date": m[2], "from": m[5], "to": m[6], "share": m[4],
                  "note": f"سند انتقال شماره {m[1]}" + (f"، دفترخانه {m[3]}" if m[3] else "")}
                 for m in re.finditer(rf"به\s+موجب\s+سند\s+انتقال\s+شماره\s+(\d+)\s+مورخ\s+({DATE})(?:\s+دفترخانه\s+(?:شماره\s+)?(\d+))?"
                                      rf"\s+(.{{1,30}}?)\s+از\s+(.+?)\s+به\s+(.+?)\s+منتقل\s+شد", flat)]
    return F.PageData.model_validate({**d, "boundaries": sides, "owners": owners, "transfers": transfers})

# ---------- the model ----------

PROMPT = """تو داده‌های یک سند مالکیت دفترچه‌ای را از متن یک صفحه‌ی آن (خروجی OCR) استخراج می‌کنی.
فقط یک شیء JSON با همین کلیدها برگردان:
{"owners": [{"name": نام و نام خانوادگی, "father_name": نام پدر, "national_id": شماره ملی, "share": سهم همان‌طور که نوشته شده مثل «سه دانگ»}],
 "main_plate": پلاک اصلی, "sub_plate": پلاک فرعی, "section": بخش ثبتی, "area": عدد مساحت, "area_unit": واحد مساحت,
 "boundaries": {"north": حد شمالی, "east": حد شرقی, "south": حد جنوبی, "west": حد غربی},
 "book": شماره دفتر, "page": شماره صفحه‌ی دفتر, "deed_number": شماره سند, "issue_date": تاریخ صدور,
 "transfers": [{"date": تاریخ, "from": انتقال‌دهنده, "to": انتقال‌گیرنده, "share": سهم منتقل‌شده, "note": شماره سند انتقال و دفترخانه}]}
قانون‌ها:
- فقط چیزی را بنویس که عیناً در متن آمده است. هر چیزی که در متن نیست یا خوانا نیست null باشد. هرگز حدس نزن و چیزی نساز.
- عددها و تاریخ‌ها را دقیقاً همان‌طور که در متن آمده بنویس.
- حدود اربعه را با همان عبارت متن بنویس (مثلاً «به طول 12 متر دیوار به دیوار پلاک 1519 فرعی»)."""

def by_model(text):
    """One page read by the model, in the schema. One more try if the answer does not fit, then ExtractError.
    ModelOff (the AI switch is off) goes up to the caller, who reads the page by rules instead."""
    note = ""
    for _ in range(2):
        try:
            got = ask_json(PROMPT + note, text, max_tokens=1200, timeout=MODEL_TIMEOUT)
        except ModelOff:   # switched off, or ModelDown: the caller reads the page by rules
            raise
        except Exception:
            raise ModelDown()
        try:
            if got is None:
                raise ValueError("no JSON")
            return F.PageData.model_validate(got)
        except (ValidationError, ValueError) as e:
            note = "\nپاسخ قبلی تو با این ساختار جور نبود (" + str(e)[:200] + "). فقط همان JSON را درست برگردان."
    raise ExtractError("پاسخ مدل دو بار با ساختار خواسته‌شده جور نبود. دوباره امتحان کنید یا متن را دستی وارد کنید.")

# ---------- checking every value against the page ----------

def _tokens(text):
    return [w for w in re.split(r"[\s،,:]+", clean(text) or "") if len(w) >= 2]

def _find(value, lines):
    """The page line that holds this value, and the OCR's confidence for it: (line, conf) or None.
    lines: [{"text", "conf"}] with clean text; conf None for pasted text."""
    v = clean(value)
    if not v:
        return None
    if re.fullmatch(r"[\d./]+", v):
        hits = [l for l in lines if re.search(rf"(?<![\d.]){re.escape(v)}(?![\d])", l["text"])]
    else:
        # whole words only («دانگ» inside «ششدانگ» does not count), and at least 80% of them on one line
        toks = _tokens(v)
        hits = [l for l in lines if toks and sum(t in _tokens(l["text"]) for t in toks) >= math.ceil(len(toks) * .8)]
    return (hits[0]["text"], hits[0]["conf"]) if hits else None

def _confidence(conf, issues):
    if issues:
        return "low"
    if conf is None or conf >= 85:
        return "high"
    return "medium" if conf >= 65 else "low"

def field(value=None, confidence="none", source=None, page=None, issues=()):
    return {"value": value, "confidence": confidence, "source": source, "page": page, "conflicts": [], "issues": list(issues)}

def check(raw, key, lines, page_no, flat=None):
    """One value as read (rules or model) -> its field: kept only if the page holds it, then checked."""
    if raw in (None, ""):
        return field()
    found = _find(raw, lines)
    if not found and flat is not None and key in ("name", "father_name", "share"):
        found = (None, None) if clean(raw) in flat else None   # split across two lines: still in the text
    if not found:
        return field()   # not in the text: never kept, whoever proposed it
    source, conf = found
    value, issues = F.validate(key, raw)
    return field(value, _confidence(conf, issues), source, page_no, issues)

# a label that is on the page while its value could not be read: the field stays empty and says so
LABELS = {"deed_number": r"شماره\s*سند", "issue_date": r"تاریخ\s*(?:صدور|ثبت)", "book": r"دفتر\s*(?:شماره)?\s*(?!خانه)",
          "area": r"مساحت", "section": r"بخش\s"}

def page_fields(data, lines, page_no):
    """A page's PageData -> {"scalars": {key: field}, "owners": [{name, father_name, national_id, share}], "transfers": [...]}"""
    lines = [{"text": clean(l["text"]) or "", "conf": l.get("conf")} for l in lines]
    flat = " ".join(l["text"] for l in lines)
    raw = {k: getattr(data, k) for k in SCALARS if k not in BOUNDARIES}
    raw.update({k: getattr(data.boundaries, k) for k in BOUNDARIES})
    scalars = {k: check(raw[k], k, lines, page_no) for k in SCALARS}
    if scalars["area_unit"]["value"] is None and scalars["area"]["value"] is not None:
        scalars["area_unit"] = field(None, "low", scalars["area"]["source"], page_no, ["واحد مساحت در سند نیامده است."])
    for k, pattern in LABELS.items():
        if scalars[k]["value"] is None:
            hit = next((l["text"] for l in lines if re.search(pattern, l["text"])), None)
            if hit:
                scalars[k] = field(None, "low", hit, page_no, [f"«{NAMES[k]}» در سند آمده ولی مقدارش خوانا نیست."])
    owners = []
    for o in data.owners:
        # this owner's own lines are looked at first, so a share is matched to its owner's line, not another's
        mine = [l for l in lines if any(x and clean(x) in l["text"] for x in (o.national_id, o.name))]
        ordered = mine + [l for l in lines if l not in mine]
        f = {k: check(getattr(o, k), k, ordered, page_no, flat) for k in ("name", "father_name", "national_id", "share")}
        if f["name"]["value"] or f["national_id"]["value"]:
            owners.append(f)
    transfers = []
    for t in data.transfers:
        date = check(t.date, "date", lines, page_no)
        parts = {"date": date["value"], "from": check(t.from_, "name", lines, page_no, flat)["value"],
                 "to": check(t.to, "name", lines, page_no, flat)["value"], "share": check(t.share, "share", lines, page_no, flat)["value"],
                 "note": check(t.note, "note", lines, page_no)["value"]}
        if any(parts.values()):
            transfers.append({**parts, "page": page_no, "source": date["source"], "issues": date["issues"]})
    return {"scalars": scalars, "owners": owners, "transfers": transfers}

# ---------- the whole deed ----------

RANK = {"high": 3, "medium": 2, "low": 1, "none": 0}

def _settle(candidates):
    """Several pages' fields for one thing -> one field: the surest value, the others as conflicts."""
    have = [c for c in candidates if c["value"] is not None]
    if not have:
        flagged = [c for c in candidates if c["issues"]]
        return flagged[0] if flagged else field()
    have.sort(key=lambda c: -RANK[c["confidence"]])
    best = dict(have[0], conflicts=[], issues=list(have[0]["issues"]))
    seen = {str(best["value"])}
    for c in have[1:]:
        if str(c["value"]) not in seen:
            seen.add(str(c["value"]))
            best["conflicts"].append({"value": c["value"], "page": c["page"], "source": c["source"]})
    if best["conflicts"]:
        best["issues"].append("در صفحه‌های مختلف مقدار متفاوت آمده است؛ مقدار درست را انتخاب کنید.")
        best["confidence"] = "low"
    return best

def merge(pages):
    """[page_fields per readable page] -> the deed: {"fields", "owners", "transfers", "issues"}."""
    scalars = {k: _settle([p["scalars"][k] for p in pages]) for k in SCALARS}
    groups = {}
    for p in pages:
        for o in p["owners"]:
            key = o["national_id"]["value"] or o["name"]["value"]
            groups.setdefault(key, []).append(o)
    owners = [{k: _settle([o[k] for o in same]) for k in ("name", "father_name", "national_id", "share")} for same in groups.values()]
    transfers, seen = [], set()
    for p in pages:
        for t in p["transfers"]:
            key = (t["date"], t["from"], t["to"])
            if key not in seen:
                seen.add(key)
                transfers.append(t)
    return {"fields": scalars, "owners": owners, "transfers": transfers, "issues": deed_issues(scalars, owners)}

NAMES = {"deed_number": "شماره سند", "issue_date": "تاریخ صدور", "book": "شماره دفتر", "page": "شماره صفحه", "main_plate": "پلاک اصلی",
         "sub_plate": "پلاک فرعی", "section": "بخش ثبتی", "area": "مساحت", "area_unit": "واحد مساحت",
         "north": "حد شمالی", "east": "حد شرقی", "south": "حد جنوبی", "west": "حد غربی"}

def deed_issues(scalars, owners):
    """What the reviewer must look at for the deed as a whole."""
    out = []
    missing = [NAMES[k] for k, f in scalars.items() if f["value"] is None and not f["issues"]]
    if missing:
        out.append("در سند پیدا نشد (خالی مانده): " + "، ".join(missing) + ".")
    unread = [NAMES[k] for k, f in scalars.items() if f["value"] is None and f["issues"]]
    if unread:
        out.append("آمده ولی خوانا نیست: " + "، ".join(unread) + ".")
    if not owners:
        out.append("هیچ مالکی در سند پیدا نشد.")
    else:
        why = F.shares_issue([F.dang(o["share"]["value"]) for o in owners])
        if why:
            out.append(why)
    conflicts = [k for k, f in scalars.items() if f["conflicts"]] + [k for o in owners for k, f in o.items() if f["conflicts"]]
    if conflicts:
        out.append(f"{len(conflicts)} مورد در صفحه‌های مختلف با هم نمی‌خواند.")
    return out

def extract(pages, use_model=True):
    """pages: [{"n", "lines", "readable"}] -> (the deed, how it was read: «model» or «rules»).
    The model is tried first when use_model; with the AI switch off it reads by rules."""
    readable = [p for p in pages if p["readable"]]
    method, down = ("model" if use_model else "rules"), False
    out = []
    for p in readable:
        text = "\n".join(l["text"] for l in p["lines"])
        data = None
        if method == "model":
            try:
                data = by_model(text)
            except ModelDown:   # before ModelOff: ModelDown is a kind of it
                method, down = "rules", True
            except ModelOff:
                method = "rules"
        if data is None:
            data = rules(text)
        out.append(page_fields(data, p["lines"], p["n"]))
    deed = merge(out)
    unreadable = [p["n"] for p in pages if not p["readable"]]
    if unreadable:
        deed["issues"].insert(0, "صفحه‌ی " + "، ".join(map(str, unreadable)) + " خوانا نبود و در استخراج نیامد.")
    if down:
        deed["issues"].insert(0, "مدل در زمان مقرر پاسخ نداد؛ سند با قاعده‌های ثابت خوانده شد.")
    return deed, method
