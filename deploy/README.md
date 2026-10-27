# Deploy

The demo runs on 89.45.89.72 at https://agent.pudineh.com.

- App: `/opt/javid`, run by the `javid` user through systemd (`/etc/systemd/system/javid.service`, uvicorn on 127.0.0.1:8000).
- nginx: `/etc/nginx/sites-available/agent.pudineh.com`, HTTPS by certbot. DNS: `agent` A record in `/etc/bind/zones/pudineh.com.db` on the same server.
- Models: AvalAI (`qwen3.8-flash`, `gemini-embedding-001`), since OpenRouter refuses this server. Settings in `/opt/javid/.env`, including `SITE_USER`/`SITE_PASSWORD` (the door) and `ADMIN_USER`/`ADMIN_PASSWORD` (the account that opens every assistant and gives other people access; their accounts are kept in `/opt/javid/access.db`). After changing `.env`: `sudo systemctl restart javid`.
- pip: PyPI is blocked from Iran; `.venv/pip.conf` points at the Runflare mirror with Liara as a fallback.

## Automatic updates

`.github/workflows/deploy.yml`: a push to a `claude/` branch is merged into `main`, and every change to `main`
runs `/usr/local/bin/javid-deploy` on the server over SSH. No tests run there. That script (a copy of
`deploy/javid-deploy.sh`) only fetches `main` and then runs `deploy/after-update.sh` from the new code: libraries when
`requirements.txt` changed, the document search when `docs/` changed, the demo data when `seed.py` or `db.py` changed
(this wipes what was done in the demo so far), then a restart.

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
