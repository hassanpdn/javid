"""The site's front door: one username and password for the whole site, before the demo's own logins.

It is on only when SITE_PASSWORD is set in .env (the live server). Locally and in tests it is off.
After a correct login the browser gets a signed cookie, so the door stays open for 30 days.
The cookie holds only an expiry time and a signature; the signature's key is made from the username and
password, so nobody can make a valid cookie without knowing the password, and changing the password
closes the door for every browser at once.
"""
import os, time, hmac, hashlib
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

USER = os.getenv("SITE_USER", "")
PASSWORD = os.getenv("SITE_PASSWORD", "")
ON = bool(PASSWORD)
COOKIE, DAYS = "site", 30
_KEY = hashlib.sha256(f"{USER}\0{PASSWORD}".encode()).digest()

router = APIRouter(prefix="/gate")

def _sign(expires):
    return hmac.new(_KEY, str(expires).encode(), hashlib.sha256).hexdigest()

def allowed(request: Request):
    """True when the door is off, or the browser has a valid cookie that has not expired."""
    if not ON:
        return True
    expires, _, sig = request.cookies.get(COOKIE, "").partition(".")
    return expires.isdigit() and int(expires) > time.time() and hmac.compare_digest(sig, _sign(expires))

# Failed tries per address in the last 5 minutes. After 10, that address has to wait.
_failed = {}
MAX_FAILS, FAIL_WINDOW = 10, 300

class GateLogin(BaseModel):
    username: str
    password: str

@router.get("/status")
def status(request: Request):
    """on: the door exists. ok: this browser may come in. reset_on_load: start every visit on the setup form."""
    return {"on": ON, "ok": allowed(request), "reset_on_load": os.getenv("RESET_ON_LOAD") == "1"}

@router.post("/login")
def login(req: GateLogin, request: Request, response: Response):
    if not ON:
        return {"ok": True}
    who, now = request.client.host if request.client else "", time.time()
    recent = [t for t in _failed.get(who, []) if now - t < FAIL_WINDOW]
    if len(recent) >= MAX_FAILS:
        raise HTTPException(status_code=429, detail="تلاش‌های ناموفق زیاد بود. چند دقیقه دیگر دوباره امتحان کنید.")
    # compare_digest takes the same time whatever the input, so timing gives nothing away
    good = hmac.compare_digest(req.username.strip().encode(), USER.encode()) & hmac.compare_digest(req.password.encode(), PASSWORD.encode())
    if not good:
        _failed[who] = recent + [now]
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور درست نیست")
    _failed.pop(who, None)
    expires = int(now) + DAYS * 86400
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, f"{expires}.{_sign(expires)}", max_age=DAYS * 86400,
                        httponly=True, secure=https, samesite="lax")
    return {"ok": True}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}
