#!/bin/sh
# Start step for deploy.tz (Shipfile `run`). Binds 0.0.0.0:$PORT as the platform requires.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8000}"

case "${APP_ROLE:-}" in
  api)
    cd "$ROOT/backend"
    PY="$(command -v python3 || command -v python)"
    # --proxy-headers: trust X-Forwarded-* from the platform router / Next.js proxy so
    # login throttling and audit logs see the real client IP, not the proxy's.
    exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" \
      --proxy-headers --forwarded-allow-ips='*' --workers "${WEB_CONCURRENCY:-2}"
    ;;
  web)
    cd "$ROOT/frontend"
    exec npx next start -H 0.0.0.0 -p "$PORT"
    ;;
  *)
    echo "APP_ROLE must be 'api' or 'web' (got '${APP_ROLE:-}')." >&2
    exit 1
    ;;
esac
