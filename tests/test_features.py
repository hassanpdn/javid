"""Runtime switches for the parent and student roles. With both off the app is an internal CRM for the staff:
those roles can't log in, logged-in sessions end, and parents can't be messaged."""
import httpx, pytest
import conftest
from conftest import BASE, Client

def set_features(**f):
    r = httpx.post(BASE + "/features", json=f)
    assert r.status_code == 200
    return r.json()["features"]

@pytest.fixture
def internal_mode():
    """Both roles off for the test, back on afterwards."""
    parent = Client("vali")                 # logged in before the switch
    assert set_features(parents=False, students=False) == {"parents": False, "students": False}
    yield parent
    set_features(parents=True, students=True)
    conftest._tokens.pop("vali", None)

def test_switches_show_in_school_info(internal_mode):
    assert httpx.get(BASE + "/school").json()["features"] == {"parents": False, "students": False}

def test_switched_off_roles_cannot_log_in(internal_mode):
    for user in ("vali", "daneshamooz"):
        assert httpx.post(BASE + "/login", json={"username": user, "password": "1234"}).status_code == 403
    assert httpx.post(BASE + "/login", json={"username": "modir", "password": "1234"}).status_code == 200

def test_logged_in_parent_is_logged_out(internal_mode):
    assert internal_mode.get("/parent/child").status_code == 401

def test_no_parents_among_recipients(internal_mode):
    r = Client("edari").get("/staff/recipients").json()
    assert all(x["kind"] != "parent" for x in r["groups"] + r["people"])
    sent = Client("edari").post("/staff/letters/1/refer", {"recipients": ["group:parents"], "parent_text": "x"})
    assert sent.status_code == 400          # nobody left to send to

def test_no_messages_to_parents(internal_mode):
    assert Client("moshaver").post("/counselor/students/1/suggest").status_code == 403

def test_staff_keep_working(internal_mode):
    for user, path in [("modir", "/manager/overview"), ("edari", "/staff/letters"), ("moshaver", "/counselor/students")]:
        assert Client(user).get(path).status_code == 200

def test_one_switch_at_a_time():
    assert set_features(students=False) == {"parents": True, "students": False}
    assert httpx.post(BASE + "/login", json={"username": "vali", "password": "1234"}).status_code == 200
    assert httpx.post(BASE + "/login", json={"username": "daneshamooz", "password": "1234"}).status_code == 403
    set_features(students=True)
    assert httpx.post(BASE + "/login", json={"username": "daneshamooz", "password": "1234"}).status_code == 200
