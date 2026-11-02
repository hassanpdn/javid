"""The law office's own database (law.db, path LAW_DB_PATH), apart from the other assistants'.

Dates are ISO («2026-11-02»); a hearing's time is «2026-11-05 10:30». Every change made in the app goes into events
with who and when (log); the owner sees it live and the checks read it.
"""
import os, sqlite3, secrets
from datetime import datetime, date
import db as school_db   # only for its password hashing

DB_PATH = os.getenv("LAW_DB_PATH", "law.db")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
ROLE_NAMES = {"owner": "وکیل", "associate": "همکار وکیل", "secretary": "منشی"}

def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY, name TEXT, phone TEXT);
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY, title TEXT, client_id INTEGER, opponent TEXT, side TEXT, field TEXT, court TEXT, branch TEXT,
    number TEXT, archive TEXT, stage TEXT, lawyer_id INTEGER, status TEXT, created TEXT, last_report TEXT);
CREATE TABLE IF NOT EXISTS notices (          -- a notice from the courts' system and what it asks for
    id INTEGER PRIMARY KEY, case_id INTEGER, kind TEXT, served TEXT, deadline TEXT, hearing TEXT, text TEXT,
    status TEXT, done_at TEXT, done_by INTEGER, note TEXT, entered_by INTEGER, entered TEXT);
CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, case_id INTEGER, at TEXT, user_id INTEGER, text TEXT);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY, at TEXT, who TEXT, role TEXT, kind TEXT, text TEXT, case_id INTEGER);
"""
TABLES = ("users", "sessions", "meta", "clients", "cases", "notices", "reports", "events")

def init():
    with conn() as c:
        c.executescript(SCHEMA)

def wipe():
    with conn() as c:
        for t in TABLES:
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
    return f"{today().isoformat()} {datetime.now():%H:%M}"

def add_user(c, username, full_name, role):
    return c.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
                     (username, school_db.hash_password("1234"), full_name, role)).lastrowid

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

def log(c, user, kind, text, case_id=None, at=None):
    c.execute("INSERT INTO events (at, who, role, kind, text, case_id) VALUES (?,?,?,?,?,?)",
              (at or stamp(), user["full_name"] if user else "سیستم", ROLE_NAMES.get(user["role"], "") if user else "", kind, text, case_id))
