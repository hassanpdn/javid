"""The site's door (gate.py) and the reset that starts every visit on the setup form."""
import importlib, os, sys
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
import conftest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_door_and_reset_are_off_without_settings():
    assert httpx.get(conftest.BASE + "/gate/status").json() == {"on": False, "ok": True, "reset_on_load": False, "hub": False}
    assert httpx.post(conftest.BASE + "/setup/reset").status_code == 404   # nobody can wipe the school by accident

def test_door_needs_the_right_password_and_signs_its_cookie(monkeypatch):
    monkeypatch.setenv("SITE_USER", "pudineh")
    monkeypatch.setenv("SITE_PASSWORD", "secret-for-test")
    import gate
    gate = importlib.reload(gate)
    app = FastAPI(); app.include_router(gate.router)
    c = TestClient(app)
    assert c.get("/gate/status").json()["ok"] is False
    assert c.post("/gate/login", json={"username": "pudineh", "password": "wrong"}).status_code == 401
    c.cookies.set("site", "9999999999.forged")
    assert c.get("/gate/status").json()["ok"] is False
    c.cookies.clear()
    r = c.post("/gate/login", json={"username": "pudineh", "password": "secret-for-test"})
    assert r.status_code == 200 and "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/gate/status").json()["ok"] is True
    monkeypatch.delenv("SITE_PASSWORD")
    importlib.reload(gate)
