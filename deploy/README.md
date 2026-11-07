# Deploy

The demo runs on 89.45.89.72 at https://agent.pudineh.com.

- App: `/opt/javid`, run by the `javid` user through systemd (`/etc/systemd/system/javid.service`, uvicorn on 127.0.0.1:8000).
- nginx: `/etc/nginx/sites-available/agent.pudineh.com`, HTTPS by certbot. DNS: `agent` A record in `/etc/bind/zones/pudineh.com.db` on the same server.
- Models: AvalAI (`qwen3.8-flash`, `gemini-embedding-001`), since OpenRouter refuses this server. Settings in `/opt/javid/.env`, including `SITE_USER`/`SITE_PASSWORD` (the door) and `ADMIN_USER`/`ADMIN_PASSWORD` (the account that opens every assistant and gives other people access; their accounts are kept in `/opt/javid/access.db`). After changing `.env`: `sudo systemctl restart javid`.
- pip: PyPI is blocked from Iran; `.venv/pip.conf` points at the Runflare mirror with Liara as a fallback.
- The deed assistant (`deed/README.md`) needs, once, as root: `apt install tesseract-ocr tesseract-ocr-fas poppler-utils`, and
  `client_max_body_size 15m;` in the nginx site (scans up to 10 MB are sent as base64), then `systemctl reload nginx`.

## The eco-lodge's public website (eco.pudineh.com)

The lodge's website is public, on its own address; the host's panel stays behind the door at agent.pudineh.com. Once,
as root:

```
# 1. DNS: an «eco» A record next to «agent» in /etc/bind/zones/pudineh.com.db (raise the zone's serial), then
rndc reload pudineh.com
# 2. nginx
cp /opt/javid/deploy/eco.pudineh.com.nginx /etc/nginx/sites-available/eco.pudineh.com
ln -s /etc/nginx/sites-available/eco.pudineh.com /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
# 3. HTTPS
certbot --nginx -d eco.pudineh.com
# 4. the app: in /opt/javid/.env
#    LODGE_HOST=eco.pudineh.com
#    LODGE_URL=https://eco.pudineh.com
systemctl restart javid
```

Then open the lodge's card on the assistants page and press «ساخت دمو» once: until then the website says it is not set
up. The lodge is not reset on each visit like the other demos (guests make accounts and reviews there); it is built
again only from its setup form. Photos and receipts live in `/opt/javid/lodge_files/`.

## The hotel's public website (hotel.pudineh.com)

The same steps for the hotel, whose panel also stays behind the door. Once, as root:

```
# 1. DNS: a «hotel» A record next to «agent» in /etc/bind/zones/pudineh.com.db (raise the zone's serial), then
rndc reload pudineh.com
# 2. nginx
cp /opt/javid/deploy/hotel.pudineh.com.nginx /etc/nginx/sites-available/hotel.pudineh.com
ln -s /etc/nginx/sites-available/hotel.pudineh.com /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
# 3. HTTPS
certbot --nginx -d hotel.pudineh.com
# 4. the app: in /opt/javid/.env
#    HOTEL_HOST=hotel.pudineh.com
#    HOTEL_URL=https://hotel.pudineh.com
systemctl restart javid
```

Then open the hotel's card and fill its setup form once: until then the website says it is not set up. Like the lodge,
the hotel is no longer forgotten on each visit; the demo data is still rebuilt each day (and from its setup form), and
guests' accounts and their bookings still to come are carried over. Receipts live in `/opt/javid/hotel_files/`.

## Automatic updates

`.github/workflows/deploy.yml`: a push to a `claude/` branch is merged into `main`, and every change to `main`
runs `/usr/local/bin/javid-deploy` on the server over SSH. No tests run there. That script (a copy of
`deploy/javid-deploy.sh`) only fetches `main` and then runs `deploy/after-update.sh` from the new code: libraries when
`requirements.txt` changed, the document search when `docs/` changed, the demo data when `seed.py` or `db.py` changed
(this wipes what was done in the demo so far), then a restart, then a check that the app answers on
`127.0.0.1:8000` within a minute.

If any of those steps fails, or the app does not answer, the script puts the server back on the commit it was on
(code, libraries, document search and demo data), restarts that, and exits with an error, so the GitHub Actions run
shows red. `main` still has the broken commit: fix it and push again. To go back to an older version by hand,
`git revert` the commit and push; the revert deploys like any change.

One-time server setup, as root:

```
# 1. the update script, owned by root so the javid user can run it but not change it
install -m 755 /opt/javid/deploy/javid-deploy.sh /usr/local/bin/javid-deploy

# 2. javid may restart the app, and nothing else, as root
echo 'javid ALL=(root) NOPASSWD: /usr/bin/systemctl restart javid' > /etc/sudoers.d/javid-deploy
chmod 440 /etc/sudoers.d/javid-deploy && visudo -cf /etc/sudoers.d/javid-deploy

# 3. a key that can only run the update script
ssh-keygen -t ed25519 -N "" -C github-deploy -f /root/javid-deploy-key
install -d -m 700 -o javid -g javid /home/javid/.ssh
echo "command=\"/usr/local/bin/javid-deploy\",restrict $(cat /root/javid-deploy-key.pub)" >> /home/javid/.ssh/authorized_keys
chown javid:javid /home/javid/.ssh/authorized_keys && chmod 600 /home/javid/.ssh/authorized_keys
```

Then add three repository secrets on GitHub (Settings > Secrets and variables > Actions):
`DEPLOY_SSH_KEY` = `cat /root/javid-deploy-key`, `DEPLOY_KNOWN_HOSTS` = `ssh-keyscan -t ed25519 89.45.89.72`,
`DEPLOY_HOST` = `89.45.89.72`. After that, delete `/root/javid-deploy-key` (the private half) from the server.

Only if `deploy/javid-deploy.sh` itself changes, copy it again (step 1); changes to `after-update.sh` need nothing. By hand: `sudo -u javid javid-deploy`. Logs: `journalctl -u javid -f`.
Otherwise demo data is rebuilt when the day changes or from the setup form.

## Backups and alerts

`deploy/backup.py` runs every night at 03:30 Tehran time and keeps 14 days in `/var/backups/javid/`: every database
(copied safely while the app writes, then checked), the settings files, `.env`, and the hotel's, lodge's and fabric
shop's files, in one `javid-<date>.tar.gz` readable only by the `javid` user. `deploy/watch.py` runs every 5 minutes and
sends an alert when the app or the site stops answering, the disk is nearly full, the night's backup failed, the HTTPS
certificate is near its end, or the app logs server errors; once when it starts, every 6 hours while it lasts, and
«درست شد» when it is gone. `.github/workflows/uptime.yml` checks the site from outside every 15 minutes, for when the whole
server is down. Changes to `backup.py` and `watch.py` arrive with the code; only the four unit files below need copying
again if they change.

Once, as root:

```
install -d -m 700 -o javid -g javid /var/backups/javid
usermod -aG systemd-journal javid          # the watcher reads the app's log (journalctl -u javid)
cp /opt/javid/deploy/javid-backup.service /opt/javid/deploy/javid-backup.timer \
   /opt/javid/deploy/javid-watch.service /opt/javid/deploy/javid-watch.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now javid-backup.timer javid-watch.timer
systemctl start javid-backup               # a first backup now
cat /var/backups/javid/last.json           # "ok": true
systemctl list-timers 'javid-*'            # both timers and when they run next
```

Where alerts go: Bale works from a server in Iran and reaches the phone; email if the server can send mail. Either or
both, in `/opt/javid/.env` (read on every run, no restart needed):

```
# Bale: in Bale, ask @botfather for a new bot and copy its token. Send any message to the new bot, then
#   curl -s https://tapi.bale.ai/bot<TOKEN>/getUpdates
# and take "chat":{"id": ...} from the answer.
BALE_TOKEN=
BALE_CHAT_ID=
# Email (port 465 = SSL, 587 = STARTTLS)
SMTP_HOST=
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL=
```

Then check it: `sudo -u javid /opt/javid/.venv/bin/python /opt/javid/deploy/watch.py --test` should bring a message. For
the outside check, put the same values in GitHub (Settings > Secrets and variables > Actions) as `BALE_TOKEN`,
`BALE_CHAT_ID` and/or `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL`. GitHub is outside Iran, so
when Iran's international internet is cut, that check reports the site down although people in Iran can still open it.

A backup only on this server is lost with this server, so each night's file also goes to Google Drive, encrypted by
rclone before it leaves (the backup holds `.env` and guests' details), into a folder rclone made itself and can only
see its own files in. 30 days are kept there. Once:

```
# on the server, as root
apt install -y rclone && rclone version
curl -s -o /dev/null -w "%{http_code}\n" https://www.googleapis.com/drive/v3/about     # 401 = Drive is reachable

# on your Mac (Homebrew): sign in to Google in the browser that opens, allow, and copy the {...} line it prints
brew install rclone
rclone authorize "drive" "eyJzY29wZSI6ImRyaXZlLmZpbGUifQ=="

# on the server: the Drive remote with that token, then an encrypting remote on top of it. Keep the password
# somewhere other than this server (a password manager): without it the backups on Drive cannot be opened.
sudo -u javid rclone config create gdrive drive scope drive.file token '{"access_token":...PASTE...}'
sudo -u javid rclone config create javid-drive crypt remote gdrive:javid-backups password 'YOUR-LONG-PASSWORD' --obscure
echo 'BACKUP_RCLONE=javid-drive:' >> /opt/javid/.env
systemctl start javid-backup && cat /var/backups/javid/last.json     # "offsite": ["javid-drive:"]
sudo -u javid rclone ls javid-drive:                                   # the backups on Drive, decrypted names
```

Or to another server instead of Drive: `apt install rsync` on both, then
`sudo -u javid ssh-keygen -t ed25519 -N ""`, add `/home/javid/.ssh/id_ed25519.pub` to the other server's
`authorized_keys`, connect once by hand (`sudo -u javid ssh backup@other-server true`) to accept its key, and set
`BACKUP_REMOTE=backup@other-server:/backups/javid/` in `.env`.

A backup from Drive, when this server is gone: on any computer with rclone, make the same two remotes (a new token
from `rclone authorize`, the same password), then `rclone copy javid-drive:javid-2026-11-07_0330.tar.gz ./`.

To bring something back from a backup (here only the accounts, `access.db`), as root:

```
systemctl stop javid
mkdir -p /tmp/restore && tar -xzf /var/backups/javid/javid-2026-11-07_0330.tar.gz -C /tmp/restore
cp /tmp/restore/javid-2026-11-07_0330/access.db /opt/javid/access.db && chown javid:javid /opt/javid/access.db
systemctl start javid
rm -rf /tmp/restore
```
