# Architecture and scaling

## Request and processing paths

```text
Browser / companion extension
            │ HTTPS
      CDN + TLS gateway
       ├── versioned static frontend assets
       └── /api/* (no cache) ── FastAPI replicas
                                  ├── PostgreSQL + pgvector
                                  ├── Redis (rate limits, task broker)
                                  └── private S3 objects / signed playback URLs
                                             ▲
                                  Celery ingestion workers
                                  └── STT / embedding / LLM providers
```

The Angular application is a static build. Nginx serves it and proxies same-origin `/api/` requests. A CDN can cache hashed assets globally. Authenticated API responses must bypass edge caches. The API is stateless between requests except for shared database/Redis state; ingestion runs separately in Celery. Object content lives outside containers.

## Tenant boundary

Membership connects user, organization and role. Organization-scoped requests resolve the authenticated caller's membership using `X-Org-Id`. Every tenant resource access must constrain organization and role/audience; a guessed object ID is not authorization. Missing and inaccessible resources use a non-disclosing not-found response.

Isolation is enforced in application queries and API dependencies, supported by regression tests. PostgreSQL row-level security is not configured in this repository. A security review must include new raw SQL, background jobs, join conditions, citations, exports and administrative endpoints when they are added.

## Data map

| Tables | Meaning |
|---|---|
| users, organizations, memberships, invitations | Identity, tenant boundary and access |
| organization_plans | Plan metadata; not a payment provider or complete entitlement engine |
| applications, application_modules | Knowledge catalog |
| sources, video_processing_jobs | Original source metadata, status and processing stages |
| transcript_chunks | Text, timestamps, embeddings and audience metadata |
| assistant_conversations, assistant_messages, assistant_citations | User conversations and persisted evidence |
| feedback, usage_metrics, audit_logs | Product feedback, usage rollups, accountability |

UUID keys identify records. Migration files define the actual schema. Vectors are currently dimension 384; changing an environment variable alone does not change the database. A model/dimension change requires a migration, a complete re-embedding plan, a rebuild of the vector index and a retrieval-quality check. Do not mix embedding models within an index.

## Ingestion and retrieval

Uploads enter a private organization-prefixed object key. Video audio is extracted with ffmpeg/ffprobe into configurable, offset-tracked WAV windows, transcribed into timed segments, chunked and embedded in bounded batches. Documents are parsed, chunked and embedded. Processing stage rows expose progress. Successful ingestion enters review; approval makes the content eligible for retrieval, and archive removes eligibility. Source status and denormalized chunk status must remain consistent. The LLM runs during question answering over approved retrieved evidence, not during the upload pipeline.

Questions are embedded and matched only against permitted, approved/indexed chunks. Evidence is passed to the model; citations are derived from selected chunks. Missing evidence produces a no-answer response. Confidence labels summarize retrieval evidence and are not calibrated probabilities. Real model output can still be wrong; a citation helps users inspect evidence and does not prove that every answer claim is supported.

## Scaling plan

1. Start with managed PostgreSQL supporting pgvector, managed Redis with persistence and `noeviction`, private S3-compatible storage, one API deployment and a separate bounded worker pool.
2. Add API replicas behind a health-aware load balancer. Keep auth/rate-limit state shared. Use one migration job before rollout and avoid per-replica migrations.
3. Size database connections explicitly: `API replicas × API_WORKERS × (DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW)`, plus worker processes and migration/admin headroom, must stay below the database connection budget. Add a tested connection pooler when needed.
4. Scale workers by queue age and CPU/memory, with provider concurrency/cost ceilings. Large files occupy object storage plus extraction scratch space and provider payloads. Test maximum file sizes under concurrent ingestion before raising limits.
5. Benchmark tenant-filtered vector queries on representative data. Tune or replace the initial IVFFlat index only with recall and latency evidence; tiny seed datasets are not a capacity benchmark.
6. Introduce direct multipart uploads with scoped presigned URLs, quarantine scanning, resumable ingestion, a transactional outbox, reliable dead-letter handling and per-tenant queue fairness before a high-volume ingest offering.

The supplied Compose production profile runs on one host and does not implement autoscaling, multi-zone failover, sticky load balancing, a Kubernetes operator or disaster recovery orchestration. Translate the same images and release steps to the chosen container platform for those capabilities. No concurrent-user capacity is certified yet.

## Current boundaries

List APIs and the current assistant/provider call pattern need workload-specific load testing. Plan metadata is not a hard spending limit. Retention days are a stored preference, not a scheduled deletion job. A durable queue does not by itself prove exactly-once processing: inspect partial writes and status before retrying an interrupted job. Source objects and database backups need a coordinated restoration plan.
