#!/bin/sh
# Build step for deploy.tz (Shipfile `script`). Runs once per deploy, before start.sh.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$(command -v python3 || command -v python)"

case "${APP_ROLE:-}" in
  api)
    : "${TT_DATABASE_URL:?Set TT_DATABASE_URL to the Postgres connection URL}"
    cd "$ROOT/backend"
    "$PY" -m pip install --upgrade pip
    "$PY" -m pip install .
    # Bring the database schema up to date before the new code starts.
    "$PY" -m alembic upgrade head
    ;;
  web)
    : "${TT_BACKEND_ORIGIN:?Set TT_BACKEND_ORIGIN to the API app URL, e.g. https://dit-timetable-api.deploy.tz}"
    cd "$ROOT/frontend"
    npm ci --no-audit --no-fund
    # TT_BACKEND_ORIGIN is baked into the /api proxy rewrite at build time.
    npm run build
    ;;
  *)
    echo "APP_ROLE must be 'api' or 'web' (got '${APP_ROLE:-}')." >&2
    exit 1
    ;;
esac
