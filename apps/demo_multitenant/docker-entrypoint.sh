#!/bin/sh
# The data directory is the deployment's own: provided on the host and mounted in, never seeded or
# rewritten from the image.
set -e

: "${COFY_MANAGEMENT_DATA_DIR:?COFY_MANAGEMENT_DATA_DIR must be set}"

# Behind a TLS-terminating proxy, the forwarded headers are what make the login callback URL
# the API builds an https:// one on the public host. Only the proxy can reach this port.
exec /app/packages/management-api/.venv/bin/uvicorn cofy.management.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --proxy-headers \
  --forwarded-allow-ips '*'

