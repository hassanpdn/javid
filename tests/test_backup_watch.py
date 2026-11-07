"""The live server's nightly backup (deploy/backup.py) and its watcher (deploy/watch.py): what goes into a backup and
that its databases are whole, old backups going away, and alerts sent once, reminded, and closed."""
import importlib.util, json, os, sqlite3, tarfile, time
from datetime import datetime, timedelta
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"

def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

backup, watch = load("backup"), load("watch")

def make_app(root):
    app = root / "app"
    (app / "hotel_files").mkdir(parents=True)
    with sqlite3.connect(app / "access.db") as c:
        c.execute("CREATE TABLE people (name TEXT)")
        c.executemany("INSERT INTO people VALUES (?)", [("سارا",), ("رضا",)])
    (app / "lodge.json").write_text('{"name": "x"}')
    (app / ".env").write_text("ADMIN_PASSWORD=secret\n")
    (app / "hotel_files" / "receipt.jpg").write_bytes(b"\xff\xd8 photo")
    return app

def test_backup_holds_what_cannot_be_rebuilt(tmp_path):
    app, dest = make_app(tmp_path), tmp_path / "backups"
    writer = sqlite3.connect(app / "access.db")              # the app is writing while the backup runs
    writer.execute("INSERT INTO people VALUES ('در حال نوشتن')")
    out = backup.backup(app, dest, datetime(2026, 11, 7, 3, 30))
    writer.rollback(); writer.close()
    assert out.name == "javid-2026-11-07_0330.tar.gz" and oct(out.stat().st_mode & 0o777) == "0o600"
    with tarfile.open(out) as t:
        names = set(t.getnames())
        t.extractall(tmp_path / "x", filter="data")
    top = "javid-2026-11-07_0330"
    assert {f"{top}/access.db", f"{top}/lodge.json", f"{top}/.env", f"{top}/hotel_files/receipt.jpg"} <= names
    with sqlite3.connect(tmp_path / "x" / top / "access.db") as c:
        assert sorted(r[0] for r in c.execute("SELECT name FROM people")) == ["رضا", "سارا"]   # whole, without the unfinished write
    assert not list(dest.glob("*.part")) and not list(dest.glob(".work-*"))

def test_a_broken_database_fails_the_backup(tmp_path):
    app = make_app(tmp_path)
    (app / "broken.db").write_bytes(b"not a database at all" * 100)
    try:
        backup.backup(app, tmp_path / "backups")
        assert False, "a broken database must fail the backup"
    except Exception:
        pass
    assert not list((tmp_path / "backups").glob("javid-*.tar.gz"))

def test_old_backups_go(tmp_path):
    now = datetime(2026, 11, 20, 4, 0)
    for days in (1, 13, 15, 30):
        (tmp_path / f"javid-{(now - timedelta(days=days)).strftime(backup.STAMP)}.tar.gz").write_bytes(b"x")
    (tmp_path / "javid-notes.tar.gz").write_bytes(b"x")       # a name that is not a backup's is left alone
    gone = backup.prune(tmp_path, 14, now)
    assert len(gone) == 2 and len(list(tmp_path.glob("javid-*.tar.gz"))) == 3

def test_the_backup_check(tmp_path):
    assert "هنوز" in watch.check_backup(tmp_path)
    (tmp_path / "last.json").write_text(json.dumps({"at": datetime.now().isoformat(), "ok": False, "error": "disk full"}))
    assert "disk full" in watch.check_backup(tmp_path)
    (tmp_path / "last.json").write_text(json.dumps({"at": datetime.now().isoformat(), "ok": True}))
    assert watch.check_backup(tmp_path) is None
    old = (datetime.now() - timedelta(hours=30)).isoformat()
    (tmp_path / "last.json").write_text(json.dumps({"at": old, "ok": True}))
    assert "30 ساعت" in watch.check_backup(tmp_path)

def test_alerts_once_then_reminded_then_closed():
    t = 1_000_000
    msgs, state = watch.decide({"app": "down", "disk": None}, {}, t)
    assert len(msgs) == 1 and msgs[0].startswith("هشدار")
    msgs, state = watch.decide({"app": "down"}, state, t + 300)
    assert msgs == []                                         # not again every five minutes
    msgs, state = watch.decide({"app": "down"}, state, t + watch.REMIND)
    assert len(msgs) == 1 and "هنوز" in msgs[0]
    msgs, state = watch.decide({"app": None}, state, t + watch.REMIND + 300)
    assert len(msgs) == 1 and msgs[0].startswith("درست شد") and "app" not in state

def test_server_errors_at_most_hourly_and_never_closed():
    t = 2_000_000
    msgs, state = watch.decide({"errors": "3 errors"}, {}, t)
    assert len(msgs) == 1
    assert watch.decide({"errors": "2 errors"}, state, t + 600)[0] == []
    assert len(watch.decide({"errors": "1 error"}, state, t + watch.EVENT_GAP)[0]) == 1
    msgs, state = watch.decide({"errors": None}, state, t + 900)
    assert msgs == [] and "errors" not in state              # no «درست شد» for something that happened

def test_error_lines():
    assert watch.ERROR_LINE.search('INFO:     127.0.0.1:1 - "GET /lang/today HTTP/1.1" 500 Internal Server Error')
    assert watch.ERROR_LINE.search("ERROR:    Exception in ASGI application")
    assert not watch.ERROR_LINE.search('INFO:     127.0.0.1:1 - "GET /lang/today HTTP/1.1" 200 OK')
