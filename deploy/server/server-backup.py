#!/usr/bin/env python3
"""The whole server's nightly backup, for every project on it (javid, the portfolio, alefbaft, ...), run by root from
the server-backup timer every night at 04:15 Tehran time. Installed as /usr/local/sbin/server-backup, a copy owned by
root (deploy/server/README.md), so code pushed to GitHub never runs as root by itself.

1. Runs every executable file in /etc/server-backup/before.d/ in name order: each makes a safe copy of something that
   cannot be copied while in use, e.g. «postgres» dumps every PostgreSQL database into /var/backups/postgres/. javid
   makes its own copies at 03:30 (deploy/backup.py) into /var/backups/javid/. A step that fails fails the backup.
2. restic backs up BACKUP_PATHS (default /opt /var/www /etc /home /root /var/backups), without what /etc/server-backup/
   excludes lists (.venv, node_modules, caches), to RESTIC_REPOSITORY: Google Drive through rclone
   («rclone:gdrive:server-backups»). restic encrypts everything before it leaves, and after the first night sends only
   what changed.
3. Keeps 14 daily, 8 weekly and 12 monthly snapshots and deletes the rest. On Sundays it also reads back a part of
   what is on Drive (restic check) to know the backups can be restored.
4. Writes /var/lib/server-backup/last.json (readable by everyone, no secrets in it); javid's watcher (deploy/watch.py)
   alerts when it says failed or is more than a day old. A failure also sends an email itself.

Settings: /etc/server-backup/env (root only), KEY=VALUE lines: RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE, and SMTP_HOST,
SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL for the email. Only the standard library: it runs with the system's
python3.
"""
import json, os, smtplib, socket, subprocess, sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

CONF = Path(os.getenv("SERVER_BACKUP_CONF", "/etc/server-backup"))
STATUS = Path(os.getenv("SERVER_BACKUP_STATUS", "/var/lib/server-backup/last.json"))
PATHS = "/opt /var/www /etc /home /root /var/backups"
KEEP = ["--keep-daily", "14", "--keep-weekly", "8", "--keep-monthly", "12"]

def read_env(path):
    """KEY=VALUE lines, # comments and empty lines skipped, quotes around a value removed."""
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("'\"")
    return out

def run(args, env, timeout):
    """Runs one step; its output goes to the journal (journalctl -u server-backup). Raises with its last lines."""
    p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout)
    print(p.stdout[-4000:], end="")
    if p.returncode != 0:
        print(p.stderr[-4000:], end="", file=sys.stderr)
        tail = (p.stderr or p.stdout).strip().splitlines()[-3:]
        raise RuntimeError(f"{Path(args[0]).name} {' '.join(args[1:3])}: " + " / ".join(tail))
    return p.stdout

def steps(conf, env, today):
    """The commands of one night, in order: the before.d steps, the backup, the clean-up, the Sunday check."""
    out = [[str(f)] for f in sorted((conf / "before.d").glob("*")) if f.is_file() and os.access(f, os.X_OK)]
    paths = env.get("BACKUP_PATHS", PATHS).split()
    out.append(["restic", "backup", "--exclude-file", str(conf / "excludes"), "--exclude-caches", "--tag", "nightly", *paths])
    out.append(["restic", "forget", *KEEP, "--prune"])
    if today.weekday() == 6:                       # Sunday: read back 5% of the data on Drive
        out.append(["restic", "check", "--read-data-subset=5%"])
    return out

def alert(env, text):
    host, to = env.get("SMTP_HOST"), env.get("ALERT_EMAIL")
    if not (host and to):
        return False
    m = EmailMessage()
    m["Subject"] = f"{socket.gethostname()}: " + text.splitlines()[0][:90]
    m["From"], m["To"] = env.get("SMTP_USER") or to, to
    m.set_content(text)
    port = int(env.get("SMTP_PORT", "465"))
    with (smtplib.SMTP_SSL(host, port, timeout=30) if port == 465 else smtplib.SMTP(host, port, timeout=30)) as s:
        if port != 465:
            s.starttls()
        if env.get("SMTP_USER"):
            s.login(env["SMTP_USER"], env.get("SMTP_PASSWORD", ""))
        s.send_message(m)
    return True

def write_status(**status):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), **status}, ensure_ascii=False))
    os.chmod(STATUS, 0o644)

def main(args):
    conf = read_env(CONF / "env")
    env = {**os.environ, **conf}
    for need in ("RESTIC_REPOSITORY", "RESTIC_PASSWORD_FILE"):
        if not env.get(need):
            sys.exit(f"{need} is missing in {CONF / 'env'}")
    if args[:1] == ["--test-alert"]:
        sys.exit(0 if alert(env, "پیام آزمایشی از پشتیبان‌گیری سرور: اگر شبی انجام نشود، این‌جا خبر می‌دهد.") else 1)
    started = datetime.now()
    try:
        for step in steps(CONF, env, started):
            run(step, env, timeout=6 * 3600)
        snap = json.loads(run(["restic", "snapshots", "--latest", "1", "--json"], env, 600) or "[]")
        write_status(ok=True, seconds=round((datetime.now() - started).total_seconds()), snapshot=(snap[-1]["short_id"] if snap else None))
        print("server-backup: done")
    except Exception as e:
        write_status(ok=False, error=f"{type(e).__name__}: {e}")
        try:
            alert(env, f"پشتیبان‌گیری امشب سرور انجام نشد.\n\n{e}\n\njournalctl -u server-backup -n 80")
        except Exception as mail_error:
            print(f"email: {mail_error}", file=sys.stderr)
        print(f"server-backup failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
