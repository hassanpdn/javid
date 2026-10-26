#!/bin/bash
# Brings /opt/javid up to date with main and restarts the app.
# Installed on the server as /usr/local/bin/javid-deploy (owned by root) and run as the javid user,
# either by GitHub Actions through the deploy key (forced command) or by hand: sudo -u javid javid-deploy
set -euo pipefail
cd /opt/javid

OLD=$(git rev-parse HEAD)
git fetch --quiet origin main
# The server never has its own code changes. .env, school.db, db/ and school.json are git-ignored, so this keeps them.
git reset --quiet --hard origin/main
NEW=$(git rev-parse HEAD)
echo "javid-deploy: $OLD -> $NEW"
CHANGED=$(git diff --name-only "$OLD" "$NEW")

# Only the slow steps that a change actually needs (pip uses the Iranian mirror set in .venv/pip.conf)
if grep -qx 'requirements.txt' <<< "$CHANGED"; then
  echo "javid-deploy: installing libraries"
  .venv/bin/pip install --quiet -r requirements.txt
fi
if grep -qE '^(docs/|ingest\.py$|common\.py$)' <<< "$CHANGED"; then
  echo "javid-deploy: rebuilding the document search"
  .venv/bin/python ingest.py
fi

# The only root command javid may run (see /etc/sudoers.d/javid-deploy)
sudo /usr/bin/systemctl restart javid
echo "javid-deploy: done"
