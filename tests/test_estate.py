"""The real estate agency's assistant: setup from nothing, the planted situations, reading pasted text, matching,
visits, deals and their commission check, the website taking a request, roles, and the model's numbers being checked."""
import httpx, pytest
import conftest, fake_llm

def base(path):
    return conftest.BASE + "/estate" + path

@pytest.fixture(scope="module")
def tokens():
    r = httpx.post(base("/setup"), json={"agency": httpx.get(base("/setup/default")).json()["agency"]}, timeout=120)
    assert r.status_code == 200, r.text
    out = {}
    for u in ("modir", "moshaver1", "moshaver2"):
        r = httpx.post(base("/login"), json={"username": u, "password": "1234"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": "Bearer " + r.json()["token"]}
    return out

def get(path, who, tokens):
    return httpx.get(base(path), headers=tokens[who], timeout=30)

def post(path, body, who, tokens):
    return httpx.post(base(path), json=body, headers=tokens[who], timeout=30)

def test_owner_sees_every_planted_situation(tokens):
    o = get("/overview", "modir", tokens).json()
    kinds = [a["type"] for a in o["alerts"]]
    assert sorted(kinds) == sorted(["missed", "visit", "stale", "report", "price", "duplicate"])   # each exactly once, nothing extra
    found = {f["type"] for f in get("/checks", "modir", tokens).json()}
    assert found == {"outside", "fee", "duplicate"}
    outside = next(f for f in get("/checks", "modir", tokens).json() if f["type"] == "outside")
    assert "3 بازدید" in outside["title"] and len(outside["how"]) >= 3

def test_agents_do_not_see_checks_or_settings(tokens):
    assert get("/checks", "moshaver1", tokens).status_code == 403
    assert get("/overview", "moshaver1", tokens).status_code == 403
    assert post("/settings", {"rate": 4, "sale_fee": 1, "rent_fee": 50}, "moshaver1", tokens).status_code == 403
    assert httpx.get(base("/listings")).status_code == 401
    school = httpx.post(conftest.BASE + "/login", json={"username": "modir", "password": "1234"}).json()["token"]
    assert httpx.get(base("/listings"), headers={"Authorization": "Bearer " + school}).status_code == 401   # a school token is not an agency token

def test_price_check_flags_the_overpriced_unit_with_its_sum(tokens):
    alert = next(a for a in get("/overview", "modir", tokens).json()["alerts"] if a["type"] == "price")
    d = get(f"/listings/{alert['listing_id']}", "modir", tokens).json()
    p = d["price"]
    assert p["verdict"] == "high" and p["diff"] >= 20 and p["n"] >= 3
    assert p["how"][-1].startswith("= این فایل") and p["low"] <= p["mid"] <= p["high"]

def test_reading_a_pasted_listing_finds_its_duplicate(tokens):
    text = "رهن و اجاره پونک خیابان سمنگان ۹۲ متر دو خوابه طبقه سوم، رهن ۵۰۰ میلیون اجاره ۱۳ میلیون. مالک: فرشته یزدانی ۰۹۱۲۳۳۷۰۴۱۸"
    r = post("/read", {"kind": "listing", "text": text}, "moshaver1", tokens).json()
    f = r["fields"]
    assert (f["kind"], f["hood"], f["area"], f["rooms"], f["floor"]) == ("rent", "پونک", 92, 2, 3)
    assert f["deposit"] == 500_000_000 and f["rent"] == 13_000_000 and f["owner_phone"] == "09123370418"
    assert "500 میلیون" in r["found"]["deposit"]
    assert r["duplicates"] and r["duplicates"][0]["why"] == "شماره‌ی مالک یکی است"

def test_nothing_is_made_up_from_the_text(tokens):
    fake_llm.MODE = "evil"
    r = post("/read", {"kind": "request", "text": "دنبال اجاره در شهران هستم، دو خواب"}, "moshaver1", tokens).json()
    f = r["fields"]
    assert f["hoods"] == ["شهران"] and f["rooms"] == 2 and f["deposit"] is None and f["phone"] is None and f["name"] is None

def test_a_call_clears_the_missed_match(tokens):
    m = next(a for a in get("/overview", "modir", tokens).json()["alerts"] if a["type"] == "missed")
    assert post("/calls", {"listing_id": m["listing_id"], "request_id": m["request_id"], "outcome": "پیشنهاد شد، بازدید می‌خواهد"}, "moshaver1", tokens).status_code == 200
    assert "missed" not in {a["type"] for a in get("/overview", "modir", tokens).json()["alerts"]}

def test_new_listing_meets_its_buyers(tokens):
    body = {"kind": "sale", "hood": "پونک", "street": "بلوار عدل", "area": 100, "rooms": 2, "floor": 2, "floors": 5, "age": 3, "elevator": True,
            "parking": True, "storage": False, "price": 7_400_000_000, "owner_name": "آزمون مالک", "owner_phone": "09120000001"}
    r = post("/listings", body, "moshaver2", tokens).json()
    d = get(f"/listings/{r['id']}", "moshaver2", tokens).json()
    assert r["matches"] == len(d["matches"]) >= 1
    assert d["matches"][0]["reasons"] and not d["matches"][0]["called"]
    assert any(a["type"] == "new_match" for a in get("/today", "moshaver2", tokens).json()["alerts"])

def test_visit_drafts_confirm_and_outcome(tokens):
    v = next(a for a in get("/overview", "modir", tokens).json()["alerts"] if a["type"] == "visit")
    drafts = get(f"/visits/{v['visit_id']}/drafts", "moshaver1", tokens).json()
    assert "فردا ساعت 17:30" in drafts["customer"] and drafts["owner_phone"] not in drafts["customer"]
    assert post(f"/visits/{v['visit_id']}/confirm", {}, "moshaver1", tokens).status_code == 200
    assert "visit" not in {a["type"] for a in get("/overview", "modir", tokens).json()["alerts"]}
    fake_llm.MODE = "down"
    out = post(f"/visits/{v['visit_id']}/outcome", {"text": "پسندیدند، پنجشنبه با همسرش دوباره می‌آید"}, "moshaver1", tokens).json()
    assert out["next_step"].startswith("بازدید دوم") and "پنجشنبه" in out["next_step"]

def test_deal_under_tariff_shows_in_the_checks(tokens):
    l = next(x for x in get("/listings?kind=rent", "moshaver1", tokens).json() if not x["flags"])
    pre = post("/deals/preview", {"kind": "rent", "deposit": l["deposit"], "rent": l["rent"], "agents": [2, 3]}, "moshaver1", tokens).json()
    assert pre["total"] == 2 * pre["each"] and sum(p["amount"] for p in pre["split"]) <= pre["total"]
    r = post("/deals", {"listing_id": l["id"], "buyer": "آزمون مستأجر", "deposit": l["deposit"], "rent": l["rent"], "agents": [2, 3],
                        "commission": pre["total"] // 2}, "moshaver1", tokens).json()
    assert r["below_tariff"]
    fees = [f for f in get("/checks", "modir", tokens).json() if f["type"] == "fee"]
    assert len(fees) == 2
    assert get(f"/listings/{l['id']}", "modir", tokens).json()["listing"]["status"] == "rented"

def test_stale_listing_confirmed_by_a_call(tokens):
    s = next(a for a in get("/overview", "modir", tokens).json()["alerts"] if a["type"] == "stale")
    assert post(f"/listings/{s['listing_id']}/contact", {"status": "active", "price": 1, "note": "هنوز می‌فروشد"}, "moshaver2", tokens).status_code == 200
    d = get(f"/listings/{s['listing_id']}", "modir", tokens).json()
    assert d["listing"]["contact_text"] == "امروز" and "هنوز" in d["history"][0]["text"]

def test_owner_report_numbers_are_checked(tokens):
    a = next(x for x in get("/overview", "modir", tokens).json()["alerts"] if x["type"] == "report")
    fake_llm.MODE = "badnum"
    r = post(f"/listings/{a['listing_id']}/report/draft", {}, "moshaver1", tokens).json()
    assert r["checked"] is False and "97" not in r["text"] and "گرامی" in r["text"]
    assert post(f"/listings/{a['listing_id']}/report", {"text": r["text"]}, "moshaver1", tokens).status_code == 200
    assert "report" not in {x["type"] for x in get("/overview", "modir", tokens).json()["alerts"]}

def test_convert_deposit_and_rent(tokens):
    r = post("/convert", {"deposit": 500_000_000, "rent": 10_000_000, "new_deposit": 300_000_000}, "moshaver1", tokens).json()
    assert r["rent"] == 16_000_000 and r["equivalent"] == 25_000_000   # 3% a month: 200 million less deposit = 6 million more rent

def test_website_takes_a_request_without_owner_details(tokens):
    start = httpx.post(base("/site/chat"), json={"chat": "", "text": ""}).json()
    say = lambda t: httpx.post(base("/site/chat"), json={"chat": start["chat"], "text": t}, timeout=30).json()
    before = get("/site/leads", "moshaver1", tokens).json()["last"]
    r = say("دنبال خرید آپارتمان دو خواب در پونک هستم")
    assert "بودجه" in r["messages"][0]
    r = say("تا ۹ میلیارد")
    shown = " ".join(r["messages"])
    assert "واحد" in shown and "09" not in shown
    r = say("۰۹۱۲۷۷۷۸۸۹۹")
    assert r["lead"] and "ثبت شد" in r["messages"][0]
    leads = get(f"/site/leads?after={before}", "moshaver1", tokens).json()
    assert [l["id"] for l in leads["new"]] == [r["lead"]["id"]]
    req = get(f"/requests/{r['lead']['id']}", "modir", tokens).json()["request"]
    assert req["source"] == "site" and req["phone"] == "09127778899" and req["hoods_list"] == ["پونک"]

def test_brief_and_assistant_numbers_are_checked(tokens):
    fake_llm.MODE = "badnum"
    b = get("/brief", "modir", tokens).json()
    assert b["checked"] is False and "97" not in b["text"]
    a = post("/ask", {"question": "در پونک چند فایل فعال داریم؟"}, "moshaver1", tokens).json()
    assert "97" not in a["answer"] and "پونک" in a["answer"]

def test_rent_is_the_amount_written_after_its_word(tokens):
    fake_llm.MODE = "nojson"   # rules only
    text = "خانم شیما طاهری ۰۹۳۵۱۲۲۶۶۴۰ زنگ زد، دنبال اجاره در جنت‌آباد یا شهران، دو خواب، رهن ۴۰۰ میلیون و اجاره تا ۱۵ میلیون"
    f = post("/read", {"kind": "request", "text": text}, "moshaver1", tokens).json()["fields"]
    assert (f["deposit"], f["rent"], f["name"], f["hoods"]) == (400_000_000, 15_000_000, "شیما طاهری", ["جنت‌آباد", "شهران"])
