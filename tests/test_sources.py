"""The data map (sources.py): every assistant has one, every computed number names raw data that exists in it, and
only the permanent account sees it."""
import importlib, os, sys
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
ADMIN = {"username": "admin-for-test", "password": "admin-secret"}

def test_every_assistant_has_a_whole_map():
    import access, sources
    assert set(sources.CATALOG) == set(access.APPS)
    for app, c in sources.CATALOG.items():
        keys = {i["key"] for i in c["items"]}
        assert len(keys) == len(c["items"]), app                       # no key twice
        for i in c["items"]:
            if i["kind"] == "raw":
                assert i["way"] in sources.WAYS and i["real"] and i["who"], (app, i["key"])
            else:
                assert i["made_of"] and set(i["made_of"]) <= keys, (app, i["key"])
        if app != "deed":                                              # the panels mark their four cards and today's work
            assert {"stat.0", "stat.1", "stat.2", "stat.3", "alerts"} <= keys, app

def test_only_the_permanent_account(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USER", ADMIN["username"])
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN["password"])
    monkeypatch.setenv("ACCESS_DB_PATH", str(tmp_path / "access.db"))
    import access, sources
    access = importlib.reload(access); sources = importlib.reload(sources)
    app = FastAPI(); app.include_router(access.router); app.include_router(sources.router)
    assert TestClient(app).get("/access/sources/hotel").status_code == 403
    admin = TestClient(app)
    assert admin.post("/access/login", json=ADMIN).status_code == 200
    m = admin.get("/access/sources/hotel").json()
    stat = next(i for i in m["items"] if i["key"] == "stat.0")
    assert stat["made_of_text"] and all(t for t in stat["made_of_text"])
    assert admin.get("/access/sources/nothing").status_code == 404
    monkeypatch.delenv("ADMIN_PASSWORD")
    importlib.reload(access); importlib.reload(sources)
