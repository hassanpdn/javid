"""The hotel's public website (hotel/public.py): open without the panel's login, prices by code, a guest's own account,
a tentative booking the desk sees, the deposit receipt checked by a person, guests kept apart, cancelling by the
hotel's rule, and accounts and bookings still to come surviving a rebuild of the demo."""
import base64, io
import httpx, pytest
import conftest

def base(path):
    return conftest.BASE + "/hotel" + path

@pytest.fixture(scope="module")
def desk():
    r = httpx.post(base("/setup"), json={"hotel": httpx.get(base("/setup/default")).json()["hotel"]}, timeout=120)
    assert r.status_code == 200, r.text
    r = httpx.post(base("/login"), json={"username": "rezerv", "password": "1234"})
    return {"Authorization": "Bearer " + r.json()["token"]}

def png():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (40, 30), (40, 90, 140)).save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def account(name, phone):
    r = httpx.post(base("/public/register"), json={"name": name, "phone": phone, "password": "safe-pass"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}

STAY = {"arrive": "1405/08/25", "depart": "1405/08/27", "adults": 2, "ages": [4]}

def test_the_site_and_search_are_public(desk):
    s = httpx.get(base("/public/site")).json()
    assert s["name"] and len(s["types"]) == 5 and "card" not in s
    found = httpx.post(base("/public/search"), json=STAY).json()
    garden = next(o for o in found["options"] if o["type"] == "dbl_garden")
    assert garden["free"] and garden["fits"] and "رایگان" in garden["how"][-1]          # the 4-year-old is free
    desk_price = next(o for o in httpx.post(base("/quote"), json=STAY, headers=desk).json()["options"] if o["type"] == "dbl_garden")
    assert garden["total"] == desk_price["total"]                            # the same price the desk quotes
    assert httpx.post(base("/public/search"), json={**STAY, "arrive": "1405/07/01", "depart": "1405/07/03"}).status_code == 422   # past
    assert httpx.get(base("/public/my")).status_code == 401

def test_book_send_receipt_and_the_desk_confirms(desk):
    g = account("نیلوفر صالحی", "09127770101")
    b = httpx.post(base("/public/bookings"), json={**STAY, "type": "dbl_sea", "eta": "18:00", "requests": "طبقه‌ی بالا"}, headers=g).json()
    assert b["status"] == "tentative" and b["can_pay"] and b["card"] and b["deposit_text"]
    seen = httpx.get(base(f"/bookings/{b['id']}"), headers=desk).json()
    assert seen["booking"]["source"] == "site" and seen["booking"]["requests"] == "طبقه‌ی بالا"
    assert httpx.get(base("/site/new"), headers=desk).json()["waiting"] >= 1
    assert httpx.post(base(f"/public/bookings/{b['id']}/receipt"), json={"data": png()}, headers=g).json()["ok"]
    assert httpx.post(base(f"/public/bookings/{b['id']}/receipt"), json={"data": png()}, headers=g).status_code == 409   # one at a time
    alerts = httpx.get(base("/today"), headers=desk).json()["alerts"]
    assert [a["booking_id"] for a in alerts if a["type"] == "receipt"] == [b["id"]]
    d = httpx.get(base(f"/bookings/{b['id']}"), headers=desk).json()
    assert d["receipt"]["status"] == "waiting" and d["receipt"]["data"].startswith("data:image/")
    assert httpx.post(base(f"/bookings/{b['id']}/receipt"), json={"ok": True}, headers=desk).json()["status"] == "confirmed"
    mine = httpx.get(base("/public/my"), headers=g).json()["bookings"][0]
    assert mine["status"] == "confirmed" and mine["paid_text"] == d["receipt"]["deposit_text"] and not mine["can_pay"]

def test_guests_are_kept_apart(desk):
    a, b = account("آرین مقدم", "09127770202"), account("ژاله نیک‌نام", "09127770303")
    x = httpx.post(base("/public/bookings"), json={**STAY, "type": "triple", "ages": []}, headers=a).json()
    assert httpx.post(base(f"/public/bookings/{x['id']}/cancel"), headers=b).status_code == 404
    assert httpx.get(base("/public/my"), headers=b).json()["bookings"] == []
    assert httpx.get(base("/today"), headers=a).status_code == 401           # a guest's token never opens the panel
    assert httpx.post(base("/public/register"), json={"name": "کسی دیگر", "phone": "09127770202", "password": "another"}).status_code == 409
    assert httpx.post(base("/public/login"), json={"phone": "09127770202", "password": "wrong-one"}).status_code == 401

def test_cancel_by_the_rule(desk):
    g = account("مهرداد افشار", "09127770404")
    x = httpx.post(base("/public/bookings"), json={**STAY, "type": "dbl_garden"}, headers=g).json()
    r = httpx.post(base(f"/public/bookings/{x['id']}/cancel"), headers=g).json()
    assert r["percent"] == 90 and r["amount"] == 0                           # nothing was paid yet
    assert httpx.get(base("/public/my"), headers=g).json()["bookings"][0]["status"] == "cancelled"

def test_accounts_and_coming_bookings_survive_a_rebuild(desk):
    # an earlier test's guest (five new accounts a minute from one address is the limit)
    r = httpx.post(base("/public/login"), json={"phone": "09127770101", "password": "safe-pass"})
    g = {"Authorization": "Bearer " + r.json()["token"]}
    x = httpx.post(base("/public/bookings"), json={**STAY, "type": "suite"}, headers=g).json()
    assert httpx.post(base("/setup"), json={"hotel": httpx.get(base("/setup/default")).json()["hotel"]}, timeout=120).status_code == 200
    mine = httpx.get(base("/public/my"), headers=g).json()["bookings"]           # the same token still works
    assert sorted((m["type"], m["stay_text"], m["status"]) for m in mine) == [("dbl_sea", x["stay_text"], "confirmed"), ("suite", x["stay_text"], "tentative")]
    assert next(m for m in mine if m["type"] == "dbl_sea")["paid_text"]       # with its deposit
    for m in mine:     # leave nothing for the planted situations of the next rebuild (two trips on one number look like a duplicate)
        assert httpx.post(base(f"/public/bookings/{m['id']}/cancel"), headers=g).status_code == 200
