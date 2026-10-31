"""The deed assistant's own storage: deed.db (DEED_DB_PATH) and the files in DEED_DIR, apart from the other assistants.

documents: one uploaded deed (a file or pasted text), where it is in the work, the deed as extracted and as the
reviewer left it. pages: each page's image and what OCR read on it. ocr: OCR results by page-image hash, so the same
page is never read twice. On the live site every visit starts fresh (reset), like the other assistants.
"""
import json, os, shutil, sqlite3
from datetime import datetime

DB_PATH = os.getenv("DEED_DB_PATH", "deed.db")
DIR = os.getenv("DEED_DIR", "deed_files")

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY, name TEXT, source TEXT, kind TEXT, status TEXT, message TEXT, progress TEXT,
    method TEXT, result TEXT, edited TEXT, created_at TEXT, confirmed_at TEXT);
CREATE TABLE IF NOT EXISTS pages (
    doc_id INTEGER, n INTEGER, image TEXT, hash TEXT, lines TEXT, conf INTEGER, rotation INTEGER, readable INTEGER, note TEXT,
    PRIMARY KEY (doc_id, n));
CREATE TABLE IF NOT EXISTS ocr (hash TEXT PRIMARY KEY, lines TEXT, conf INTEGER, rotation INTEGER, readable INTEGER, note TEXT);
"""

def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c

def init():
    os.makedirs(DIR, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)

def now():
    return datetime.now().isoformat(timespec="seconds")

def doc_dir(doc_id):
    return os.path.join(DIR, str(doc_id))

def add(name, source, kind):
    with conn() as c:
        cur = c.execute("INSERT INTO documents (name, source, kind, status, created_at) VALUES (?, ?, ?, 'processing', ?)",
                        (name, source, kind, now()))
        return cur.lastrowid

def update(doc_id, **cols):
    cols = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in cols.items()}
    with conn() as c:
        c.execute(f"UPDATE documents SET {', '.join(k + ' = ?' for k in cols)} WHERE id = ?", (*cols.values(), doc_id))

def get(doc_id):
    with conn() as c:
        d = c.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not d:
            return None
        pages = c.execute("SELECT * FROM pages WHERE doc_id = ? ORDER BY n", (doc_id,)).fetchall()
    d = dict(d)
    for k in ("result", "edited", "progress"):
        d[k] = json.loads(d[k]) if d[k] else None
    d["pages"] = [{**dict(p), "lines": json.loads(p["lines"] or "[]"), "readable": bool(p["readable"])} for p in pages]
    return d

def all_docs():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, name, source, status, message, created_at, confirmed_at FROM documents ORDER BY id DESC")]

def save_page(doc_id, n, image, h, r):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (doc_id, n, image, h, json.dumps(r["lines"], ensure_ascii=False), r["conf"], r["rotation"], int(r["readable"]), r["note"]))

def cached_ocr(h):
    with conn() as c:
        r = c.execute("SELECT * FROM ocr WHERE hash = ?", (h,)).fetchone()
    return {**dict(r), "lines": json.loads(r["lines"]), "readable": bool(r["readable"])} if r else None

def cache_ocr(h, r):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO ocr VALUES (?, ?, ?, ?, ?, ?)",
                  (h, json.dumps(r["lines"], ensure_ascii=False), r["conf"], r["rotation"], int(r["readable"]), r["note"]))

def reset():
    """Forget every uploaded deed, its files and the OCR cache (which holds the pages' text). Called on each new visit
    of the live site and on every logout."""
    init()
    with conn() as c:
        c.executescript("DELETE FROM documents; DELETE FROM pages; DELETE FROM ocr;")
    shutil.rmtree(DIR, ignore_errors=True)
    os.makedirs(DIR, exist_ok=True)
