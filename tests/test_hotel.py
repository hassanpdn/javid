"""The hotel's assistant: setup from nothing, the planted situations, prices, availability and room suggestions,
a booking from pasted text, the deposit, check-in and check-out, closing the day, roles, the website, and the model's
numbers being checked."""
import httpx, pytest
import conftest, fake_llm

def base(path):
    return conftest.BASE + "/hotel" + path

@pytest.fixture(scope="module")
def tokens():
    r = httpx.post(base("/setup"), json={"hotel": httpx.get(base("/setup/default")).json()["hotel"]}, timeout=120)
    assert r.status_code == 200, r.text
    out = {}
    for u in ("modir", "rezerv", "paziresh", "khanedari"):
        r = httpx.post(base("/login"), json={"username": u, "password": "1234"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": "Bearer " + r.json()["token"]}
    return out

def get(path, who, tokens):
    return httpx.get(base(path), headers=tokens[who], timeout=30)

def post(path, body, who, tokens):
    return httpx.post(base(path), json=body, headers=tokens[who], timeout=30)

def test_every_planted_situation_once(tokens):
    o = get("/today", "modir", tokens).json()
    assert sorted(a["type"] for a in o["alerts"]) == sorted(["vip", "deposit", "deposit", "overbooked", "clash", "ooo", "duplicate", "allotment",
                                                              "balance", "returning", "gap", "task"])
    assert sorted(x["type"] for x in get("/checks", "modir", tokens).json()) == ["cancel_after", "cash", "dirty", "discount"]

def test_price_and_rules():
    from hotel import facts
    assert facts.season("2027-03-22")[0] == "نوروز" and facts.season("2026-07-10")[0] == "تابستان"
    assert facts.weekend("2026-11-05") and not facts.weekend("2026-11-07")          # Thursday night yes, Saturday night no
    assert facts.people(2, [3, 8]) == (3, 1)                                         # the 3-year-old is free and takes no bed
    assert facts.money(1_600_000) == "1.6 میلیون تومان" and facts.money(950_000) == "950 هزار تومان"

def test_roles(tokens):
    assert get("/checks", "rezerv", tokens).status_code == 403
    assert get("/today", "khanedari", tokens).status_code == 403            # housekeeping sees only rooms and requests
    assert get("/rooms", "khanedari", tokens).status_code == 200
    assert httpx.get(base("/rooms")).status_code == 401
    room = get("/rooms", "khanedari", tokens).json()[0]
    assert post(f"/rooms/{room['id']}/status", {"status": "inspected"}, "paziresh", tokens).status_code == 403

def test_booking_from_text_to_check_out(tokens):
    text = "سلام، ۲۰ تا ۲۲ آذر یک اتاق رو به باغ برای دو بزرگسال و یک بچه‌ی ۴ ساله با صبحانه. به نام نیما کرمانی ۰۹۱۲۷۷۷۶۶۵۵"
    r = post("/read", {"text": text}, "rezerv", tokens).json()
    f = r["fields"]
    assert (f["arrive"], f["depart"], f["adults"], f["ages"], f["type"], f["board"], f["phone"]) == ("1405/09/20", "1405/09/22", 2, [4], "dbl_garden", "BB", "09127776655")
    assert f["name"] == "نیما کرمانی" and "۲۰ تا ۲۲ آذر" in r["found"]["arrive"] or "20 تا 22 آذر" in r["found"]["arrive"]
    q = post("/quote", {"arrive": f["arrive"], "depart": f["depart"], "adults": 2, "ages": [4], "board": "BB"}, "rezerv", tokens).json()
    opt = next(o for o in q["options"] if o["type"] == "dbl_garden")
    assert opt["fits"] and len(opt["nights"]) == 2 and opt["how"][-2].startswith("= جمع")
    b = post("/bookings", {"arrive": f["arrive"], "depart": f["depart"], "adults": 2, "ages": [4], "board": "BB", "type": "dbl_garden",
                           "name": f["name"], "phone": f["phone"], "source": "whatsapp"}, "rezerv", tokens).json()
    assert b["status"] == "tentative" and b["total"] == opt["total"]
    msg = get(f"/bookings/{b['id']}/message", "rezerv", tokens).json()["text"]
    assert "بیعانه" in msg and str(b["id"]) in msg
    paid = post(f"/bookings/{b['id']}/pay", {"amount": opt["deposit"], "method": "card"}, "rezerv", tokens).json()
    assert paid["status"] == "confirmed"
    assert post("/bookings", {"arrive": f["arrive"], "depart": f["depart"], "type": "dbl_garden", "name": "x y z", "phone": "09120000000",
                              "discount": 30}, "rezerv", tokens).status_code == 403      # a discount over the limit needs the manager

def test_check_in_needs_a_clean_room_and_check_out_a_paid_folio(tokens):
    vip = next(a for a in get("/today", "paziresh", tokens).json()["alerts"] if a["type"] == "vip")
    r = post(f"/bookings/{vip['booking_id']}/checkin", {"national_id": "0012345678"}, "paziresh", tokens)
    assert r.status_code == 409 and "تمیز" in r.json()["detail"]
    room = get(f"/bookings/{vip['booking_id']}", "paziresh", tokens).json()["booking"]["room_id"]
    before = next(r for r in get("/rooms", "khanedari", tokens).json() if r["id"] == room)
    if before["booking_id"]:                      # the guest before is leaving today: settle and check them out first
        left = get(f"/bookings/{before['booking_id']}", "paziresh", tokens).json()["folio"]["balance"]
        if left > 0:
            post(f"/bookings/{before['booking_id']}/pay", {"amount": left, "method": "card"}, "paziresh", tokens)
        assert post(f"/bookings/{before['booking_id']}/checkout", {}, "paziresh", tokens).json()["ok"]
    assert post(f"/rooms/{room}/status", {"status": "clean"}, "khanedari", tokens).json()["ok"]
    assert post(f"/bookings/{vip['booking_id']}/checkin", {"national_id": "0012345678", "docs": True}, "paziresh", tokens).json()["ok"]
    assert "vip" not in {a["type"] for a in get("/today", "paziresh", tokens).json()["alerts"]}
    assert any(p["id"] == vip["booking_id"] for p in get("/police", "paziresh", tokens).json())
    bal = next(a for a in get("/today", "paziresh", tokens).json()["alerts"] if a["type"] == "balance")
    r = post(f"/bookings/{bal['booking_id']}/checkout", {}, "paziresh", tokens)
    assert r.status_code == 409 and "مانده" in r.json()["detail"]
    left = get(f"/bookings/{bal['booking_id']}", "paziresh", tokens).json()["folio"]["balance"]
    assert left == 7_800_000
    post(f"/bookings/{bal['booking_id']}/pay", {"amount": left, "method": "card"}, "paziresh", tokens)
    assert post(f"/bookings/{bal['booking_id']}/checkout", {}, "paziresh", tokens).json()["ok"]

def test_rooms_are_not_sold_twice(tokens):
    clash = next(a for a in get("/today", "rezerv", tokens).json()["alerts"] if a["type"] == "clash")
    d = get(f"/bookings/{clash['booking_id']}", "rezerv", tokens).json()
    to = d["suggest"][0]["room_id"]
    assert post(f"/bookings/{clash['booking_id']}/room", {"room_id": d["booking"]["room_id"]}, "rezerv", tokens).status_code == 409
    assert post(f"/bookings/{clash['booking_id']}/room", {"room_id": to}, "rezerv", tokens).json()["ok"]
    assert "clash" not in {a["type"] for a in get("/today", "rezerv", tokens).json()["alerts"]}

def test_the_gap_closes_by_moving_the_later_stay(tokens):
    gap = next(a for a in get("/today", "rezerv", tokens).json()["alerts"] if a["type"] == "gap")
    assert post(f"/bookings/{gap['booking_id']}/room", {"room_id": gap["room_id"]}, "rezerv", tokens).json()["ok"]
    assert "gap" not in {a["type"] for a in get("/today", "rezerv", tokens).json()["alerts"]}

def test_tomorrow_gets_rooms_and_the_day_closes(tokens):
    p = get("/peak", "paziresh", tokens).json()
    n = len(p["tomorrow"])
    assert n and all(x["suggest"] for x in p["tomorrow"])
    assert len(post("/assign/tomorrow", {}, "paziresh", tokens).json()["assigned"]) == n
    assert not get("/peak", "paziresh", tokens).json()["tomorrow"]
    s = get("/close", "paziresh", tokens).json()
    r = post("/close", {"cash_counted": s["cash"]}, "paziresh", tokens).json()
    assert r["posted"] == s["rooms"] and r["diff"] == 0
    assert post("/close", {"cash_counted": 0}, "paziresh", tokens).status_code == 409

def test_cancel_follows_the_rule(tokens):
    b = [x for x in get("/bookings?when=upcoming", "rezerv", tokens).json() if x["status"] == "confirmed"][-1]
    r = post(f"/bookings/{b['id']}/cancel", {}, "rezerv", tokens).json()
    assert r["percent"] in (90, 50, 0) and r["amount"] == round(r["paid"] * r["percent"] / 100 / 10_000) * 10_000

def test_brief_numbers_are_checked(tokens):
    fake_llm.MODE = "badnum"
    r = get("/brief", "modir", tokens).json()
    fake_llm.MODE = "good"
    assert r["checked"] is False and "کار منتظر هتل است" in r["text"]

def test_the_website_takes_a_tentative_booking(tokens):
    say = lambda chat, text: httpx.post(base("/site/chat"), json={"chat": chat, "text": text}, timeout=30).json()
    r = say("", "")
    chat = r["chat"]
    r = say(chat, "۱۰ تا ۱۲ دی، دو بزرگسال")
    assert r["chips"] and any("تومان" in m for m in r["messages"])
    r = say(chat, r["chips"][0])
    r = say(chat, "سارا امینی ۰۹۱۲۵۵۵۴۴۳۳")
    assert r["booking"]
    b = get(f"/bookings/{r['booking']['id']}", "rezerv", tokens).json()["booking"]
    assert b["status"] == "tentative" and b["source"] == "site" and b["guest"] == "سارا امینی"
    assert any(x["id"] == b["id"] for x in get("/site/new?after=0", "rezerv", tokens).json()["new"])
