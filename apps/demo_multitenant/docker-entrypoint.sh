#!/bin/sh
# Seeds the data directory from the committed defaults on its first boot (an empty or freshly
# mounted volume), then leaves it alone on every later boot - so a redeploy keeps whatever
# communities were configured instead of resetting them.
set -e

: "${COFY_MANAGEMENT_DATA_DIR:?COFY_MANAGEMENT_DATA_DIR must be set}"
mkdir -p "$COFY_MANAGEMENT_DATA_DIR"

if [ -z "$(ls -A "$COFY_MANAGEMENT_DATA_DIR" 2>/dev/null)" ]; then
  echo "Nothing in $COFY_MANAGEMENT_DATA_DIR yet - seeding it from the committed defaults"
  cp -r /app/seed/. "$COFY_MANAGEMENT_DATA_DIR"/
fi

# Behind a TLS-terminating proxy, the forwarded headers are what make the login callback URL
# the API builds an https:// one on the public host. Only the proxy can reach this port.
exec /app/packages/management-api/.venv/bin/uvicorn cofy.management.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --proxy-headers \
  --forwarded-allow-ips '*'

