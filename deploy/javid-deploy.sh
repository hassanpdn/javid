#!/bin/bash
# Installed once on the server as /usr/local/bin/javid-deploy (owned by root) and run as the javid user,
# by GitHub Actions through the deploy key (forced command) or by hand: sudo -u javid javid-deploy
# It only fetches the newest main, then hands over to deploy/after-update.sh from that same code,
# so changes to the update steps reach the server with the code and this file never needs copying again.
# DEPLOY_FROM: where main comes from. GitHub (origin) by default; the server's own bare repository
# (/srv/git/javid.git) when the post-receive hook there runs it, so deploys work without GitHub (deploy/offline/).
set -euo pipefail
cd /opt/javid

OLD=$(git rev-parse HEAD)
git fetch --quiet "${DEPLOY_FROM:-origin}" main
# The server never has its own code changes. .env, school.db, db/ and school.json are git-ignored, so this keeps them.
git reset --quiet --hard FETCH_HEAD
echo "javid-deploy: $OLD -> $(git rev-parse HEAD)"
exec deploy/after-update.sh "$OLD"
