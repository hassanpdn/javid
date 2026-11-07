"""The whole server's nightly backup (deploy/server/server-backup.py): the order of a night's steps, its settings
file, what it writes when it works or fails, and the watcher reading that."""
import importlib.util, json, os
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "deploy"

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

sb = load(ROOT / "server" / "server-backup.py", "server_backup")
watch = load(ROOT / "watch.py", "watch")

def conf_dir(tmp_path):
    conf = tmp_path / "conf"
    (conf / "before.d").mkdir(parents=True)
    for name, mode in (("20-postgres", 0o755), ("10-files", 0o755), ("notes.txt", 0o644)):
        f = conf / "before.d" / name
        f.write_text("#!/bin/sh\ntrue\n")
        os.chmod(f, mode)
    (conf / "excludes").write_text("**/.venv\n")
    (conf / "env").write_text('# settings\nRESTIC_REPOSITORY=rclone:gdrive:server-backups\nRESTIC_PASSWORD_FILE="/etc/server-backup/restic-password"\n\nBACKUP_PATHS=/opt /etc\n')
    return conf

def test_a_nights_steps_in_order(tmp_path):
    conf = conf_dir(tmp_path)
    env = sb.read_env(conf / "env")
    assert env["RESTIC_PASSWORD_FILE"] == "/etc/server-backup/restic-password" and env["BACKUP_PATHS"] == "/opt /etc"
    friday = sb.steps(conf, env, datetime(2026, 11, 6))
    names = [s[0].split("/")[-1] if "/" in s[0] else s[0] + " " + s[1] for s in friday]
    assert names == ["10-files", "20-postgres", "restic backup", "restic forget"]          # not the file that cannot run
    assert friday[2][-2:] == ["/opt", "/etc"] and "--exclude-file" in friday[2]
    assert "--prune" in friday[3] and "--keep-daily" in friday[3]
    sunday = sb.steps(conf, env, datetime(2026, 11, 8))
    assert sunday[-1][:2] == ["restic", "check"]                                          # the weekly read-back

def test_failure_is_written_and_mailed(tmp_path, monkeypatch):
    conf = conf_dir(tmp_path)
    monkeypatch.setattr(sb, "CONF", conf)
    monkeypatch.setattr(sb, "STATUS", tmp_path / "state" / "last.json")
    sent = []
    monkeypatch.setattr(sb, "alert", lambda env, text: sent.append(text) or True)
    def fake_run(args, env, timeout):
        if args[:2] == ["restic", "backup"]:
            raise RuntimeError("restic backup: Fatal: unable to open repository")
        return "[]"
    monkeypatch.setattr(sb, "run", fake_run)
    try:
        sb.main([])
        assert False, "a failed night must exit with an error"
    except SystemExit as e:
        assert e.code == 1
    last = json.loads((tmp_path / "state" / "last.json").read_text())
    assert last["ok"] is False and "unable to open repository" in last["error"]
    assert oct((tmp_path / "state" / "last.json").stat().st_mode & 0o777) == "0o644"
    assert sent and "unable to open repository" in sent[0]

def test_success_is_written(tmp_path, monkeypatch):
    conf = conf_dir(tmp_path)
    monkeypatch.setattr(sb, "CONF", conf)
    monkeypatch.setattr(sb, "STATUS", tmp_path / "last.json")
    ran = []
    monkeypatch.setattr(sb, "run", lambda args, env, timeout: ran.append(args) or ('[{"short_id": "4f2a9c1d"}]' if args[1:2] == ["snapshots"] else ""))
    sb.main([])
    last = json.loads((tmp_path / "last.json").read_text())
    assert last["ok"] is True and last["snapshot"] == "4f2a9c1d"
    assert ran[-1][:2] == ["restic", "snapshots"]

def test_the_watcher_reads_it(tmp_path):
    f = tmp_path / "last.json"
    assert watch.check_server_backup(f) is None                       # not set up yet: nothing to say
    f.write_text(json.dumps({"at": datetime.now().isoformat(), "ok": False, "error": "no network"}))
    assert "no network" in watch.check_server_backup(f)
    f.write_text(json.dumps({"at": (datetime.now() - timedelta(hours=40)).isoformat(), "ok": True}))
    assert "40 ساعت" in watch.check_server_backup(f)
    f.write_text(json.dumps({"at": datetime.now().isoformat(), "ok": True}))
    assert watch.check_server_backup(f) is None
