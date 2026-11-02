"""The dental clinic's assistant: setup from nothing, the planted situations, free slots and booking, the roles,
payments and balances, the follow-up of a plan, and the model's numbers being checked."""
import httpx, pytest
import conftest, fake_llm

def base(path):
    return conftest.BASE + "/dental" + path

@pytest.fixture(scope="module")
def tokens():
    r = httpx.post(base("/setup"), json={"clinic": httpx.get(base("/setup/default")).json()["clinic"]}, timeout=120)
    assert r.status_code == 200, r.text
    out = {}
    for u in ("doktor", "monshi"):
        r = httpx.post(base("/login"), json={"username": u, "password": "1234"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": "Bearer " + r.json()["token"]}
    return out

def get(path, who, tokens):
    return httpx.get(base(path), headers=tokens[who], timeout=30)

def post(path, body, who, tokens):
    return httpx.post(base(path), json=body, headers=tokens[who], timeout=30)

def test_every_planted_situation_once(tokens):
    o = get("/today", "doktor", tokens).json()
    assert sorted(a["type"] for a in o["alerts"]) == ["noshow", "plan", "plan", "slot", "unconfirmed"]
    assert o["alerts"][0]["type"] == "unconfirmed"
    plans = [a for a in o["alerts"] if a["type"] == "plan"]
    assert plans[0]["money"] > plans[1]["money"]          # the bigger plan first
    assert sorted(f["type"] for f in get("/checks", "doktor", tokens).json()) == ["halfway", "unpaid"]

def test_slots_and_money_rules():
    from dental import facts
    assert facts.fits_session("13:30", 30) and not facts.fits_session("13:30", 60)   # an hour does not cross the midday break
    assert facts.gaps(["10:00", "10:30", "17:00"]) == [("10:00", "11:00"), ("17:00", "17:30")]
    assert facts.money(38_000_000) == "38 میلیون تومان" and facts.money(1_500_000) == "1.5 میلیون تومان" and facts.money(400_000) == "400 هزار تومان"

def test_roles(tokens):
    assert get("/checks", "monshi", tokens).status_code == 403
    assert get("/brief", "monshi", tokens).status_code == 403
    assert httpx.get(base("/patients")).status_code == 401
    a = next(r["appt"] for r in get("/today", "monshi", tokens).json()["schedule"]["rows"] if r["appt"])
    assert post(f"/appointments/{a['id']}/status", {"status": "done"}, "monshi", tokens).status_code == 403   # only the dentist

def test_booking_the_empty_hour_from_the_waiting_list(tokens):
    slot = next(a for a in get("/today", "monshi", tokens).json()["alerts"] if a["type"] == "slot")
    free = get(f"/free?d={slot['date']}&minutes=60", "monshi", tokens).json()["times"]
    assert free == [slot["time"]]
    w = get("/waitlist", "monshi", tokens).json()[0]
    r = post("/appointments", {"patient_id": w["patient_id"], "service": "filling", "date": slot["date"], "time": slot["time"], "waitlist_id": w["id"]}, "monshi", tokens)
    assert r.status_code == 200, r.text
    again = post("/appointments", {"patient_id": w["patient_id"], "service": "checkup", "date": slot["date"], "time": slot["time"]}, "monshi", tokens)
    assert again.status_code == 409                                # the slot is taken now
    o = get("/today", "monshi", tokens).json()
    assert "slot" not in {a["type"] for a in o["alerts"]} and len(get("/waitlist", "monshi", tokens).json()) == 2

def test_confirming_clears_the_alert(tokens):
    a = next(x for x in get("/today", "monshi", tokens).json()["alerts"] if x["type"] == "unconfirmed")
    text = get(f"/appointments/{a['appt_id']}/reminder", "monshi", tokens).json()["text"]
    assert "ساعت 11:00" in text
    assert post(f"/appointments/{a['appt_id']}/status", {"status": "confirmed"}, "monshi", tokens).json()["ok"]
    assert "unconfirmed" not in {x["type"] for x in get("/today", "monshi", tokens).json()["alerts"]}

def test_payment_settles_the_balance(tokens):
    u = next(x for x in get("/checks", "doktor", tokens).json() if x["type"] == "unpaid")
    p = get(f"/patients/{u['patient_id']}", "monshi", tokens).json()
    assert p["balance"]["left"] == 5_000_000
    assert post(f"/patients/{u['patient_id']}/payments", {"amount": 5_000_000, "method": "card"}, "monshi", tokens).json()["left"] == 0
    assert "unpaid" not in {x["type"] for x in get("/checks", "doktor", tokens).json()}

def test_follow_up_message_is_checked(tokens):
    a = next(x for x in get("/today", "monshi", tokens).json()["alerts"] if x["type"] == "plan")
    fake_llm.MODE = "badnum"                                       # the model changes the numbers
    r = post(f"/plans/{a['plan_id']}/followup/draft", {}, "monshi", tokens).json()
    assert r["checked"] is False and "میلیون" not in r["text"]     # replaced by the code-written text, which has no price
    fake_llm.MODE = "good"
    assert post(f"/plans/{a['plan_id']}/contact", {"kind": "sent"}, "monshi", tokens).json()["ok"]
    assert a["plan_id"] not in {x.get("plan_id") for x in get("/today", "monshi", tokens).json()["alerts"]}

def test_new_patient_and_duplicate_phone(tokens):
    r = post("/patients", {"name": "نگار تست", "phone": "09120000001"}, "monshi", tokens)
    assert r.status_code == 200
    assert post("/patients", {"name": "کس دیگر", "phone": "۰۹۱۲۰۰۰۰۰۰۱"}, "monshi", tokens).status_code == 409
    assert post("/patients", {"name": "شماره بد", "phone": "1234567890"}, "monshi", tokens).status_code == 422
