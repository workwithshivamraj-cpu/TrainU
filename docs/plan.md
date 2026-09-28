# TrainU — Build Plan

## What we're building
TrainU is a multi-tenant enterprise training/knowledge platform. Content Owners
upload KT videos and documents; a background pipeline transcribes, chunks, and
embeds the content; a RAG assistant answers employee questions using only
approved, organization-scoped content, with citations to exact video
timestamps.

## Stack decisions
- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + Alembic, Python 3.12.
- **DB**: PostgreSQL 16 + `pgvector` extension for embeddings.
- **Queue/worker**: Celery + Redis (broker + result backend).
- **Object storage**: MinIO (S3-compatible), boto3 client, presigned URLs for
  private video/doc access.
- **Media**: `ffmpeg` (via subprocess) for audio extraction.
- **STT**: provider abstraction (`app/services/stt.py`) — `mock` provider
  (deterministic seeded transcripts, no network/API key) and a
  `faster-whisper`/Whisper-API-compatible provider stub controlled by env var.
- **LLM/Embeddings**: provider abstraction (`app/services/llm.py`,
  `app/services/embeddings.py`) — `mock` provider (deterministic hash-based
  embeddings + templated structured answers grounded in retrieved chunks) and
  OpenAI-compatible / Ollama-compatible HTTP adapters selected by
  `LLM_PROVIDER` env var. Demo mode never requires a key.
- **Auth**: JWT access (short-lived) + refresh (long-lived, rotated) tokens,
  `passlib[bcrypt]` hashing, RBAC via a dependency that checks org membership
  + role.
- **Frontend**: Angular 17 standalone components + Tailwind CSS.
- **Tests**: `pytest` + `httpx.AsyncClient` for backend integration tests;
  Playwright for a smoke e2e test of the core demo flow.

## Multi-tenancy approach
Every tenant-owned table carries `organization_id`. A `get_current_membership`
FastAPI dependency resolves the caller's active organization (from a header
or their sole membership) and every query/service function takes that
`organization_id` explicitly and filters by it — there is no global "list
everything" query path. Roles are enumerated
(`platform_admin, org_admin, content_owner, contributor, viewer`) and checked
via a `require_role(...)` dependency. Cross-org access attempts return 404
(not 403) to avoid leaking existence.

## RAG flow
1. Resolve org + optional filters (application, role, version, environment).
2. Embed the question with the configured embeddings provider.
3. `SELECT ... ORDER BY embedding <=> :q LIMIT k` against `transcript_chunks`
   scoped to `organization_id` and `status = 'approved'` (plus optional
   filters).
4. If nothing scores above a minimum similarity threshold → return the fixed
   "could not find an approved source" response (no LLM call).
5. Otherwise build a prompt containing only the retrieved chunk text +
   metadata, call the LLM provider requesting strict JSON, validate against a
   Pydantic schema, and persist the conversation/message/citations.

## Processing pipeline states
`uploaded -> queued -> processing -> awaiting_review -> approved -> indexed`
(or `failed` at any processing step). Only `indexed` sources with `approved`
status are retrievable by the assistant.

## Build order
1. Repo scaffold + this plan.
2. Backend skeleton (config, db, logging, app factory).
3. Models (SQLAlchemy) covering the full schema below.
4. Auth + RBAC + org/application/membership/invitation APIs.
5. Source ingestion API + Celery pipeline (mock STT/embeddings by default).
6. RAG assistant API + feedback.
7. Usage/audit APIs.
8. Alembic migration + seed script (Portfolio Team org, 2 apps, sample
   sources/chunks, demo users).
9. Backend tests.
10. Angular frontend (auth, layout, assistant, admin screens).
11. Frontend e2e smoke test.
12. Docker Compose + `.env.example`.
13. Docs (README, architecture, api, operations).
14. Run migrations + tests + compose, verify the end-to-end demo flow.

## Data model
User, Organization, Membership (user↔org + role), Invitation, Application,
ApplicationModule, Source, VideoProcessingJob, TranscriptChunk (pgvector
column), AssistantConversation, AssistantMessage, AssistantCitation,
Feedback, UsageMetric, AuditLog, OrganizationPlan. See `docs/architecture.md`
for the full ER description once implemented.

## Known scope limits for this MVP (documented, not hidden)
- STT and LLM real-provider adapters are implemented against OpenAI-compatible
  and Whisper-API-compatible HTTP contracts but are not exercised by
  automated tests (no network in this environment) — mock mode is the
  default and what CI/tests run against.
- Payments/billing are schema-ready (`OrganizationPlan`) but not integrated.
- Signed video URLs use MinIO presigned URLs; a CDN layer is out of scope.
