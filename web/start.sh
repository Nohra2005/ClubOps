#!/usr/bin/env bash
set -euo pipefail

: "${CLUBOPS_SESSION_SECRET:?Set the server session secret}"
: "${CLUBOPS_GOOGLE_CLIENT_ID:?Set the Google OAuth web client ID}"
if [[ "$CLUBOPS_GOOGLE_CLIENT_ID" != "${CLUBOPS_WEB_GOOGLE_CLIENT_ID:-}" ]]; then
  echo 'The server and built frontend Google client IDs differ. Rebuild with the same public ID.' >&2
  exit 1
fi
if [[ "${CLUBOPS_DEV_LOGIN:-0}" != 0 || "${CLUBOPS_COOKIE_SECURE:-1}" != 1 ]]; then
  echo 'Production requires dev login disabled and secure cookies enabled.' >&2
  exit 1
fi

python scripts/load_rulebook.py --data-dir "${CLUBOPS_DATA_DIR:-/var/data/clubops}"
caddy validate --config /app/web/Caddyfile --adapter caddyfile

api_pid=''
web_pid=''
stop() {
  trap - TERM INT EXIT
  [[ -z "$api_pid" ]] || kill -TERM "$api_pid" 2>/dev/null || true
  [[ -z "$web_pid" ]] || kill -TERM "$web_pid" 2>/dev/null || true
  wait || true
}
trap stop TERM INT EXIT
uvicorn clubops.api.app:build --factory --host 127.0.0.1 --port 8000 --workers 1 &
api_pid=$!
caddy run --config /app/web/Caddyfile --adapter caddyfile &
web_pid=$!
# If either service stops, stop its sibling; the platform can restart the container.
set +e
wait -n "$api_pid" "$web_pid"
status=$?
set -e
if [[ "$status" == 0 ]]; then status=1; fi
exit "$status"
