"""Watches the live server and tells Hassan when something is wrong (run every 5 minutes by the javid-watch timer).

Checks: the app answers on the server itself, the site answers through nginx and HTTPS, the disk has room, last
night's backups worked (javid's own, deploy/backup.py, and the whole server's to Google Drive,
deploy/server/server-backup.py), the HTTPS certificate has more than 14 days left, and the app's log of the
last minutes has no server errors (500s or crashes).

Each problem is sent once when it starts, again every 6 hours while it lasts, and «درست شد» once when it is gone. A run
of 500s is sent at most once an hour. What was sent is kept in watch-state.json in the backup folder.

Alerts go to Bale (a bot in the Bale messenger: works from a server in Iran and reaches the phone) and/or email,
whichever is set in .env (deploy/README.md says how):
    BALE_TOKEN, BALE_CHAT_ID                    the bot's token and the chat it writes to
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL

    python deploy/watch.py           # what the timer runs
    python deploy/watch.py --test    # sends a test message, to check the settings
    python deploy/watch.py --outside https://agent.pudineh.com   # from outside (the GitHub workflow): only whether it answers
"""
import json, os, re, shutil, smtplib, socket, ssl, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

APP = Path(os.getenv("JAVID_DIR", "/opt/javid"))
STATE_DIR = Path(os.getenv("BACKUP_DIR", "/var/backups/javid"))
PUBLIC = os.getenv("PUBLIC_URL", "https://agent.pudineh.com")
REMIND = 6 * 3600          # a problem still there is sent again after this long
EVENT_GAP = 3600           # server errors are sent at most this often
BACKUP_AGE = 26 * 3600     # the nightly backup is late after this long
DISK_FREE = 0.10           # alert under 10% free

def answers(url, timeout=15):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def check_app():
    ok, why = answers("http://127.0.0.1:8000/")
    return None if ok else f"برنامه روی خود سرور جواب نمی‌دهد ({why}). ببینید: journalctl -u javid -n 50"

def check_public():
    ok, why = answers(PUBLIC + "/")
    return None if ok else f"سایت {PUBLIC} از راه nginx جواب نمی‌دهد ({why})."

def check_disk(path=APP):
    u = shutil.disk_usage(path)
    free = u.free / u.total
    return None if free >= DISK_FREE else f"دیسک سرور تقریباً پر است: {round(100 * free)} درصد خالی ({u.free // 2**30} گیگابایت)."

def check_backup(state_dir=STATE_DIR, now=None):
    now = now or time.time()
    f = state_dir / "last.json"
    if not f.exists():
        return "هنوز هیچ پشتیبانی گرفته نشده است (javid-backup.timer را ببینید)."
    last = json.loads(f.read_text())
    if not last.get("ok"):
        return f"پشتیبان‌گیری دیشب انجام نشد: {last.get('error', '')}"
    age = now - datetime.fromisoformat(last["at"]).timestamp()
    return None if age <= BACKUP_AGE else f"آخرین پشتیبان {round(age / 3600)} ساعت پیش گرفته شده است."

SERVER_STATUS = Path(os.getenv("SERVER_BACKUP_STATUS", "/var/lib/server-backup/last.json"))

def check_server_backup(path=None, now=None):
    """The whole server's backup to Google Drive. Before it is set up (no status file yet) there is nothing to check."""
    path, now = path or SERVER_STATUS, now or time.time()
    if not path.exists():
        return None
    last = json.loads(path.read_text())
    if not last.get("ok"):
        return f"پشتیبان سرور در گوگل درایو دیشب گرفته نشد: {last.get('error', '')}"
    age = now - datetime.fromisoformat(last["at"]).timestamp()
    return None if age <= BACKUP_AGE else f"آخرین پشتیبان سرور در گوگل درایو {round(age / 3600)} ساعت پیش گرفته شده است."

def check_cert(host=None, now=None):
    host = host or PUBLIC.split("//")[-1].split("/")[0]
    try:
        with socket.create_connection((host, 443), timeout=15) as s, ssl.create_default_context().wrap_socket(s, server_hostname=host) as t:
            end = ssl.cert_time_to_seconds(t.getpeercert()["notAfter"])
    except Exception as e:
        return f"گواهی HTTPS سایت خوانده نشد ({type(e).__name__}: {e})."
    days = (end - (now or time.time())) / 86400
    return None if days > 14 else f"گواهی HTTPS سایت {round(days)} روز دیگر تمام می‌شود (certbot renew)."

ERROR_LINE = re.compile(r'" 5\d\d |Exception in ASGI application|Traceback')

def check_errors():
    """Server errors in the app's log of the last 6 minutes (the timer runs every 5)."""
    try:
        out = subprocess.run(["journalctl", "-u", "javid", "--since", "-6min", "--no-pager", "-o", "cat"], capture_output=True, text=True, timeout=30).stdout
    except Exception as e:
        return f"گزارش برنامه خوانده نشد ({e})."
    bad = [l for l in out.splitlines() if ERROR_LINE.search(l)]
    return None if not bad else f"{len(bad)} خطای سرور در چند دقیقه‌ی گذشته. اولی: {bad[0].strip()[:200]}"

# key: (check, kind). state: a problem that lasts and then goes away; event: something that happened
NAMES = {"app": "برنامه روی سرور", "public": "سایت", "disk": "دیسک", "backup": "پشتیبان‌گیری", "server_backup": "پشتیبان سرور در گوگل درایو", "cert": "گواهی HTTPS", "errors": "خطای سرور"}
CHECKS = {"app": (check_app, "state"), "public": (check_public, "state"), "disk": (check_disk, "state"),
          "backup": (check_backup, "state"), "server_backup": (check_server_backup, "state"), "cert": (check_cert, "state"), "errors": (check_errors, "event")}

def decide(found, state, now):
    """found: {key: problem text or None}. Returns (messages to send, new state)."""
    out, new = [], dict(state)
    for key, problem in found.items():
        kind = CHECKS.get(key, (None, "state"))[1]
        was = state.get(key)
        if problem:
            if not was:
                out.append("هشدار: " + problem)
                new[key] = {"since": now, "sent": now}
            elif now - was["sent"] >= (EVENT_GAP if kind == "event" else REMIND):
                out.append(("هشدار: " if kind == "event" else f"هشدار، هنوز پس از {round((now - was['since']) / 3600)} ساعت: ") + problem)
                new[key] = {**was, "sent": now}
        elif was:
            new.pop(key)
            if kind == "state":
                out.append(f"درست شد: {NAMES.get(key, key)}، پس از {max(1, round((now - was['since']) / 60))} دقیقه.")
    return out, new

def send(text):
    """To every channel set in .env. Returns how many took it."""
    sent, where = 0, f"javid · {socket.gethostname()} · {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M')}"
    token, chat = os.getenv("BALE_TOKEN"), os.getenv("BALE_CHAT_ID")
    if token and chat:
        body = json.dumps({"chat_id": chat, "text": f"{text}\n\n{where}"}).encode()
        req = urllib.request.Request(f"https://tapi.bale.ai/bot{token}/sendMessage", body, {"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=20).read(); sent += 1
        except Exception as e:
            print(f"bale: {e}", file=sys.stderr)
    host, to = os.getenv("SMTP_HOST"), os.getenv("ALERT_EMAIL")
    if host and to:
        m = EmailMessage()
        m["Subject"] = "agent.pudineh.com: " + text.splitlines()[0][:80]
        m["From"], m["To"] = os.getenv("SMTP_USER") or to, to
        m.set_content(f"{text}\n\n{where}")
        port = int(os.getenv("SMTP_PORT", "465"))
        try:
            with (smtplib.SMTP_SSL(host, port, timeout=30) if port == 465 else smtplib.SMTP(host, port, timeout=30)) as s:
                if port != 465:
                    s.starttls()
                if os.getenv("SMTP_USER"):
                    s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
                s.send_message(m); sent += 1
        except Exception as e:
            print(f"email: {e}", file=sys.stderr)
    return sent

def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(APP / ".env")
    except ImportError:
        pass

def main(args):
    load_env()
    if args[:1] == ["--test"]:
        n = send("پیام آزمایشی از نگهبان سرور: هشدارها به این‌جا می‌رسند.")
        print(f"sent to {n} channel(s)")
        sys.exit(0 if n else 1)
    if args[:1] == ["--outside"]:                     # the GitHub workflow: only whether the site answers
        ok, why = answers(args[1].rstrip("/") + "/", timeout=30)
        print("up" if ok else f"down: {why}")
        sys.exit(0 if ok else 1)
    state_file = STATE_DIR / "watch-state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    found = {key: check() for key, (check, _) in CHECKS.items()}
    messages, state = decide(found, state, time.time())
    for m in messages:
        print(m)
        send(m)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state))

if __name__ == "__main__":
    main(sys.argv[1:])
