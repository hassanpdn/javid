"""Who may open which assistant (the cards on the assistants page).

Two kinds of login, both checked here:
- the permanent account (ADMIN_USER / ADMIN_PASSWORD in the server's .env): opens every assistant and makes guest codes.
- a guest code: a username and a one-time password made by the permanent account for chosen assistants and a set time.
  The password works for the first login only; after that the same browser stays in until the code's time is up.
  Inside an assistant a guest can do everything (setup form, every role).

It is on only when ADMIN_PASSWORD is set (the live server). Locally and in tests every assistant opens straight away.
After a login the browser gets a signed cookie (like gate.py). A guest's cookie is checked against the guest's row on
every call, so ending a code shuts that browser out at once.
Guest codes live in their own small database (access.db), so resetting or rebuilding the demo data keeps them.
"""
import os, time, hmac, hashlib, secrets, sqlite3
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

APPS = ("school", "fabric")
USER = os.getenv("ADMIN_USER", "")
PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ON = bool(PASSWORD)
COOKIE, ADMIN_DAYS = "access", 30
DB_PATH = os.getenv("ACCESS_DB_PATH", "access.db")
_KEY = hashlib.sha256(f"access\0{USER}\0{PASSWORD}".encode()).digest()

router = APIRouter(prefix="/access")

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS guests (
        id INTEGER PRIMARY KEY, label TEXT NOT NULL, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
        apps TEXT NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
        used_at INTEGER, ended INTEGER NOT NULL DEFAULT 0)""")
    return c

def _hash(password):
    return hashlib.sha256(f"{password}\0".encode() + _KEY).hexdigest()

def _sign(text):
    return hmac.new(_KEY, text.encode(), hashlib.sha256).hexdigest()

def _cookie(who, expires):
    """who is "admin" or "g{id}". The cookie is who.expires.signature."""
    body = f"{who}.{expires}"
    return f"{body}.{_sign(body)}"

def holder(request: Request):
    """Whoever this browser's cookie belongs to: {"admin": bool, "apps": [...], "label", "expires"}, or None."""
    return _holder(request.cookies.get(COOKIE, ""))

def _holder(cookie):
    if not ON:   # without a password the signing key is known to anyone, so no cookie counts
        return None
    who, _, rest = cookie.partition(".")
    expires, _, sig = rest.partition(".")
    if not (expires.isdigit() and int(expires) > time.time() and hmac.compare_digest(sig, _sign(f"{who}.{expires}"))):
        return None
    if who == "admin":
        return {"admin": True, "apps": list(APPS), "label": "", "expires": int(expires)}
    if not who[1:].isdigit():
        return None
    with _conn() as c:
        g = c.execute("SELECT * FROM guests WHERE id = ?", (int(who[1:]),)).fetchone()
    if not g or g["ended"] or g["expires_at"] <= time.time():
        return None
    return {"admin": False, "apps": g["apps"].split(","), "label": g["label"], "expires": g["expires_at"]}

def allows(request: Request, app):
    """True when the door is off or this browser may open the assistant (app "any": at least one assistant)."""
    if not ON:
        return True
    h = holder(request)
    return bool(h) and (app == "any" or app in h["apps"])

def app_for(path):
    """Which assistant an API path belongs to (None: needs no assistant, like the page files or the door)."""
    first = path.strip("/").split("/")[0]
    if first == "fabric":
        return "fabric"
    if path == "/setup/reset":   # every page load of the live demo; it clears both assistants
        return "any"
    return "school"

def check(username, password):
    """The cookie value and its lifetime in seconds for a right username and password, else None.
    A guest's password is spent here: the second login with it fails."""
    if not ON:
        return None
    name, now = username.strip(), int(time.time())
    if hmac.compare_digest(name.encode(), USER.encode()) & hmac.compare_digest(password.encode(), PASSWORD.encode()):
        expires = now + ADMIN_DAYS * 86400
        return _cookie("admin", expires), expires - now
    with _conn() as c:
        g = c.execute("SELECT * FROM guests WHERE username = ?", (name.lower(),)).fetchone()
        if not g or g["ended"] or g["used_at"] or g["expires_at"] <= now:
            return None
        if not hmac.compare_digest(g["password_hash"], _hash(password.strip())):
            return None
        # only one login may spend it, even when two arrive at the same moment
        if c.execute("UPDATE guests SET used_at = ? WHERE id = ? AND used_at IS NULL", (now, g["id"])).rowcount != 1:
            return None
    return _cookie(f"g{g['id']}", g["expires_at"]), g["expires_at"] - now

def set_cookie(request: Request, response: Response, value, max_age):
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, value, max_age=max_age, httponly=True, secure=https, samesite="lax")

# Failed tries per address in the last 5 minutes. After 10, that address has to wait.
_failed = {}
MAX_FAILS, FAIL_WINDOW = 10, 300

def too_many(request: Request):
    who, now = request.client.host if request.client else "", time.time()
    _failed[who] = [t for t in _failed.get(who, []) if now - t < FAIL_WINDOW]
    return len(_failed[who]) >= MAX_FAILS

def failed(request: Request):
    _failed.setdefault(request.client.host if request.client else "", []).append(time.time())

def _status(cookie):
    h = _holder(cookie) if ON else None
    return {"on": ON, "admin": bool(h and h["admin"]), "apps": h["apps"] if h else ([] if ON else list(APPS)),
            "guest": {"label": h["label"], "expires": h["expires"]} if h and not h["admin"] else None}

class AccessLogin(BaseModel):
    username: str
    password: str

@router.get("/status")
def status(request: Request):
    """on: cards ask for a login. admin: the permanent account. apps: the assistants this browser may open."""
    return _status(request.cookies.get(COOKIE, ""))

@router.post("/login")
def login(req: AccessLogin, request: Request, response: Response):
    if not ON:
        return _status("")
    if too_many(request):
        raise HTTPException(status_code=429, detail="تلاش‌های ناموفق زیاد بود. چند دقیقه دیگر دوباره امتحان کنید.")
    got = check(req.username, req.password)
    if not got:
        failed(request)
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور درست نیست، یا این رمز قبلاً استفاده شده.")
    set_cookie(request, response, *got)
    return _status(got[0])

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}

# Guest codes: only the permanent account sees and makes them.
def _admin(request: Request):
    h = holder(request) if ON else None
    if not (h and h["admin"]):
        raise HTTPException(status_code=403)

def _guest(g):
    now = time.time()
    state = "ended" if g["ended"] else "expired" if g["expires_at"] <= now else "in" if g["used_at"] else "waiting"
    return {"id": g["id"], "label": g["label"], "username": g["username"], "apps": g["apps"].split(","),
            "created_at": g["created_at"], "expires_at": g["expires_at"], "used_at": g["used_at"], "state": state}

class NewGuest(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    apps: list[str] = Field(min_length=1)
    hours: int = Field(ge=1, le=24 * 14)

@router.get("/guests")
def guests(request: Request):
    _admin(request)
    with _conn() as c:
        rows = c.execute("SELECT * FROM guests ORDER BY id DESC LIMIT 50").fetchall()
    return [_guest(g) for g in rows]

@router.post("/guests")
def new_guest(req: NewGuest, request: Request):
    """Makes a username and a 6-digit one-time password. The password is shown only in this reply."""
    _admin(request)
    apps = [a for a in APPS if a in req.apps]
    if not apps:
        raise HTTPException(status_code=422, detail="دست‌کم یک دستیار را انتخاب کنید.")
    password, now = f"{secrets.randbelow(10**6):06d}", int(time.time())
    with _conn() as c:
        for _ in range(20):
            username = f"guest{secrets.randbelow(9000) + 1000}"
            if not c.execute("SELECT 1 FROM guests WHERE username = ?", (username,)).fetchone():
                break
        cur = c.execute("""INSERT INTO guests (label, username, password_hash, apps, created_at, expires_at)
                           VALUES (?, ?, ?, ?, ?, ?)""", (req.label.strip(), username, _hash(password), ",".join(apps), now, now + req.hours * 3600))
        g = c.execute("SELECT * FROM guests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {**_guest(g), "password": password}

@router.post("/guests/{gid}/end")
def end_guest(gid: int, request: Request):
    """Ends a code now: an unused password stops working and a guest who is in is shut out on the next click."""
    _admin(request)
    with _conn() as c:
        if c.execute("UPDATE guests SET ended = 1 WHERE id = ?", (gid,)).rowcount != 1:
            raise HTTPException(status_code=404)
    return {"ok": True}
