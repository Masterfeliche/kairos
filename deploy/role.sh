#!/bin/sh
# Shared by setup.sh and start.sh: decide which app this is.
#
# APP_ROLE wins when set. deploy.tz may not pass environment variables into the Docker
# build, so otherwise infer it: launched by `npm run build` / `npm start` (the Node
# stack, which uses the root package.json) means the website; an image with Python and
# no Node means the API.

has() { command -v "$1" >/dev/null 2>&1; }

if [ -z "${APP_ROLE:-}" ]; then
  if [ -n "${npm_lifecycle_event:-}" ]; then
    APP_ROLE=web
  elif has npm && ! has python3 && ! has python; then
    APP_ROLE=web
  elif ! has npm && { has python3 || has python; }; then
    APP_ROLE=api
  fi
fi

case "${APP_ROLE:-}" in
  api | web) ;;
  *)
    echo "Cannot tell whether this is the API or the website: set APP_ROLE to 'api' or 'web'." >&2
    exit 1
    ;;
esac

python_bin() {
  if has python3; then echo python3
  elif has python; then echo python
  else
    echo "Python is not installed in this image (APP_ROLE=api needs the Python stack)." >&2
    exit 1
  fi
}
