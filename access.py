"""Who may open which assistant (the cards on the assistants page).

Two kinds of login, both checked here:
- the permanent account (ADMIN_USER / ADMIN_PASSWORD in the server's .env): opens every assistant, and is the only one
  who gives access to other people.
- a person's account, made by the permanent account on the assistants page: a name, a username and password, the
  assistants (one or more) this person may open, and an optional last day. Inside an assistant they can do everything
  (setup form, every role); the assistants page shows them only their own cards.

It is on only when ADMIN_PASSWORD is set (the live server). Locally and in tests every assistant opens straight away.
After a login the browser gets a signed cookie (like gate.py). A person's cookie is checked against their row on every
call, so changing their assistants takes effect at once, and deleting them, a new password or their last day passing
shuts that browser out.
Accounts live in their own small database (access.db), so resetting or rebuilding the demo data keeps them.
"""
import os, re, time, hmac, hashlib, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
import jalali

APPS = ("school", "fabric")
USER = os.getenv("ADMIN_USER", "")
PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ON = bool(PASSWORD)
COOKIE, DAYS = "access", 30
DB_PATH = os.getenv("ACCESS_DB_PATH", "access.db")
_KEY = hashlib.sha256(f"access\0{USER}\0{PASSWORD}".encode()).digest()
TEHRAN = timezone(timedelta(hours=3, minutes=30))   # Iran has had no summer time since 2022

router = APIRouter(prefix="/access")

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    # pw_ver goes up with every new password, and is part of the cookie, so an old password's logins end
    c.execute("""CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
        pw_ver INTEGER NOT NULL DEFAULT 1, apps TEXT NOT NULL, expires_on TEXT, expires_at INTEGER,
        created_at INTEGER NOT NULL, last_login INTEGER)""")
    return c

# Passwords are stored salted and stretched (PBKDF2), never as they were typed.
def _hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()

def _password_ok(password, stored):
    salt, _, _ = stored.partition("$")
    return hmac.compare_digest(_hash(password, salt), stored)

def _sign(text):
    return hmac.new(_KEY, text.encode(), hashlib.sha256).hexdigest()

def _cookie(who, expires):
    """who is "admin" or "p{id}-{pw_ver}". The cookie is who.expires.signature."""
    body = f"{who}.{expires}"
    return f"{body}.{_sign(body)}"

def _expired(p, now=None):
    return p["expires_at"] is not None and p["expires_at"] <= (now or time.time())

def holder(request: Request):
    """Whoever this browser's cookie belongs to: {"admin", "name", "apps", "expires_on"}, or None."""
    return _holder(request.cookies.get(COOKIE, ""))

def _holder(cookie):
    if not ON:   # without a password the signing key is known to anyone, so no cookie counts
        return None
    who, _, rest = cookie.partition(".")
    expires, _, sig = rest.partition(".")
    if not (expires.isdigit() and int(expires) > time.time() and hmac.compare_digest(sig, _sign(f"{who}.{expires}"))):
        return None
    if who == "admin":
        return {"admin": True, "name": "", "apps": list(APPS), "expires_on": None}
    m = re.fullmatch(r"p(\d+)-(\d+)", who)
    if not m:
        return None
    with _conn() as c:
        p = c.execute("SELECT * FROM people WHERE id = ?", (int(m[1]),)).fetchone()
    if not p or p["pw_ver"] != int(m[2]) or _expired(p):
        return None
    return {"admin": False, "name": p["name"], "apps": [a for a in p["apps"].split(",") if a in APPS], "expires_on": p["expires_on"]}

def allows(request: Request, app):
    """True when logins are off or this browser may open the assistant (app "any": at least one assistant)."""
    if not ON:
        return True
    h = holder(request)
    return bool(h) and (app == "any" or app in h["apps"])

def app_for(path):
    """Which assistant an API path belongs to."""
    first = path.strip("/").split("/")[0]
    if first == "fabric":
        return "fabric"
    if path == "/setup/reset":   # every page load of the live demo; it clears both assistants
        return "any"
    return "school"

def check(username, password):
    """The cookie value and its lifetime in seconds for a right username and password, else None."""
    if not ON:
        return None
    name, now = username.strip().lower(), int(time.time())
    if hmac.compare_digest(name.encode(), USER.lower().encode()) & hmac.compare_digest(password.encode(), PASSWORD.encode()):
        expires = now + DAYS * 86400
        return _cookie("admin", expires), expires - now
    with _conn() as c:
        p = c.execute("SELECT * FROM people WHERE username = ?", (name,)).fetchone()
        if not p:
            _hash(password)   # the same work as a real check, so the time taken doesn't tell whether the username exists
            return None
        if _expired(p, now) or not _password_ok(password, p["password_hash"]):
            return None
        c.execute("UPDATE people SET last_login = ? WHERE id = ?", (now, p["id"]))
    expires = now + DAYS * 86400 if p["expires_at"] is None else min(now + DAYS * 86400, p["expires_at"])
    return _cookie(f"p{p['id']}-{p['pw_ver']}", expires), expires - now

def set_cookie(request: Request, response: Response, value, max_age):
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, value, max_age=max_age, httponly=True, secure=https, samesite="lax")

# Failed tries per address in the last 5 minutes. After 10, that address has to wait.
_failed = {}
MAX_FAILS, FAIL_WINDOW = 10, 300

def _too_many(request: Request):
    who, now = request.client.host if request.client else "", time.time()
    _failed[who] = [t for t in _failed.get(who, []) if now - t < FAIL_WINDOW]
    return len(_failed[who]) >= MAX_FAILS

def _status(cookie):
    h = _holder(cookie) if ON else None
    return {"on": ON, "admin": bool(h and h["admin"]), "name": h["name"] if h else "",
            "apps": h["apps"] if h else ([] if ON else list(APPS)), "expires_on": h["expires_on"] if h else None}

class AccessLogin(BaseModel):
    username: str
    password: str

@router.get("/status")
def status(request: Request):
    """on: cards need a login. admin: the permanent account. apps: the assistants this browser may open."""
    return _status(request.cookies.get(COOKIE, ""))

@router.post("/login")
def login(req: AccessLogin, request: Request, response: Response):
    if not ON:
        return _status("")
    if _too_many(request):
        raise HTTPException(status_code=429, detail="تلاش‌های ناموفق زیاد بود. چند دقیقه دیگر دوباره امتحان کنید.")
    got = check(req.username, req.password)
    if not got:
        _failed.setdefault(request.client.host if request.client else "", []).append(time.time())
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور درست نیست، یا تاریخ دسترسی تمام شده.")
    set_cookie(request, response, *got)
    return _status(got[0])

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}

# People's accounts: only the permanent account sees and changes them.
def _admin(request: Request):
    h = holder(request) if ON else None
    if not (h and h["admin"]):
        raise HTTPException(status_code=403)

def _person(p):
    return {"id": p["id"], "name": p["name"], "username": p["username"], "apps": [a for a in p["apps"].split(",") if a in APPS],
            "expires_on": p["expires_on"], "expired": _expired(p), "created_at": p["created_at"], "last_login": p["last_login"]}

def _last_moment(expires_on):
    """«1405/08/30» → the end of that day in Tehran, as a timestamp. None stays None (no last day)."""
    if not expires_on:
        return None
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", expires_on.strip())
    try:
        d = jalali.to_gregorian(int(m[1]), int(m[2]), int(m[3]))
        assert m and 1 <= int(m[2]) <= 12 and 1 <= int(m[3]) <= 31
    except Exception:
        raise HTTPException(status_code=422, detail="تاریخ درست نیست.")
    end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=TEHRAN).timestamp()
    if end <= time.time():
        raise HTTPException(status_code=422, detail="تاریخ پایان باید امروز یا بعد از امروز باشد.")
    return int(end)

class Person(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    username: str = Field(min_length=3, max_length=30)
    password: str = Field("", max_length=100)   # empty when editing = keep the old one
    apps: list[str] = Field(min_length=1)
    expires_on: str | None = None              # Jalali «1405/08/30», or None for no last day

def _clean(req: Person, gid=None):
    username = req.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,30}", username):
        raise HTTPException(status_code=422, detail="نام کاربری فقط حروف انگلیسی، عدد، نقطه، خط تیره و زیرخط، دست‌کم ۳ حرف.")
    if username in {USER.lower(), os.getenv("SITE_USER", "").lower()}:
        raise HTTPException(status_code=422, detail="این نام کاربری را نمی‌شود داد.")
    apps = [a for a in APPS if a in req.apps]
    if not apps:
        raise HTTPException(status_code=422, detail="دست‌کم یک دستیار را انتخاب کنید.")
    if (req.password or gid is None) and len(req.password) < 6:
        raise HTTPException(status_code=422, detail="رمز عبور دست‌کم ۶ حرف باشد.")
    return username, apps, _last_moment(req.expires_on)

def _taken(c, username, gid=None):
    row = c.execute("SELECT id FROM people WHERE username = ?", (username,)).fetchone()
    if row and row["id"] != gid:
        raise HTTPException(status_code=409, detail="این نام کاربری را کس دیگری دارد.")

@router.get("/people")
def people(request: Request):
    _admin(request)
    with _conn() as c:
        rows = c.execute("SELECT * FROM people ORDER BY id DESC").fetchall()
    return [_person(p) for p in rows]

@router.post("/people")
def add_person(req: Person, request: Request):
    _admin(request)
    username, apps, expires_at = _clean(req)
    with _conn() as c:
        _taken(c, username)
        cur = c.execute("""INSERT INTO people (name, username, password_hash, apps, expires_on, expires_at, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (req.name.strip(), username, _hash(req.password), ",".join(apps), req.expires_on or None, expires_at, int(time.time())))
        p = c.execute("SELECT * FROM people WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _person(p)

@router.post("/people/{gid}")
def edit_person(gid: int, req: Person, request: Request):
    """Changes take effect at once. A new password ends the logins made with the old one."""
    _admin(request)
    username, apps, expires_at = _clean(req, gid)
    with _conn() as c:
        if not c.execute("SELECT 1 FROM people WHERE id = ?", (gid,)).fetchone():
            raise HTTPException(status_code=404)
        _taken(c, username, gid)
        c.execute("UPDATE people SET name = ?, username = ?, apps = ?, expires_on = ?, expires_at = ? WHERE id = ?",
                  (req.name.strip(), username, ",".join(apps), req.expires_on or None, expires_at, gid))
        if req.password:
            c.execute("UPDATE people SET password_hash = ?, pw_ver = pw_ver + 1 WHERE id = ?", (_hash(req.password), gid))
        p = c.execute("SELECT * FROM people WHERE id = ?", (gid,)).fetchone()
    return _person(p)

@router.post("/people/{gid}/delete")
def delete_person(gid: int, request: Request):
    """The person is shut out on their next click."""
    _admin(request)
    with _conn() as c:
        if c.execute("DELETE FROM people WHERE id = ?", (gid,)).rowcount != 1:
            raise HTTPException(status_code=404)
    return {"ok": True}
