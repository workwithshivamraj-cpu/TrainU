# Operations and recovery

See [runtime profiles](runtime-profiles.md) for the deterministic Compose demo, host-run real-AI proof of concept and production template, including startup/preflight commands and their current limits.

## Private local LLM for development

The assistant supports Ollama through its OpenAI-compatible local API. Install Ollama from its official distribution, pull an instruction model whose license fits your use, and point the API at `http://127.0.0.1:11434/v1`. For the TrainU demo, `qwen2.5:7b` is installed locally and served by Ollama; the assistant sends prompts and retrieved approved passages to that loopback endpoint only. This keeps this development inference request on the same machine. The model is Apache-2.0 licensed according to the Ollama library entry. Treat model files and prompts as local data, and bind Ollama to loopback unless there is an intentionally secured private deployment.

Example backend environment:

```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5:7b
EMBEDDINGS_PROVIDER=ollama
EMBEDDINGS_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDINGS_API_KEY=ollama
EMBEDDINGS_MODEL=all-minilm
EMBEDDING_DIM=384
```

The local host demo uses Qwen2.5 7B (its observed digest and generation parameters are in `infrastructure/model-lock.json`) for answer generation and all-minilm for semantic retrieval; the installed all-minilm model returns 384-dimensional vectors to match the existing pgvector column. The assistant UI labels each result with the provider/model returned by the API. It shows “No model call” when no approved evidence passes retrieval, and handles greetings as conversation instead of searching for a training record. After changing embedding models, re-embed every searchable chunk with the selected model before querying; never mix vectors from different embedding spaces. The local demo's seeded transcript/STT remains scripted. Ollama is a local inference option, not a production security guarantee: restrict network access, protect model endpoints and data, review license/weights, and test output quality for your workload.

## Ownership

Before launch, name a service owner, release owner, security contact and backup/recovery operator. Put actual contact paths in the customer support surface. Assign alert coverage and escalation windows; no 24/7 support or SLA is implied by this repository.

## Health and observability

API `/health` is process liveness; `/health/ready` checks backing dependencies. Frontend `/health` verifies static serving. Worker health uses Celery inspection. Probe ready instances before sending traffic; use queue backlog age and successful task completions to detect a worker that is alive but stalled.

Ship application/container logs to access-controlled storage. Measure request count, 4xx/5xx rates, latency percentiles, auth/rate-limit failures, database pool/connection saturation, Redis memory/queue age, ingestion stage durations/failures, object-store errors, provider rate limits/cost, and filesystem scratch pressure. Alert thresholds must come from staging/pilot baselines. Avoid recording credentials, presigned URL query strings, invitation tokens or customer transcript/question bodies in general logs. Distributed tracing/central metrics collection require deployment integration.

## Release and rollback

1. Identify the commit and immutable image digests; require passing CI and launch gate evidence.
2. Confirm backup freshness and one successful isolated restore drill. Assess schema compatibility with the previous application version.
3. Run the migration as a single release job. Do not start a migration concurrently on every API/worker replica.
4. Roll out API/worker/frontend, check readiness and execute a known tenant workflow.
5. If a regression occurs, halt rollout. For a compatible schema, restore the prior image pair. For an incompatible schema, use the tested forward-fix or coordinated database restore plan; `alembic downgrade` is not an automatic safe rollback.
6. Record the incident, affected tenants, data impact, actions and validation results.

When redeploying a Compose frontend after backend container IP changes, recreate/reload Nginx so its upstream DNS resolution is refreshed. A production orchestrator should provide a stable service address.

## Backup policy to configure

Use managed PostgreSQL point-in-time recovery plus encrypted, access-controlled backups in an independent failure domain. Enable private object-store versioning and lifecycle policies. Database metadata alone cannot restore videos/documents. Redis durability protects queued work but is not the authoritative content backup. Set retention and recovery objectives with the actual customer contract; there are no measured RPO/RTO guarantees yet.

The repository includes `scripts/backup-db.sh` for custom-format logical backups and a checksum. It reads libpq environment settings (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGSSLMODE`, `PGSSLROOTCERT`, `PGPASSFILE`) so passwords do not appear in the process argument list. Use a PostgreSQL client compatible with the server major version. Run it from a protected operator host and upload the output to encrypted off-host backup storage.

```bash
bash scripts/backup-db.sh /protected/trainu-backups
```

## Restore drill

1. Create an isolated empty database/network and an isolated restoration of the matching media bucket versions. Keep live applications disconnected from the restore target.
2. Verify backup checksum, decrypt through the approved secret flow, and restore with `PG*` settings pointing at the isolated database. `scripts/restore-db.sh` refuses a populated public schema and requires `TRAINU_RESTORE_CONFIRM` equal to the target database name.
3. Run the matching application image and appropriate migrations. Validate tenant/member counts, membership denial across two tenants, source/chunk counts, approval state and a known citation/playback. Verify all expected media objects exist.
4. Measure the recovery duration and record the recovery point. Decide whether the measured result satisfies the agreed objective.
5. A live cutover requires a coordinated write freeze, worker drain, latest recoverable data/object state, endpoint switch, functional verification and controlled resume. Avoid two active writers against divergent restored/live databases.

Never run the backend test suite against a customer database: its fixture drops and recreates tables.

## Failed or interrupted ingestion

Inspect the source failure reason and stage jobs, correlate worker/provider logs, and check object existence. Fix the underlying provider, storage, file-format or capacity issue. Content owners can retry a failed source where the retry endpoint/UI is available. A task stuck in `processing` after an abrupt worker failure requires inspection before recovery; do not blindly queue duplicates or mark it approved. A complete reconciliation/outbox/dead-letter service remains a scale workstream. Archive an unusable source and upload a corrected replacement when appropriate.

For provider outages, limit new ingestion, preserve originals and avoid repeated paid API retries. For Redis failure, restore broker availability and inspect tasks/status before resuming workers. For a database outage, fail readiness, stop write traffic and follow the managed database failover procedure.

## Security incident and data requests

Revoke the affected integration credentials, restrict affected access, retain necessary audit evidence and determine tenant/data exposure. Rotate application signing secrets only with an understood session invalidation plan. Coordinate customer communication through the service owner's approved process. Restore normal operation after containment and verification, then add a regression test or control for the cause.

Retention days are metadata until a scheduled deletion mechanism is implemented. Account/organization export and deletion currently require an authenticated support request, identity/authority checks and an operator procedure covering SQL records, object versions, provider copies and backup retention. Do not promise instant erasure or an automatic retention policy. Document the actual completed action and exceptions for each request.
