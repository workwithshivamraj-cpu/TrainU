# Operations

## Prerequisites

- Docker + Docker Compose (recommended path), **or**
- Python 3.12+, Node 20+, PostgreSQL 16 with `pgvector`, Redis, `ffmpeg` on `PATH` for running services natively.

## Local setup (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
docker compose run --rm backend python -m scripts.seed
```

Services and ports (all overridable in `.env`):

| Service | Port | Notes |
|---|---|---|
| `frontend` | 4200 | nginx serving the built Angular app |
| `backend` | 8000 | FastAPI; `/api/v1/docs` for Swagger |
| `worker` | — | Celery worker, no exposed port |
| `postgres` | 5432 | `pgvector/pgvector:pg16` image |
| `redis` | 6379 | Celery broker/result backend |
| `minio` | 9000 / 9001 | S3 API / web console |

`backend` and `worker` share one Docker image (`backend/Dockerfile`); the
entrypoint script picks a mode (`api` | `worker` | `seed`) from the compose
`command:`. Both wait for Postgres to accept connections and run
`alembic upgrade head` before starting, so migrations are always applied
before the app serves traffic — no manual migration step needed on a normal
`docker compose up`.

To re-seed from scratch: stop the stack, remove the `trainu_postgres_data`
and `trainu_minio_data` volumes (`docker compose down -v`), then repeat the
two commands above.

## Running tests

```bash
# Backend — needs a local Postgres+pgvector reachable at the URL in
# backend/tests/conftest.py (defaults to postgresql+psycopg2://trainu:trainu@localhost:5432/trainu_test)
cd backend
createdb trainu_test  # once
psql trainu_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
pytest -q

# Frontend unit tests
cd frontend
npm test

# Frontend e2e (needs the full stack running at http://localhost:4200 / :8000, seeded)
npm run e2e
```

Backend tests run with `CELERY_TASK_ALWAYS_EAGER=true` (set automatically in
`tests/conftest.py`), so `.delay()` calls execute synchronously in-process —
no Redis or separate worker required to run the suite.

## Demo credentials

See the table in `README.md`. All demo users share the password
`TrainU_Demo123!`; change this before using the seed script against anything
beyond a local/demo database.

## Environment variables

All configuration is environment-driven (`backend/app/core/config.py`);
`.env.example` documents every variable with safe local defaults. Highlights:

- **`SECRET_KEY`** — JWT signing key. The example value is explicitly
  insecure; generate a real one for anything beyond local demo use.
- **`DATABASE_URL` / `REDIS_URL` / `S3_*`** — infrastructure connection
  strings. Docker Compose overrides the hostnames to the in-network service
  names (`postgres`, `redis`, `minio`); the same `.env` also works for
  running the backend natively against `localhost`.
- **`S3_PUBLIC_ENDPOINT_URL`** — the URL a *browser* can reach MinIO at,
  which differs from the URL the backend container uses internally
  (`http://minio:9000` vs `http://localhost:9000`). Presigned URLs are
  rewritten to this host so video playback works from the user's browser.
- **`STT_PROVIDER`**, **`LLM_PROVIDER`**, **`EMBEDDINGS_PROVIDER`** — each
  independently `mock` or a real provider; see below.
- **`RAG_MIN_SIMILARITY`**, **`RAG_MEDIUM_CONFIDENCE_SIMILARITY`**,
  **`RAG_HIGH_CONFIDENCE_SIMILARITY`** — cosine-similarity thresholds tuned
  for the mock embeddings provider's geometry (see below for what to change
  when switching to real embeddings).

## Mock mode vs real AI/transcription

### Mock mode (default)

- `STT_PROVIDER=mock`: `app/services/stt.py::MockSTTProvider` splits a
  transcript (seeded, or a short generic placeholder for arbitrary uploads
  with no seed text) into evenly-timed sentences. No audio is actually
  decoded — `ffmpeg` still runs to extract the audio track and probe real
  duration, but transcription itself is deterministic.
- `LLM_PROVIDER=mock`, `EMBEDDINGS_PROVIDER=mock`:
  `app/services/embeddings.py::MockEmbeddingsProvider` is a stopword-filtered
  hashed bag-of-words embedding (dimension `EMBEDDING_DIM`, default 384);
  `app/services/llm.py::MockLLMProvider` builds answers only from retrieved
  chunk text (chronologically ordered, single-source for "how do I"
  questions). This is what the seed data, the automated tests, and the demo
  flow are tuned against.

### Real providers

Set independently per concern — you can mix, e.g. real embeddings with the
mock LLM:

```bash
# OpenAI-compatible
STT_PROVIDER=whisper_api
STT_API_BASE_URL=https://api.openai.com/v1
STT_API_KEY=sk-...
STT_MODEL=whisper-1

LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

EMBEDDINGS_PROVIDER=openai
EMBEDDINGS_BASE_URL=https://api.openai.com/v1
EMBEDDINGS_API_KEY=sk-...
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

```bash
# Ollama (local, no API key)
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1

EMBEDDINGS_PROVIDER=ollama
EMBEDDINGS_BASE_URL=http://localhost:11434/v1
EMBEDDINGS_MODEL=nomic-embed-text
EMBEDDING_DIM=768
```

**Important — changing `EMBEDDING_DIM` requires a migration.** The
`pgvector` column is created with a fixed dimension
(`transcript_chunks.embedding VECTOR(384)` in the initial migration). If you
switch to a real embeddings model with a different output dimension, you
must:

1. Write a new Alembic migration that alters the column to the new
   dimension (`ALTER TABLE transcript_chunks ALTER COLUMN embedding TYPE
   vector(N)`) and rebuilds the IVFFlat index.
2. Re-run ingestion for existing sources (or re-run `scripts/seed.py` against
   a fresh database) so every chunk's embedding is regenerated with the new
   model — old and new embeddings are not comparable.
3. Re-tune `RAG_MIN_SIMILARITY` / `RAG_MEDIUM_CONFIDENCE_SIMILARITY` /
   `RAG_HIGH_CONFIDENCE_SIMILARITY` for the new model's similarity
   distribution; the defaults are tuned for the mock provider's geometry and
   real embedding models typically cluster at different cosine-similarity
   ranges.

The real STT/LLM/embeddings adapters (`WhisperAPISTTProvider`,
`OpenAICompatibleLLMProvider`, `OpenAICompatibleEmbeddingsProvider`) are
fully implemented against standard OpenAI-compatible HTTP contracts, but are
not exercised by the automated test suite (no network access in CI/this
environment) — test them against your provider before relying on them in
production.

## Database overview

See `docs/architecture.md` for the full table list. Migrations live in
`backend/alembic/versions/`; the initial migration
(`3fc92ab4e5e4_initial_schema.py`) creates the `vector` extension, every
table, all foreign-key/tenant-scoping indexes, and the IVFFlat cosine index
on `transcript_chunks.embedding`. Generate new migrations with:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
```

Always review autogenerated migrations before applying — Alembic doesn't
know about `pgvector`-specific index types, so IVFFlat/HNSW indexes need to
be added by hand (see the initial migration for the pattern).

## Production hardening and scaling considerations

This MVP is deliberately scoped for a correct, demonstrable single-tenant-host
deployment. Before production rollout:

- **Secrets**: rotate `SECRET_KEY` to a real random value, injected via your
  platform's secret manager — never commit `.env`.
- **Rate limiting**: `app/core/rate_limit.py` is an in-process sliding
  window, which only works correctly with a single API replica. Move it to
  Redis (`INCR` + `EXPIRE` per key) before running more than one backend
  instance.
- **Object storage**: MinIO is fine for local/self-hosted demo use; for
  production, point `S3_*` at a real S3-compatible bucket with lifecycle
  policies matching each organization's `retention_days`, and consider
  virus/content scanning on upload before a file is queued for processing.
- **STT/LLM cost & latency**: real transcription and LLM calls are
  synchronous within a Celery task; for large videos, consider chunked/async
  provider APIs and backpressure (Celery concurrency limits, task time
  limits) so one huge upload can't starve the worker pool.
- **pgvector index tuning**: the IVFFlat index's `lists` parameter (100 in
  the initial migration) should scale with row count — rebuild with a larger
  `lists` value as `transcript_chunks` grows past ~100k rows, or migrate to
  an HNSW index (`pgvector` ≥ 0.5) for better recall/latency at scale.
- **Email delivery**: invitations currently return a token for the inviter
  to share manually (shown in the UI as a copyable link) — wire up a
  transactional email provider before relying on invites at scale.
- **Observability**: `structlog` output is currently console-rendered;
  ship it to a log aggregator, and add request tracing/metrics
  (e.g. OpenTelemetry) for latency and error-rate visibility into the RAG
  pipeline specifically, since that's the highest-variance path.
- **Horizontal scaling**: the API is stateless (JWT auth, no server-side
  sessions) so it scales horizontally behind a load balancer once the rate
  limiter is Redis-backed; the Celery worker scales by adding replicas and
  tuning `--concurrency`.
- **TLS**: terminate TLS in front of both `frontend` and `backend` in any
  non-local deployment; `CORS_ORIGINS` should be locked to the real frontend
  origin(s).
