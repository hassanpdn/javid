"""Login, sessions and who may call what. Rule: role and identity come from the login, never from the request."""
import httpx, pytest
from conftest import BASE, Client, login

def test_login_and_me():
    me = Client(token=login("modir", fresh=True)).get("/me").json()
    assert me["role"] == "manager" and "password" not in me

@pytest.mark.parametrize("body", [{"username": "modir", "password": "x"}, {"username": "nobody1", "password": "1234"}])
def test_wrong_login(body):
    assert httpx.post(BASE + "/login", json=body).status_code == 401

def test_missing_field():
    assert httpx.post(BASE + "/login", json={"username": "modir"}).status_code == 422

@pytest.mark.parametrize("header", [None, "", "Bearer nope", "garbage"])
def test_bad_token(header):
    assert httpx.get(BASE + "/me", headers={"Authorization": header} if header is not None else {}).status_code == 401

def test_logout_ends_session():
    c = Client(token=login("edari", fresh=True))
    c.post("/logout")
    assert c.get("/me").status_code == 401
    login("edari", fresh=True)

def test_too_many_failed_logins_wait():
    codes = [httpx.post(BASE + "/login", json={"username": "brute", "password": str(i)}).status_code for i in range(7)]
    assert codes[:5] == [401] * 5 and codes[5:] == [429, 429]

def test_api_docs_are_off():
    assert httpx.get(BASE + "/docs").status_code == 404
    assert httpx.get(BASE + "/openapi.json").status_code == 404

def test_assets_are_compressed_and_cached():
    html = httpx.get(BASE + "/").text
    js = html.split('src="')[1].split('"')[0]
    r = httpx.get(BASE + js, headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"
    assert "immutable" in r.headers.get("cache-control", "")

USERS = ["modir", "edari", "moalem", "moshaver", "vali", "daneshamooz"]
ENDPOINTS = [
    ("/manager/overview", {"modir"}),
    ("/staff/letters", {"modir", "edari"}),
    ("/staff/log", {"modir", "edari"}),
    ("/staff/recipients", {"modir", "edari"}),
    ("/counselor/students", {"modir", "moshaver"}),
    ("/counselor/students/1", {"modir", "moshaver"}),
    ("/parent/child", {"vali"}),
    ("/parent/forms/physical", {"vali"}),
    ("/notifications", set(USERS)),
]
@pytest.mark.parametrize("path,allowed", ENDPOINTS)
@pytest.mark.parametrize("user", USERS)
def test_who_can_open_what(user, path, allowed):
    code = Client(user).get(path).status_code
    assert code == (200 if user in allowed else 403), f"{user} {path} -> {code}"

def test_parent_cannot_write_elsewhere():
    v = Client("vali")
    assert v.post("/counselor/students/2/notes", {"note": "x"}).status_code == 403
    assert v.post("/manager/warnings", {"teacher_id": 3, "text": "x"}).status_code == 403
    assert v.post("/staff/letters", {"body": "x" * 30}).status_code == 403

def test_cannot_touch_someone_elses_notification():
    from conftest import db
    with db() as c:
        nid = c.execute("SELECT id FROM notifications WHERE user_id != 6 LIMIT 1").fetchone()
    if not nid:   # make one for the manager
        Client("edari").post("/staff/letters/1/refer", {"recipients": ["user:1"], "needs_ack": True})
        with db() as c:
            nid = c.execute("SELECT id FROM notifications WHERE user_id = 1 LIMIT 1").fetchone()
    v = Client("vali")
    assert v.post(f"/notifications/{nid[0]}/read").status_code == 404
    assert v.post(f"/notifications/{nid[0]}/ack").status_code == 404
