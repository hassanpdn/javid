"""The hotel's own database (hotel.db, path HOTEL_DB_PATH), apart from the other assistants'.

Dates are ISO («2026-11-02»); a moment is «2026-11-02 14:30». A booking holds one room (or one room type, until a room
is given) from its arrival day to its departure day: the nights are arrive .. depart - 1. Money is in toman. The folio
of a booking is its charges minus its payments. Every change made in the app goes into events with who and when.
"""
import os, sqlite3, secrets
from datetime import datetime, date
import db as school_db   # only for its password hashing

DB_PATH = os.getenv("HOTEL_DB_PATH", "hotel.db")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
ROLE_NAMES = {"manager": "مدیر هتل", "reservation": "رزرو", "reception": "پذیرش", "housekeeping": "خانه‌داری"}

def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS rooms (            -- status: clean, dirty, inspected; ooo_*: out of order (repairs)
    id INTEGER PRIMARY KEY, number TEXT, type TEXT, floor INTEGER, status TEXT, ooo_from TEXT, ooo_to TEXT, ooo_note TEXT);
CREATE TABLE IF NOT EXISTS room_log (id INTEGER PRIMARY KEY, room_id INTEGER, at TEXT, status TEXT, user_id INTEGER);
CREATE TABLE IF NOT EXISTS guests (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, national_id TEXT, vip INTEGER DEFAULT 0, notes TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS agencies (         -- kind: agency, site (online booking sites), company
    id INTEGER PRIMARY KEY, name TEXT, kind TEXT, discount REAL, commission REAL, phone TEXT);
CREATE TABLE IF NOT EXISTS allotments (id INTEGER PRIMARY KEY, agency_id INTEGER, type TEXT, arrive TEXT, depart TEXT, rooms INTEGER, release TEXT);
CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, name TEXT, agency_id INTEGER, allotment_id INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS bookings (         -- status: tentative, confirmed, in_house, out, cancelled, noshow
    id INTEGER PRIMARY KEY, guest_id INTEGER, room_id INTEGER, type TEXT, arrive TEXT, depart TEXT, adults INTEGER, children TEXT,
    board TEXT, source TEXT, agency_id INTEGER, group_id INTEGER, ref TEXT, status TEXT, deposit_due TEXT, nights TEXT, total INTEGER,
    discount REAL, eta TEXT, requests TEXT, created TEXT, created_by INTEGER, checked_in TEXT, checked_out TEXT, plate TEXT, docs INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS charges (id INTEGER PRIMARY KEY, booking_id INTEGER, day TEXT, at TEXT, kind TEXT, amount INTEGER, note TEXT, user_id INTEGER);
CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, booking_id INTEGER, at TEXT, amount INTEGER, method TEXT, kind TEXT, user_id INTEGER);
CREATE TABLE IF NOT EXISTS tasks (            -- kind: request (a guest asked), repair; status: open, done
    id INTEGER PRIMARY KEY, room_id INTEGER, booking_id INTEGER, kind TEXT, text TEXT, created TEXT, status TEXT, done_at TEXT, done_by INTEGER);
CREATE TABLE IF NOT EXISTS waitlist (id INTEGER PRIMARY KEY, guest_id INTEGER, type TEXT, arrive TEXT, depart TEXT, adults INTEGER, note TEXT, added TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS closes (day TEXT PRIMARY KEY, at TEXT, user_id INTEGER, posted INTEGER, cash_expected INTEGER, cash_counted INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS web_chats (id TEXT PRIMARY KEY, state TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT, who TEXT, role TEXT, kind TEXT, text TEXT, booking_id INTEGER);
-- the public website (public.py): guests' own accounts, which bookings each made, and deposit receipts (waiting, ok, rejected)
CREATE TABLE IF NOT EXISTS site_accounts (id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE, password TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS site_sessions (token TEXT PRIMARY KEY, account_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS site_bookings (booking_id INTEGER PRIMARY KEY, account_id INTEGER);
CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, booking_id INTEGER, at TEXT, file TEXT, status TEXT);
"""
# wiped when the demo is built again; guests' accounts and sessions are not, and their bookings still to come are carried
# over (keep_site / restore_site), so a guest of the public website never loses their account or their trip
TABLES = ("users", "sessions", "meta", "rooms", "room_log", "guests", "agencies", "allotments", "groups", "bookings", "charges",
          "payments", "tasks", "waitlist", "closes", "web_chats", "events", "site_bookings", "receipts")
DIR = os.getenv("HOTEL_DIR", "hotel_files")   # receipts' photos

def init():
    os.makedirs(DIR, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)

def keep_site():
    """The website guests' bookings still to come (with their payments and receipts), read before a rebuild."""
    with conn() as c:
        rows = c.execute("""SELECT b.*, s.account_id, g.name AS g_name, g.phone AS g_phone FROM site_bookings s
                            JOIN bookings b ON b.id = s.booking_id JOIN guests g ON g.id = b.guest_id
                            WHERE b.status IN ('tentative', 'confirmed') AND b.arrive >= ?""", (today().isoformat(),)).fetchall()
        return [{"b": dict(r), "pays": [dict(p) for p in c.execute("SELECT * FROM payments WHERE booking_id = ?", (r["id"],))],
                 "receipts": [dict(x) for x in c.execute("SELECT * FROM receipts WHERE booking_id = ?", (r["id"],))]} for r in rows]

def restore_site(c, kept):
    """Put them back into the rebuilt demo, without a room (the desk gives one, as with any booking)."""
    cols = ("type", "arrive", "depart", "adults", "children", "board", "source", "status", "deposit_due", "nights", "total", "discount", "eta",
            "requests", "created")
    for k in kept:
        b = k["b"]
        g = c.execute("SELECT id FROM guests WHERE phone = ? ORDER BY id DESC LIMIT 1", (b["g_phone"],)).fetchone()
        gid = g["id"] if g else c.execute("INSERT INTO guests (name, phone, vip, notes, created) VALUES (?,?,0,'',?)",
                                          (b["g_name"], b["g_phone"], today().isoformat())).lastrowid
        bid = c.execute(f"INSERT INTO bookings (guest_id, {', '.join(cols)}) VALUES (?{', ?' * len(cols)})", (gid, *(b[x] for x in cols))).lastrowid
        c.execute("INSERT INTO site_bookings (booking_id, account_id) VALUES (?, ?)", (bid, b["account_id"]))
        for p in k["pays"]:
            c.execute("INSERT INTO payments (booking_id, at, amount, method, kind) VALUES (?,?,?,?,?)", (bid, p["at"], p["amount"], p["method"], p["kind"]))
        for r in k["receipts"]:
            c.execute("INSERT INTO receipts (booking_id, at, file, status) VALUES (?,?,?,?)", (bid, r["at"], r["file"], r["status"]))

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

def now_time():
    return f"{datetime.now():%H:%M}"

def stamp():
    return f"{today().isoformat()} {now_time()}"

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
        c.execute("DELETE FROM site_sessions WHERE token = ?", (token,))

hash_password, check_password = school_db.hash_password, school_db.check_password

def account_by_token(token):
    if not token:
        return None
    with conn() as c:
        row = c.execute("""SELECT a.* FROM site_sessions s JOIN site_accounts a ON a.id = s.account_id
                           WHERE s.token = ? AND s.created_at > datetime('now', '-30 days')""", (token,)).fetchone()
    return dict(row) if row else None

def account_session(c, account_id):
    token = secrets.token_urlsafe(32)
    c.execute("INSERT INTO site_sessions (token, account_id) VALUES (?, ?)", (token, account_id))
    return token

def logout_all():
    with conn() as c:
        c.execute("DELETE FROM sessions")

def public_user(u):
    return {"id": u["id"], "username": u["username"], "full_name": u["full_name"], "role": u["role"],
            "role_name": ROLE_NAMES.get(u["role"], u["role"])}

def log(c, user, kind, text, booking_id=None, at=None):
    """user: a staff user, a website guest ({"name": ...}) or None (the website's assistant)."""
    if user and "role" in user:
        who, role = user["full_name"], ROLE_NAMES.get(user["role"], "")
    else:
        who, role = (user["name"] if user else "سایت هتل"), ("مهمان" if user else "")
    c.execute("INSERT INTO events (at, who, role, kind, text, booking_id) VALUES (?,?,?,?,?,?)", (at or stamp(), who, role, kind, text, booking_id))
