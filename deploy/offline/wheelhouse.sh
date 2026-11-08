#!/bin/bash
# Keeps every Python library an app needs, as files, on the server, so installing never needs the internet:
#   sudo bash deploy/offline/wheelhouse.sh javid        (or hamsayedar)
# Downloads them now, through the venv's own pip.conf (the Iranian mirror), into /opt/<app>/wheelhouse, and adds
# find-links to that pip.conf so pip looks there first. Run it again after requirements.txt changes. Safe to run twice.
set -uo pipefail
APP="${1:-}"
fail() { echo "FAIL: $*"; exit 1; }
[ "$(id -u)" = 0 ] || fail "run as root (sudo)"
[[ "$APP" =~ ^(javid|hamsayedar)$ ]] || fail "usage: wheelhouse.sh javid|hamsayedar"
DIR="/opt/$APP"; CONF="$DIR/.venv/pip.conf"; WH="$DIR/wheelhouse"
[ -f "$CONF" ] || fail "$CONF is missing"
sudo -u "$APP" mkdir -p "$WH"
# what is installed now, exactly (so the files match what runs), plus requirements.txt
sudo -u "$APP" "$DIR/.venv/bin/pip" freeze --exclude-editable > "/tmp/$APP-freeze.txt" || fail "pip freeze"
sudo -u "$APP" "$DIR/.venv/bin/pip" download -q -d "$WH" -r "/tmp/$APP-freeze.txt" || fail "download from the mirror"
sudo -u "$APP" "$DIR/.venv/bin/pip" download -q -d "$WH" pip setuptools wheel || fail "download pip itself"
grep -q "^find-links" "$CONF" || sed -i "/^\[global\]/a find-links = $WH" "$CONF"
grep -q "^find-links = $WH" "$CONF" || fail "could not add find-links to $CONF"
# proof: everything installs from the folder alone, without any index
sudo -u "$APP" "$DIR/.venv/bin/pip" download -q --no-index --find-links "$WH" -d /tmp/$APP-check -r "/tmp/$APP-freeze.txt" >/dev/null 2>&1 \
  || fail "the folder does not hold everything"
rm -rf "/tmp/$APP-check"
echo "PASS: $(ls "$WH" | wc -l) files, $(du -sh "$WH" | cut -f1) in $WH"
