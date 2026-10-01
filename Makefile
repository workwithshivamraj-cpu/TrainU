.PHONY: setup up down seed logs test build smoke doctor install-poc models-poc models-container scanner-up
POC_PYTHON ?= python3.12
setup:
	@test -f .env || cp .env.example .env
up: setup
	docker compose build backend frontend
	docker compose up -d postgres redis minio
	TRAINU_LOCAL_BACKUP_DIR="$(CURDIR)/.local-backups" TRAINU_KEEP_WRITERS_STOPPED=true bash scripts/backup-local-data.sh
	TRAINU_MIGRATION_BACKUP_CONFIRMED=verified-local-backup docker compose --profile local-tools up -d
	bash scripts/wait-ready.sh http://localhost:8000/health/ready
	bash scripts/wait-ready.sh http://localhost:4200/health
seed:
	docker compose run --rm backend seed
down:
	docker compose down
logs:
	docker compose logs -f --tail=100 backend worker
test:
	docker compose exec -T -e ENVIRONMENT=test -e TRAINU_ALLOW_SCHEMA_RESET=true -e TRAINU_TEST_DATABASE_URL=postgresql+psycopg2://trainu:trainu@postgres:5432/trainu_test -e TRAINU_TEST_STORAGE_BUCKET=trainu-media-test -e TRAINU_TEST_S3_ENDPOINT_URL=http://minio:9000 -e TRAINU_TEST_REDIS_URL=redis://redis:6379/1 -e RATE_LIMIT_BACKEND=memory backend pytest -q
build:
	cd frontend && npm ci && npm run build -- --configuration production
smoke:
	bash scripts/smoke.sh http://localhost:4200
doctor:
	bash scripts/doctor.sh $(PROFILE)
install-poc:
	@command -v "$(POC_PYTHON)" >/dev/null || { echo "Missing $(POC_PYTHON); install Python 3.12 or set POC_PYTHON." >&2; exit 1; }
	@test -x backend/.venv-poc/bin/python || $(POC_PYTHON) -m venv backend/.venv-poc
	backend/.venv-poc/bin/python -m pip install -r backend/requirements.txt
models-poc:
	python3 scripts/validate-model-lock.py
	cd backend && HF_HOME="$(CURDIR)/.local-models/huggingface" PYTHONPATH=. .venv-poc/bin/python ../scripts/download-models.py
models-container:
	python3 scripts/validate-model-lock.py
	docker compose run --rm --no-deps -v "$(CURDIR):/workspace:ro" -e HF_HOME=/var/cache/trainu/huggingface --entrypoint python backend /workspace/scripts/download-models.py
scanner-up:
	docker compose --profile scanner up -d clamav
