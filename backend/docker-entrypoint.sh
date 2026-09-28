#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Waiting for Postgres..."
python - <<'PY'
import time
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

for attempt in range(60):
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] Postgres is ready.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] Postgres not ready yet ({exc}); retrying...")
        time.sleep(2)
print("[entrypoint] Postgres never became ready.", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] Running database migrations..."
alembic upgrade head

MODE="${1:-api}"

case "$MODE" in
  api)
    echo "[entrypoint] Starting FastAPI..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    echo "[entrypoint] Starting Celery worker..."
    exec celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    ;;
  seed)
    echo "[entrypoint] Seeding demo data..."
    exec python -m scripts.seed
    ;;
  *)
    echo "[entrypoint] Unknown mode '$MODE'. Use api | worker | seed."
    exit 1
    ;;
esac
