"""«سلامت سرور» (health.py): reading the load, memory and uptime, the backups' status and the watcher's problems,
the colour of each, and that only the permanent account sees it."""
import importlib, json, os, sys
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import health

def fake_proc(tmp_path, used_gb=6, total_gb=8, load5=1.0):
    p = tmp_path / "proc"
    p.mkdir(parents=True)
    (p / "uptime").write_text("277200.5 1000.0\n")                       # 3 days 5 hours
    (p / "meminfo").write_text(f"MemTotal: {total_gb * 2**20} kB\nMemFree: 100 kB\nMemAvailable: {int((total_gb - used_gb) * 2**20)} kB\n")
    (p / "loadavg").write_text(f"0.5 {load5} 0.8 1/200 300\n")
    return p

def test_numbers_and_their_colours(tmp_path, monkeypatch):
    proc = fake_proc(tmp_path)
    up = health.uptime(proc)
    assert up["days"] == 3 and up["hours"] == 5 and "3 روز" in up["text"]
    m = health.memory(proc)
    assert m["pct"] == 75 and m["tone"] == "ok" and m["total_gb"] == 8
    assert health.memory(fake_proc(tmp_path / "x", used_gb=7.5))["tone"] == "bad"     # 94%
    monkeypatch.setattr(health.os, "cpu_count", lambda: 2)
    assert health.load(fake_proc(tmp_path / "y", load5=1.6))["tone"] == "warn"         # 80% of two cores
    assert health.tone(85, 80, 90) == "warn" and health.tone(91, 80, 90) == "bad" and health.tone(10, 80, 90) == "ok"

def test_backups_and_problems(tmp_path):
    javid, server = tmp_path / "javid", tmp_path / "server.json"
    javid.mkdir()
    assert [b["tone"] for b in health.backups(javid, server)] == ["warn", "warn"]       # not set up yet
    server.write_text(json.dumps({"at": datetime.now().isoformat(), "ok": True}))
    (javid / "last.json").write_text(json.dumps({"at": (datetime.now() - timedelta(hours=40)).isoformat(), "ok": True}))
    b = health.backups(javid, server)
    assert b[0]["tone"] == "ok" and b[1]["tone"] == "bad" and "40" in b[1]["text"]
    server.write_text(json.dumps({"at": datetime.now().isoformat(), "ok": False, "error": "no network"}))
    assert "no network" in health.backups(javid, server)[0]["text"]
    assert health.problems(javid) == []
    (javid / "watch-state.json").write_text(json.dumps({"disk": {"since": 1794049677, "sent": 1794049677}}))
    assert health.problems(javid)[0]["text"] == "دیسک تقریباً پر است"

def test_only_the_permanent_account(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USER", "admin-for-test")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    monkeypatch.setenv("ACCESS_DB_PATH", str(tmp_path / "access.db"))
    import access
    access = importlib.reload(access); h = importlib.reload(health)
    monkeypatch.setattr(h, "certificates", lambda hosts=None: [])
    monkeypatch.setattr(h, "updates", lambda: None)
    app = FastAPI(); app.include_router(access.router); app.include_router(h.router)
    assert TestClient(app).get("/access/health").status_code == 403
    admin = TestClient(app)
    assert admin.post("/access/login", json={"username": "admin-for-test", "password": "admin-secret"}).status_code == 200
    d = admin.get("/access/health").json()
    assert d["overall"]["tone"] in ("ok", "warn", "bad") and "memory" in d and "services" in d and "backups" in d
    monkeypatch.delenv("ADMIN_PASSWORD")
    importlib.reload(access); importlib.reload(health)
