"""Rule: numbers are computed by code; the model only writes text. Model output with numbers is checked."""
import fake_llm, pytest
from conftest import Client, db, add_letter, run_agent

def test_parent_answer_with_wrong_numbers_uses_code_answer():
    fake_llm.MODE = "badnum"
    r = Client("vali").post("/parent/ask", {"question": "این ماه چند روز غیبت داشته؟"}).json()
    assert "97" not in r["answer"] and "۹۷" not in r["answer"] and r["checked"]

def test_stats_reply_with_wrong_numbers_uses_template():
    fake_llm.MODE = "badnum"
    add_letter("درخواست آمار غیبت مهر برای آزمون", "لطفا آمار غیبت مهر ماه را به تفکیک پایه ارسال کنید.")
    run_agent()
    with db() as c:
        l = c.execute("SELECT status, reply FROM letters WHERE subject = 'درخواست آمار غیبت مهر برای آزمون'").fetchone()
    assert l["status"] == "awaiting_approval" and "۹۷" not in l["reply"]

def test_good_stats_reply_is_kept():
    add_letter("درخواست آمار غیبت مهر آزمون دوم", "لطفا آمار غیبت مهر ماه را به تفکیک پایه ارسال کنید.")
    run_agent()
    with db() as c:
        reply = c.execute("SELECT reply FROM letters WHERE subject = 'درخواست آمار غیبت مهر آزمون دوم'").fetchone()[0]
    assert "پاسخ مدل" in reply   # the fake model repeats the data, so its draft passes the check

def late_alert():
    return next(a for a in Client("modir").get("/manager/overview").json()["alerts"] if a["type"] == "teacher_late")

def test_warning_draft_with_wrong_dates_is_flagged():
    fake_llm.MODE = "badnum"
    r = Client("modir").post("/manager/warnings/draft", {"teacher_id": late_alert()["teacher_id"]}).json()
    assert r["verified"] is False and r["missing"]
    assert all("آبان" in m or "مهر" in m for m in r["missing"])   # real month names, not a hardcoded one

def test_correct_warning_draft_is_verified():
    r = Client("modir").post("/manager/warnings/draft", {"teacher_id": late_alert()["teacher_id"]}).json()
    assert r["verified"] is True, r["missing"]

def test_briefing_numbers_are_checked():
    add_letter("بخشنامه آزمون عدد خلاصه", "این بخشنامه فقط برای اطلاع است.")
    run_agent()                      # clears the cached summary
    fake_llm.MODE = "badnum"
    text = Client("modir").get("/manager/briefing").json()["text"]
    assert "97" not in text and "۹۷" not in text

def test_classifier_cannot_close_a_letter_as_acknowledged():
    fake_llm.MODE = "evil"   # always answers "ack"
    add_letter("قرارداد خرید آزمون", "پیشنهاد قرارداد خرید ۵۰۰ میلیونی. لطفا تأیید کنید.")
    run_agent()
    with db() as c:
        assert c.execute("SELECT category FROM letters WHERE subject = 'قرارداد خرید آزمون'").fetchone()[0] != "ack"

def test_invalid_recipients_from_model_are_dropped():
    fake_llm.MODE = "evil"   # suggests user:999, a SQL-looking string and individual parents
    keys = Client("edari").post("/staff/letters/1/suggest").json()["keys"]
    assert "user:999" not in keys and "DROP TABLE" not in keys
    assert all(k.startswith(("group:", "user:")) for k in keys)

def test_unknown_label_from_model_means_unclear():
    fake_llm.MODE = "evil"
    assert Client("vali").post("/parent/ask", {"question": "سلام خوبید امروز هوا چطوره"}).json()["intent"] == "unclear"

def test_think_tags_are_removed():
    assert "<think>" not in Client("vali").post("/parent/ask", {"question": "وضعیت ریاضیش چطوره؟"}).json()["answer"]

def test_briefing_model_down_gives_503():
    add_letter("بخشنامه آزمون برای پاک شدن خلاصه", "این بخشنامه فقط برای اطلاع است.")
    run_agent()                      # handling a letter clears the cached morning summary
    fake_llm.MODE = "down"
    assert Client("modir").get("/manager/briefing").status_code == 503

def test_insight_model_down_gives_503():
    Client("moshaver").post("/counselor/students/2/notes", {"note": "یادداشت آزمون قطعی"})   # new note: not cached
    fake_llm.MODE = "down"
    assert Client("moshaver").get("/counselor/students/2/insight").status_code == 503

def test_parent_report_falls_back_when_model_down():
    fake_llm.MODE = "down"
    r = Client("vali").get("/parent/report")
    assert r.status_code == 200 and r.json()["text"]

def test_agent_puts_letter_back_when_model_down():
    fake_llm.MODE = "down"
    add_letter("نامه آزمون قطعی", "متن نامه برای آزمون قطعی مدل است.")
    assert Client("edari").post("/staff/agent/next").status_code == 503
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM letters WHERE status = 'processing'").fetchone()[0] == 0
    fake_llm.MODE = "good"
    run_agent()
