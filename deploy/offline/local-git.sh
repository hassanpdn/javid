#!/bin/bash
# A git repository on the server itself for an app, so code can be pushed from the Mac and deployed without GitHub.
#   sudo bash deploy/offline/local-git.sh javid        (or hamsayedar)
# Makes /srv/git/<app>.git (a bare repository owned by the app's user) with everything the app's working copy has,
# and a post-receive hook: a push to main there runs /usr/local/bin/<app>-deploy with DEPLOY_FROM pointing at it
# (the same backup / update / check / roll back as a deploy from GitHub). Safe to run twice.
# The Mac's key is added separately (README.md): it may only run git-shell, as the app's user, never as root.
set -uo pipefail
APP="${1:-}"
fail() { echo "FAIL: $*"; exit 1; }
[ "$(id -u)" = 0 ] || fail "run as root (sudo)"
[[ "$APP" =~ ^(javid|hamsayedar)$ ]] || fail "usage: local-git.sh javid|hamsayedar"
id "$APP" >/dev/null 2>&1 || fail "no user $APP"
[ -x "/usr/local/bin/$APP-deploy" ] || fail "/usr/local/bin/$APP-deploy is missing"
grep -q 'DEPLOY_FROM' "/usr/local/bin/$APP-deploy" || fail "/usr/local/bin/$APP-deploy is the old copy: install the new one first (README.md)"
REPO="/srv/git/$APP.git"
install -d -m 755 /srv/git
if [ ! -d "$REPO" ]; then
  install -d -m 750 -o "$APP" -g "$APP" "$REPO"
  sudo -u "$APP" git init -q --bare -b main "$REPO" || fail "git init"
fi
# everything the server's copy has (it was fetched from GitHub)
sudo -u "$APP" git -C "/opt/$APP" push -q "$REPO" HEAD:refs/heads/main 2>&1 || fail "could not copy /opt/$APP into $REPO"
cat > "$REPO/hooks/post-receive" <<HOOK
#!/bin/bash
# Deploy when main was pushed (made by deploy/offline/local-git.sh)
while read -r old new ref; do
  if [ "\$ref" = "refs/heads/main" ]; then
    echo "deploying \$new from the server's own repository"
    DEPLOY_FROM="$REPO" /usr/local/bin/$APP-deploy
  fi
done
HOOK
chown "$APP:$APP" "$REPO/hooks/post-receive"; chmod 755 "$REPO/hooks/post-receive"
[ "$(sudo -u "$APP" git -C "$REPO" rev-parse main)" = "$(sudo -u "$APP" git -C "/opt/$APP" rev-parse HEAD)" ] || fail "the copy differs"
echo "PASS: $REPO is at $(sudo -u "$APP" git -C "$REPO" rev-parse --short main); push to $APP@<server>:$REPO main"
