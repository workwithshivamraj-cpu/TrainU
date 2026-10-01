#!/usr/bin/env bash
# Requires pg_dump matching or newer than the PostgreSQL server major version.
# PGHOST, PGPORT, PGDATABASE, PGUSER, PGSSLMODE and PGPASSFILE come from a
# secret manager. Passwords are deliberately never command-line arguments.
set -euo pipefail
umask 077
: "${PGHOST:?Set PGHOST}"
: "${PGDATABASE:?Set PGDATABASE}"
: "${PGUSER:?Set PGUSER}"
backup_dir="${1:?Usage: backup-db.sh /protected/backup/directory}"
mkdir -p "$backup_dir"
backup_file="$backup_dir/trainu-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump"
trap 'rm -f "$backup_file.partial"' EXIT
pg_dump --format=custom --no-owner --no-acl --file="$backup_file.partial"
pg_restore --list "$backup_file.partial" >/dev/null
mv "$backup_file.partial" "$backup_file"
python3 - "$backup_file" <<'PY'
import hashlib
from pathlib import Path
import sys
path = Path(sys.argv[1])
with path.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
path.with_suffix('.dump.sha256').write_text(f'{digest}  {path.name}\n')
print(f'Created {path.name}; upload to encrypted off-host backup storage and perform a restore drill.')
PY
