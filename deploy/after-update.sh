#!/bin/bash
# Runs on the server after javid-deploy has moved /opt/javid to the newest main. $1 is the commit it was on before.
# Only the slow steps that the changed files need, then a restart, then a check that the app answers.
# If any step fails, or the app does not answer within a minute, the server goes back to the commit it was on
# (code, libraries, document search and demo data) and restarts that; the GitHub Actions run then shows red.
#
# Everything is inside main(), so bash has read the whole script before it starts: going back rewrites this file
# on disk, and bash reads a plain script while it runs it.
set -euo pipefail
cd /opt/javid

main() {
  OLD="$1"
  CHANGED=$(git diff --name-only "$OLD" HEAD)
  trap rollback ERR

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
  if answers; then
    echo "javid-deploy: done"
  else
    echo "javid-deploy: the app did not answer after the restart"
    rollback
  fi
}

# Up to a minute for the app to answer its home page on the server itself
answers() {
  for _ in $(seq 30); do
    if .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" 2>/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

# Back to the commit the server was on, with what that commit needs, then restart it. Best effort: each step may
# fail without stopping the others, and the deploy is reported as failed either way.
rollback() {
  trap - ERR
  set +e
  echo "javid-deploy: going back to $OLD"
  git reset --quiet --hard "$OLD"
  grep -qx 'requirements.txt' <<< "$CHANGED" && .venv/bin/pip install --quiet -r requirements.txt
  grep -qE '^(docs/|ingest\.py$|common\.py$)' <<< "$CHANGED" && .venv/bin/python ingest.py
  grep -qxE 'seed\.py|db\.py' <<< "$CHANGED" && .venv/bin/python seed.py
  sudo /usr/bin/systemctl restart javid
  if answers; then echo "javid-deploy: back on $OLD"; else echo "javid-deploy: $OLD does not answer either, look at: journalctl -u javid"; fi
  exit 1
}

main "$@"
exit
