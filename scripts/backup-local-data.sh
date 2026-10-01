#!/usr/bin/env bash
# Take a consistent local PostgreSQL + private-object snapshot before migrations.
set -euo pipefail
umask 077

backup_root="${TRAINU_LOCAL_BACKUP_DIR:-$(pwd)/.local-backups}"
mkdir -p "$backup_root"
chmod 700 "$backup_root"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$backup_root/$stamp"
mkdir "$backup_dir"
chmod 700 "$backup_dir"
api_was_running="$(docker compose ps --status running -q backend 2>/dev/null || true)"
worker_was_running="$(docker compose ps --status running -q worker 2>/dev/null || true)"
restore_writers() {
  result=$?
  trap - EXIT
  rm -f "$backup_dir"/*.partial
  if [[ "$result" != 0 || "${TRAINU_KEEP_WRITERS_STOPPED:-false}" != true ]]; then
    if [[ -n "$api_was_running" ]]; then docker start "$api_was_running" >/dev/null || result=1; fi
    if [[ -n "$worker_was_running" ]]; then docker start "$worker_was_running" >/dev/null || result=1; fi
  fi
  exit "$result"
}
trap restore_writers EXIT

# Stop writers before taking the database and object-store snapshots. Services
# are started separately by `make up`, so fresh installs are covered too.
docker compose stop backend worker >/dev/null 2>&1 || true
# pg_isready reports that the server accepts connections even while the
# official image is still creating POSTGRES_DB and running init scripts. Wait
# for a real query against the configured database before starting pg_dump.
database_ready=false
for _ in $(seq 1 60); do
  if docker compose exec -T postgres sh -ec \
    'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT 1"' \
    >/dev/null 2>&1; then
    database_ready=true
    break
  fi
  sleep 1
done
if [[ "$database_ready" != true ]]; then
  echo 'Configured migration database is unavailable; backup and migration are blocked.' >&2
  exit 1
fi

docker compose exec -T postgres sh -ec \
  'pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > "$backup_dir/database.dump.partial"
test -s "$backup_dir/database.dump.partial"
mv "$backup_dir/database.dump.partial" "$backup_dir/database.dump"
docker compose exec -T postgres sh -ec \
  'pg_restore --list' < "$backup_dir/database.dump" >/dev/null

backup_abs="$(cd "$backup_root" && pwd -P)/$stamp"
docker compose run --rm --no-deps -T \
  -v "$backup_abs:/backup" \
  -v "$(pwd)/scripts/backup-local-storage.py:/tmp/backup-local-storage.py:ro" \
  --entrypoint python backend /tmp/backup-local-storage.py /backup

python3 - "$backup_dir" <<'PY'
import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1])
files = sorted(path for path in root.rglob('*') if path.is_file() and path.name != 'SHA256SUMS')
if not (root / 'storage-manifest.json').is_file():
    raise SystemExit('Object-storage manifest is missing; migration is blocked.')
with (root / 'SHA256SUMS').open('w', encoding='utf-8') as output:
    for path in files:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        output.write(f'{digest.hexdigest()}  {path.relative_to(root)}\n')
print(f'Local database and object snapshot saved under {root}; keep it private and verify before migration.')
PY
