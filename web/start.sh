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
exec bash /app/web/serve.sh
