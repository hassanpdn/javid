"""The fabric wholesaler's assistant: setup from nothing, the planted situations, the phone desk writing
into the Excel files, roles, and the model's numbers being checked."""
import base64, os
import httpx, openpyxl, pytest
import conftest, fake_llm

def base(path):
    return conftest.BASE + "/fabric" + path

@pytest.fixture(scope="module")
def tokens():
    r = httpx.post(base("/setup"), json={"business": httpx.get(base("/setup/default")).json()["business"]}, timeout=120)
    assert r.status_code == 200, r.text
    out = {}
    for u in ("sahebkar", "forooshande", "hesabdar"):
        r = httpx.post(base("/login"), json={"username": u, "password": "1234"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": "Bearer " + r.json()["token"]}
    return out

def test_setup_reads_the_three_files_and_reports_what_it_cleaned(tokens):
    files = httpx.get(base("/files"), headers=tokens["hesabdar"]).json()
    assert [f["key"] for f in files["files"]] == ["stock", "sales", "accounts"]
    notes = " ".join(files["notes"])
    assert "حاج" in notes and "جمع کل" in notes and "رقم فارسی" in notes

def test_owner_sees_every_planted_situation(tokens):
    o = httpx.get(base("/overview"), headers=tokens["sahebkar"]).json()
    kinds = {a["type"] for a in o["alerts"]}
    assert {"bounced", "cash", "limit", "low", "quiet", "dead"} <= kinds
    assert o["week"]["left"] < 0                                  # next week's cheques are not covered
    brief = httpx.get(base("/brief"), headers=tokens["sahebkar"], timeout=30).json()
    assert brief["text"]

def test_model_numbers_are_checked(tokens):
    fake_llm.MODE = "badnum"
    r = httpx.post(base("/ask"), json={"question": "فروش این ماه چقدر بود؟"}, headers=tokens["sahebkar"], timeout=30).json()
    assert r["checked"] is False and "97" not in r["answer"]
    fake_llm.MODE = "badnum"
    with_bounced = [d for d in httpx.get(base("/money"), headers=tokens["hesabdar"]).json()["debtors"] if d["bounced"]][0]
    draft = httpx.post(base("/reminders/draft"), json={"customer_id": with_bounced["id"]}, headers=tokens["hesabdar"], timeout=30).json()
    assert draft["checked"] is False and "97" not in draft["text"]

def test_roles_stay_in_their_lane(tokens):
    assert httpx.get(base("/money"), headers=tokens["forooshande"]).status_code == 403
    assert httpx.get(base("/overview"), headers=tokens["hesabdar"]).status_code == 403
    assert httpx.post(base("/order/read"), json={"customer_id": 1, "note": "۲ توپ کتان"}, headers=tokens["hesabdar"]).status_code == 403
    assert httpx.get(base("/overview")).status_code == 401
    # a school login is not a fabric login
    school = httpx.post(conftest.BASE + "/login", json={"username": "modir", "password": "1234"}).json()["token"]
    assert httpx.get(base("/me"), headers={"Authorization": "Bearer " + school}).status_code == 401

def test_phone_order_goes_into_all_three_files(tokens):
    h = tokens["forooshande"]
    cust = [c for c in httpx.get(base("/customers?q=رضایی"), headers=h).json()]
    assert len(cust) == 1
    card = httpx.get(base(f"/customers/{cust[0]['id']}"), headers=h).json()
    assert any("برگشت" in w["text"] for w in card["warnings"])
    draft = httpx.post(base("/order/read"), json={"customer_id": cust[0]["id"], "note": "۲ توپ کتان کش مشکی و ۲۰ متر حریر سفید"},
                       headers=h, timeout=30).json()
    assert [(l["title"], l["rolls"], l["meters"]) for l in draft["lines"]] == [("کتان کش مشکی", 2, 100), ("حریر سفید", 0, 20)]
    assert any("برگشت" in w["text"] for w in draft["warnings"])   # the seller is warned before confirming
    before = {p["code"]: p["meters"] for p in httpx.get(base("/stock"), headers=h).json()}
    r = httpx.post(base("/order/confirm"), headers=h, json={
        "customer_id": cust[0]["id"], "payment": "چک", "cheque_days": 60, "cheque_bank": "ملت",
        "lines": [{"code": l["code"], "rolls": l["rolls"], "meters": l["meters"]} for l in draft["lines"]]})
    assert r.status_code == 200, r.text
    no = r.json()["invoice"]
    after = {p["code"]: p["meters"] for p in httpx.get(base("/stock"), headers=h).json()}
    assert before[draft["lines"][0]["code"]] - after[draft["lines"][0]["code"]] == 100
    folder = os.path.join(os.path.dirname(conftest.DB_PATH), "fabric_files")
    sales = openpyxl.load_workbook(os.path.join(folder, "sales.xlsx"))["فروش"]
    assert any(row[0] == no for row in sales.iter_rows(values_only=True))
    last = list(sales.iter_rows(values_only=True))[-1]
    assert last[0] == "جمع کل"                                     # the hand-typed total stays at the bottom
    cheques = openpyxl.load_workbook(os.path.join(folder, "accounts.xlsx"))["چک‌های دریافتی"]
    assert list(cheques.iter_rows(values_only=True))[-1][1] == "ملت"

def test_confirm_ignores_prices_from_the_browser_and_refuses_too_much(tokens):
    h = tokens["forooshande"]
    p = httpx.get(base("/stock?q=حریر صورتی"), headers=h).json()[0]
    r = httpx.post(base("/order/confirm"), headers=h, json={"customer_id": 4, "payment": "نقد",
                   "lines": [{"code": p["code"], "rolls": p["rolls"] + 50}]})
    assert r.status_code == 400
    r = httpx.post(base("/order/confirm"), headers=h, json={"customer_id": 4, "payment": "بیت‌کوین", "lines": [{"code": p["code"], "rolls": 1}]})
    assert r.status_code == 400

def test_a_broken_upload_changes_nothing(tokens):
    h = tokens["hesabdar"]
    before = httpx.get(base("/files"), headers=h).json()["files"]
    bad = base64.b64encode(b"PK not really a workbook").decode()
    r = httpx.post(base("/files/accounts"), json={"data": bad}, headers=h)
    assert r.status_code == 400
    assert httpx.get(base("/files"), headers=h).json()["files"] == before
    assert httpx.post(base("/files/accounts"), json={"data": bad}, headers=tokens["forooshande"]).status_code == 403

def test_the_three_files_are_checked_against_each_other(tokens):
    r = httpx.get(base("/reconcile"), headers=tokens["hesabdar"]).json()
    kinds = sorted(i["kind"] for i in r["issues"])
    assert kinds == ["cash", "invoice", "stock", "stock"]          # the marks the planted theft left, and nothing else
    assert all(i["how"] for i in r["issues"])                      # every finding shows the sum behind it
    cheque = next(ch for ch in r["checks"] if ch["key"] == "cheque")
    assert cheque["ok"]                                             # cheque sales, including the one confirmed above
    assert httpx.get(base("/reconcile"), headers=tokens["forooshande"]).status_code == 403

def test_every_change_is_in_the_event_log(tokens):
    ev = httpx.get(base("/events"), headers=tokens["sahebkar"]).json()
    texts = " ".join(e["text"] for e in ev)
    assert "وارد شد" in texts and "ثبت شد" in texts
    confirmed = next(e for e in ev if e["kind"] == "invoice" and e["detail"] and e["detail"].get("steps"))
    assert [s["file"] for s in confirmed["detail"]["steps"]] == ["فروش", "انبار", "حسابداری"]
    assert httpx.get(base("/events"), headers=tokens["hesabdar"]).status_code == 403

def test_report_lines_say_where_they_come_from_and_download(tokens):
    r = httpx.get(base("/report?period=last_30"), headers=tokens["hesabdar"]).json()
    assert all(row["how"] for sec in r["sections"] for row in sec["rows"])
    d = httpx.get(base("/report/download?period=last_30"), headers=tokens["sahebkar"])
    assert d.status_code == 200 and d.content.startswith(b"PK")
    assert httpx.get(base("/report?period=forever"), headers=tokens["sahebkar"]).status_code == 400

def say(chat, text):
    r = httpx.post(base("/shop/chat"), json={"chat": chat, "text": text}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()

def test_website_assistant_takes_an_unpaid_order_and_the_shop_hears_of_it(tokens):
    before = httpx.get(base("/web-orders/new"), headers=tokens["sahebkar"]).json()["waiting"]
    chat = say("", "")["chat"]
    r = say(chat, "۲ توپ مخمل")
    assert "کدام" in " ".join(r["messages"]) and "مخمل ساده سرمه‌ای" in r["chips"]       # it asks which one
    r = say(chat, "مخمل ساده سبز یشمی")
    assert any("انبار" in t for t in r["trace"])                                         # price and stock came from the stock file
    r = say(chat, "همین کافیه")
    r = say(chat, "09120000001")
    assert "نام" in " ".join(r["messages"])                                              # a new customer: it asks the name
    r = say(chat, "زهرا کاظمی")
    r = say(chat, "بله")
    order = r["order"]
    assert order and str(order["id"]) in " ".join(r["messages"]).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    news = httpx.get(base("/web-orders/new"), headers=tokens["forooshande"]).json()
    assert news["waiting"] == before + 1
    folder = os.path.join(os.path.dirname(conftest.DB_PATH), "fabric_files")
    sheet = openpyxl.load_workbook(os.path.join(folder, "sales.xlsx"))["سفارش‌های سایت"]
    assert [row[-1] for row in sheet.iter_rows(min_row=2, values_only=True) if row[0] == order["id"]] == ["پرداخت نشده"]
    # paid: it becomes an invoice, the new customer joins the accounts file
    r = httpx.post(base(f"/web-orders/{order['id']}/invoice"), json={"payment": "نقد"}, headers=tokens["forooshande"])
    assert r.status_code == 200, r.text
    assert r.json()["new_customer"] is True
    assert httpx.post(base(f"/web-orders/{order['id']}/invoice"), json={"payment": "نقد"}, headers=tokens["forooshande"]).status_code == 400
    assert httpx.get(base("/web-orders"), headers=tokens["hesabdar"]).status_code == 403
    rec = httpx.get(base("/reconcile"), headers=tokens["hesabdar"]).json()
    assert sorted(i["kind"] for i in rec["issues"]) == ["cash", "invoice", "stock", "stock"]   # the sale kept the files in agreement

def test_website_knows_a_returning_customer_by_phone(tokens):
    phone = httpx.get(base("/shop/demo-phones"), headers=tokens["sahebkar"]).json()[0]["phone"]
    chat = say("", "")["chat"]
    say(chat, "۱ توپ کتان کش کرم")
    say(chat, "همین")
    r = say(chat, phone)
    assert "خوش آمدید" in " ".join(r["messages"]) and "ثبت کنم؟" in r["messages"]
