#!/usr/bin/env bash
# Refuses to restore into an existing populated database. Use an isolated target.
set -euo pipefail
: "${PGHOST:?Set isolated target PGHOST}"
: "${PGDATABASE:?Set isolated target PGDATABASE}"
: "${PGUSER:?Set target PGUSER}"
backup_file="${1:?Usage: restore-db.sh /protected/backup.dump}"
if [[ "${TRAINU_RESTORE_CONFIRM:-}" != "$PGDATABASE" ]]; then
  echo 'Set TRAINU_RESTORE_CONFIRM to the isolated target database name.' >&2
  exit 1
fi
existing_tables="$(psql --no-psqlrc --tuples-only --no-align --command="SELECT count(*) FROM pg_tables WHERE schemaname = 'public';")"
if [[ "$existing_tables" != "0" ]]; then
  echo 'Restore refused: target public schema is not empty.' >&2
  exit 1
fi
pg_restore --exit-on-error --single-transaction --no-owner --no-acl --dbname="$PGDATABASE" "$backup_file"
echo 'Restored to isolated target. Run migrations and tenant/citation verification before any cutover.'
