"""The eco-lodge's own database (lodge.db, path LODGE_DB_PATH) and its photos (LODGE_DIR), apart from the others.

Two kinds of people log in: the lodge's staff (users: the host and a helper, in the panel) and guests (guests, on the
public website, with a mobile number and their own password). Their sessions are kept apart, so a guest's token never
opens the panel.

A booking holds one unit from its arrival day to the day before its departure. Its life: requested (the guest asked)
→ approved (the host said yes; waiting for the deposit until deposit_due) → paid (a receipt was sent) → confirmed
(the host checked the receipt). It can be rejected (by the host), or cancelled (by either side). Money is in toman.
"""
import os, sqlite3, secrets
from datetime import datetime, date
import db as school_db   # only for its password hashing

DB_PATH = os.getenv("LODGE_DB_PATH", "lodge.db")
DIR = os.getenv("LODGE_DIR", "lodge_files")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
ROLE_NAMES = {"host": "میزبان", "helper": "همکار"}

def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS units (            -- active 0: not shown or sold (a room under repair, closed for the season)
    id INTEGER PRIMARY KEY, name TEXT, kind TEXT, beds INTEGER, capacity INTEGER, price INTEGER, weekend_price INTEGER,
    description TEXT, amenities TEXT, art TEXT, active INTEGER DEFAULT 1, sort INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS photos (id INTEGER PRIMARY KEY, unit_id INTEGER, file TEXT, sort INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS blocks (id INTEGER PRIMARY KEY, unit_id INTEGER, start TEXT, end TEXT, note TEXT);   -- nights start .. end - 1 closed
CREATE TABLE IF NOT EXISTS guests (id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE, password TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS guest_sessions (token TEXT PRIMARY KEY, guest_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY, guest_id INTEGER, unit_id INTEGER, arrive TEXT, depart TEXT, adults INTEGER, children INTEGER,
    status TEXT, source TEXT, nights TEXT, total INTEGER, deposit INTEGER, deposit_due TEXT, note TEXT, created TEXT, decided TEXT,
    feedback_asked TEXT);
CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, booking_id INTEGER, at TEXT, file TEXT, status TEXT);  -- waiting, ok, rejected
CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, booking_id INTEGER, at TEXT, side TEXT, text TEXT, seen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS reviews (          -- status: waiting (for the host), shown, hidden
    id INTEGER PRIMARY KEY, booking_id INTEGER UNIQUE, guest_id INTEGER, unit_id INTEGER, stars INTEGER, text TEXT, at TEXT,
    status TEXT, reply TEXT);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT, who TEXT, role TEXT, kind TEXT, text TEXT, booking_id INTEGER);
"""
TABLES = ("users", "sessions", "meta", "units", "photos", "blocks", "guests", "guest_sessions", "bookings", "receipts", "messages", "reviews", "events")

def init():
    os.makedirs(DIR, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)

def wipe():
    with conn() as c:
        for t in TABLES:
            c.execute(f"DELETE FROM {t}")
    for f in os.listdir(DIR):
        try:
            os.remove(os.path.join(DIR, f))
        except OSError:
            pass

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

hash_password, check_password = school_db.hash_password, school_db.check_password

def add_user(c, username, full_name, role):
    return c.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
                     (username, hash_password("1234"), full_name, role)).lastrowid

def login(username, password):
    with conn() as c:
        user = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not check_password(password, user["password"]):
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

def guest_by_token(token):
    if not token:
        return None
    with conn() as c:
        row = c.execute("""SELECT g.* FROM guest_sessions s JOIN guests g ON g.id = s.guest_id
                           WHERE s.token = ? AND s.created_at > datetime('now', '-30 days')""", (token,)).fetchone()
    return dict(row) if row else None

def guest_session(c, guest_id):
    token = secrets.token_urlsafe(32)
    c.execute("INSERT INTO guest_sessions (token, guest_id) VALUES (?, ?)", (token, guest_id))
    return token

def logout(token):
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE token = ?", (token,))
        c.execute("DELETE FROM guest_sessions WHERE token = ?", (token,))

def logout_all():
    with conn() as c:
        c.execute("DELETE FROM sessions")

def public_user(u):
    return {"id": u["id"], "username": u["username"], "full_name": u["full_name"], "role": u["role"], "role_name": ROLE_NAMES.get(u["role"], u["role"])}

def log(c, who, kind, text, booking_id=None, at=None):
    """who: a staff user, a guest ({"name": ...}) or None (the website)."""
    if who and "role" in who:
        name, role = who["full_name"], ROLE_NAMES.get(who["role"], "")
    else:
        name, role = (who["name"] if who else "سایت"), "مهمان"
    c.execute("INSERT INTO events (at, who, role, kind, text, booking_id) VALUES (?,?,?,?,?,?)", (at or stamp(), name, role, kind, text, booking_id))
