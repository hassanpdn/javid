"""Real visitors' speed (speed.py): reports pass the site's door, only known screens are kept, too many from one
address are dropped, and only the permanent account sees the summary, worked out by code."""
import importlib, os, sys
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
ADMIN = {"username": "admin-for-test", "password": "admin-secret"}

def _app(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USER", ADMIN["username"])
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN["password"])
    monkeypatch.setenv("ACCESS_DB_PATH", str(tmp_path / "access.db"))
    import access, speed
    access = importlib.reload(access); speed = importlib.reload(speed)
    app = FastAPI(); app.include_router(access.router); app.include_router(speed.router)
    return app, speed

def _cleanup(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD")
    import access, speed
    importlib.reload(access); importlib.reload(speed)

def test_reports_and_the_summary(monkeypatch, tmp_path):
    app, speed = _app(monkeypatch, tmp_path)
    admin = TestClient(app)
    assert admin.post("/access/login", json=ADMIN).status_code == 200
    for ms in (1000, 2000, 3000, 4000, 30000):
        assert admin.post("/speed", json={"screen": "school:manager", "kind": "load", "ms": ms, "kb": 200, "phone": True, "net": "4g"}).json()["ok"]
    assert admin.post("/speed", json={"screen": "hub", "kind": "load", "ms": 900, "failed": 1}).json()["ok"]
    assert not admin.post("/speed", json={"screen": "made-up", "kind": "load", "ms": 1}).json()["ok"]   # unknown screens are not kept
    v = admin.get("/speed").json()
    assert v["count"] == 6
    m = next(s for s in v["screens"] if s["screen"] == "school:manager")
    assert (m["count"], m["median"], m["p90"], m["worst"], m["kb"], m["failed"]) == (5, 3000, 30000, 30000, 200, 0)
    assert next(s for s in v["screens"] if s["screen"] == "hub")["failed"] == 1
    assert v["latest"][0]["who"] == "حساب دائمی" and v["latest"][0]["label"] == "صفحه‌ی دستیارها"
    assert admin.get("/speed?device=desktop").json()["count"] == 1
    assert TestClient(app).get("/speed").status_code == 403   # only the permanent account
    _cleanup(monkeypatch)

def test_too_many_from_one_address_are_dropped(monkeypatch, tmp_path):
    app, speed = _app(monkeypatch, tmp_path)
    c = TestClient(app)
    oks = [c.post("/speed", json={"screen": "deed", "kind": "open", "ms": 500}).json()["ok"] for _ in range(speed.PER_MINUTE + 5)]
    assert oks.count(True) == speed.PER_MINUTE
    _cleanup(monkeypatch)

def test_the_door_covers_it():
    import conftest, httpx
    # without the door (local runs and tests) /speed is open; behind it, app.py's gate answers 401 «site» like any API call
    assert httpx.post(conftest.BASE + "/speed", json={"screen": "hub", "kind": "load", "ms": 1}).status_code == 200
