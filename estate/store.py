"""The agency's own database (estate.db, path ESTATE_DB_PATH), apart from the school's and the fabric shop's.

Money is in toman, dates are ISO («2026-11-02»), a visit's time is «2026-11-03 17:30». Every change made in the app
goes into events with who and when (log); the owner sees it live and the checks read it.
"""
import json, os, sqlite3, secrets
from datetime import datetime, date
import db as school_db   # only for its password hashing

DB_PATH = os.getenv("ESTATE_DB_PATH", "estate.db")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
ROLE_NAMES = {"owner": "مدیر بنگاه", "agent": "مشاور املاک"}

def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS listings (          -- a unit for sale or rent (فایل)
    id INTEGER PRIMARY KEY, kind TEXT, hood TEXT, street TEXT, area INTEGER, rooms INTEGER, floor INTEGER, floors INTEGER,
    age INTEGER, elevator INTEGER, parking INTEGER, storage INTEGER, price INTEGER, deposit INTEGER, rent INTEGER,
    owner_name TEXT, owner_phone TEXT, note TEXT, agent_id INTEGER, status TEXT, created TEXT, last_contact TEXT,
    last_report TEXT, closed TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS requests (          -- a buyer or a renter looking for a unit (متقاضی)
    id INTEGER PRIMARY KEY, kind TEXT, name TEXT, phone TEXT, hoods TEXT, budget INTEGER, deposit INTEGER, rent INTEGER,
    rooms INTEGER, area INTEGER, needs TEXT, note TEXT, agent_id INTEGER, status TEXT, created TEXT, closed TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS calls (             -- a match offered to a buyer: who called whom about which unit
    id INTEGER PRIMARY KEY, listing_id INTEGER, request_id INTEGER, at TEXT, user_id INTEGER, outcome TEXT);
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY, listing_id INTEGER, request_id INTEGER, at TEXT, agent_id INTEGER, status TEXT,
    outcome TEXT, note TEXT, next_step TEXT);
CREATE TABLE IF NOT EXISTS deals (             -- closed deals; the old ones are the price history of each neighbourhood
    id INTEGER PRIMARY KEY, kind TEXT, listing_id INTEGER, request_id INTEGER, date TEXT, hood TEXT, area INTEGER, age INTEGER,
    price INTEGER, deposit INTEGER, rent INTEGER, buyer TEXT, seller TEXT, agents TEXT, commission INTEGER, expected INTEGER);
CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, listing_id INTEGER, at TEXT, user_id INTEGER, text TEXT);
CREATE TABLE IF NOT EXISTS web_chats (id TEXT PRIMARY KEY, state TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS events (            -- who did what and when; nothing in the app changes without a line here
    id INTEGER PRIMARY KEY, at TEXT, who TEXT, role TEXT, kind TEXT, text TEXT, listing_id INTEGER, request_id INTEGER);
"""
DATA_TABLES = ("users", "sessions", "listings", "requests", "calls", "visits", "deals", "reports", "web_chats", "events", "meta")

def init():
    with conn() as c:
        c.executescript(SCHEMA)

def wipe():
    with conn() as c:
        for t in DATA_TABLES:
            c.execute(f"DELETE FROM {t}")

def get_meta(key, default=None):
    with conn() as c:
        row = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default

def set_meta(c, key, value):
    c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))

def today():
    return date.fromisoformat(os.getenv("DEMO_TODAY") or date.today().isoformat())

def stamp():
    """Now, on the demo's day: «2026-11-02 14:20»."""
    return f"{today().isoformat()} {datetime.now():%H:%M}"

# ---------- logins ----------

def add_user(c, username, full_name, role):
    cur = c.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
                    (username, school_db.hash_password("1234"), full_name, role))
    return cur.lastrowid

def login(username, password):
    with conn() as c:
        user = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not school_db.check_password(password, user["password"]):
            return None
        token = secrets.token_urlsafe(32)
        c.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user["id"]))
    return token, dict(user)

def user_by_token(token):
    if not token:
        return None
    with conn() as c:
        row = c.execute(f"""SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
                            WHERE s.token = ? AND s.created_at > datetime('now', '-{SESSION_DAYS} days')""", (token,)).fetchone()
    return dict(row) if row else None

def logout(token):
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE token = ?", (token,))

def logout_all():
    with conn() as c:
        c.execute("DELETE FROM sessions")

def public_user(u):
    return {"id": u["id"], "username": u["username"], "full_name": u["full_name"], "role": u["role"],
            "role_name": ROLE_NAMES.get(u["role"], u["role"])}

def log(c, user, kind, text, listing_id=None, request_id=None):
    """One line in the event log. user is the logged-in user (dict) or None for the website or the system."""
    c.execute("INSERT INTO events (at, who, role, kind, text, listing_id, request_id) VALUES (?,?,?,?,?,?,?)",
              (stamp(), user["full_name"] if user else "سایت بنگاه", ROLE_NAMES.get(user["role"], "") if user else "",
               kind, text, listing_id, request_id))

def as_json(v):
    return json.dumps(v, ensure_ascii=False)
