"""Nightly backup of the live server (run by the javid-backup timer, see deploy/README.md).

What cannot be rebuilt: the accounts given to people (access.db), the hotel's and the eco-lodge's guests with their
accounts, bookings and reviews (hotel.db, lodge.db), their photos and receipts (hotel_files/, lodge_files/), the
fabric shop's Excel files, every assistant's settings (*.json) and the server's .env. The other databases are demo data
rebuilt every day, but they are small and copied too, so one backup is the whole state of a day. The document search
(db/) is rebuilt by ingest.py and is left out.

Each database is copied with SQLite's own backup (safe while the app is writing to it) and then checked with
«PRAGMA integrity_check» before it counts. Everything goes into one file, /var/backups/javid/javid-<date>.tar.gz,
readable only by the javid user (it holds .env and password hashes). Files older than BACKUP_KEEP_DAYS (14) are deleted.
With BACKUP_REMOTE set (an rsync destination over SSH, e.g. backup@other-server:/backups/javid/), the file is also
copied there; a backup only on the same disk is lost with that disk.

last.json in the backup folder says when the last backup ran and whether it worked; deploy/watch.py alerts when it
failed or is older than a day. Exit code 1 on failure, so systemd shows it too.

    python deploy/backup.py          # what the timer runs
"""
import json, os, shutil, sqlite3, subprocess, sys, tarfile, tempfile
from datetime import datetime, timedelta
from pathlib import Path

APP = Path(os.getenv("JAVID_DIR", "/opt/javid"))
DEST = Path(os.getenv("BACKUP_DIR", "/var/backups/javid"))
KEEP_DAYS = int(os.getenv("BACKUP_KEEP_DAYS", "14"))
FOLDERS = ("hotel_files", "lodge_files", "fabric_files")       # uploaded photos and receipts, the fabric shop's Excel files
STAMP = "%Y-%m-%d_%H%M"

def copy_db(src, dst):
    """A consistent copy of a database in use, checked before it counts."""
    with sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=30) as a, sqlite3.connect(dst) as b:
        a.backup(b)
    with sqlite3.connect(dst) as b:
        result = b.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"{src.name}: integrity_check says {result}")

def backup(app=APP, dest=DEST, now=None):
    """Makes javid-<date>.tar.gz in dest and returns its path."""
    now = now or datetime.now()
    dest.mkdir(parents=True, exist_ok=True)
    os.chmod(dest, 0o700)
    with tempfile.TemporaryDirectory(dir=dest, prefix=".work-") as work:
        root = Path(work) / "javid"
        root.mkdir()
        dbs = sorted(app.glob("*.db"))
        if not dbs:
            raise RuntimeError(f"no database found in {app}")
        for db in dbs:
            copy_db(db, root / db.name)
        for f in sorted(app.glob("*.json")) + [app / ".env"]:
            if f.is_file():
                shutil.copy2(f, root / f.name)
        for d in FOLDERS:
            if (app / d).is_dir():
                shutil.copytree(app / d, root / d)
        out = dest / f"javid-{now.strftime(STAMP)}.tar.gz"
        part = out.with_suffix(".part")
        with tarfile.open(part, "w:gz") as tar:
            tar.add(root, arcname=f"javid-{now.strftime(STAMP)}")
        os.chmod(part, 0o600)
        part.rename(out)                                        # a half-written file never looks like a backup
    return out

def prune(dest=DEST, keep_days=KEEP_DAYS, now=None):
    """Deletes backups older than keep_days, judged by the date in their name; returns what it deleted."""
    now = now or datetime.now()
    gone = []
    for f in dest.glob("javid-*.tar.gz"):
        try:
            made = datetime.strptime(f.name[len("javid-"):-len(".tar.gz")], STAMP)
        except ValueError:
            continue
        if now - made > timedelta(days=keep_days):
            f.unlink()
            gone.append(f.name)
    return gone

def offsite(path, remote):
    """Copies the backup to another machine over SSH (the javid user's key must be allowed there)."""
    subprocess.run(["rsync", "-a", "--partial", "-e", "ssh -o BatchMode=yes -o ConnectTimeout=30", str(path), remote], check=True, timeout=1800)

def write_status(dest, **status):
    (dest / "last.json").write_text(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), **status}, ensure_ascii=False))

def main():
    try:                                     # BACKUP_REMOTE and friends may be in the server's .env
        from dotenv import load_dotenv
        load_dotenv(APP / ".env")
    except ImportError:
        pass
    global DEST, KEEP_DAYS
    DEST = Path(os.getenv("BACKUP_DIR", str(DEST))); KEEP_DAYS = int(os.getenv("BACKUP_KEEP_DAYS", str(KEEP_DAYS)))
    try:
        out = backup(APP, DEST)
        gone = prune(DEST, KEEP_DAYS)
        remote = os.getenv("BACKUP_REMOTE", "").strip()
        if remote:
            offsite(out, remote)
        write_status(DEST, ok=True, file=out.name, size=out.stat().st_size, offsite=bool(remote))
        print(f"backup: {out} ({out.stat().st_size // 1024} KB)" + (f", copied to {remote}" if remote else "") + (f", deleted {len(gone)} old" if gone else ""))
    except Exception as e:
        DEST.mkdir(parents=True, exist_ok=True)
        write_status(DEST, ok=False, error=f"{type(e).__name__}: {e}")
        print(f"backup failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
