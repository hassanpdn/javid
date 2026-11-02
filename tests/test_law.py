"""The law office's assistant: setup from nothing, the planted situations, deadlines with Fridays and holidays,
reading a notice and matching its case, marking work done, roles, and the model's dates being checked."""
from datetime import date, timedelta
import httpx, pytest
import conftest, fake_llm

def base(path):
    return conftest.BASE + "/law" + path

@pytest.fixture(scope="module")
def tokens():
    r = httpx.post(base("/setup"), json={"office": httpx.get(base("/setup/default")).json()["office"]}, timeout=120)
    assert r.status_code == 200, r.text
    out = {}
    for u in ("vakil", "hamkar", "monshi"):
        r = httpx.post(base("/login"), json={"username": u, "password": "1234"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": "Bearer " + r.json()["token"]}
    return out

def get(path, who, tokens):
    return httpx.get(base(path), headers=tokens[who], timeout=30)

def post(path, body, who, tokens):
    return httpx.post(base(path), json=body, headers=tokens[who], timeout=30)

def test_every_planted_situation_once(tokens):
    o = get("/overview", "vakil", tokens).json()
    assert sorted(a["type"] for a in o["alerts"]) == sorted(["overdue", "deadline", "deadline", "hearing", "idle", "report"])
    assert sorted(f["type"] for f in get("/checks", "vakil", tokens).json()) == ["entry", "late", "missed"]
    assert o["alerts"][0]["type"] == "overdue"   # the most urgent first

def test_deadline_rules():
    from law import facts
    off = facts.solar_holidays(1405)
    # 20 days after a Saturday is a Friday: the last day moves to Saturday
    sat = date(2026, 10, 24)
    assert sat.weekday() == 5
    last, why = facts.deadline(sat.isoformat(), 20, set())
    assert last == (sat + timedelta(days=21)).isoformat() and "جمعه" in why
    # a last day on 22 Bahman (an official holiday) moves on; 22 Bahman 1405 is 11 Feb 2027
    served = (date(2027, 2, 11) - timedelta(days=10)).isoformat()
    last, why = facts.deadline(served, 10, off)
    assert last > "2027-02-11" and "تعطیل رسمی" in why

def test_roles(tokens):
    assert get("/checks", "hamkar", tokens).status_code == 403
    assert get("/overview", "monshi", tokens).status_code == 403
    assert post("/settings", {"days": {"judgment": 30}}, "hamkar", tokens).status_code == 403
    n = get("/deadlines", "monshi", tokens).json()["week"][0]
    assert post(f"/notices/{n['id']}/done", {}, "monshi", tokens).status_code == 403   # only lawyers mark work done
    assert httpx.get(base("/cases")).status_code == 401

def test_associate_sees_own_work(tokens):
    mine = get("/today", "hamkar", tokens).json()["alerts"]
    lawyer = {a["detail"].split("مسئول: ")[-1] for a in mine if "مسئول: " in a["detail"]}
    assert lawyer and all("نیلوفر احمدی" in x for x in lawyer)

def test_reading_a_notice_matches_its_case_and_sets_the_deadline(tokens):
    text = get("/sample", "monshi", tokens).json()["text"]
    r = post("/read", {"text": text}, "monshi", tokens).json()
    f = r["fields"]
    assert f["kind"] == "judgment" and f["number"] and f["branch"] and f["served"] and r["cases"] and r["cases"][0]["why"] == "شماره‌ی پرونده یکی است"
    assert f["number"] in r["found"]["number"]
    n = post("/notices", {"case_id": r["cases"][0]["id"], "kind": f["kind"], "served": f["served"], "text": text}, "monshi", tokens).json()
    assert n["left"] >= 20 and n["how"][1] == "مهلت: 20 روز" and n["how"][-1].startswith("= روز آخر")

def test_nothing_is_made_up(tokens):
    fake_llm.MODE = "evil"
    f = post("/read", {"text": "ابلاغیه‌ای رسیده است، لطفاً بررسی شود."}, "monshi", tokens).json()["fields"]
    assert all(v is None for v in f.values())

def test_marking_done_clears_the_alert(tokens):
    a = next(x for x in get("/overview", "vakil", tokens).json()["alerts"] if x["type"] == "overdue")
    r = post(f"/notices/{a['notice_id']}/done", {"note": "لایحه‌ی رفع نقص تقدیم شد"}, "hamkar", tokens).json()
    assert r["late"]
    assert "overdue" not in {x["type"] for x in get("/overview", "vakil", tokens).json()["alerts"]}
    assert "late" in [f["type"] for f in get("/checks", "vakil", tokens).json() if f["case_id"] == a["case_id"]]

def test_hearing_needs_its_time(tokens):
    cid = get("/cases", "monshi", tokens).json()[0]["id"]
    assert post("/notices", {"case_id": cid, "kind": "hearing", "served": "1405/08/01"}, "monshi", tokens).status_code == 422
    assert post("/notices", {"case_id": cid, "kind": "judgment", "served": "1499/13/40"}, "monshi", tokens).status_code == 422

def test_client_report_dates_are_checked(tokens):
    a = next(x for x in get("/overview", "vakil", tokens).json()["alerts"] if x["type"] == "report")
    fake_llm.MODE = "badnum"
    r = post(f"/cases/{a['case_id']}/report/draft", {}, "vakil", tokens).json()
    assert r["checked"] is False and "97" not in r["text"] and "گرامی" in r["text"]
    assert post(f"/cases/{a['case_id']}/report", {"text": r["text"]}, "vakil", tokens).status_code == 200
    assert "report" not in {x["type"] for x in get("/overview", "vakil", tokens).json()["alerts"] if x["case_id"] == a["case_id"]}

def test_settings_change_new_deadlines(tokens):
    assert post("/settings", {"days": {"judgment": 30}, "holidays": ["1405/09/10"]}, "vakil", tokens).json()["days"]["judgment"] == 30
    assert post("/settings", {"days": {"judgment": 0}}, "vakil", tokens).status_code == 422
    post("/settings", {"days": {"judgment": 20}, "holidays": []}, "vakil", tokens)
