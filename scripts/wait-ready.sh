#!/usr/bin/env bash
set -euo pipefail
url="${1:?Usage: wait-ready.sh URL [attempts]}"
attempts="${2:-60}"
for ((attempt=1; attempt<=attempts; attempt++)); do
  if curl --fail --silent --max-time 5 "$url" >/dev/null; then
    echo "Ready: $url"
    exit 0
  fi
  sleep 2
done
echo "Readiness timeout: $url" >&2
exit 1
