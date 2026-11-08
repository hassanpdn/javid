# The whole server's backup

Every project on this server (javid, the portfolio and its admin, the DNS zones, nginx and the certificates) goes to Google Drive every night at 04:15 Tehran time: restic encrypts it before it leaves and, after the
first night, sends only what changed. When PostgreSQL is in use it is dumped first (`before.d/postgres`;
not installed since 2026-11-08, when alefbaft, its only user, was removed from the server); javid makes its own safe copies
at 03:30 (`deploy/backup.py`). 14 daily, 8 weekly and 12 monthly snapshots are kept; on Sundays part of what is on Drive
is read back to be sure it can be restored. A failed night sends an email, and javid's watcher also says when there has
been no backup for a day.

The script runs as root, so the server keeps its own copy in `/usr/local/sbin`: code pushed to GitHub never runs as root
by itself. After a change to `server-backup.py`, `before.d/` or the unit files, copy them again (step 3).

## Once, as root

```
# 1. restic, and the folders for its settings (root only)
apt install -y restic
install -d -m 700 /etc/server-backup /etc/server-backup/before.d

# 2. Google Drive for root: on your Mac run   rclone authorize "drive" "eyJzY29wZSI6ImRyaXZlLmZpbGUifQ"
#    sign in, allow, copy the {...} line it prints, and put it in place of PASTE (drive.file: rclone sees only what it made)
rclone config create gdrive drive scope drive.file token 'PASTE'
rclone lsd gdrive:                                   # no error = connected

# 3. the script, the PostgreSQL step, the exclude list and the timer
install -m 755 /opt/javid/deploy/server/server-backup.py /usr/local/sbin/server-backup
install -m 755 /opt/javid/deploy/server/before.d/postgres /etc/server-backup/before.d/postgres   # only with PostgreSQL in use
install -m 644 /opt/javid/deploy/server/excludes /etc/server-backup/excludes
cp /opt/javid/deploy/server/server-backup.service /opt/javid/deploy/server/server-backup.timer /etc/systemd/system/

# 4. settings: the email values are the same as in /opt/javid/.env
install -m 600 /opt/javid/deploy/server/env.example /etc/server-backup/env
nano /etc/server-backup/env

# 5. the encryption password. Keep a copy OUTSIDE this server (a password manager): without it the backups on Drive
#    can never be opened, and if this server is lost, that copy is the only one.
openssl rand -base64 32 > /etc/server-backup/restic-password && chmod 600 /etc/server-backup/restic-password
cat /etc/server-backup/restic-password

# 6. make the encrypted store on Drive, then the first backup (it takes a while: the first one sends everything)
set -a; . /etc/server-backup/env; set +a
restic init
systemctl daemon-reload && systemctl enable --now server-backup.timer
systemctl start server-backup; journalctl -u server-backup -n 30 --no-pager
cat /var/lib/server-backup/last.json; echo           # "ok": true
restic snapshots                                     # the first snapshot
/usr/bin/python3 /usr/local/sbin/server-backup --test-alert    # a test email
```

## Bringing something back

restic commands need the settings in the shell first: `set -a; . /etc/server-backup/env; set +a`

```
restic snapshots                                         # every saved night, with its id
restic ls latest /etc/nginx/sites-available              # what a folder held in the last one
restic restore latest --target /tmp/restore --include /etc/nginx/sites-available/pudineh-portfolio
restic restore 4f2a9c1d --target /tmp/restore --include /opt/portfolio      # a whole folder from a given night
```

What was restored is under `/tmp/restore`, with its full path; copy back what is needed. PostgreSQL:
`gunzip -c /tmp/restore/var/backups/postgres/all.sql.gz | sudo -u postgres psql`. A javid database: from
`/var/backups/javid/` as in `deploy/README.md`.

If this server is gone: on a new one, `apt install restic rclone`, step 2 again (a new token), the saved password in
`/etc/server-backup/restic-password`, the same `env`, then `restic snapshots` and `restic restore latest --target /`.
