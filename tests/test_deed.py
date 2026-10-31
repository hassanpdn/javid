"""The deed data extraction assistant (deed/): cleaning and checks, reading by rules, the model's answer checked
against the page (never guessed), pages that disagree, file checks, and the review from upload to the JSON.
OCR tests need Tesseract with Persian (apt: tesseract-ocr tesseract-ocr-fas poppler-utils) and are skipped without it."""
import base64, os, time
os.environ.setdefault("LLM_API_KEY", "x")   # deed.extract imports llm.py, whose client needs a key to start
import httpx, pytest
import conftest, fake_llm
from deed import fields as F, extract, ocr

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deed", "samples")
CLEAN = """شماره سند: ۴۸۲۹۱۳
دفتر شماره 312 صفحه 47
تاريخ صدور: 1384/06/15
ششدانگ یک باب خانه به مساحت 245.50 مترمربع
پلاک شماره 1520 فرعی از 87 اصلی واقع در بخش 11 تهران
مالک: آقای کامران نیک‌سرشت فرزند جهانگیر
به شماره ملی 5260181591 نسبت به شش دانگ
شمالاً به طول 12 متر دیوار به دیوار پلاک 1519 فرعی"""

def page(text, n=1, conf=None):
    return {"n": n, "readable": True, "lines": [{"text": l, "conf": conf} for l in text.splitlines()]}

# ---------- cleaning and checks ----------

def test_digits_and_letters_are_normalized():
    assert F.clean("علي كريمي ۱۲۳٫۵ ـ ٤٥") == "علی کریمی 123.5 45"

def test_jalali_dates_are_checked():
    assert F.jalali_date("۱۳۸۴/۶/۱۵") == ("1384/06/15", "")
    assert F.jalali_date("1403/12/30")[0] == "1403/12/30"            # a leap year
    assert F.jalali_date("1402/12/30")[0] is None                    # not a leap year
    assert F.jalali_date("1390/07/31")[0] is None                    # Mehr has 30 days
    assert F.jalali_date("1499/01/01")[1] == "تاریخ در آینده است."

def test_shares_must_add_up_to_six_dang():
    assert [F.dang(s) for s in ("سه دانگ", "یک و نیم دانگ", "ششدانگ", "۲٫۵ دانگ", "مشاع")] == [3, 1.5, 6, 2.5, None]
    assert F.shares_issue([3, 1.5, 1.5]) == ""
    assert "5" in F.shares_issue([3, 2])
    assert F.shares_issue([3, None])

def test_national_id_check_digit():
    assert F.national_id_ok("5260181591") and not F.national_id_ok("5260181592") and not F.national_id_ok("1111111111")

# ---------- reading ----------

def test_rules_read_a_clean_deed():
    deed, method = extract.extract([page(CLEAN)], use_model=False)
    v = {k: f["value"] for k, f in deed["fields"].items()}
    assert method == "rules"
    assert (v["deed_number"], v["issue_date"], v["book"], v["page"]) == ("482913", "1384/06/15", "312", "47")
    assert (v["main_plate"], v["sub_plate"], v["section"], v["area"], v["area_unit"]) == ("87", "1520", "11 تهران", 245.5, "مترمربع")
    assert v["north"].startswith("به طول 12 متر") and v["east"] is None          # not in the text: null
    o = deed["owners"][0]
    assert (o["name"]["value"], o["father_name"]["value"], o["national_id"]["value"], o["share"]["value"]) == \
           ("کامران نیک‌سرشت", "جهانگیر", "5260181591", "شش دانگ")
    assert deed["fields"]["deed_number"]["source"] == "شماره سند: 482913"
    assert not [i for i in deed["issues"] if "دانگ" in i]

def test_unreadable_value_is_flagged_not_guessed():
    deed, _ = extract.extract([page("شماره سند: .\n" + CLEAN.split("\n", 1)[1])], use_model=False)
    f = deed["fields"]["deed_number"]
    assert f["value"] is None and f["confidence"] == "low" and "خوانا نیست" in f["issues"][0]

def test_pages_that_disagree_keep_both_values():
    deed, _ = extract.extract([page(CLEAN), page("به مساحت 186 مترمربع طبق صورتمجلس تفکیکی", 2)], use_model=False)
    area = deed["fields"]["area"]
    assert area["value"] == 245.5 and area["conflicts"] == [{"value": 186, "page": 2, "source": "به مساحت 186 مترمربع طبق صورتمجلس تفکیکی"}]
    assert area["confidence"] == "low" and any("نمی‌خواند" in i for i in deed["issues"])

def test_confidence_follows_the_ocr():
    sure, _ = extract.extract([page(CLEAN, conf=92)], use_model=False)
    unsure, _ = extract.extract([page(CLEAN, conf=50)], use_model=False)
    assert sure["fields"]["book"]["confidence"] == "high" and unsure["fields"]["book"]["confidence"] == "low"

def test_unreadable_page_is_left_out_with_a_message():
    deed, _ = extract.extract([page(CLEAN), {"n": 2, "readable": False, "lines": []}], use_model=False)
    assert "صفحه‌ی 2 خوانا نبود" in deed["issues"][0]

# ---------- through the server (the test server's model is tests/fake_llm.py) ----------

def wait(doc_id, timeout=60):
    for _ in range(timeout * 4):
        d = httpx.get(f"{conftest.BASE}/deed/documents/{doc_id}").json()
        if d["status"] != "processing":
            return d
        time.sleep(.25)
    raise AssertionError("still processing")

def test_model_answer_is_checked_against_the_page():
    fake_llm.CALLS.clear()
    d = wait(httpx.post(conftest.BASE + "/deed/documents/text", json={"text": CLEAN}).json()["id"])
    assert d["status"] == "review" and d["method"] == "model" and fake_llm.CALLS
    f = d["deed"]["fields"]
    assert f["deed_number"]["value"] == "482913" and f["main_plate"]["value"] == "87"
    assert f["book"]["value"] is None             # the model said 777, which is nowhere in the deed: dropped

def test_model_cannot_invent_an_owner():
    fake_llm.MODE = "evil"
    d = wait(httpx.post(conftest.BASE + "/deed/documents/text", json={"text": CLEAN}).json()["id"])
    assert d["deed"]["fields"]["deed_number"]["value"] is None and d["deed"]["owners"] == []

def test_invalid_json_is_asked_again_then_reported():
    fake_llm.MODE, fake_llm.CALLS[:] = "nojson", []
    d = wait(httpx.post(conftest.BASE + "/deed/documents/text", json={"text": CLEAN}).json()["id"])
    assert d["status"] == "error" and "دو بار" in d["message"] and len(fake_llm.CALLS) == 2

def test_model_down_falls_back_to_rules():
    fake_llm.MODE = "down"
    d = wait(httpx.post(conftest.BASE + "/deed/documents/text", json={"text": CLEAN}).json()["id"])
    assert d["status"] == "review" and d["method"] == "rules" and "قاعده" in d["deed"]["issues"][0]
    assert d["deed"]["fields"]["book"]["value"] == "312"

def test_wrong_or_big_files_are_refused():
    def send(data):
        return httpx.post(conftest.BASE + "/deed/documents", json={"name": "x", "data": base64.b64encode(data).decode()})
    r = send(b"GIF89a just a gif")
    assert r.status_code == 415 and "JPG" in r.json()["detail"]
    assert send(b"%PDF" + b"0" * (10 * 1024 * 1024)).status_code == 413
    assert httpx.post(conftest.BASE + "/deed/documents", json={"name": "x", "data": "not base64!"}).status_code == 422

def test_review_confirm_and_export():
    d = wait(httpx.post(conftest.BASE + "/deed/documents/text", json={"text": CLEAN}).json()["id"])
    base = f"{conftest.BASE}/deed/documents/{d['id']}"
    assert httpx.get(base + "/export").status_code == 409                   # not before it is confirmed
    edit = {"fields": {"book": "۳۱۲", "issue_date": "1384/6/15"},
            "owners": [{"name": "كامران نيك‌سرشت", "father_name": "جهانگیر", "national_id": "۵۲۶۰۱۸۱۵۹۱", "share": "سه دانگ"}],
            "transfers": []}
    saved = httpx.post(base + "/save", json=edit).json()
    assert saved["deed"]["fields"]["book"]["value"] == "312" and saved["deed"]["fields"]["book"]["edited"]
    assert any("3 دانگ" in i for i in saved["deed"]["issues"])               # one owner with three dang
    edit["owners"][0]["share"] = "شش دانگ"
    assert httpx.post(base + "/confirm", json=edit).json()["status"] == "confirmed"
    out = httpx.get(base + "/export").json()
    assert out["registry"] == {"book": "312", "page": None} and out["issue_date"] == "1384/06/15"
    assert out["owners"][0]["name"] == "کامران نیک‌سرشت" and out["owners"][0]["national_id"] == "5260181591"
    assert out["shares_total_dang"] == 6 and "1405" in out["review"]["confirmed_at"]

# ---------- OCR ----------

needs_ocr = pytest.mark.skipif(not ocr.available(), reason="Tesseract with Persian is not installed")

@needs_ocr
def test_samples_are_read_from_the_scans():
    fake_llm.MODE = "down"   # read by rules, so the result comes from the scan alone
    ids = {k: httpx.post(f"{conftest.BASE}/deed/samples/{k}").json()["id"] for k in ("clean", "shared", "unclear")}
    clean, shared, unclear = (wait(ids[k], 120) for k in ("clean", "shared", "unclear"))
    assert clean["deed"]["fields"]["deed_number"]["value"] == "482913"
    assert len(shared["pages"]) == 2 and len(shared["deed"]["owners"]) == 3 and shared["deed"]["transfers"]
    assert shared["deed"]["fields"]["area"]["conflicts"][0]["value"] == 186
    assert unclear["pages"][0]["rotation"] == 90 and unclear["deed"]["fields"]["deed_number"]["value"] is None
    assert unclear["deed"]["fields"]["issue_date"]["value"] is None
    r = httpx.get(f"{conftest.BASE}/deed/documents/{ids['clean']}/pages/1")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"

@needs_ocr
def test_blank_page_is_reported_not_extracted(tmp_path):
    from PIL import Image
    Image.new("RGB", (1200, 1600), "white").save(tmp_path / "blank.png")
    data = base64.b64encode((tmp_path / "blank.png").read_bytes()).decode()
    d = wait(httpx.post(conftest.BASE + "/deed/documents", json={"name": "blank", "data": data}).json()["id"])
    assert d["status"] == "error" and "خوانا" in d["message"] and d["pages"][0]["note"]

def test_logout_forgets_every_deed():
    wait(httpx.post(conftest.BASE + "/deed/documents/text", json={"text": CLEAN}).json()["id"])
    assert httpx.get(conftest.BASE + "/deed/documents").json()
    assert httpx.post(conftest.BASE + "/gate/logout").status_code == 200
    assert httpx.get(conftest.BASE + "/deed/documents").json() == []
