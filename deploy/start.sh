#!/bin/sh
# Start step. deploy.tz runs it via `npm start` (Node stack) or the Shipfile `run`.
# Binds 0.0.0.0:$PORT as the platform requires.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/deploy/role.sh"
PORT="${PORT:-8000}"
echo "kairos start: APP_ROLE=$APP_ROLE port=$PORT"

case "$APP_ROLE" in
  api)
    : "${TT_DATABASE_URL:?Set TT_DATABASE_URL to the Postgres connection URL}"
    PY="$(python_bin)"
    cd "$ROOT/backend"
    # Apply pending migrations before serving (a no-op when already at head). Done at
    # start, not build, because the database is only reachable at runtime.
    "$PY" -m alembic upgrade head
    # --proxy-headers: trust X-Forwarded-* from the platform router / website proxy so
    # login throttling and audit logs see the real client IP, not the proxy's.
    exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" \
      --proxy-headers --forwarded-allow-ips='*' --workers "${WEB_CONCURRENCY:-2}"
    ;;
  web)
    cd "$ROOT/frontend"
    exec npx next start -H 0.0.0.0 -p "$PORT"
    ;;
esac
