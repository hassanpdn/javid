"""Logins for each assistant (access.py): the permanent account, people's accounts it makes, and the door taking both."""
import importlib, os, sys, time
import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import conftest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
ADMIN = {"username": "admin-for-test", "password": "admin-secret"}

def test_off_without_settings():
    s = httpx.get(conftest.BASE + "/access/status").json()
    assert s["on"] is False and s["apps"] == ["school", "fabric"]
    assert httpx.get(conftest.BASE + "/access/people").status_code == 403

def _app(monkeypatch, tmp_path, door_user="door", door_password="door-secret"):
    monkeypatch.setenv("ADMIN_USER", ADMIN["username"])
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN["password"])
    monkeypatch.setenv("SITE_USER", door_user)
    monkeypatch.setenv("SITE_PASSWORD", door_password)
    monkeypatch.setenv("ACCESS_DB_PATH", str(tmp_path / "access.db"))
    import access, gate
    access = importlib.reload(access); gate = importlib.reload(gate)
    app = FastAPI(); app.include_router(gate.router); app.include_router(access.router)
    @app.get("/fabric/ping")
    def fabric_ping(request: Request):
        return {"ok": access.allows(request, access.app_for("/fabric/ping"))}
    @app.get("/school")
    def school_ping(request: Request):
        return {"ok": access.allows(request, access.app_for("/school"))}
    return app, access

def _cleanup(monkeypatch):
    for k in ("ADMIN_PASSWORD", "SITE_PASSWORD"):
        monkeypatch.delenv(k)
    import access, gate
    importlib.reload(access); importlib.reload(gate)

def _admin(app):
    c = TestClient(app)
    assert c.post("/access/login", json=ADMIN).status_code == 200
    return c

def test_permanent_account_at_the_door_opens_every_card(monkeypatch, tmp_path):
    # the door's own login is the same as the permanent account's: one login must open everything
    app, access = _app(monkeypatch, tmp_path, door_user=ADMIN["username"], door_password=ADMIN["password"])
    c = TestClient(app)
    assert c.post("/gate/login", json=ADMIN).status_code == 200
    s = c.get("/access/status").json()
    assert s["admin"] is True and s["apps"] == ["school", "fabric"]
    assert c.get("/school").json()["ok"] and c.get("/fabric/ping").json()["ok"]
    _cleanup(monkeypatch)

def test_person_sees_only_their_cards_and_changes_apply_at_once(monkeypatch, tmp_path):
    app, access = _app(monkeypatch, tmp_path)
    admin = _admin(app)
    p = admin.post("/access/people", json={"name": "خانم احمدی", "username": "Ahmadi", "password": "rose-2026",
                                            "apps": ["school", "fabric"], "expires_on": None}).json()
    assert p["username"] == "ahmadi" and p["apps"] == ["school", "fabric"] and "password" not in p
    assert admin.post("/access/people", json={"name": "x", "username": "ahmadi", "password": "123456", "apps": ["school"]}).status_code == 409

    guest = TestClient(app)
    assert guest.post("/gate/login", json={"username": "ahmadi", "password": "wrong-one"}).status_code == 401
    assert guest.post("/gate/login", json={"username": "ahmadi", "password": "rose-2026"}).status_code == 200
    s = guest.get("/access/status").json()
    assert s["admin"] is False and s["name"] == "خانم احمدی" and s["apps"] == ["school", "fabric"]
    assert guest.get("/access/people").status_code == 403          # only the permanent account gives access
    assert TestClient(app).post("/access/login", json={"username": "ahmadi", "password": "rose-2026"}).status_code == 200   # not one-time

    admin.post(f"/access/people/{p['id']}", json={"name": "خانم احمدی", "username": "ahmadi", "password": "", "apps": ["fabric"]})
    assert guest.get("/access/status").json()["apps"] == ["fabric"]
    assert not guest.get("/school").json()["ok"] and guest.get("/fabric/ping").json()["ok"]

    # a new password ends the logins made with the old one
    admin.post(f"/access/people/{p['id']}", json={"name": "خانم احمدی", "username": "ahmadi", "password": "new-pass-1", "apps": ["fabric"]})
    assert guest.get("/access/status").json()["apps"] == []
    assert TestClient(app).post("/access/login", json={"username": "ahmadi", "password": "new-pass-1"}).status_code == 200

    admin.post(f"/access/people/{p['id']}/delete")
    assert TestClient(app).post("/access/login", json={"username": "ahmadi", "password": "new-pass-1"}).status_code == 401
    _cleanup(monkeypatch)

def test_last_day(monkeypatch, tmp_path):
    app, access = _app(monkeypatch, tmp_path)
    admin = _admin(app)
    assert admin.post("/access/people", json={"name": "x", "username": "old", "password": "123456", "apps": ["school"],
                                              "expires_on": "1400/01/01"}).status_code == 422
    p = admin.post("/access/people", json={"name": "دیر", "username": "late", "password": "123456", "apps": ["school"],
                                           "expires_on": "1499/12/29"}).json()
    assert p["expires_on"] == "1499/12/29" and p["expired"] is False
    guest = TestClient(app)
    assert guest.post("/access/login", json={"username": "late", "password": "123456"}).status_code == 200
    with access._conn() as db:
        db.execute("UPDATE people SET expires_at = ? WHERE id = ?", (int(time.time()) - 1, p["id"]))
    assert guest.get("/access/status").json()["apps"] == [] and not guest.get("/school").json()["ok"]
    assert TestClient(app).post("/access/login", json={"username": "late", "password": "123456"}).status_code == 401
    assert admin.get("/access/people").json()[0]["expired"] is True
    _cleanup(monkeypatch)

def test_today_comes_from_the_server_in_tehran(monkeypatch, tmp_path):
    from datetime import datetime
    import jalali
    app, access = _app(monkeypatch, tmp_path)
    assert TestClient(app).get("/access/status").json()["today"] == jalali.jstr(datetime.now(access.TEHRAN).date())
    _cleanup(monkeypatch)

def test_forged_cookie(monkeypatch, tmp_path):
    app, access = _app(monkeypatch, tmp_path)
    c = TestClient(app)
    c.cookies.set("access", f"admin.{int(time.time()) + 999}.forged")
    assert c.get("/access/status").json()["apps"] == []
    _cleanup(monkeypatch)
