#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-api}"
case "$MODE" in
  api|worker|migrate|seed) ;;
  *) echo "Unknown mode: use api | worker | migrate | seed" >&2; exit 1 ;;
esac

python - <<'PY'
import sys
import time
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 5})
for attempt in range(30):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        break
    except Exception:
        # Connection error messages can contain credentials: do not echo them.
        if attempt == 29:
            print("Database unavailable after startup retries.", file=sys.stderr)
            sys.exit(1)
        time.sleep(2)
PY

# Migration execution is a separate release job, never a per-replica side effect.
if [[ "$MODE" == "migrate" ]]; then
    if [[ "${ENVIRONMENT:-local}" != "test" && "${TRAINU_MIGRATION_BACKUP_CONFIRMED:-}" != "verified-local-backup" ]]; then
        echo "Migration refused: take and verify a database and object-storage backup, then set TRAINU_MIGRATION_BACKUP_CONFIRMED=verified-local-backup for this migration job." >&2
        exit 1
    fi
    exec alembic upgrade head
fi

# Local object stores start empty on a clean installation. Bootstrap only the
# explicitly named local bucket before the API becomes ready; never create or
# mutate a production bucket implicitly. The worker starts after API health.
if [[ "$MODE" == "api" && "${STORAGE_AUTO_CREATE_BUCKET:-false}" == "true" ]]; then
    python - <<'PY'
from app.services.storage import ensure_bucket
ensure_bucket()
PY
fi

case "$MODE" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      --workers "${API_WORKERS:-2}" \
      --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
    ;;
  worker)
    exec celery -A app.workers.celery_app worker --loglevel=info \
      --concurrency="${CELERY_CONCURRENCY:-2}" \
      --max-tasks-per-child="${CELERY_MAX_TASKS_PER_CHILD:-20}"
    ;;
  seed)
    if [[ "${ENVIRONMENT:-local}" != "local" && "${ENVIRONMENT:-local}" != "test" ]]; then
      echo "Demo seed is only permitted for local/test environments." >&2
      exit 1
    fi
    exec python -m scripts.seed
    ;;
esac
