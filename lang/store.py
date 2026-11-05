"""The language institute's own database (lang.db, path LANG_DB_PATH), apart from the other assistants'.

Dates are ISO («2026-11-02»), a time of day «17:45». Money is in toman. A class meets on a pair of weekdays
(satmon, suntue, wedthu) at one of the day's slots, in one room. An enrolment is a learner in a class: active in the
running term, registered for the next one, then passed or failed. Every change made in the app goes into events with
who and when (log); the manager sees it live.
"""
import os, sqlite3, secrets
from datetime import datetime, date
import db as school_db   # only for its password hashing

DB_PATH = os.getenv("LANG_DB_PATH", "lang.db")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
ROLE_NAMES = {"owner": "مدیر", "secretary": "منشی", "teacher": "استاد", "student": "زبان‌آموز"}

def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT, ref_id INTEGER);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, levels TEXT, avail TEXT, joined TEXT);
CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, created TEXT, start_key TEXT);
CREATE TABLE IF NOT EXISTS terms (id INTEGER PRIMARY KEY, name TEXT, start TEXT, end TEXT, kind TEXT);   -- past, current, next
CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY, term_id INTEGER, course TEXT, teacher_id INTEGER, room INTEGER, pair TEXT, time TEXT);
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY, student_id INTEGER, class_id INTEGER, status TEXT, registered TEXT, fee INTEGER,
    midterm INTEGER, final INTEGER, score INTEGER);         -- active, registered, passed, failed, dropped
CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, student_id INTEGER, enrollment_id INTEGER, at TEXT, amount INTEGER, method TEXT, user_id INTEGER);
CREATE TABLE IF NOT EXISTS attendance (class_id INTEGER, student_id INTEGER, day TEXT, status TEXT, PRIMARY KEY (class_id, student_id, day));
CREATE TABLE IF NOT EXISTS exams (id INTEGER PRIMARY KEY, class_id INTEGER, kind TEXT, title TEXT, questions TEXT, opens TEXT, closes TEXT, minutes INTEGER,
    created_by TEXT, created TEXT);                          -- quiz (a class's online test), placement
CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, exam_id INTEGER, student_id INTEGER, started TEXT, answers TEXT, submitted TEXT,
    score INTEGER, by_skill TEXT, placed TEXT);
CREATE TABLE IF NOT EXISTS ticks (student_id INTEGER, week TEXT, item TEXT, PRIMARY KEY (student_id, week, item));
CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, student_id INTEGER, at TEXT, user_id INTEGER, kind TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT, who TEXT, role TEXT, kind TEXT, text TEXT, student_id INTEGER, class_id INTEGER);
CREATE INDEX IF NOT EXISTS enr_class ON enrollments (class_id);
CREATE INDEX IF NOT EXISTS enr_student ON enrollments (student_id);
CREATE INDEX IF NOT EXISTS att_student ON attendance (student_id, day);
"""
TABLES = ("users", "sessions", "meta", "teachers", "students", "terms", "classes", "enrollments", "payments", "attendance", "exams", "attempts",
          "ticks", "contacts", "events")

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

def now_hm():
    return datetime.now().strftime("%H:%M")

def stamp():
    return f"{today().isoformat()} {datetime.now():%H:%M}"

def add_user(c, username, full_name, role, ref_id=None):
    return c.execute("INSERT INTO users (username, password, full_name, role, ref_id) VALUES (?,?,?,?,?)",
                     (username, school_db.hash_password("1234"), full_name, role, ref_id)).lastrowid

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
    return {"id": u["id"], "username": u["username"], "full_name": u["full_name"], "role": u["role"], "ref_id": u["ref_id"],
            "role_name": ROLE_NAMES.get(u["role"], u["role"])}

def log(c, user, kind, text, student_id=None, class_id=None, at=None):
    c.execute("INSERT INTO events (at, who, role, kind, text, student_id, class_id) VALUES (?,?,?,?,?,?,?)",
              (at or stamp(), user["full_name"] if user else "سیستم", ROLE_NAMES.get(user["role"], "") if user else "", kind, text, student_id, class_id))
