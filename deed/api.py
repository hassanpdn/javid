"""The deed assistant's endpoints, all under /deed. No logins of its own: the card's login on the assistants page
(access.py) covers it like every path. One kind of user, the reviewer.

A deed comes in as a file (image or PDF, sent as base64 like the fabric files) or as pasted text, is read page by
page in the background (the page shows the progress), and waits for the reviewer: they correct the form, confirm,
and download the JSON. The model only proposes values; code checks each against the page (extract.py).
"""
import base64, binascii, copy, os, shutil, threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import llm, jalali
from datetime import datetime
from . import store, ocr, extract
from . import fields as F
from .fields import SCALARS

router = APIRouter(prefix="/deed")
MAX_BYTES, MAX_PAGES = 10 * 1024 * 1024, 10
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
SAMPLES = [
    {"key": "clean", "file": "clean.png", "title": "سند تمیز، یک مالک", "desc": "یک صفحه، خوانا"},
    {"key": "shared", "file": "shared.pdf", "title": "چند مالک با سهم", "desc": "دو صفحه با سابقه‌ی انتقال؛ مساحت در دو صفحه فرق دارد"},
    {"key": "unclear", "file": "unclear.png", "title": "اسکن نامرغوب", "desc": "چرخیده و تار؛ برخی موارد نیامده یا خوانا نیست"},
]
_busy = set()                  # documents being read now
_busy_lock = threading.Lock()
store.init()

# ---------- reading a document in the background ----------

def _kind(data):
    """The file's real type from its first bytes (not its name): «png», «jpg», «pdf», or None."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"%PDF"):
        return "pdf"
    return None

def _pages(d):
    """The document's pages, read: from the pages table when already read, else split and OCR'd (cached by hash)."""
    if d["pages"]:
        return [{"n": p["n"], "lines": p["lines"], "readable": p["readable"]} for p in d["pages"]]
    if d["kind"] == "text":
        text = open(os.path.join(store.doc_dir(d["id"]), "text.txt"), encoding="utf-8").read()
        lines = [{"text": l.strip(), "conf": None} for l in text.splitlines() if l.strip()]
        persian = sum(1 for ch in text if "؀" <= ch <= "ۿ")
        r = {"lines": lines, "conf": 100, "rotation": 0, "readable": persian >= ocr.MIN_PERSIAN,
             "note": "" if persian >= ocr.MIN_PERSIAN else "در متن واردشده متن فارسی کافی نیست."}
        store.save_page(d["id"], 1, None, None, r)
        return [{"n": 1, "lines": lines, "readable": r["readable"]}]
    images = ocr.split(os.path.join(store.doc_dir(d["id"]), "original." + d["kind"]), "pdf" if d["kind"] == "pdf" else "image",
                       os.path.join(store.doc_dir(d["id"]), "pages"))
    out = []
    for i, img in enumerate(images, 1):
        store.update(d["id"], progress={"step": "ocr", "done": i - 1, "total": len(images)})
        h = ocr.file_hash(img)
        r = store.cached_ocr(h)
        if r:
            if r["rotation"]:   # the cached reading was made on the page turned upright: turn this copy too
                from PIL import Image
                Image.open(img).rotate(-r["rotation"], expand=True, fillcolor="white").save(img)
        else:
            r = ocr.read_page(img)
            store.cache_ocr(h, r)
        store.save_page(d["id"], i, img, h, r)
        out.append({"n": i, "lines": r["lines"], "readable": r["readable"]})
    return out

def _process(doc_id):
    llm.assistant.set("deed")   # a thread does not inherit the request's assistant; the AI switch is per assistant
    try:
        d = store.get(doc_id)
        pages = _pages(d)
        store.update(doc_id, progress={"step": "extract", "done": len(pages), "total": len(pages)})
        if not any(p["readable"] for p in pages):
            store.update(doc_id, status="error", progress=None, result=None,
                         message="هیچ صفحه‌ی خوانایی در این سند نبود. لطفاً اسکن روشن‌تر و صاف‌تری بفرستید.")
            return
        deed, method = extract.extract(pages)
        store.update(doc_id, status="review", message="", progress=None, method=method, result=deed, edited=None, confirmed_at=None)
    except (ocr.OcrError, extract.ExtractError) as e:
        store.update(doc_id, status="error", progress=None, message=str(e))
    except Exception:
        store.update(doc_id, status="error", progress=None, message="خواندن این سند با خطا روبه‌رو شد. دوباره امتحان کنید.")
    finally:
        with _busy_lock:
            _busy.discard(doc_id)

def _start(doc_id):
    with _busy_lock:
        if doc_id in _busy:
            raise HTTPException(status_code=409, detail="این سند هم‌اکنون در حال خواندن است.")
        _busy.add(doc_id)
    store.update(doc_id, status="processing", message="", progress={"step": "start", "done": 0, "total": 0})
    threading.Thread(target=_process, args=(doc_id,), daemon=True).start()

def _accept_file(name, data):
    """Checks the file, keeps it, and starts reading it. Returns the new document's id."""
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"حجم فایل بیش از {MAX_BYTES // 1024 // 1024} مگابایت است.")
    kind = _kind(data)
    if not kind:
        raise HTTPException(status_code=415, detail="فقط تصویر (JPG یا PNG) یا PDF پذیرفته می‌شود.")
    if not ocr.available():
        raise HTTPException(status_code=503, detail="ابزار خواندن متن (Tesseract با زبان فارسی) روی سرور نصب نیست.")
    doc_id = store.add(name or "سند بی‌نام", "file", kind)
    path = os.path.join(store.doc_dir(doc_id), "original." + kind)
    os.makedirs(store.doc_dir(doc_id), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    try:
        if kind == "pdf":
            n = ocr.pdf_pages(path)
            if not 1 <= n <= MAX_PAGES:
                raise ValueError(f"این PDF {n} صفحه دارد؛ حداکثر {MAX_PAGES} صفحه پذیرفته می‌شود." if n else "این PDF خوانده نشد.")
        else:
            from PIL import Image
            with Image.open(path) as im:
                im.verify()
    except Exception as e:
        _forget(doc_id)
        raise HTTPException(status_code=422, detail=str(e) if isinstance(e, ValueError) else "این فایل خراب است یا تصویر معتبری نیست.")
    _start(doc_id)
    return doc_id

def _forget(doc_id):
    with store.conn() as c:
        c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    shutil.rmtree(store.doc_dir(doc_id), ignore_errors=True)

def reset():
    """The live demo starts every visit fresh (RESET_ON_LOAD): every uploaded deed is forgotten."""
    store.reset()

# ---------- endpoints ----------

def _doc(doc_id):
    d = store.get(doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="این سند پیدا نشد.")
    return d

def _when(iso):
    """«2026-10-31T20:25:00» -> «1405/08/09 ساعت 20:25» (dates stay Jalali everywhere a person reads them)."""
    if not iso:
        return None
    t = datetime.fromisoformat(iso)
    return f"{jalali.jstr(t.date())} ساعت {t:%H:%M}"

def _public(d):
    """A document for the page: no file paths, pages without their full OCR lines."""
    out = {k: d[k] for k in ("id", "name", "source", "kind", "status", "message", "progress", "method")}
    out["created_at"], out["confirmed_at"] = _when(d["created_at"]), _when(d["confirmed_at"])
    out["pages"] = [{"n": p["n"], "readable": p["readable"], "note": p["note"], "rotation": p["rotation"], "conf": p["conf"],
                     "image": bool(p["image"])} for p in d["pages"]]
    out["deed"] = d["edited"] or d["result"]
    out["text"] = "\n".join(l["text"] for p in d["pages"] for l in p["lines"]) if d["kind"] == "text" else None
    return out

@router.get("/info")
def info():
    return {"ocr": ocr.available(), "max_mb": MAX_BYTES // 1024 // 1024, "max_pages": MAX_PAGES,
            "samples": [{k: s[k] for k in ("key", "title", "desc")} for s in SAMPLES]}

@router.get("/documents")
def documents():
    return [{**d, "created_at": _when(d["created_at"]), "confirmed_at": _when(d["confirmed_at"])} for d in store.all_docs()]

class Upload(BaseModel):
    name: str = Field("", max_length=120)
    data: str = Field(max_length=MAX_BYTES * 2)   # base64 (a «data:...;base64,» prefix is fine)

@router.post("/documents")
def upload(req: Upload):
    try:
        data = base64.b64decode(req.data.split(",", 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="فایل درست ارسال نشد.")
    return _public(store.get(_accept_file(F.clean(req.name), data)))

class Paste(BaseModel):
    name: str = Field("", max_length=120)
    text: str = Field(min_length=1, max_length=50_000)

@router.post("/documents/text")
def paste(req: Paste):
    doc_id = store.add(F.clean(req.name) or "متن واردشده", "text", "text")
    os.makedirs(store.doc_dir(doc_id), exist_ok=True)
    with open(os.path.join(store.doc_dir(doc_id), "text.txt"), "w", encoding="utf-8") as f:
        f.write(req.text)
    _start(doc_id)
    return _public(store.get(doc_id))

@router.post("/samples/{key}")
def sample(key: str):
    s = next((s for s in SAMPLES if s["key"] == key), None)
    if not s:
        raise HTTPException(status_code=404, detail="این نمونه پیدا نشد.")
    with open(os.path.join(SAMPLES_DIR, s["file"]), "rb") as f:
        return _public(store.get(_accept_file("نمونه: " + s["title"], f.read())))

@router.get("/documents/{doc_id}")
def document(doc_id: int):
    return _public(_doc(doc_id))

@router.get("/documents/{doc_id}/pages/{n}")
def page_image(doc_id: int, n: int):
    p = next((p for p in _doc(doc_id)["pages"] if p["n"] == n), None)
    if not p or not p["image"] or not os.path.exists(p["image"]):
        raise HTTPException(status_code=404)
    return FileResponse(p["image"], media_type="image/png")

@router.post("/documents/{doc_id}/extract")
def extract_again(doc_id: int):
    """Extract again (after the AI switch changed, or after an error). The pages are not read again."""
    d = _doc(doc_id)
    if d["status"] == "confirmed":
        raise HTTPException(status_code=409, detail="این سند تأیید شده است.")
    _start(doc_id)
    return _public(store.get(doc_id))

# ---------- the reviewer's corrections ----------

class Edit(BaseModel):
    fields: dict[str, str | float | int | None] = {}
    owners: list[dict[str, str | float | int | None]] = []
    transfers: list[dict[str, str | None]] = []

def _apply(deed, edit):
    """The reviewer's values over the extracted deed: each cleaned and checked again, marked edited when changed.
    A field the reviewer saved is settled: its «pages disagree» note goes, the other values stay listed."""
    deed = copy.deepcopy(deed)
    for k in SCALARS:
        if k in edit.fields:
            _set(deed["fields"][k], k, edit.fields[k])
    owners = []
    for i, o in enumerate(edit.owners):
        old = deed["owners"][i] if i < len(deed["owners"]) else {k: extract.field() for k in ("name", "father_name", "national_id", "share")}
        for k in ("name", "father_name", "national_id", "share"):
            _set(old[k], k, o.get(k))
        if any(old[k]["value"] for k in old):
            owners.append(old)
    deed["owners"] = owners
    transfers = []
    for t in edit.transfers:
        date, issues = F.validate("date", t.get("date"))
        row = {"date": date, "from": F.clean(t.get("from")), "to": F.clean(t.get("to")), "share": F.clean(t.get("share")),
               "note": F.clean(t.get("note"))}
        if any(row.values()):
            transfers.append({**row, "page": t.get("page"), "source": t.get("source"), "issues": issues})
    deed["transfers"] = transfers
    deed["issues"] = extract.deed_issues(deed["fields"], deed["owners"])
    return deed

def _set(f, key, raw):
    value, issues = F.validate(key, raw)
    if value != f["value"]:
        f["edited"] = True
    f["value"], f["issues"] = value, issues
    if issues:
        f["confidence"] = "low"
    f["resolved"] = bool(f["conflicts"])

def _review(doc_id, edit, confirm):
    d = _doc(doc_id)
    if d["status"] not in ("review", "confirmed") or not d["result"]:
        raise HTTPException(status_code=409, detail="این سند هنوز آماده‌ی بررسی نیست.")
    deed = _apply(d["edited"] or d["result"], edit)
    store.update(doc_id, edited=deed, status="confirmed" if confirm else "review", confirmed_at=store.now() if confirm else None)
    return _public(store.get(doc_id))

@router.post("/documents/{doc_id}/save")
def save(doc_id: int, edit: Edit):
    return _review(doc_id, edit, False)

@router.post("/documents/{doc_id}/confirm")
def confirm(doc_id: int, edit: Edit):
    return _review(doc_id, edit, True)

@router.get("/documents/{doc_id}/export")
def export(doc_id: int):
    """The confirmed deed as plain JSON, ready for the single-page deed."""
    d = _doc(doc_id)
    if d["status"] != "confirmed":
        raise HTTPException(status_code=409, detail="اول باید سند تأیید شود.")
    deed = d["edited"]
    v = {k: f["value"] for k, f in deed["fields"].items()}
    owners = [{"name": o["name"]["value"], "father_name": o["father_name"]["value"], "national_id": o["national_id"]["value"],
               "share": o["share"]["value"], "share_dang": F.dang(o["share"]["value"])} for o in deed["owners"]]
    shares = [o["share_dang"] for o in owners]
    return {
        "deed_number": v["deed_number"], "issue_date": v["issue_date"],
        "registry": {"book": v["book"], "page": v["page"]},
        "plate": {"main": v["main_plate"], "sub": v["sub_plate"]}, "section": v["section"],
        "area": {"value": v["area"], "unit": v["area_unit"]},
        "boundaries": {k: v[k] for k in ("north", "east", "south", "west")},
        "owners": owners, "shares_total_dang": sum(shares) if shares and None not in shares else None,
        "transfers": [{k: t[k] for k in ("date", "from", "to", "share", "note")} for t in deed["transfers"]],
        "review": {"source_file": d["name"], "read_by": d["method"], "confirmed_at": _when(d["confirmed_at"]), "open_issues": deed["issues"]},
    }
