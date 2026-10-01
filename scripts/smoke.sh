#!/usr/bin/env bash
# Read-only checks; safe against staging. Does not create users or data.
set -euo pipefail
origin="${1:-http://localhost:4200}"
origin="${origin%/}"
curl --fail --silent --max-time 10 "$origin/health" >/dev/null
curl --fail --silent --max-time 10 "$origin/" >/dev/null
curl --fail --silent --max-time 10 "$origin/docs/launch-checklist.md" >/dev/null
headers="$(curl --silent --show-error --max-time 10 --dump-header - --output /dev/null "$origin/api/v1/auth/me")"
if ! printf '%s\n' "$headers" | grep -Eq '^HTTP/[^ ]+ 401'; then
  echo 'Unauthenticated API request did not return 401.' >&2
  exit 1
fi
if ! printf '%s\n' "$headers" | grep -Eqi '^cache-control:.*no-store'; then
  echo 'API cache policy must be no-store.' >&2
  exit 1
fi
echo 'Smoke checks passed: frontend, health, documentation, auth boundary and cache policy.'
