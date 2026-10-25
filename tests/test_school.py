"""Setting the demo up for another school: every name comes from the form, nothing says Javid any more.
These tests rebuild the demo data, so they end by going back to Javid with fresh logins."""
import httpx, pytest
import conftest, fake_llm
from conftest import BASE, Client, db

NIKAN = {"name": "دبستان نیکان", "gender": "boys", "city": "اصفهان", "district": "ناحیه ۲",
         "manager_title": "آقای", "manager_name": "علی رستمی", "counselor_title": "آقای", "counselor_name": "رضا یزدانی",
         "staff_title": "خانم", "staff_name": "سمیرا امینی"}

def setup(school):
    return httpx.post(BASE + "/setup", json={"school": school}, timeout=60)

def test_nothing_is_given_out_before_setup():
    r = httpx.get(BASE + "/school")
    assert r.json() == {"set_up": False}
    assert "جاوید" not in r.text and "انوشه" not in r.text

def test_default_school_for_the_button():
    d = httpx.get(BASE + "/setup/default").json()["school"]
    assert d["name"] == "جاوید" and d["manager_name"] == "دکتر انوشه‌پور"
    assert httpx.post(BASE + "/setup/unlock", json={}).status_code in (404, 405)   # no password step any more

@pytest.mark.parametrize("change,code", [
    ({"name": "  "}, 400), ({"gender": "x"}, 400), ({"manager_title": "دکتر"}, 400), ({"city": "ا" * 50}, 400),
])
def test_bad_setup_is_refused(change, code):
    r = setup({**NIKAN, **change})
    assert r.status_code == code, r.text
    assert httpx.get(BASE + "/school").json()["set_up"] is False   # nothing changed

def test_setup_for_another_school():
    old = Client("modir")
    assert setup(NIKAN).status_code == 200
    assert old.get("/me").status_code == 401          # old accounts are gone
    conftest._tokens.clear()

    info = httpx.get(BASE + "/school").json()
    assert info["school"]["full_name"] == "دبستان نیکان"   # «دبستان» typed in the name is not doubled
    assert info["names"]["modir"] == "آقای علی رستمی" and info["names"]["karimi"] == "حمید کریمی"
    assert "آرین" in info["names"]["vali"]
    assert "saved" not in info and "default" not in info   # no other school's name is ever given out

    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM students WHERE gender = 'm'").fetchone()[0] == 30
        senders = {r[0] for r in c.execute("SELECT sender FROM letters")}
        replies = " ".join(r[0] for r in c.execute("SELECT reply FROM letters WHERE reply IS NOT NULL"))
    assert "اداره آموزش و پرورش ناحیه ۲ اصفهان" in senders
    assert "جاوید" not in replies

    me = Client("modir").get("/me").json()
    assert me["full_name"] == "آقای علی رستمی"
    answer = Client("vali").post("/parent/ask", {"question": "بچه من بیش فعاله؟"}).json()["answer"]
    assert "آقای رضا یزدانی" in answer
    fake_llm.CALLS.clear()
    Client("vali").get("/parent/report")
    assert fake_llm.CALLS and all("جاوید" not in c["system"] for c in fake_llm.CALLS)
    assert any("دبستان نیکان" in c["system"] for c in fake_llm.CALLS)

def test_back_to_the_default_school_forgets_the_other():
    default = httpx.get(BASE + "/setup/default").json()["school"]
    assert setup(default).status_code == 200
    conftest._tokens.clear()
    r = httpx.get(BASE + "/school")
    assert r.json()["names"]["vali"].endswith("(ولیِ آوا)")
    assert "نیکان" not in r.text and "رستمی" not in r.text
