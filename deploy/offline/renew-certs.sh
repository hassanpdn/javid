#!/bin/bash
# Renews every HTTPS certificate now, so each has its full 90 days: run it ONCE, right before a known cut of the
# international internet (Let's Encrypt cannot renew during one). Never on a timer: renewing the same names again and
# again hits Let's Encrypt's limit on duplicate certificates.
#   sudo bash deploy/offline/renew-certs.sh
set -uo pipefail
fail() { echo "FAIL: $*"; exit 1; }
[ "$(id -u)" = 0 ] || fail "run as root (sudo)"
nginx -t >/dev/null 2>&1 || fail "nginx -t fails: fix that first, or nginx would not reload the new certificates"
certbot renew --force-renewal --quiet || fail "certbot renew (see /var/log/letsencrypt/letsencrypt.log)"
systemctl reload nginx || fail "nginx reload"
certbot certificates 2>/dev/null | grep -E "Certificate Name|Expiry"
echo "PASS: every certificate renewed"
