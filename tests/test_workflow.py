"""State rules: every action only works in the right state, and nothing is sent twice."""
from conftest import Client, db, add_letter, run_agent

def parent_notifications():
    with db() as c:
        return c.execute("SELECT COUNT(*) FROM notifications WHERE user_id = 6 AND kind = 'suggestion'").fetchone()[0]

def test_counselor_message_is_sent_once():
    m = Client("moshaver")
    d = m.post("/counselor/students/1/suggest").json()
    before = parent_notifications()
    assert m.post(f"/counselor/suggestions/{d['id']}/approve", {"for_parent": "پیام یک"}).status_code == 200
    assert m.post(f"/counselor/suggestions/{d['id']}/approve", {"for_parent": "پیام دو"}).status_code == 409
    assert parent_notifications() - before == 1

def test_dismissed_message_cannot_be_sent():
    m = Client("moshaver")
    d = m.post("/counselor/students/1/suggest").json()
    m.post(f"/counselor/suggestions/{d['id']}/dismiss")
    assert m.post(f"/counselor/suggestions/{d['id']}/approve", {"for_parent": "x"}).status_code == 409

def test_closed_letter_cannot_be_approved_again():
    with db() as c:
        lid = c.execute("SELECT id FROM letters WHERE status = 'done' LIMIT 1").fetchone()
    if not lid:
        add_letter("بخشنامه آزمون اعلام وصول", "اعلام وصول این بخشنامه الزامی است.")
        run_agent()
        with db() as c:
            lid = c.execute("SELECT id FROM letters WHERE status = 'done' LIMIT 1").fetchone()
    with db() as c:
        before = c.execute("SELECT COUNT(*) FROM agent_log WHERE letter_id = ?", (lid[0],)).fetchone()[0]
    assert Client("edari").post(f"/staff/letters/{lid[0]}/approve", {"reply": "x"}).status_code == 409
    assert Client("edari").post(f"/staff/letters/{lid[0]}/complete").status_code == 409
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM agent_log WHERE letter_id = ?", (lid[0],)).fetchone()[0] == before

def test_warning_issue_ack_and_no_second_warning():
    alert = next(a for a in Client("modir").get("/manager/overview").json()["alerts"] if a["type"] == "teacher_late")
    tid = alert["teacher_id"]
    assert Client("modir").post("/manager/warnings", {"teacher_id": tid, "text": "تذکر آزمون"}).status_code == 200
    assert Client("modir").post("/manager/warnings", {"teacher_id": tid, "text": "تذکر آزمون"}).status_code == 409
    with db() as c:
        n = c.execute("""SELECT n.id FROM notifications n JOIN users u ON u.id = n.user_id
                         WHERE u.role = 'teacher' AND u.ref_id = ? AND n.ref_type = 'warning'""", (tid,)).fetchall()
    assert len(n) == 1
    teacher = "karimi" if tid == 3 else f"teacher{tid}"
    assert Client(teacher).post(f"/notifications/{n[0][0]}/ack").status_code == 200
    assert any("رؤیت کرد" in x["title"] for x in Client("modir").get("/notifications").json()["items"])

def test_late_alert_uses_last_30_days():
    titles = [a["title"] for a in Client("modir").get("/manager/overview").json()["alerts"] if a["type"] == "teacher_late"]
    assert titles and all("۳۰ روز اخیر" in t for t in titles)
