# Architecture

## System overview

```
                     ┌──────────────────┐
                     │   Angular SPA    │  (Tailwind CSS, standalone components)
                     └────────┬─────────┘
                              │ HTTPS / JSON, JWT bearer + X-Org-Id header
                     ┌────────▼─────────┐
                     │   FastAPI API    │  (Pydantic validation, RBAC deps)
                     └───┬──────────┬───┘
                         │          │
             ┌───────────▼──┐   ┌───▼────────────┐
             │ PostgreSQL   │   │ Redis           │
             │ + pgvector   │   │ (Celery broker) │
             └──────────────┘   └───┬─────────────┘
                                     │
                            ┌────────▼─────────┐
                            │  Celery worker    │  (same codebase as API)
                            │  ingestion tasks  │
                            └───┬───────────┬───┘
                                │           │
                       ┌────────▼──┐   ┌────▼─────────────┐
                       │  MinIO    │   │ STT / LLM /        │
                       │ (S3 API)  │   │ Embeddings adapters │
                       └───────────┘   └────────────────────┘
```

The backend is a single Python codebase (`backend/`) used two ways: as the
FastAPI process serving the API, and as the Celery worker process running
background ingestion tasks. They share the same models, database session
factory, and provider abstractions, so there is exactly one implementation
of "what an approved source looks like" and "how a chunk gets embedded."

## Multi-tenancy

Every tenant-owned table has an `organization_id` foreign key
(`applications`, `sources`, `transcript_chunks`, `assistant_conversations`,
`usage_metrics`, `audit_logs`, etc.). There is no query path in the codebase
that reads these tables without an explicit `organization_id` filter.

Request-time organization resolution: a user can belong to multiple
organizations (`memberships` table, one row per user↔org↔role). The
frontend sends the active organization via the `X-Org-Id` header on every
request; `app/api/deps.py::get_current_membership` validates that the
authenticated user actually has an active membership in that organization
before resolving it — if not, the API returns `404` (not `403`), so it never
confirms or denies the existence of an organization to a caller who isn't a
member of it. Every service function that touches tenant data takes the
resolved `organization_id` as an explicit parameter rather than inferring it
from ambient state, which makes "did we forget to scope this query" a
type-checkable/reviewable property rather than a runtime footgun.

### Roles

`platform_admin > org_admin > content_owner > contributor > viewer`, ranked
in `app/models/enums.py::ROLE_RANK`. `app/api/deps.py::require_role(min)` is
a FastAPI dependency that 403s if the caller's role in the active
organization is below the minimum — used on every mutating endpoint
(creating applications, uploading/approving/deleting sources, managing
members, changing roles, updating org settings). Read endpoints generally
require only an active membership (any role); a handful of dashboards
(usage, audit log) require `org_admin`.

The Angular app mirrors these checks in the UI (hiding buttons/nav items,
and a `roleGuard` on admin routes) purely for UX — the backend is the actual
enforcement boundary, and every RBAC rule has a corresponding backend
integration test in `backend/tests/test_rbac.py`.

## Data model

| Table | Purpose |
|---|---|
| `users` | Login identity, independent of any organization |
| `organizations` | Tenant boundary |
| `memberships` | user ↔ organization ↔ role (a user can have many) |
| `invitations` | Pending org invites by email + role, token-based acceptance |
| `organization_plans` | Subscription/plan-ready schema (seats, storage/question limits, trial flag) — no payment integration in this MVP |
| `applications` | The application catalog KT content is organized around |
| `application_modules` | Sub-areas of an application |
| `sources` | An uploaded KT video or document, its metadata, and its processing/approval status |
| `video_processing_jobs` | One row per pipeline stage run (audio extraction, transcription, chunking, embedding, document parsing) — makes processing status fully observable |
| `transcript_chunks` | The retrievable unit: text + timestamps + `pgvector` embedding + denormalized org/app/source-status for fast filtering |
| `assistant_conversations` / `assistant_messages` | Chat history per user per organization |
| `assistant_citations` | Persisted citations for each assistant answer (source, chunk, timestamps, quoted evidence, similarity, rank) |
| `feedback` | Helpful / not-helpful ratings + optional comment on an assistant message |
| `usage_metrics` | Daily rollup per organization: stored/processed video minutes, questions asked, active users |
| `audit_logs` | Login, invites, uploads, processing, approvals, deletions, role changes, assistant answers |

All tables use UUID primary keys, `created_at`/`updated_at` timestamps, and
indexes on every foreign key used in a tenant-scoped `WHERE` clause. The
`transcript_chunks.embedding` column is a `pgvector` `VECTOR(384)` (dimension
configurable via `EMBEDDING_DIM`) with an IVFFlat cosine-similarity index
(`ix_transcript_chunks_embedding_cosine`) created in the initial migration.

## Video/document ingestion pipeline

Implemented in `app/services/pipeline.py` (`run_pipeline`), invoked either by
a Celery task (`app/workers/tasks.py::process_source`, real async path) or
directly by the seed script (synchronous, so seed data goes through the
identical code path as a live upload). One `VideoProcessingJob` row is
written per stage so processing is fully observable in the UI.

**Video sources:**
1. Original file stored in MinIO/S3 under `orgs/{org_id}/sources/{source_id}/{filename}` (private bucket, only ever accessed via short-lived presigned URLs).
2. `ffmpeg` extracts a mono 16kHz WAV track (`app/services/media.py`).
3. The configured STT provider transcribes it into timestamped segments (`app/services/stt.py`).
4. `app/services/chunking.py::chunk_transcript` greedily groups consecutive segments into 30–90s chunks, breaking on sentence boundaries, so every chunk is both a coherent quote and a playable clip.
5. Each chunk is embedded (`app/services/embeddings.py`) and stored as a `TranscriptChunk` row with its exact `start_seconds`/`end_seconds`, topic, org/app/source-status metadata.
6. The source moves to `awaiting_review`.

**Document sources** (PDF/DOCX/Markdown/plain text) follow the same shape
minus audio/transcription: text is extracted (`pypdf` / `python-docx` / raw
read), then paragraph-chunked (`chunk_document`) and embedded identically.
Document chunks have `start_seconds = end_seconds = 0` and are cited as a
document reference rather than a video clip in the UI.

### Source status state machine

```
uploaded → queued → processing → awaiting_review → approved → indexed
                         ↓                ↓            ↓
                       failed         archived     archived
```

Enforced centrally in `app/models/enums.py::SOURCE_STATUS_TRANSITIONS` and
checked by `app/api/v1/sources.py::_transition` — any API call attempting an
invalid transition (e.g. approving a source that isn't `awaiting_review`)
gets `409 Conflict`. Only `approved`/`indexed` sources (and their chunks,
via the denormalized `source_status` column kept in sync by
`app/services/source_state.py::sync_chunk_status`) are ever returned by
retrieval — this is what makes "approval gates visibility" a property of the
query itself, not just something the UI happens to hide.

Deletion is deliberately two-step: a source must be `archived` before it can
be hard-deleted (`DELETE /sources/{id}` returns `409` otherwise), so there's
no one-click path to permanently losing content.

## RAG (retrieval-augmented generation) flow

Implemented in `app/services/rag.py::answer_question`, called from
`POST /api/v1/assistant/ask`:

1. The caller's organization is already resolved by the auth dependency — every retrieval query is scoped to it, non-negotiably.
2. The question is embedded with the configured embeddings provider.
3. `transcript_chunks` are queried with `ORDER BY embedding <=> :query_vector` (pgvector cosine distance), filtered to `organization_id = :org` AND `source_status IN ('approved', 'indexed')` AND (if supplied) `application_id`, `application_version`, `environment`, and the caller's `role` against each chunk's `audience_roles`.
4. If nothing clears `RAG_MIN_SIMILARITY`, the **fixed** response is returned — *"I could not find an approved source that answers this question..."* — and the LLM is never called. Confidence is `none`, citations are empty.
5. Otherwise, the retrieved chunks (and only those chunks) are handed to the LLM provider, which must return `{answer, steps, follow_up_questions}`. The mock provider is template-based and literally cannot emit text absent from the retrieved chunks; the real OpenAI/Ollama-compatible provider is instructed via system prompt to answer only from the provided context and asked for strict JSON.
6. Citations, related clips, and confidence are computed independently of the LLM's output, straight from retrieval metadata (`CitationResult`/`RelatedClip` dataclasses) — so a citation can never reference another organization, an unapproved source, or a source the LLM "made up," regardless of what the LLM returns.
7. The conversation, message, and citations are persisted; usage metrics (`questions_asked`, `active_users`) and an audit log entry (`assistant_answer_generated`) are recorded.

Response shape (see `app/schemas/assistant.py::AskResponse`):

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "answer": "...",
  "steps": ["...", "..."],
  "confidence": "high | medium | low | none",
  "citations": [
    {
      "source_id": "uuid",
      "chunk_id": "uuid",
      "source_title": "ClientVantage KT — Creating a New Client Account",
      "start_seconds": 68.75,
      "end_seconds": 75.35,
      "quoted_evidence": "...",
      "confidence_score": 0.41,
      "is_archived": false
    }
  ],
  "related_clips": [...],
  "follow_up_questions": [...]
}
```

### Why the mock embeddings/LLM providers are trustworthy for a demo

The mock embeddings provider (`MockEmbeddingsProvider`) is a deterministic,
stopword-filtered, hashed bag-of-words vector — not a neural embedding, but
because it's still a normalized vector compared by cosine similarity, it
rewards genuine vocabulary overlap between a question and the source
material and (after stopword removal) does *not* fire on generic questions
that share only function words with indexed content. The mock LLM provider
never free-generates text: for "how do I" questions it extracts and
chronologically orders sentences from the single best-matching source; for
other questions it stitches together the top sentences from the top chunks.
Every word in a mock-mode answer traces back to a specific retrieved chunk.

## Security

- Passwords hashed with bcrypt (`passlib`). JWT access tokens (short-lived) + refresh tokens (14-day default, rotated on use), `python-jose`, `SECRET_KEY` from environment only — never hard-coded, never exposed to the frontend.
- Authorization enforced per-request via FastAPI dependencies (`get_current_user`, `get_current_membership`, `require_role`), not just in the UI.
- Object storage is private; the API hands out short-lived presigned URLs (`app/services/storage.py::get_presigned_url`, 15-minute default) rather than public links.
- Upload validation: file extension allowlist, per-type size limits, rejection of empty files (`app/api/v1/sources.py`).
- Rate limiting on `/auth/*` and `/assistant/ask` (`app/core/rate_limit.py`) — in-process sliding window for the single-instance MVP; see `docs/operations.md` for the Redis-backed upgrade path for multi-replica deployments.
- Structured logging via `structlog`; HTTP exceptions are logged with status/path/detail without leaking stack traces to clients.
- Data retention is a first-class organization setting (`organizations.retention_days`), editable by Org Admins.
- No facial recognition, surveillance, or employee-monitoring features exist or are planned in this codebase.
