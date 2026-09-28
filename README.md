# TrainU

**Ask TrainU. Learn directly from your team's approved training knowledge.**

TrainU is a multi-tenant enterprise training and knowledge platform. Content
Owners upload approved KT/training videos and documents; a background
pipeline transcribes, chunks, and embeds the content; employees ask
questions in plain language and get a concise, citation-grounded answer that
links straight to the exact video timestamp or document section it came
from. If TrainU can't find approved evidence, it says so — it never invents
an answer.

This repository is a complete, runnable MVP: FastAPI + PostgreSQL/pgvector +
Celery/Redis + MinIO on the backend, Angular + Tailwind on the frontend, all
wired together with Docker Compose, database migrations, seed data, and
tests. It runs out of the box with **no paid services or API keys** — mock
providers stand in for speech-to-text and the LLM/embeddings, with real
OpenAI-compatible/Ollama-compatible/Whisper-API adapters ready to enable via
environment variables.

## Quick start

```bash
git clone <this-repo> trainu && cd trainu
cp .env.example .env
docker compose up --build
```

Then, in a separate terminal, seed the demo organization, applications, and
approved KT content:

```bash
docker compose run --rm backend python -m scripts.seed
```

Open the app:

- Frontend: http://localhost:4200
- Backend API docs (Swagger/OpenAPI): http://localhost:8000/api/v1/docs
- MinIO console: http://localhost:9001 (user/pass from `.env`)

### Demo login

| Email | Password | Role |
|---|---|---|
| `owner@portfolioteam.example` | `TrainU_Demo123!` | Content Owner |
| `admin@portfolioteam.example` | `TrainU_Demo123!` | Org Admin |
| `contributor@portfolioteam.example` | `TrainU_Demo123!` | Contributor |
| `viewer@portfolioteam.example` | `TrainU_Demo123!` | Viewer |
| `platform.admin@trainu.dev` | `TrainU_Demo123!` | Org Admin + Platform Admin |

Try asking TrainU:

- "How do I create a new client account?"
- "How do I update the status of a client account?"
- "Which role can approve a client account status change?"
- "How do I create a purchase order?"

Each returns a grounded answer with numbered steps, a confidence level,
citations you can click to jump the video player to the exact timestamp,
related clips, and follow-up questions.

## Repository layout

```
backend/          FastAPI application (API, models, services, Celery tasks, migrations, tests)
frontend/         Angular + Tailwind single-page app
infrastructure/   nginx config used by the frontend's Docker image
docs/             architecture, API, product plan, and operations documentation
docker-compose.yml
.env.example
```

There is no separate `worker/` directory: the Celery worker runs the same
`backend/` codebase in a different container (`worker` service in
`docker-compose.yml`), which keeps the ingestion pipeline, models, and
provider abstractions in one place instead of duplicated across two Python
packages.

## Local development (without Docker)

Prerequisites: Python 3.12+, Node 20+, PostgreSQL 16 with the `pgvector`
extension available, Redis, and `ffmpeg` on `PATH`.

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example ../.env   # or create backend/.env with DATABASE_URL etc. pointed at localhost
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload

# Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info

# Frontend (separate terminal)
cd frontend
npm install
npm start   # serves on http://localhost:4200
```

## Tests

```bash
# Backend: unit + API integration tests (registration, RBAC, org isolation,
# upload validation, processing state machine, approval gating, retrieval
# scoping, citation schema, no-answer behavior, feedback)
cd backend
pytest -q

# Frontend: critical-path Playwright smoke tests (login, ask-and-cite,
# role-based nav) against a running stack
cd frontend
npm run e2e
```

Backend tests use a separate `trainu_test` database and run with
`CELERY_TASK_ALWAYS_EAGER=true`, so the full ingestion pipeline executes
synchronously in-process — no separate worker or broker needed for CI.

## Mock mode vs real AI/transcription

Everything works end to end with **zero external credentials** by default:

- `STT_PROVIDER=mock` — deterministic, timestamped transcript generation.
- `LLM_PROVIDER=mock` / `EMBEDDINGS_PROVIDER=mock` — a lexical, hashed
  bag-of-words embedding plus a template-based answer synthesizer that only
  ever assembles its answer from the retrieved chunk text (so it's
  structurally incapable of inventing facts).

To use real providers, set in `.env`:

```
STT_PROVIDER=whisper_api
STT_API_BASE_URL=https://api.openai.com/v1
STT_API_KEY=sk-...

LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...

EMBEDDINGS_PROVIDER=openai
EMBEDDINGS_BASE_URL=https://api.openai.com/v1
EMBEDDINGS_API_KEY=sk-...
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536   # must match the model's output dimension — see docs/operations.md
```

Ollama works the same way with an OpenAI-compatible base URL
(`http://localhost:11434/v1`) and no API key. See `docs/operations.md` for
the full walkthrough, including the migration needed when changing
`EMBEDDING_DIM`.

## Documentation

- [`docs/plan.md`](docs/plan.md) — build plan and scope decisions
- [`docs/architecture.md`](docs/architecture.md) — system architecture, data model, RAG flow, multi-tenancy
- [`docs/api.md`](docs/api.md) — API surface reference
- [`docs/operations.md`](docs/operations.md) — setup, environment variables, provider configuration, production hardening

## What's fully functional

Registration/login with JWT access+refresh tokens, organization creation and
invitations, role-based access control enforced on every endpoint, the
application catalog, video/document upload with type/size validation, the
full ingestion pipeline (audio extraction → transcription → chunking →
embedding → pgvector storage), the source review/approval workflow and
state machine, the RAG assistant with strict organization-scoped retrieval,
citation-grounded answers, confidence levels, related clips, follow-up
questions, feedback capture, usage metrics, and the audit log — all backed
by real database-driven logic and exercised by automated tests, not
placeholder UI.

## What to harden before production

See "Production hardening and scaling considerations" in
[`docs/operations.md`](docs/operations.md) — summary: swap the mock
STT/LLM/embeddings providers for real ones and re-tune the RAG thresholds
for real embedding geometry, move the in-process rate limiter to Redis,
add email delivery for invitations, add virus/content scanning on uploads,
and put the API behind TLS with `SECRET_KEY` rotated to a real secret.
