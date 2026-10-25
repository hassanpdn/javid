from fastapi import Depends, Header, HTTPException
import db, school

def get_token(authorization: str = Header(None)):
    return (authorization or "").removeprefix("Bearer ").strip()

def current_user(token: str = Depends(get_token)):
    user = db.user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="لطفا دوباره وارد شوید")
    if not school.role_enabled(user["role"]):   # the role was switched off: whoever is logged in with it is out
        raise HTTPException(status_code=401, detail="این نقش در این نسخه فعال نیست")
    return user

def require_role(*roles):
    # Usage: user = Depends(require_role("manager"))
    def check(user: dict = Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="به این بخش دسترسی ندارید")
        return user
    return check
