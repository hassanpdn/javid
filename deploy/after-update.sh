#!/bin/bash
# Runs on the server after javid-deploy has moved /opt/javid to the newest main. $1 is the commit it was on before.
# Only the slow steps that the changed files need, then a restart.
set -euo pipefail
cd /opt/javid
CHANGED=$(git diff --name-only "$1" HEAD)

# pip uses the Iranian mirror set in .venv/pip.conf (PyPI itself is blocked from Iran)
if grep -qx 'requirements.txt' <<< "$CHANGED"; then
  echo "javid-deploy: installing libraries"
  .venv/bin/pip install --quiet -r requirements.txt
fi
if grep -qE '^(docs/|ingest\.py$|common\.py$)' <<< "$CHANGED"; then
  echo "javid-deploy: rebuilding the document search"
  .venv/bin/python ingest.py
fi
# The demo data is rebuilt when the code that makes it or the database layout changed.
# This wipes what was done in the demo so far (decisions, warnings, messages); the school in school.json stays.
if grep -qxE 'seed\.py|db\.py' <<< "$CHANGED"; then
  echo "javid-deploy: rebuilding the demo data"
  .venv/bin/python seed.py
fi

# The only root command javid may run (see /etc/sudoers.d/javid-deploy). Also clears texts the app keeps in memory.
sudo /usr/bin/systemctl restart javid
echo "javid-deploy: done"
