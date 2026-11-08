"""«سلامت سرور» on the assistants page, for the permanent account only (GET /access/health): how the server is doing
right now, in plain words, each part green, yellow or red.

The app runs as the javid user, not root, so this reads only what anyone on the server may read: /proc for the load,
memory and uptime, the disk's free space, «systemctl is-active» for the services, the backups' status files (javid's in
/var/backups/javid, the whole server's in /var/lib/server-backup), the watcher's open problems, the HTTPS certificates
by connecting to each site, the waiting updates (Ubuntu's apt-check) and the last SSH logins (last). What is slow to
find out (updates, certificates) is kept for ten minutes. Nothing here changes anything on the server.

HEALTH_SERVICES and HEALTH_HOSTS (spaces between) say which services and which sites to look at.
"""
import json, os, re, shutil, socket, ssl, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request
import access
from jalali import to_jalali, MONTHS

router = APIRouter(prefix="/access")
SERVICES = os.getenv("HEALTH_SERVICES", "javid nginx named").split()   # PostgreSQL left with alefbaft (2026-11-08)
HOSTS = os.getenv("HEALTH_HOSTS", "agent.pudineh.com pudineh.com eco.pudineh.com hotel.pudineh.com").split()
PROC = Path(os.getenv("HEALTH_PROC", "/proc"))
JAVID_BACKUP = Path(os.getenv("BACKUP_DIR", "/var/backups/javid"))
SERVER_BACKUP = Path(os.getenv("SERVER_BACKUP_STATUS", "/var/lib/server-backup/last.json"))
SERVICE_NAMES = {"javid": "دستیارها (javid)", "nginx": "وب‌سرور (nginx)", "postgresql": "پایگاه داده (PostgreSQL)", "named": "DNS (BIND)"}
_slow = {}   # key -> (when, value)

def jtext(dt):
    """2026-11-07 17:30 -> «16 آبان 1405، ساعت 17:30» (the page turns the digits Persian)."""
    y, m, d = to_jalali(dt.date())
    return f"{d} {MONTHS[m - 1]} {y}، ساعت {dt:%H:%M}"

def tone(pct, warn, bad):
    return "bad" if pct >= bad else "warn" if pct >= warn else "ok"

def uptime(proc=PROC):
    secs = float((proc / "uptime").read_text().split()[0])
    days, hours = int(secs // 86400), int(secs % 86400 // 3600)
    reboot = Path("/var/run/reboot-required").exists()
    return {"days": days, "hours": hours, "reboot": reboot, "tone": "warn" if reboot else "ok",
            "text": (f"{days} روز و {hours} ساعت" if days else f"{hours} ساعت" if hours else "کمتر از یک ساعت") + " است که روشن است",
            "note": "پس از به‌روزرسانی‌ها، یک بار راه‌اندازی دوباره لازم است." if reboot else ""}

def memory(proc=PROC):
    info = {}
    for line in (proc / "meminfo").read_text().splitlines():
        k, v = line.split(":", 1)
        info[k] = int(v.split()[0]) * 1024
    total, free = info["MemTotal"], info.get("MemAvailable", info.get("MemFree", 0))
    pct = round(100 * (total - free) / total)
    return {"pct": pct, "used_gb": round((total - free) / 2**30, 1), "total_gb": round(total / 2**30, 1), "tone": tone(pct, 80, 92)}

def load(proc=PROC):
    one, five, _ = (float(x) for x in (proc / "loadavg").read_text().split()[:3])
    cpus = os.cpu_count() or 1
    pct = min(100, round(100 * five / cpus))
    return {"pct": pct, "cpus": cpus, "load": five, "tone": tone(pct, 70, 95)}

def disk(path="/"):
    u = shutil.disk_usage(path)
    pct = round(100 * u.used / u.total)
    return {"pct": pct, "free_gb": round(u.free / 2**30), "total_gb": round(u.total / 2**30), "tone": tone(pct, 80, 90)}

def services(names=SERVICES):
    out = []
    for name in names:
        try:
            state = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
        except Exception:
            state = "unknown"
        out.append({"name": name, "label": SERVICE_NAMES.get(name, name), "state": state,
                    "tone": "ok" if state == "active" else "warn" if state in ("activating", "reloading", "unknown") else "bad",
                    "text": {"active": "در حال کار", "inactive": "خاموش", "failed": "از کار افتاده", "activating": "در حال روشن شدن"}.get(state, "نامعلوم")})
    try:
        failed = subprocess.run(["systemctl", "list-units", "--failed", "--no-legend", "--plain"], capture_output=True, text=True, timeout=10).stdout
        failed = [l.split()[0] for l in failed.splitlines() if l.strip()]
    except Exception:
        failed = []
    return out, failed

def _status(path, max_hours=26):
    """A backup's last.json: (tone, text, when)."""
    try:
        last = json.loads(path.read_text())
    except (OSError, ValueError):
        return "warn", "هنوز گزارشی نیست", None
    at = datetime.fromisoformat(last["at"])
    hours = (datetime.now() - at).total_seconds() / 3600
    if not last.get("ok"):
        return "bad", "انجام نشد: " + str(last.get("error", ""))[:160], last["at"]
    if hours > max_hours:
        return "bad", f"آخرین بار {round(hours)} ساعت پیش", last["at"]
    return "ok", f"{round(hours)} ساعت پیش" if hours >= 1 else "کمتر از یک ساعت پیش", last["at"]

def backups(javid=JAVID_BACKUP, server=SERVER_BACKUP):
    out = []
    for label, path in (("پشتیبان کل سرور در گوگل درایو", server), ("پشتیبان پایگاه‌های داده‌ی دستیارها", javid / "last.json")):
        t, text, at = _status(path)
        out.append({"label": label, "tone": t, "text": text, "at": at})
    return out

def _cached(key, seconds, make):
    hit = _slow.get(key)
    if hit and time.time() - hit[0] < seconds:
        return hit[1]
    value = make()
    _slow[key] = (time.time(), value)
    return value

def certificates(hosts=HOSTS):
    def one(host):
        try:
            with socket.create_connection((host, 443), timeout=5) as s, ssl.create_default_context().wrap_socket(s, server_hostname=host) as t:
                days = round((ssl.cert_time_to_seconds(t.getpeercert()["notAfter"]) - time.time()) / 86400)
            return {"host": host, "days": days, "tone": tone(-days, -21, -7), "text": f"{days} روز مانده"}
        except Exception as e:
            return {"host": host, "days": None, "tone": "bad", "text": "پاسخ نداد" if isinstance(e, OSError) else "خوانده نشد"}
    def all_at_once():                         # side by side, so a site that does not answer costs 5 seconds, not 5 each
        with ThreadPoolExecutor(max_workers=len(hosts) or 1) as pool:
            return list(pool.map(one, hosts))
    return _cached("certs", 600, all_at_once)

def updates():
    """Ubuntu's own count of waiting updates and how many of them are security fixes."""
    def find():
        tool = "/usr/lib/update-notifier/apt-check"
        if not os.path.exists(tool):
            return None
        try:
            p = subprocess.run([tool], capture_output=True, text=True, timeout=60)
            m = re.match(r"(\d+);(\d+)", (p.stderr or p.stdout).strip())
        except Exception:
            return None
        if not m:
            return None
        n, sec = int(m.group(1)), int(m.group(2))
        return {"all": n, "security": sec, "tone": "bad" if sec >= 10 else "warn" if sec or n > 50 else "ok"}
    return _cached("updates", 600, find)

def logins(n=6):
    """The last SSH logins to the server (who, from where, when)."""
    try:
        out = subprocess.run(["last", "-n", str(n + 4), "-w", "-i", "--time-format", "iso"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0] in ("reboot", "wtmp", "") or not parts[1].startswith("pts"):
            continue
        try:
            at = jtext(datetime.fromisoformat(parts[3][:19]))
        except ValueError:
            at = parts[3]
        rows.append({"user": parts[0], "ip": parts[2], "at": at, "now": "still" in line})
        if len(rows) == n:
            break
    return rows

def problems(state_dir=JAVID_BACKUP):
    """What the watcher (deploy/watch.py) is alerting about at this moment."""
    try:
        state = json.loads((state_dir / "watch-state.json").read_text())
    except (OSError, ValueError):
        return []
    names = {"app": "دستیارها روی سرور جواب نمی‌دهند", "public": "سایت از بیرون جواب نمی‌دهد", "disk": "دیسک تقریباً پر است",
             "backup": "پشتیبان‌گیری دستیارها انجام نشد", "server_backup": "پشتیبان کل سرور انجام نشد", "cert": "گواهی HTTPS رو به پایان است",
             "errors": "خطای سرور در دستیارها"}
    return [{"key": k, "text": names.get(k, k), "since": jtext(datetime.fromtimestamp(v["since"]))} for k, v in state.items()]

def snapshot():
    def safe(fn, *a):
        try:
            return fn(*a)
        except Exception:
            return None
    svc, failed = services()
    parts = {"uptime": safe(uptime), "memory": safe(memory), "load": safe(load), "disk": safe(disk), "services": svc, "failed": failed,
             "backups": backups(), "certificates": certificates(), "updates": safe(updates), "logins": logins(), "problems": problems()}
    tones = [p["tone"] for p in (parts["memory"], parts["load"], parts["disk"], parts["uptime"], parts["updates"]) if p]
    tones += [s["tone"] for s in svc] + [b["tone"] for b in parts["backups"]] + [c["tone"] for c in parts["certificates"]]
    tones += ["bad"] * (len(failed) + len(parts["problems"]))
    bad, warn = tones.count("bad"), tones.count("warn")
    parts["overall"] = {"tone": "bad" if bad else "warn" if warn else "ok", "bad": bad, "warn": warn,
                        "text": f"{bad} مورد نیاز به رسیدگی دارد" if bad else f"{warn} مورد را ببینید" if warn else "همه‌چیز خوب است"}
    parts["at"] = datetime.now().strftime("%H:%M")
    return parts

@router.get("/health")
def health(request: Request):
    access._admin(request)
    return snapshot()
