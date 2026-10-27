"""Logins for each assistant (access.py): the permanent account, one-time guest codes, and the door taking both."""
import importlib, os, sys, time
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
import conftest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_off_without_settings():
    s = httpx.get(conftest.BASE + "/access/status").json()
    assert s["on"] is False and s["apps"] == ["school", "fabric"]
    assert httpx.get(conftest.BASE + "/access/guests").status_code == 403

def _app(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USER", "admin-for-test")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    monkeypatch.setenv("SITE_USER", "door")
    monkeypatch.setenv("SITE_PASSWORD", "door-secret")
    monkeypatch.setenv("ACCESS_DB_PATH", str(tmp_path / "access.db"))
    import access, gate
    access = importlib.reload(access); gate = importlib.reload(gate)
    app = FastAPI(); app.include_router(gate.router); app.include_router(access.router)
    @app.get("/fabric/ping")
    def fabric_ping(request: __import__("fastapi").Request):
        return {"ok": access.allows(request, access.app_for("/fabric/ping"))}
    @app.get("/school")
    def school_ping(request: __import__("fastapi").Request):
        return {"ok": access.allows(request, access.app_for("/school"))}
    return app, access, gate

def _cleanup(monkeypatch):
    for k in ("ADMIN_PASSWORD", "SITE_PASSWORD"):
        monkeypatch.delenv(k)
    import access, gate
    importlib.reload(access); importlib.reload(gate)

def test_permanent_account_opens_everything_and_makes_codes(monkeypatch, tmp_path):
    app, access, gate = _app(monkeypatch, tmp_path)
    c = TestClient(app)
    assert c.get("/access/status").json()["apps"] == []
    assert c.post("/access/login", json={"username": "admin-for-test", "password": "wrong"}).status_code == 401
    s = c.post("/access/login", json={"username": "admin-for-test", "password": "admin-secret"}).json()
    assert s["admin"] is True and s["apps"] == ["school", "fabric"]
    assert c.get("/school").json()["ok"] and c.get("/fabric/ping").json()["ok"]
    g = c.post("/access/guests", json={"label": "مدیر نمونه", "apps": ["school"], "hours": 2}).json()
    assert g["username"].startswith("guest") and len(g["password"]) == 6 and g["state"] == "waiting"
    assert "password" not in c.get("/access/guests").json()[0]   # shown once, never listed
    _cleanup(monkeypatch)

def test_guest_code_works_once_for_its_assistants_until_ended(monkeypatch, tmp_path):
    app, access, gate = _app(monkeypatch, tmp_path)
    admin = TestClient(app)
    admin.post("/access/login", json={"username": "admin-for-test", "password": "admin-secret"})
    g = admin.post("/access/guests", json={"label": "مهمان", "apps": ["school"], "hours": 2}).json()

    guest = TestClient(app)
    assert guest.get("/gate/status").json()["ok"] is False
    # the guest signs in at the site's door with the code; the door and the school open, the fabric shop does not
    assert guest.post("/gate/login", json={"username": g["username"], "password": g["password"]}).status_code == 200
    assert guest.get("/gate/status").json()["ok"] is True
    s = guest.get("/access/status").json()
    assert s["admin"] is False and s["apps"] == ["school"] and s["guest"]["label"] == "مهمان"
    assert guest.get("/school").json()["ok"] and not guest.get("/fabric/ping").json()["ok"]
    assert guest.get("/access/guests").status_code == 403   # guests can't make codes

    # one time only: a second browser with the same password gets nothing
    other = TestClient(app)
    assert other.post("/access/login", json={"username": g["username"], "password": g["password"]}).status_code == 401
    assert other.post("/gate/login", json={"username": g["username"], "password": g["password"]}).status_code == 401

    assert admin.get("/access/guests").json()[0]["state"] == "in"
    admin.post(f"/access/guests/{g['id']}/end")
    assert not guest.get("/school").json()["ok"] and guest.get("/gate/status").json()["ok"] is False
    _cleanup(monkeypatch)

def test_expired_code_and_forged_cookie(monkeypatch, tmp_path):
    app, access, gate = _app(monkeypatch, tmp_path)
    admin = TestClient(app)
    admin.post("/access/login", json={"username": "admin-for-test", "password": "admin-secret"})
    g = admin.post("/access/guests", json={"label": "دیر", "apps": ["fabric"], "hours": 1}).json()
    with access._conn() as db:
        db.execute("UPDATE guests SET expires_at = ? WHERE id = ?", (int(time.time()) - 1, g["id"]))
    assert TestClient(app).post("/access/login", json={"username": g["username"], "password": g["password"]}).status_code == 401
    c = TestClient(app)
    c.cookies.set("access", f"admin.{int(time.time()) + 999}.forged")
    assert c.get("/access/status").json()["apps"] == []
    _cleanup(monkeypatch)
