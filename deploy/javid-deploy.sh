#!/bin/bash
# Installed once on the server as /usr/local/bin/javid-deploy (owned by root) and run as the javid user,
# by GitHub Actions through the deploy key (forced command) or by hand: sudo -u javid javid-deploy
# It only fetches the newest main, then hands over to deploy/after-update.sh from that same code,
# so changes to the update steps reach the server with the code and this file never needs copying again.
set -euo pipefail
cd /opt/javid

OLD=$(git rev-parse HEAD)
git fetch --quiet origin main
# The server never has its own code changes. .env, school.db, db/ and school.json are git-ignored, so this keeps them.
git reset --quiet --hard origin/main
echo "javid-deploy: $OLD -> $(git rev-parse HEAD)"
exec deploy/after-update.sh "$OLD"
