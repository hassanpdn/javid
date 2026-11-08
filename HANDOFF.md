# Handoff: everything needed to carry on without the people or tools that built it

Written on 2026-11-08 (1405/08/17), in case the tools or people that built this are no longer available. Read this first, then
`CLAUDE.md` (how to work in this repository, every rule), `ARCHITECTURE.md` (how the code is built and why),
`PRODUCTION.md` (what a real customer would need) and `deploy/README.md` (the server). Nothing below repeats those.

## Who and what

- Owner: Hassan (Pudineh, pudineh.com). Product and frontend developer (Vue), learning backend and servers. Writes
  Persian, wants answers in standard written Persian when he writes Persian, technical terms in Persian script.
- This repository (`hassanpdn/javid`): the demos of AI assistants for Iranian businesses, live at
  https://agent.pudineh.com behind a door (site password + per-assistant accounts). Nine assistants: school, fabric
  wholesaler, deed extraction, real estate, law office, dental clinic, hotel (+ public site hotel.pudineh.com),
  eco-lodge (+ public site eco.pudineh.com), language institute. All data is fake, rebuilt every day.
- The other real product on the same server: `hassanpdn/hamsayedar` («همسایه‌دار», building management, real data,
  https://hamsayedar.pudineh.com). It has its own `HANDOFF.md`.
- Also on the server, not built here: Hassan's portfolio (`hassanpdn/portfolio`, pudineh.com) and its admin
  (`hassanpdn/portfolio-admin`, admin.pudineh.com, run by pm2 as root). They deploy themselves through restricted SSH
  keys (`/opt/portfolio/deploy/autodeploy.sh`, `/opt/portfolio-admin/deploy/autodeploy.sh`).

## How we work (the habits that kept this working)

- Discuss a new feature's spec with Hassan before building; build one narrow thing at a time; small commits that say
  what and why; tests for what changed; look at every screen on desktop and at 360px.
- Server work: ONE command per message, explain it in one line, wait for its output before the next. Never ask him to
  paste a password, key or token; show it on his own screen only. He sometimes answers "done" without the output:
  put a check of the previous step at the start of the next command.
- Before deleting or changing anything on the server, look at it first (list, grep, show line numbers), then change
  exactly that, with a `.bak` copy, and check the result (`nginx -t`, `named-checkconf`, `visudo -c`) before reloading.
- In this repository a push to a `claude/` branch is a release: `.github/workflows/deploy.yml` merges it into `main`
  and the server updates itself (`deploy/javid-deploy.sh` → `deploy/after-update.sh`). A change to `seed.py` or
  `db.py` wipes the live demo data (fake, but people may be in the middle of a demo).

## The server

- `server.pudineh.com`, 89.45.89.72, Ubuntu 24.04 (kernel 6.8), 60 GB disk, BIOS boot. GRUB is installed on
  `/dev/disk/by-id/ata-QEMU_HARDDISK_QM00001` (the image once named the disk /dev/vda; on 2026-11-08 an upgrade left
  grub-pc half-configured because of that; fixed with debconf-set-selections and `dpkg --configure grub-pc`).
- Root login by SSH key only. The key named `alefbaft-server` in `/root/.ssh/authorized_keys` is Hassan's Mac (the
  name is historical; keep it). The two other keys there are the portfolio deploys.
- Users: `javid` (this app, `/opt/javid`), `hamsayedar` (`/opt/hamsayedar`), root runs pm2 (portfolio-admin).
- Services: `javid` (uvicorn 127.0.0.1:8000), `hamsayedar` (127.0.0.1:8010), `nginx`, `named` (BIND, the
  authoritative DNS of pudineh.com: ns1/ns2.pudineh.com, zone `/etc/bind/zones/pudineh.com.db`; raise the serial on
  every change), pm2 `portfolio-admin`. PostgreSQL is installed but disabled (its only user, alefbaft, was removed on
  2026-11-08). Netdata was installed by Hassan with another AI; how it is exposed is not recorded here.
- nginx sites: `agent.pudineh.com`, `eco.pudineh.com`, `hotel.pudineh.com`, `hamsayedar.pudineh.com`,
  `pudineh-portfolio`, `portfolio-admin`, `default`. HTTPS by certbot (auto-renew timer); `certbot certificates`.
- PyPI is blocked from Iran: each venv has its own `pip.conf` pointing at an Iranian mirror (Runflare, Liara as
  fallback): `/opt/javid/.venv/pip.conf`, copied to `/opt/hamsayedar/.venv/pip.conf`.
- AI models for the demos come through AvalAI (an Iranian gateway); the key is in `/opt/javid/.env`.

## Backups (all of them)

| What | When (Tehran) | Where | Kept |
|---|---|---|---|
| javid's databases, files, `.env` (`deploy/backup.py`) | 03:30 | `/var/backups/javid/javid-*.tar.gz` | 14 days |
| hamsayedar: registry, every building, photos, `.env` | 03:45 | `/var/backups/hamsayedar/` | 14 days |
| the whole server (`deploy/server/server-backup.py`, restic) | 04:15 | Google Drive `gdrive:server-backups`, encrypted | 14 daily, 8 weekly, 12 monthly |

- The whole-server backup takes `/opt /var/www /etc /home /root /var/backups`. Its settings and the restic password
  file are in `/etc/server-backup/` (root only). **Without the restic password the Drive copies cannot be opened**:
  it must also be kept off the server (Hassan's password manager). Restoring: `deploy/server/README.md`.
- Each backup writes a `last.json` (`/var/backups/javid/last.json`, `/var/backups/hamsayedar/last.json`,
  `/var/lib/server-backup/last.json`). The watcher alerts when one failed or is older than a day.
- On 2026-11-07 the first restic run took ~3.7 h (no cache); the unit was fixed (HOME, RESTIC_CACHE_DIR). Check that
  later runs take minutes.

## Alerts and health

- `deploy/watch.py` every 5 minutes (javid-watch timer): app, public site, disk, both backups, certificate, server
  errors. Sends to Gmail (SMTP in `/opt/javid/.env`) and Bale if `BALE_TOKEN`/`BALE_CHAT_ID` are set (not set yet:
  the Bale bot needed identity verification). If the international internet is cut, Gmail stops; Bale would still work.
- `.github/workflows/uptime.yml` checks the site from outside every 15 minutes.
- «سلامت سرور» on the assistants page (permanent account only): `health.py`; services listed by `HEALTH_SERVICES` in
  `/opt/javid/.env` (now "javid hamsayedar nginx named").

## Outside services this depends on

GitHub (code, deploys, the uptime check), Google Drive (whole-server backup through rclone), Gmail (alerts), AvalAI
(models), Let's Encrypt (certificates, 90 days; renewal needs the international internet), the Iranian PyPI mirrors,
Google AI Studio (Gemini key for hamsayedar's review). A daily «product manager» report ran as a Claude scheduled
task (`.claude/skills/product-manager`); it stops with the Claude account.

## Open work

- Preparing for an international internet cut: `deploy/offline/README.md` (deploy without GitHub through the
  server's own git repositories, a wheelhouse of every Python library, renewing every certificate before a known cut;
  each script ends with PASS or FAIL). Written on 2026-11-08, not yet run on the server. Still open there: time sync
  and DNS resolvers through domestic servers (needs the server's facts), a local copy of the Ubuntu packages, pinning
  `requirements.txt` to the versions the server runs.
- Renaming «javid»: the name of the school demo became the name of the whole system (repository, server user,
  `/opt/javid`, the services `javid`, `javid-backup`, `javid-watch`, `javid-deploy`, `/var/backups/javid`,
  `HEALTH_SERVICES`). Proposed name `pudineh-agents`. Postponed on purpose: half a rename silently breaks backups,
  the watcher or deploys. Plan: (1) in the code, read every such name from settings with today's as the default, and
  rename the GitHub repository (GitHub redirects the old address); (2) on the server in one sitting, after a backup:
  new user and folder, units, sudoers, deploy key, backup folder, watcher state, `HEALTH_SERVICES`, then remove the old.
- The review team in `.claude/agents/` (security, QA, performance, product design): read only; run the ones a change
  touches before pushing. In hamsayedar the pipeline runs them through Gemini.
- Javid: assistants still to build are listed in `CLAUDE.md` («Assistants still to build»), each with its spec agreed
  with Hassan first.
- Hamsayedar: phase 2 (money) and after, see its `HANDOFF.md`.
