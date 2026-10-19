#!/bin/sh
# Build step. deploy.tz runs it via `npm run build` (Node stack) or the Shipfile `script`.
# It must not need the database or runtime-only environment variables: those may not be
# available while the image is built.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/deploy/role.sh"
echo "kairos setup: APP_ROLE=$APP_ROLE"

case "$APP_ROLE" in
  api)
    PY="$(python_bin)"
    # Usually already installed by the platform from requirements.txt; this is a no-op then.
    "$PY" -m pip install -r "$ROOT/requirements.txt"
    ;;
  web)
    cd "$ROOT/frontend"
    npm ci --no-audit --no-fund
    npm run build
    ;;
esac
