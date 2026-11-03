"""The eco-lodge: setup, the planted situations, the public website (search, a guest's account, a request, the
host's approval, a receipt, confirmation, a review after the stay), units switched off and closed nights, the limits
between guests and between guests and the panel, and the photos."""
import base64, io
import httpx, pytest
import conftest

def base(path):
    return conftest.BASE + "/lodge" + path

@pytest.fixture(scope="module")
def tokens():
    r = httpx.post(base("/setup"), json={"lodge": httpx.get(base("/setup/default")).json()["lodge"]}, timeout=120)
    assert r.status_code == 200, r.text
    out = {}
    for u in ("golin", "hamkar"):
        r = httpx.post(base("/login"), json={"username": u, "password": "1234"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": "Bearer " + r.json()["token"]}
    return out

def get(path, who, tokens):
    return httpx.get(base(path), headers=tokens[who], timeout=30)

def post(path, body, who, tokens):
    return httpx.post(base(path), json=body, headers=tokens[who], timeout=30)

def guest(token):
    return {"Authorization": "Bearer " + token}

def png():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 160, 90)).save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def test_every_planted_situation(tokens):
    a = get("/today", "golin", tokens).json()["alerts"]
    kinds = [x["type"] for x in a]
    for k, n in (("request", 2), ("receipt", 1), ("deposit", 1), ("message", 1), ("review", 1), ("feedback", 2)):
        assert kinds.count(k) == n, (k, kinds)

def test_the_website_is_public_and_hides_what_it_should(tokens):
    s = httpx.get(base("/public/site")).json()
    assert len(s["units"]) == 11 and s["rating"]["count"] > 0            # the unit under repair is not shown
    assert all(r["status"] == "shown" for r in s["reviews"]) and all(" " not in r["guest"] for r in s["reviews"])   # first names only
    assert httpx.get(base("/today")).status_code == 401                  # the panel is not public
    assert httpx.get(conftest.BASE + "/eco").status_code == 200

def test_a_guest_books_pays_and_the_host_confirms(tokens):
    r = httpx.post(base("/public/register"), json={"name": "نسیم آزاد", "phone": "09125550101", "password": "safe-pass"})
    assert r.status_code == 200
    g = guest(r.json()["token"])
    found = httpx.post(base("/public/search"), json={"arrive": "1405/09/10", "depart": "1405/09/12", "people": 2}).json()["units"]
    u = found[0]
    assert u["quote"]["total"] == min(x["quote"]["total"] for x in found)
    b = httpx.post(base("/public/bookings"), json={"unit_id": u["id"], "arrive": "1405/09/10", "depart": "1405/09/12", "people": 2}, headers=g).json()
    assert b["status"] == "requested" and not b["can_pay"]
    again = httpx.post(base("/public/search"), json={"arrive": "1405/09/10", "depart": "1405/09/12", "people": 2, "unit_id": u["id"]}).json()
    assert not again["free"]                                             # a request holds the nights
    assert post(f"/bookings/{b['id']}/approve", {}, "hamkar", tokens).json()["ok"]
    mine = httpx.get(base("/public/my"), headers=g).json()["bookings"][0]
    assert mine["can_pay"] and mine["card"]
    assert httpx.post(base(f"/public/bookings/{b['id']}/receipt"), json={"data": png()}, headers=g).json()["ok"]
    d = get(f"/bookings/{b['id']}", "golin", tokens).json()["booking"]
    assert d["status"] == "paid" and d["receipt_data"].startswith("data:image/")
    assert post(f"/bookings/{b['id']}/confirm", {}, "golin", tokens).json()["ok"]
    assert httpx.get(base("/public/my"), headers=g).json()["bookings"][0]["status"] == "confirmed"
    assert httpx.post(base(f"/public/bookings/{b['id']}/review"), json={"stars": 5, "text": "هنوز نرفته‌ام ولی عالی بود"}, headers=g).status_code == 409

def test_a_guest_sees_only_their_own(tokens):
    r = httpx.post(base("/public/login"), json={"phone": "09120000000", "password": "1234"}).json()
    demo = guest(r["token"])
    mine = httpx.get(base("/public/my"), headers=demo).json()["bookings"]
    other = httpx.get(base("/bookings?when=coming"), headers=tokens["golin"]).json()
    theirs = next(b for b in other if b["phone"] != "09120000000")
    assert httpx.post(base(f"/public/bookings/{theirs['id']}/cancel"), headers=demo).status_code == 404
    assert httpx.get(base("/today"), headers=demo).status_code == 401      # a guest's token never opens the panel
    done = next(b for b in mine if b["can_review"])                        # the stay that just ended
    assert httpx.post(base(f"/public/bookings/{done['id']}/review"), json={"stars": 4, "text": "سکوت شب و نان تازه‌ی صبح فراموش‌نشدنی بود"}, headers=demo).json()["ok"]
    assert httpx.post(base(f"/public/bookings/{done['id']}/review"), json={"stars": 4, "text": "دوباره همان نظر را می‌نویسم"}, headers=demo).status_code == 409
    rv = next(x for x in get("/reviews", "golin", tokens).json()["reviews"] if x["booking_id"] == done["id"])
    assert rv["status"] == "waiting"
    assert post(f"/reviews/{rv['id']}", {"status": "shown", "reply": "ممنون از شما"}, "golin", tokens).json()["ok"]
    assert any(x["text"].startswith("سکوت شب") for x in httpx.get(base("/public/site")).json()["reviews"])

def test_wrong_password_and_too_many_tries(tokens):
    assert httpx.post(base("/public/login"), json={"phone": "09120000000", "password": "nope"}).status_code == 401
    codes = [httpx.post(base("/public/login"), json={"phone": "09120000000", "password": "nope"}).status_code for _ in range(12)]
    assert 429 in codes

def test_switching_a_unit_off_and_closing_nights(tokens):
    u = next(x for x in get("/units", "golin", tokens).json() if x["active"])
    assert post(f"/units/{u['id']}/active", {"active": False}, "golin", tokens).json()["ok"]
    assert all(x["id"] != u["id"] for x in httpx.get(base("/public/site")).json()["units"])
    assert httpx.get(base(f"/public/units/{u['id']}")).status_code == 404
    post(f"/units/{u['id']}/active", {"active": True}, "golin", tokens)
    assert post(f"/units/{u['id']}/active", {"active": False}, "hamkar", tokens).status_code == 403   # only the host
    cal = httpx.get(base(f"/public/units/{u['id']}")).json()["calendar"]
    night = next(n for n in cal[20:] if n["free"])
    nxt = cal[cal.index(night) + 1]["j"]
    assert post(f"/units/{u['id']}/blocks", {"start": night["j"], "end": nxt, "note": "مهمان خانواده"}, "golin", tokens).json()["ok"]
    cal = httpx.get(base(f"/public/units/{u['id']}")).json()["calendar"]
    assert not next(n for n in cal if n["j"] == night["j"])["free"]

def test_photos_are_resized_and_served(tokens):
    u = get("/units", "golin", tokens).json()[0]
    p = post(f"/units/{u['id']}/photos", {"data": png()}, "golin", tokens).json()
    assert httpx.get(conftest.BASE + p["url"]).status_code == 200
    assert post(f"/units/{u['id']}/photos", {"data": "data:text/plain;base64,aGVsbG8="}, "golin", tokens).status_code == 422
    assert httpx.get(base("/public/photo/receipt-demo.png")).status_code == 404     # receipts are never public

def test_price_rules():
    from lodge import facts
    u = {"price": 2_000_000, "weekend_price": 3_000_000, "beds": 2, "capacity": 3}
    assert facts.unit_price(u, "2026-11-05") == 3_000_000 and facts.unit_price(u, "2026-11-07") == 2_000_000   # Thursday night, Saturday night
