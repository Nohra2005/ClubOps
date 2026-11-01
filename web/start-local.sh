#!/usr/bin/env bash
set -euo pipefail
if [[ ! -f /app/.local-development-build || "${CLUBOPS_WEB_DEV_LOGIN:-0}" != 1 ||
      "${CLUBOPS_DEV_LOGIN:-0}" != 1 || "${CLUBOPS_COOKIE_SECURE:-1}" != 0 ]]; then
  echo 'The local entrypoint requires a local frontend/image and dev-only cookie settings.' >&2
  exit 1
fi
umask 077
mkdir -p "$CLUBOPS_DATA_DIR"
if [[ -z "${CLUBOPS_SESSION_SECRET:-}" ]]; then
  secret_file="$CLUBOPS_DATA_DIR/.local-session-secret"
  if [[ ! -s "$secret_file" ]]; then python -c 'import secrets; print(secrets.token_urlsafe(48))' > "$secret_file"; fi
  IFS= read -r CLUBOPS_SESSION_SECRET < "$secret_file"
  export CLUBOPS_SESSION_SECRET
fi
python scripts/load_rulebook.py --data-dir "$CLUBOPS_DATA_DIR"
if [[ ! -f "$CLUBOPS_DATA_DIR/.local-demo-initialized" ]]; then
  python scripts/add_member.py --data-dir "$CLUBOPS_DATA_DIR" running-club 'Local Demo President' president@example.com president
  touch "$CLUBOPS_DATA_DIR/.local-demo-initialized"
fi
echo 'Local development: synthetic cabinet account, no Google account required. Never deploy this target publicly.'
exec bash /app/web/serve.sh
