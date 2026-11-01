#!/usr/bin/env bash
set -euo pipefail
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
