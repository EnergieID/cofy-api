#!/bin/sh
# Seeds the data directory from the committed defaults on its first boot (an empty or freshly
# mounted volume), then leaves it alone on every later boot - so a redeploy keeps whatever
# communities were configured instead of resetting them.
set -e

: "${COFY_MANAGEMENT_DATA_DIR:?COFY_MANAGEMENT_DATA_DIR must be set}"
mkdir -p "$COFY_MANAGEMENT_DATA_DIR"

if [ -z "$(ls -A "$COFY_MANAGEMENT_DATA_DIR" 2>/dev/null)" ]; then
  echo "No communities in $COFY_MANAGEMENT_DATA_DIR yet - seeding from the committed defaults"
  cp -r /app/seed/. "$COFY_MANAGEMENT_DATA_DIR"/
fi

exec /app/packages/management-api/.venv/bin/uvicorn cofy.management.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}"
