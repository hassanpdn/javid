import os, sqlite3, hashlib, secrets

DB_PATH = os.getenv("DB_PATH", "school.db")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))   # a login stays valid this many days
ROLE_NAMES = {
    "manager": "مدیر", "staff": "پرسنل اداری", "teacher": "معلم",
    "counselor": "مشاور", "parent": "ولی", "student": "دانش‌آموز",
}
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"

def check_password(password, stored):
    salt = stored.split("$", 1)[0]
    return secrets.compare_digest(hash_password(password, salt), stored)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT,
    ref_id INTEGER);  -- teacher id, student id, ... depending on role
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chat_logs (
    id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, question TEXT, answer TEXT,
    sources TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY, full_name TEXT, subject TEXT, gender TEXT);
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY, name TEXT, grade INTEGER, homeroom_teacher_id INTEGER);
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, gender TEXT, class_id INTEGER,
    parent_name TEXT, parent_phone TEXT);
CREATE TABLE IF NOT EXISTS assessments (      -- elementary descriptive grading, level 1..4
    id INTEGER PRIMARY KEY, student_id INTEGER, subject TEXT, date TEXT, jdate TEXT,
    level INTEGER, teacher_id INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS student_attendance (
    id INTEGER PRIMARY KEY, student_id INTEGER, date TEXT, jdate TEXT,
    status TEXT, excused INTEGER DEFAULT 0);  -- status: present / absent / late
CREATE TABLE IF NOT EXISTS teacher_attendance (
    id INTEGER PRIMARY KEY, teacher_id INTEGER, date TEXT, jdate TEXT, check_in TEXT, check_out TEXT);
CREATE TABLE IF NOT EXISTS counselor_notes (
    id INTEGER PRIMARY KEY, student_id INTEGER, date TEXT, jdate TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS letters (
    id INTEGER PRIMARY KEY, received_date TEXT, jreceived TEXT, sender TEXT, subject TEXT, body TEXT,
    deadline TEXT, jdeadline TEXT, status TEXT DEFAULT 'new',
    -- filled by the agent:
    category TEXT, summary TEXT, action TEXT, reply TEXT, handled_at TEXT,
    corrected INTEGER DEFAULT 0,                 -- 1 when staff fixed the agent's category
    manager_seen_at TEXT);                       -- when the manager pressed "seen" on a letter sent for their information
CREATE TABLE IF NOT EXISTS suggestions (         -- counselor-approved advice; parents only ever see approved ones
    id INTEGER PRIMARY KEY, student_id INTEGER, for_counselor TEXT, for_parent TEXT,
    status TEXT DEFAULT 'draft', created_at TEXT, approved_at TEXT, approved_by INTEGER);
CREATE TABLE IF NOT EXISTS health_forms (        -- physical and wellbeing forms filled by parents
    id INTEGER PRIMARY KEY, student_id INTEGER, kind TEXT, data TEXT, filled_by INTEGER,
    date TEXT, jdate TEXT, created_at TEXT, ai_summary TEXT, flags TEXT);
CREATE TABLE IF NOT EXISTS agent_log (           -- every step the agent takes, with its reason
    id INTEGER PRIMARY KEY, letter_id INTEGER, action TEXT, reason TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS warnings (            -- written warnings approved by the manager
    id INTEGER PRIMARY KEY, teacher_id INTEGER, text TEXT, date TEXT, jdate TEXT, issued_by INTEGER,
    acknowledged_at TEXT);                       -- when the teacher pressed "seen"
CREATE TABLE IF NOT EXISTS notifications (       -- in-app inbox for every user
    id INTEGER PRIMARY KEY, user_id INTEGER, kind TEXT, title TEXT, body TEXT,
    ref_type TEXT, ref_id INTEGER, needs_ack INTEGER DEFAULT 0,
    created_at TEXT, read_at TEXT, ack_at TEXT);
"""

LEVELS = {4: "خیلی خوب", 3: "خوب", 2: "قابل قبول", 1: "نیاز به تلاش بیشتر"}

def init():
    with conn() as c:
        c.executescript(SCHEMA)
        # databases made before a column existed get it added (CREATE TABLE IF NOT EXISTS leaves old tables as they are)
        if "manager_seen_at" not in [r["name"] for r in c.execute("PRAGMA table_info(letters)")]:
            c.execute("ALTER TABLE letters ADD COLUMN manager_seen_at TEXT")
    with conn() as c:
        empty = c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        seeded = c.execute("SELECT value FROM meta WHERE key = 'seeded_for'").fetchone()
    # The demo data is built around "today". If it was built on another day, rebuild it so the
    # dashboard and the stories line up with today's date. KEEP_DB=1 keeps the old data.
    from datetime import date
    today = os.getenv("DEMO_TODAY") or date.today().isoformat()
    if empty or ((not seeded or seeded[0] != today) and os.getenv("KEEP_DB") != "1"):
        import importlib, seed
        importlib.reload(seed)   # seed works out "today" when it is loaded
        seed.run()

def login(username, password):
    with conn() as c:
        u = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not u or not check_password(password, u["password"]):
            return None
        token = secrets.token_urlsafe(32)
        c.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, u["id"]))
        return token, dict(u)

def user_by_token(token):
    with conn() as c:
        u = c.execute("""SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id
                         WHERE sessions.token = ? AND sessions.created_at > datetime('now', ?)""",
                      (token, f"-{SESSION_DAYS} days")).fetchone()
        return dict(u) if u else None

def logout(token):
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE token = ?", (token,))

def log_chat(user, question, answer, sources):
    with conn() as c:
        c.execute("INSERT INTO chat_logs (user_id, role, question, answer, sources) VALUES (?, ?, ?, ?, ?)",
                  (user["id"], user["role"], question, answer, sources))

def stamp():
    """Demo date (from DEMO_TODAY) with the real clock time, in Persian calendar."""
    import os
    from datetime import date, datetime
    from jalali import to_jalali, MONTHS
    d = date.fromisoformat(os.getenv("DEMO_TODAY") or date.today().isoformat())
    y, m, dd = to_jalali(d)
    return f"{dd} {MONTHS[m - 1]} ساعت {datetime.now().strftime('%H:%M')}"

def notify(user_ids, kind, title, body="", ref_type=None, ref_id=None, needs_ack=False):
    with conn() as c:
        for uid in user_ids:
            c.execute("""INSERT INTO notifications (user_id, kind, title, body, ref_type, ref_id, needs_ack, created_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (uid, kind, title, body, ref_type, ref_id, int(needs_ack), stamp()))

def users_with(role, ref_id=None):
    with conn() as c:
        if ref_id is None:
            rows = c.execute("SELECT id FROM users WHERE role = ?", (role,)).fetchall()
        else:
            rows = c.execute("SELECT id FROM users WHERE role = ? AND ref_id = ?", (role, ref_id)).fetchall()
        return [r["id"] for r in rows]

def public_user(u):
    return {"username": u["username"], "full_name": u["full_name"], "role": u["role"],
            "role_name": ROLE_NAMES[u["role"]], "ref_id": u["ref_id"]}
