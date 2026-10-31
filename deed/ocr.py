"""Reading the scanned pages: everything runs here on the server, with the Tesseract and poppler command-line tools
(apt packages tesseract-ocr, tesseract-ocr-fas, poppler-utils). Nothing is sent anywhere.

A file becomes page images (pdftoppm for a PDF), each page is turned upright (Tesseract's own orientation check),
read with the Persian model, and judged: a page with too little Persian text or too low a confidence is «not
readable» and is left out, with a message, instead of passing garbage on. Results are kept per page image (by its
hash), so extracting again, or the same file uploaded twice, never reads a page twice.
"""
import csv, hashlib, io, os, re, subprocess, threading
from PIL import Image, ImageOps

TIMEOUT = 90                    # seconds for one tool run on one page
MAX_PIXELS = 40_000_000         # a bigger image is refused (and Pillow refuses to open "decompression bombs")
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
MIN_PERSIAN = 40                # fewer Persian letters than this on a page: not readable
MIN_CONF = 55                   # mean word confidence (0..100) below this: not readable

# One page at a time, each Tesseract on one thread: several at once fight over the processor's threads and a page
# that takes 2 seconds alone took over a minute
_one = threading.Lock()
_ENV = {**os.environ, "OMP_THREAD_LIMIT": "1"}

class OcrError(Exception):
    """The tools are missing or failed; the message is for the reviewer."""

def available():
    try:
        out = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=20).stdout
        return "fas" in out.split()
    except Exception:
        return False

def _run(args):
    try:
        with _one:
            return subprocess.run(args, capture_output=True, timeout=TIMEOUT, check=True, env=_ENV)
    except FileNotFoundError:
        raise OcrError("ابزار خواندن متن (Tesseract) روی سرور نصب نیست.")
    except subprocess.TimeoutExpired:
        raise OcrError("خواندن این صفحه بیش از حد طول کشید.")
    except subprocess.CalledProcessError as e:
        raise OcrError("خواندن صفحه ممکن نشد: " + (e.stderr or b"").decode(errors="ignore")[-200:])

def pdf_pages(path):
    out = _run(["pdfinfo", path]).stdout.decode(errors="ignore")
    m = re.search(r"Pages:\s+(\d+)", out)
    return int(m.group(1)) if m else 0

def split(path, kind, folder):
    """The file as one PNG per page in folder, in order: [path, ...]."""
    os.makedirs(folder, exist_ok=True)
    if kind == "pdf":
        _run(["pdftoppm", "-r", "200", "-png", path, os.path.join(folder, "p")])
        return sorted((os.path.join(folder, f) for f in os.listdir(folder) if f.startswith("p-")),
                      key=lambda f: int(re.search(r"-(\d+)\.png$", f).group(1)))
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")   # a phone photo's own "turned" flag
    out = os.path.join(folder, "p-1.png")
    img.save(out)
    return [out]

def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def _upright(path):
    """Tesseract's orientation check; the page turned upright, and how many degrees it was turned."""
    try:
        out = _run(["tesseract", path, "-", "--psm", "0", "-l", "osd"]).stdout.decode(errors="ignore")
    except OcrError:
        return path, 0   # too little text to tell: read it as it is (it may then be judged unreadable)
    m, conf = re.search(r"Rotate:\s+(\d+)", out), re.search(r"Orientation confidence:\s+([\d.]+)", out)
    turn = int(m.group(1)) if m else 0
    if not turn or not conf or float(conf.group(1)) < 1.5:
        return path, 0
    img = Image.open(path).rotate(-turn, expand=True, fillcolor="white")
    img.save(path)    # the page image shown next to the form is the upright one
    return path, turn

def _prepare(path):
    """Greyscale, small scans enlarged, contrast stretched: what helps Tesseract with old paper."""
    img = ImageOps.autocontrast(Image.open(path).convert("L"))
    if img.width < 1600:
        img = img.resize((1600, round(img.height * 1600 / img.width)))
    out = os.path.splitext(path)[0] + "-ocr.png"
    img.save(out)
    return out

def read_page(path):
    """{"text", "lines": [{"text", "conf"}], "conf", "rotation", "readable", "note"} for one page image."""
    path, turn = _upright(path)
    tsv = _run(["tesseract", _prepare(path), "-", "-l", "fas", "--psm", "6", "tsv"]).stdout.decode("utf-8", errors="ignore")
    lines = {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        word = (row.get("text") or "").strip()
        if row.get("level") != "5" or not word:
            continue
        key = (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))
        lines.setdefault(key, []).append((word, float(row["conf"])))
    out = [{"text": " ".join(w for w, _ in ws), "conf": round(sum(c for _, c in ws) / len(ws))} for _, ws in sorted(lines.items())]
    words = [c for ws in lines.values() for _, c in ws]
    conf = round(sum(words) / len(words)) if words else 0
    persian = len(re.findall(r"[؀-ۿ]", " ".join(l["text"] for l in out)))
    readable = persian >= MIN_PERSIAN and conf >= MIN_CONF
    note = "" if readable else (
        "روی این صفحه متن فارسی کافی پیدا نشد (شاید سفید، عکس یا بسیار کم‌رنگ است)." if persian < MIN_PERSIAN
        else "کیفیت این صفحه برای خواندن مطمئن کافی نیست (تار، کج یا کم‌رنگ). لطفاً اسکن بهتری بفرستید.")
    return {"text": "\n".join(l["text"] for l in out), "lines": out, "conf": conf, "rotation": turn,
            "readable": readable, "note": note}
