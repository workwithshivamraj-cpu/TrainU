# Deployment and CDN

## Deployment contract

`docker-compose.yml` is a local demo stack. `docker-compose.production.yml` is a separate profile that uses existing managed services and tested application images. It does not provision an account, TLS certificate, DNS, managed database, CDN or autoscaling. Complete the launch checklist before handling customer data.

The runtime requires PostgreSQL with pgvector and migrations applied, Redis reachable from API/workers, a private S3-compatible bucket, compatible transcription/embedding/LLM providers, and explicit HTTPS frontend origins. Production startup rejects unsafe demo/security settings. Use a staging environment with its own database, Redis namespace, bucket and credentials.

## Build and release

1. Run CI and record the commit, test results, dependency audit and container vulnerability scan. Build images with the root directory as the frontend context and `backend/` as API context:

   ```bash
   docker build -t trainu-api:release backend
   docker build -t trainu-frontend:release -f frontend/Dockerfile .
   ```

2. Push to your private registry and resolve immutable digests. Set `TRAINU_API_IMAGE` and `TRAINU_FRONTEND_IMAGE` to those digests in your protected runtime configuration. Pin and scan base image digests as part of the release process; checked-in tags are update channels, not immutable release attestations.
3. Copy `.env.production.example` to a secret-managed runtime file, replace every placeholder, and restrict access with `chmod 600`. Never commit it. Prefer workload identity for S3 by leaving explicit keys empty when supported by the runtime; otherwise use scoped credentials, never a storage root account. Exclude secrets from support bundles.
4. Provision the `vector` extension with a migration identity. The runtime database identity should have only the application data permissions it needs. If migration/runtime identities differ, run the migration job with the migration secret file, then start API/workers with the runtime file.
5. Take a recoverable database backup, validate the restore, and run the migration once:

   ```bash
   TRAINU_MIGRATION_BACKUP_CONFIRMED=verified-local-backup docker compose --env-file .env.production -f docker-compose.production.yml run --rm migrate
   docker compose --env-file .env.production -f docker-compose.production.yml up -d
   ```

   The confirmation is an operator assertion after the database and object-storage backup has been verified; it is not an automated restore check. Compose also has a migration dependency on fresh startup. Migration commands are idempotent; run exactly one release pipeline at a time. Migration success is required before application startup. [Docker documents dependency ordering](https://docs.docker.com/compose/how-tos/startup-order/).
6. Configure HTTPS ingress to the frontend's loopback port, then verify login, upload, worker processing, approval, citation playback, role denial and a second isolated tenant. Run `bash scripts/smoke.sh https://YOUR_DOMAIN` and probe API `/health/ready` through the private load balancer. Do not expose port 8000, PostgreSQL, Redis, or storage administration publicly.

## Managed service configuration

- **PostgreSQL:** use verified TLS, automated point-in-time recovery and monitoring. Provide the correct CA bundle for `sslmode=verify-full`; the sample public trust store may not contain your provider's private root. Limit connections according to the formula in architecture.md. Test the exact supported pgvector version.
- **Redis:** use TLS/auth, private networking, persistence and `noeviction`. Both task delivery and distributed rate limits depend on it. The sample `rediss` URL requires certificate verification; install your provider CA when needed. Monitor queue age and memory, and validate failover with workers running.
- **S3:** pre-create the private bucket with encryption, public access blocked and versioning/lifecycle configured. Grant only bucket listing/location plus object get/put/delete on the intended prefix. Provider IAM permissions and access keys belong to server processes only. Bucket auto-creation is a local convenience; production may pre-create it and deny create permissions.
- **AI providers:** use project-scoped secrets, limits and cost alerts. Validate regional processing, provider terms and the payloads sent. Production uses real providers; mock answers are not an acceptable launch validation.
- **Video processing:** API/worker images need `ffmpeg` and `ffprobe`. TrainU extracts mono 16 kHz PCM WAV in `STT_AUDIO_SEGMENT_SECONDS` windows (default 600 seconds, configurable from 60 to 1800), transcribes each window, and offsets transcript timestamps back to the original video. Ten-minute PCM windows are about 19.2 MB; providers can impose lower request or duration limits, so validate the selected endpoint and lower the window when needed. Video containers/codecs still need to be readable by the included FFmpeg build and the file must have an audio track; silent, encrypted, corrupt, or unsupported inputs fail with a source processing error.
- **Transcription, embeddings, and answer inference:** set real `STT_PROVIDER`, `EMBEDDINGS_PROVIDER`, and `LLM_PROVIDER` values with endpoint/model settings and credentials where required. Upload processing transcribes, chunks, and embeds in bounded batches (`EMBEDDING_BATCH_SIZE`, default 64); the LLM runs later when a member asks a question over approved evidence. Demo mode deliberately uses mock STT/embeddings/LLM and cannot validate real accuracy. Validate provider payload, duration, regional handling, rate limits, latency, and spend before offering uploads to customers.

## Edge/CDN behavior

The static build already has content-hashed script/style filenames. The supplied Nginx configuration sets one-year immutable caching for those, no-store for HTML/client routes and API responses, a short TTL for documents, and ordinary caching for unversioned assets. It also adds anti-framing, MIME-sniffing, referrer and content-security headers.

Configure the CDN with these distinct routes:

| Path | Origin / behavior |
|---|---|
| `/api/*` | API gateway, cache disabled for every method/status; forward Authorization, X-Org-Id, Content-Type and relevant request headers |
| Hashed `.js` / `.css` | Static origin, immutable cache; compression enabled |
| `/index.html`, SPA routes | Static origin, no-store or explicit revalidation; SPA fallback only for frontend routes |
| `/docs/*` | Static origin, short cache; files are generic project documents, never secrets |
| Private media | Keep API-issued S3 presigned URLs initially; do not put a public cached media path in front |

A private media CDN is a later enhancement. It requires edge authorization, signed URL/cookie generation, restricted origin access and expiry/revocation testing. Substituting a CDN hostname into an S3 signed URL is invalid. See [CloudFront private content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-overview.html) and [signed URLs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-signed-urls.html).

Terminate TLS at a trusted gateway, redirect HTTP to HTTPS and enable HSTS there after verification. Restrict origin reachability so clients cannot bypass gateway controls. Trust forwarded client headers only from that gateway; the supplied private Compose network permits Nginx to forward requests, but a different platform must narrow trusted proxy configuration to its actual network. If the outer ingress replaces headers, verify per-client rate limits across it before launch.

## Resource envelope and rollout

The production profile starts with bounded CPU/memory, nonroot users, dropped capabilities, read-only filesystems and temporary scratch space. The worker needs enough scratch/memory for simultaneous media extraction; increase only from measured workloads. The profile is not highly available by itself. Use a container platform/load balancer for multiple API instances, controlled worker replicas, readiness routing, a single migration job and rolling releases. Keep a previous known-good image pair and use backward-compatible database migrations for rollback.
