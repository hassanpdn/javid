from fastapi import APIRouter, Depends, HTTPException
import db
from auth import current_user

router = APIRouter(prefix="/notifications")

def own(c, nid, user):
    n = c.execute("SELECT * FROM notifications WHERE id = ? AND user_id = ?", (nid, user["id"])).fetchone()
    if not n:
        raise HTTPException(status_code=404, detail="اعلان پیدا نشد")
    return n

@router.get("")
def list_notifications(user: dict = Depends(current_user)):
    with db.conn() as c:
        rows = c.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 30", (user["id"],)).fetchall()
        unread = c.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL", (user["id"],)).fetchone()[0]
    return {"unread": unread, "items": [dict(r) for r in rows]}

@router.post("/{nid}/read")
def mark_read(nid: int, user: dict = Depends(current_user)):
    with db.conn() as c:
        own(c, nid, user)
        c.execute("UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE id = ?", (db.stamp(), nid))
    return {"ok": True}

@router.post("/{nid}/ack")
def acknowledge(nid: int, user: dict = Depends(current_user)):
    when = db.stamp()
    with db.conn() as c:
        n = own(c, nid, user)
        if not n["needs_ack"] or n["ack_at"]:
            return {"ok": True}
        c.execute("UPDATE notifications SET ack_at = ?, read_at = COALESCE(read_at, ?) WHERE id = ?", (when, when, nid))
        if n["ref_type"] == "warning":
            c.execute("UPDATE warnings SET acknowledged_at = ? WHERE id = ?", (when, n["ref_id"]))
    if n["ref_type"] == "warning":
        db.notify(db.users_with("manager"), "info", f"{user['full_name']} تذکر کتبی را دید", f"زمان دیدن: {when}")
    if n["ref_type"] == "letter":
        with db.conn() as c:
            c.execute("INSERT INTO agent_log (letter_id, action, reason, created_at) VALUES (?, ?, ?, ?)",
                      (n["ref_id"], f"{user['full_name']} نامه‌ی فرستاده‌شده را دید", "دیدن نامه ثبت شد.", when))
    return {"ok": True}

@router.post("/read-all")
def mark_all_read(user: dict = Depends(current_user)):
    with db.conn() as c:
        c.execute("UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL", (db.stamp(), user["id"]))
    return {"ok": True}
