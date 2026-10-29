#!/usr/bin/env bash
# Starts the test server (fake model, fresh data, tests/serve.py) on :8765 and sets up the default school, so the
# measurements have a login page with every role. HUB=1 in the environment also shows the assistants page (fabric).
# Stop it with: pkill -f "[s]erve.py"; pkill -f "[u]vicorn app:app"
set -e
cd "$(git rev-parse --show-toplevel)"
PY=${PYTHON:-.venv/bin/python}
(nohup "$PY" tests/serve.py > /tmp/perf-serve.log 2>&1 &)
for _ in $(seq 60); do curl -sf localhost:8765/ >/dev/null && break; sleep 1; done
curl -sf -XPOST localhost:8765/setup -H 'content-type: application/json' -d "$(curl -s localhost:8765/setup/default)" >/dev/null
curl -sf -XPOST localhost:8765/fabric/setup -H 'content-type: application/json' -d "$(curl -s localhost:8765/fabric/setup/default)" >/dev/null || true
echo "ready on http://127.0.0.1:8765"
