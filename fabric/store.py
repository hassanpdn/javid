"""The fabric assistant's own database (fabric.db, path FABRIC_DB_PATH), apart from the school's.

Users and sessions live only here. Everything else is a copy of the three Excel files (excel.import_all
fills it), plus what the app adds: invoices confirmed at the phone desk, reminder messages, import notes.
"""
import json, os, sqlite3, secrets
from datetime import datetime
import db as school_db   # only for its password hashing

DB_PATH = os.getenv("FABRIC_DB_PATH", "fabric.db")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
ROLE_NAMES = {"owner": "صاحب کار", "seller": "فروشنده", "accountant": "حسابدار"}

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS products (
    code TEXT PRIMARY KEY, name TEXT, material TEXT, color TEXT, width INTEGER,
    rolls INTEGER, roll_meters INTEGER, meters REAL, buy_price INTEGER, sell_price INTEGER,
    supplier TEXT, received TEXT, opening REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS stock_in (id INTEGER PRIMARY KEY, date TEXT, code TEXT, rolls INTEGER, meters REAL, supplier TEXT);
CREATE TABLE IF NOT EXISTS cash_deposits (id INTEGER PRIMARY KEY, date TEXT, amount INTEGER);
CREATE TABLE IF NOT EXISTS web_orders (       -- orders the website's assistant took; not paid, not invoices yet
    id INTEGER PRIMARY KEY, at TEXT, customer_id INTEGER, name TEXT, phone TEXT, items TEXT, total INTEGER,
    status TEXT, invoice_id INTEGER);
CREATE TABLE IF NOT EXISTS web_chats (id TEXT PRIMARY KEY, state TEXT, updated TEXT);   -- one website conversation each
CREATE TABLE IF NOT EXISTS events (           -- who did what and when; nothing in the app changes without a line here
    id INTEGER PRIMARY KEY, at TEXT, who TEXT, role TEXT, kind TEXT, text TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY, name TEXT, shop TEXT, city TEXT, phone TEXT, credit_limit INTEGER, opening INTEGER);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY, date TEXT, customer_id INTEGER, seller TEXT, payment TEXT, total INTEGER, source TEXT);
CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY, invoice_id INTEGER, product_code TEXT, rolls INTEGER, meters REAL, price INTEGER, amount INTEGER);
CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, date TEXT, customer_id INTEGER, amount INTEGER, method TEXT);
CREATE TABLE IF NOT EXISTS cheques_in (
    id INTEGER PRIMARY KEY, number TEXT, bank TEXT, customer_id INTEGER, amount INTEGER, due TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS cheques_out (id INTEGER PRIMARY KEY, number TEXT, payee TEXT, amount INTEGER, due TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, customer_id INTEGER, text TEXT, sent_at TEXT);
CREATE TABLE IF NOT EXISTS import_notes (id INTEGER PRIMARY KEY, file TEXT, note TEXT);
"""
DATA_TABLES = ("products", "customers", "invoices", "invoice_lines", "receipts", "cheques_in", "cheques_out", "import_notes",
               "stock_in", "cash_deposits")

def init():
    with conn() as c:
        c.executescript(SCHEMA)
        # a fabric.db made before the opening-stock column gets it (CREATE TABLE IF NOT EXISTS keeps old tables)
        if "opening" not in [r["name"] for r in c.execute("PRAGMA table_info(products)")]:
            c.execute("ALTER TABLE products ADD COLUMN opening REAL DEFAULT 0")

def get_meta(key, default=None):
    with conn() as c:
        row = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default

def set_meta(c, key, value):
    c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))

# ---------- logins ----------

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

def log(c, user, kind, text, detail=None):
    """One line in the event log. user is the logged-in user (dict) or None for the system itself."""
    c.execute("INSERT INTO events (at, who, role, kind, text, detail) VALUES (?,?,?,?,?,?)",
              (stamp(), user["full_name"] if user else "سیستم", user["role"] if user else "system", kind, text,
               json.dumps(detail, ensure_ascii=False) if detail is not None else None))

def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M")
