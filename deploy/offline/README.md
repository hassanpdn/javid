# Ready for a cut of the international internet

What keeps working if the server (in Iran) cannot reach GitHub, PyPI's mirrors' upstream, Google or Let's Encrypt, and
how to prepare while it still can. Each script is safe to run twice and ends with one line: `PASS ...` or
`FAIL: why`. Run them as root on the server, one at a time.

## What stops, and what does not

| Stops during a cut | What replaces it |
|---|---|
| Deploys through GitHub Actions (both apps) | Push from the Mac to the server's own git repositories (below) |
| `pip install` from the Iranian mirrors (they only have what they cached) | A wheelhouse of every library on the server |
| Gemini review, the uptime check from outside | Run `pytest` and `pnpm build` on the Mac before pushing |
| Gmail alerts (watcher, hamsayedar notices) | Bale (domestic); needs `BALE_TOKEN`/`BALE_CHAT_ID` in `/opt/javid/.env` |
| The whole-server backup to Google Drive | The nightly local backups go on (`/var/backups/javid`, `/var/backups/hamsayedar`); copy them to the Mac with `scp` |
| Let's Encrypt renewals | `renew-certs.sh` right before a known cut: 90 days from then |
| AvalAI, if it loses its upstream models | Every assistant already falls back to code-built text (`ModelOff`/`ModelDown`) |

Inside Iran the sites stay up: DNS for pudineh.com is served by this server itself (BIND).

## 1. Deploy without GitHub

Once per app (javid, hamsayedar):

1. Install the new deploy script, which can fetch from somewhere other than GitHub:
   `install -m 755 /opt/javid/deploy/javid-deploy.sh /usr/local/bin/javid-deploy` and
   `install -m 755 /opt/hamsayedar/deploy/hamsayedar-deploy /usr/local/bin/hamsayedar-deploy`
2. `bash /opt/javid/deploy/offline/local-git.sh javid` and `bash /opt/javid/deploy/offline/local-git.sh hamsayedar`:
   makes `/srv/git/<app>.git` with a hook that deploys every push to `main`.
3. The Mac's key, allowed only to push and fetch (git-shell), as the app's user, never root. On the Mac, if there is
   no key yet: `ssh-keygen -t ed25519 -f ~/.ssh/pudineh-git -N ""`; then on the server, for each app:
   `echo "command=\"git-shell -c \\\"\$SSH_ORIGINAL_COMMAND\\\"\",restrict $(cat <the Mac's pudineh-git.pub>)" >> /home/<app's home>/.ssh/authorized_keys`
   (javid's home is `/home/javid` or `/opt/javid`: `getent passwd javid` says which).
4. On the Mac, in each project: `git remote add server javid@89.45.89.72:/srv/git/javid.git` (or
   `hamsayedar@89.45.89.72:/srv/git/hamsayedar.git`), with `IdentityFile ~/.ssh/pudineh-git` for that host in
   `~/.ssh/config`.

Then, during a cut: `pytest`, `pnpm build` and commit `static/` on the Mac, then `git push server main`. The push
prints the deploy's log (backup, update, check, roll back if needed). When GitHub is back: `git push origin main`.

## 2. Python libraries on the server

`bash /opt/javid/deploy/offline/wheelhouse.sh javid` and `... wheelhouse.sh hamsayedar`: downloads exactly what is
installed, through the mirror, into `/opt/<app>/wheelhouse`, and points pip there first. Run again after a change to
`requirements.txt`. Node is not needed on the server (`static/` is committed); the Mac keeps `node_modules`.

## 3. Certificates

`bash /opt/javid/deploy/offline/renew-certs.sh` once, right before a known cut. Not on a timer.

## 4. Time and DNS (done on 2026-11-08)

- Time: systemd-timesyncd, set in `/etc/systemd/timesyncd.conf.d/iran.conf`:
  `NTP=194.225.150.25 62.60.248.134 0.ir.pool.ntp.org 1.ir.pool.ntp.org`, `FallbackNTP=ntp.ubuntu.com`. The two
  addresses are the NTP Pool's Iran servers that answered from the server (offset under a second); they are given as
  addresses too because the pool's names are resolved by servers abroad. The hosting company's 172.16.15.2 has no
  NTP. Check: `timedatectl timesync-status`.
- DNS: `/etc/resolv.conf` already uses domestic resolvers (172.16.15.2, the hosting company's, and 217.218.127.127);
  nothing to change. BIND only serves pudineh.com.

## Still to do

- A local copy of the installed Ubuntu packages (only needed to rebuild the server during a cut).
