# TrainU production-oriented POC plan

## Goal and boundaries

Complete a demonstrable, locally runnable SaaS POC for India-first IT and operations teams without paying for hosting, APIs or payment services. Keep Angular, FastAPI, PostgreSQL/pgvector, Redis, Celery, private S3-compatible storage and Docker Compose. Do not deploy publicly, process real payments, buy services or publish the browser extension.

Supported first-release workflow: English, Hindi and Hinglish conversations and video transcription; speech plus visible screen-text indexing; videos up to 2 hours / 2 GB; four organization roles; approved, cited answers and bounded excerpts; selected-text browser extension. Full visual action recognition, screen recording, courses/exams, enterprise SSO/SCIM, third-party actions and multiregion availability are out of scope.

Preserve current edits and demo data. Implement packages in order, split large packages into independently verifiable subtasks, update `docs/release-status.md` after each package, record evidence and the next action, and resume at the first incomplete item after interruption. A configured test, audit or CI workflow is not evidence that it passed. Completion means all local capabilities and gates pass; external prerequisites and the absence of a certification/deployment must remain explicit.

## Fixed implementation decisions

Amendment (2026-10-01): [model-provider-handoff.md](model-provider-handoff.md) defines configurable providers and the merged P/M execution order. Its model-selection rules supersede the fixed-model-only choice below; the local reference models and all P01–P18 acceptance gates remain.

- Local-only inference: existing Qwen2.5 7B through Ollama; no cloud fallback. Local multilingual `faster-whisper` large-v3-turbo, CPU INT8 by default. Local `intfloat/multilingual-e5-small` embeddings (384 dimensions), with separate query and passage encoding. Re-embed data when changing profiles; never mix profiles.
- Tesseract indexes English/Hindi text from one frame every five seconds, suppressing duplicates. Do not claim recognition of visual actions. A silent video is usable only if OCR finds useful text.
- Razorpay provider adapter and local payment simulator exercise the same subscription transitions. Mailpit captures local email. Production configuration must reject either simulator.
- Local and portable production Compose profiles, static-asset CDN-ready headers, no public API/media caching and no cloud provisioning. Preflight hardware/model readiness; allow one active generation and one ingestion job, queuing more.
- Plans are configurable demo fixtures, not approved offers: 14-day trial (5 seats, 5 GB, 60 total video minutes, 200 total answers); Team ₹19,900/month (25 seats, 50 GB, 20 video hours and 5,000 answers/month); Growth ₹49,900/month (100 seats, 200 GB, 100 video hours and 20,000 answers/month). No automatic overages. Every enabled role counts as a seat. Retries do not double count; failed/cancelled answers do not consume allowance; completed greetings and no-evidence answers do.
- OWASP ASVS 5.0 Level 2 is the security verification map, not a certification claim.

Keep tenant APIs under `/api/v1`. Browser auth becomes revocable opaque HttpOnly sessions with CSRF controls, verification, recovery, MFA and session management. Add resumable-upload operations; immutable source revisions and review history; asynchronous assistant request/status/cancel and paginated history; typed answer kinds (`conversation`, `grounded`, `clarification`, `no_evidence`); evidence-type/revision citations; billing/subscription and webhook interfaces; privacy export, trash and deletion operations. Update the Angular types, OpenAPI, tests and docs with every contract change. The synchronous assistant endpoint may remain as a compatibility wrapper.

## Ordered work packages

### P01 — Workspace, test safety and public-document boundary

- Make destructive tests require explicit test mode, an allowlisted `trainu_test` database URL, reset opt-in and isolated object storage; apply environment overrides before imports. CI and `make test` supply the new explicit settings.
- Replace wildcard Markdown copying with a small public-doc allowlist and remove previously copied disallowed files from build output. Initially expose only customer-safe product/demo documentation; hide release status, demo credentials, commercial workings, deployment/operations/security/QA and unfinished privacy/terms templates.
- Preserve/back up demo state before future migrations. Consolidate API/worker environment loading so provider configuration cannot silently differ.
- **Acceptance:** unsafe test targets abort before connecting or mutating; production assets contain no internal docs or credentials; preserved local demo still works.

### P02 — Reproducible zero-cost runtime

- Separate deterministic test, real-AI POC and production profiles. Add local mail, scanning and model readiness. Pin dependencies, images and model revisions; add setup/download/start/stop/diagnostic commands.
- Production rejects demo accounts, mock AI, simulated billing and development secrets. POC visibly labels simulated payment and captured mail. Preflight RAM/disk and resolve native Ollama/container networking without exposing the model port.
- **Acceptance:** clean documented startup succeeds; missing models/services give actionable health failures.

### P03 — Account security and recovery

- Replace browser token persistence with hashed opaque revocable sessions, HttpOnly cookies, origin checks and CSRF protection. Use secure production cookie flags and localhost-only development exceptions.
- Add verification/resend throttling, password recovery/change, session list/revoke, hashed one-time tokens with expiry/single use, password-reset session revocation and TOTP MFA (encrypted secret, hashed recovery codes). Require MFA for production organization administrators. Clear legacy browser tokens and cover multiple tabs/reload.
- **Acceptance:** full account journey works through Mailpit; replay, enumeration, CSRF and revocation tests pass.

### P04 — Tenant, role and invitation policy

- Centralize source visibility/management across lists, retrieval, history, citations, playback, exports and worker jobs. Viewers see allowed published material; contributors additionally manage submissions; owners/admins review workspace content; assistant retrieval always excludes unpublished content.
- Preserve last-admin protection under concurrent writes. Hash invitation tokens; add delivery/resend/revoke and reserve seats across pending invites. Add tenant-consistent constraints to relationships that could cross organizations. Operator actions stay audited; no customer impersonation.
- **Acceptance:** every endpoint/role combination passes against two tenants, inactive memberships and tampered IDs.

### P05 — Durable queues and correct usage

- Add transactional outbox delivery; attempt/checkpoint/heartbeat/lease data; stale-job recovery; three exponential retries for transient failures; permanent validation errors require correction. Separate interactive and ingestion queues with fair tenant dispatch.
- Add idempotent quota reservations/completion/release and count distinct active users correctly.
- **Acceptance:** crash, queue outage, duplicate delivery and retry do not lose jobs, duplicate content or double-charge allowance.

### P06 — Resumable, quarantined uploads

- Multipart initiate/sign/complete/status/abort API, server-owned object keys, size reservations, verified completion and cleanup of abandoned sessions. Enforce video 2 GB/120 minutes and documents 25 MB.
- Inspect true file type, parser/decoder support and file content. Scan before parse or play. Bound document pages, decompression, memory, runtime and scratch space. Rejected/unscanned objects remain private.
- **Acceptance:** interrupted upload resumes; disguised, malicious and oversized files fail; valid content processes once.

### P07 — Real multilingual speech and screen-text ingestion

- Transcribe offset-tracked audio segments locally; preserve language, segment and timestamp provenance. Sample frames every five seconds, suppress duplicates and OCR English/Hindi text with timestamps. Index silent videos only when useful visible text exists and disclose partial coverage.
- Parse text, Markdown, PDF and DOCX; add bounded OCR for scanned PDFs and preserve page/section references. Show real stage progress and actionable retries/failures.
- **Acceptance:** English/Hindi/Hinglish fixture videos and documents become reviewable without seeded transcripts, including silent OCR-only and empty-content failures.

### P08 — Immutable revisions and safe approval

- Migrate existing content into initial revisions without breaking stable source IDs. Keep published revision active while a replacement draft processes and is reviewed. Review transcript/OCR corrections and re-embed changed evidence before publication.
- Atomically publish with reviewer/time/change note/audience/application-version/environment. Track ownership/reminders/supersession. Retrieve active published content by default; version filters must be explicit.
- **Acceptance:** draft never leaks and published text can never pair with an old embedding.

### P09 — Multilingual hybrid retrieval

- Track embedding model revision/dimension/preprocessing. Re-embed into a new generation, validate completeness and switch atomically with rollback; do not mix dimensions/models.
- Combine tenant-filtered vector and PostgreSQL lexical retrieval with reciprocal-rank fusion; filter permissions and active revisions before evidence selection, including neighboring chunks. Respect application/version/environment. Clarify ambiguous task selection.
- **Acceptance:** paraphrase and cross-language searches find the correct steps; profile mismatches fail safely.

### P10 — Conversational, grounded assistant

- Supply at most six recent history turns within a token budget. Handle greetings/help/acknowledgements/clarification naturally, while keeping conversation distinct from company-fact answers.
- Validate typed model output; allow one format repair then return a retryable error. Never attach a fallback citation when evidence IDs are invalid. Procedural answers require supporting authorized citations and must state gaps/conflicts honestly.
- Add new/list/paginated/rename/delete conversations, async request/status/cancel, one pending request per conversation and permission rechecks before replaying history. Hide derived answers when supporting source access is revoked.
- **Acceptance:** greetings, multilingual follow-ups, step-specific questions, unrelated/missing evidence, conflicting procedures and malicious source instructions behave correctly.

### P11 — Bounded excerpts, voice and chat UX

- Generate actual server-ranged MP4 excerpt assets from validated evidence, cache by revision/range and permission them like the source. Use excerpt first; full video is separate, explicit opt-in. Short-lived URLs and expiry behavior are required.
- Keep mute, stop, captions and constrained seek; test actual duration. Replace browser-cloud speech recognition with reviewed local transcription before submit. Add Stop reading; use local OS voices where present and state when unavailable. Show actual queue phases; preserve input on error.
- **Acceptance:** text and local voice work in all three languages, excerpts are bounded and audio always has a stop action.

### P12 — Enforced plans and simulated/live-ready billing

- Atomically enforce members, storage, processing minutes and completed answers. Trial/active/pending/past-due/cancelled states. Razorpay adapter and local simulator share transitions. Raw-body signature verification, event-ID deduplication and out-of-order reconciliation against provider state; browser success callback never activates a plan.
- Renewal/failure/cancel-at-period-end/next-cycle changes, downgrade rejection when retained usage is over plan, usage warnings and invoice history. Tax settings configurable; live billing needs operator-approved configuration.
- **Acceptance:** duplicate/out-of-order webhooks, failed payment, quota races and cancellation cannot grant access or double-count. Use [Razorpay webhook validation guidance](https://razorpay.com/docs/webhooks/validate-test/).

### P13 — Privacy, export and deletion

- Soft-delete then retryable purge (never delete object before DB commit); restore trash up to 30 days; consistently purge originals/derivatives/vectors/history references. Organization export with manifest/checksums/expiry.
- Conversation retention defaults to 90 days; do not reinterpret existing source-retention settings to erase approved content. Retain approved sources until explicit deletion or disclosed workspace closure. Remove questions/transcripts/secrets/signed URLs from logs. Document backups and prevent restore from silently reviving purged records.
- **Acceptance:** cited-source purge failure, restore, export and integrity checks pass.

### P14 — Complete user and administrator journeys

- Onboard workspace to first approved source/answer; library search/pagination/filtering, upload progress, review inbox and useful bulk actions. Admin sees sessions/invites/usage/billing/exports/audit. Owner sees authorized aggregate feedback/unanswered topics without private chat leakage.
- Preserve light design; responsive, keyboard, focus, label, loading and empty states. Serve customer help only; operator documents require authenticated role-checked access.
- **Acceptance:** new organization completes workflow without database edits or hidden operator steps.

### P15 — Selected-text browser extension

- Keep minimal permissions/draft-before-submit. Validate URLs/text limits/encoding/sign-in/workspace switching. Add TU icons, versioned ZIP, privacy/support disclosure and Chrome/Edge screenshots/manual verification. Do not publish.
- **Acceptance:** selection reaches the right workspace as an unsubmitted draft; no page scraping.

### P16 — Operations and security controls

- Structured redacted logs, IDs, metrics, model/queue/disk health and support bundle. Consistent encrypted database/object backup manifest; restore in isolation and verify roles/sources/answers/playback.
- Harden parser/worker isolation, outbound access, secrets, container, headers and cache. Lock dependencies; generate SBOM/license notices. Secret/dependency/container/static analysis and authenticated local DAST. Map applicable [OWASP ASVS](https://owasp.org/projects/asvs?tab=main) requirements to code/test evidence.
- **Acceptance:** recovery is demonstrated; no unresolved exploitable high/critical finding or authorization flaw. No certification claim.

### P17 — Product and sales readiness

- Define supported promise/media/languages/limits/roles. Truthful pricing/demo/feature comparison, onboarding, FAQ, objections, demo script, pilot scorecard, support process and economics worksheet. Privacy/terms/data-processing/subprocessor documents contain visible operator/legal placeholders until approved.
- Measure activation, helpful answers, missing topics, pipeline success, latency and per-workspace resource use without invasive tracking. No fabricated customers, savings, uptime, certifications or production claims.
- **Acceptance:** every claim is verified or explicitly future scope.

### P18 — Release acceptance and handoff

- Full tests, real-model evaluation and all-role browser demo using processed multilingual videos; clean documented startup and restart recovery. Record model/dependency/image versions, commands, results, resource use, artifacts, unresolved gates and rollback. Leave POC running with operator quick-start.
- **Acceptance:** evidence supports “verified local release candidate”; no incomplete local coding hidden as an external prerequisite.

## Final verification gates

1. Auth/recovery/MFA/CSRF/replay/concurrency; every protected endpoint for four roles and two tenants; source revision/audience/archive access across search/chat/history/clips/export.
2. Upload interruption/type spoof/malware/parser/missing-media; duplicate jobs/crashes/partial embeddings/revision races; payment duplicate/out-of-order/failure/seat race/quota; deletion/restoration/export/backup integrity.
3. Freeze development and holdout multilingual AI sets before tuning. At least 120 questions (40 per language): paraphrase, cross-language, follow-up, no evidence, wrong app/version, OCR-only, prompt injection. Holdout targets per language: recall@5 ≥90%, supported-answer success ≥90%, citation-support precision ≥95%, critical-step/entity preservation ≥90%; timestamps ≥90% within 3 seconds; zero tenant/evidence disclosures or successful source-instruction attacks. Unsupported factual questions must abstain or clarify. Use human-reviewed evidence, not model self-grading.
4. Browser path: signup→verify→trial→invite→upload→process→review→approve→ask→excerpt/full source→feedback→simulated billing→export/delete. Include keyboard, mobile, reload, multi-tab and interruption.
5. Load ten synthetic tenants × 10,000 chunks, 20 concurrent non-AI clients, configured AI/ingestion limits. Non-AI p95 <1 second and unexpected error rate <1% on the measured host. Report observed AI and ingestion capacity; make no assumed SLA. Exercise full 2-hour media/2 GB boundary and outages/backpressure/fairness.

## External launch prerequisites

Outside this no-spend implementation: hosting/domain/TLS/production secrets/independent backups; merchant approval/live webhook/tax/invoice setup; real sender-domain email; legal entity/support contacts/customer-contract review; production load/recovery/security validation; human quality acceptance on customer data; explicit authorization to deploy, charge or publish the extension. Report each separately. If local hardware/model quality misses a gate, record the measured failure; never lower the bar to claim completion.

## Progress ledger

| Package | State | Evidence / next action |
|---|---|---|
| P01 | verified locally | 12 test-boundary checks passed; full isolated backend suite passed 43/1 skipped; Angular production docs allowlist passed; private DB/object snapshot verified (26 objects, checksums, `pg_restore --list`); API and frontend smoke checks pass. No demo rows or source objects were removed. |
| P02 | in progress | ARM64 backend image rebuilt with CPU-only PyTorch, pinned AI packages and FFmpeg/OCR; `pip check`, model imports and Tesseract English/Hindi pass. Mailpit and both pinned model snapshots are ready locally. E5 offline CPU inference passes. A separate clean Compose project passed readiness from an empty DB and object store (local bucket auto-created), survived API/worker restart, and returned HTTP 200 from its frontend; its test volumes were removed afterward. The live demo API and frontend at 8000/4300 are now responding; a full `make up` container launch encountered an existing native API port 8000 collision, so it was not treated as a passing container-start check. Offline Whisper transcription already passed with 11 English segments; this is not end-to-end ingestion or multilingual quality acceptance. Host reported 16 GiB total / 2.6 GiB available and 267.8 GiB free disk during diagnostic; candidate image measured about 3.01 GB. ClamAV ARM64 compatibility and a real scan remain unverified; model-quality/hardware and complete browser acceptance also remain. |
| P03–P18 | not started | Start each package only after the prior package has an acceptance record. |

## Subtask evidence register

Add a row when implementation begins; keep blocked evidence and the next action explicit. A prior demo or configured workflow is historical context, not proof of the current gate.

| Subtask | Dependencies | Implementation changes | Acceptance check | Evidence / state | Next action |
|---|---|---|---|---|---|
| P01.1 destructive-test boundary | Existing pytest DB fixture and CI invocation | Added fail-closed pre-import environment guard; explicitly selects only local `trainu_test`, Redis DB 1, test bucket and allowlisted local S3 endpoint; updated Make and CI settings. | Reject unsafe targets before app import; accept only explicit safe test config. | `PYTHONPATH=backend pytest -q backend/tests_environment` — 12 passed; Ruff and compile pass. Full backend integration: 43 passed, 1 skipped; only deprecation warning. | Keep database/bucket/Redis values explicit in any new test entry point. |
| P01.2 public-doc boundary | Existing wildcard docs copier and Help links | Copy only product/demo docs, remove stale generated Markdown and remove Help links that exposed internal runbooks/templates. | Build assets contain the exact allowlist only. | Angular production build passed; public and distribution docs directories each contain only `product.md` and `demo-videos.md`. | Keep allowlist check in CI and re-check when doc links are added. |
| P01.3 demo/config preservation | Existing shared Compose API/worker anchor; local services/data | Confirmed Compose API, worker and migration use the same backend env anchor. Added `scripts/backup-local-data.sh` plus a private S3 bucket downloader with SHA-256 manifest. Make and CI snapshot before migration; the migration entrypoint requires a one-job backup confirmation. Backup restores previously running services with `docker start` against captured container IDs to avoid starting dependencies. | Preserve demo; only authorize migration after database and object snapshot succeeds. | Private snapshot has verified SHA-256 for 28 files (database dump, 26 objects and storage manifest), object manifest count 26, and successful `pg_restore --list`. Current DB is at Alembic head `92f67a531c10` with 5 users, 1 organization and 5 sources; health checks pass. The first backup attempt failed during checksum writing and restarting the worker also re-started its migration dependency; that job exited 0 and current revision is at head. The corrected backup is complete after that event, and future restore starts captured containers directly without dependencies. | Exercise a restore into an isolated local database and storage namespace at P16. |
| P02.1 runtime diagnostic | P01 test/document boundary | Added `scripts/doctor.sh`, Make target and runtime profile guide for deterministic demo, host real-AI POC and production template. Script reports tool/model readiness without echoing credentials. | Missing local media/model requirements must be actionable; production configuration remains fail-closed. | `bash -n` passes. Initial diagnostic correctly reported missing host capabilities before image/cache setup. Current `bash scripts/doctor.sh poc` passes against the built image, pinned Ollama digest, loopback Mailpit and both model snapshots. Host RAM available was 2.6 GiB and free disk 267.8 GiB at check time. | Keep diagnostics read-only and run after environment changes; record its result at final acceptance. |
| P02.2 dependency and model locks | P02.1 | Pinned Python AI packages, CPU-only PyTorch install, base image digests, Qwen settings/digest, and immutable Whisper/E5 revisions; added lock validators/download/cache diagnostics. | Rebuild image without CUDA wheels; verify imports, cache identity, dimensionality and normalized embeddings offline. | CI full `pip-audit` found two advisories for the PyTorch 2.10.0 pin. Updated the requirement and CPU wheel to patched `2.14.1` / `2.14.1+cpu`; full dependency audit now reports no known vulnerabilities. ARM64 image build, `pip check`, imports and full backend suite passed on 2.14.1. The cache still has both immutable E5/Whisper snapshots; the earlier measured offline E5 and Whisper inference used 2.10.0 and must be repeated on 2.14.1. | Repeat offline E5 and Whisper inference on patched image, then add bilingual model-quality evaluation; do not mix E5 vectors with the current embedding generation. |
| P02.3 media and OCR runtime | P02.1 | Added FFmpeg, ffprobe and English/Hindi Tesseract to the backend/worker image. | Verify tools and both OCR language packs in the candidate image. | Image reports FFmpeg/ffprobe `7.1.5`, Tesseract languages `eng`, `hin`, `osd`; package and import checks pass. | Continue with P07 real ingestion integration; keep video duration/size limits enforced at upload and processing stages. |
| P02.4 local mail and model cache | P02.1 | Added loopback Mailpit and persistent Compose model-cache volume plus `make models-container`; downloaded immutable E5 and Whisper snapshots. | Mailpit readiness and model-cache diagnostics pass without cloud credentials; app should clearly label captured/simulated providers. | Mailpit readiness endpoint responds; `make doctor PROFILE=poc` recognizes both cached models. Snapshot cache is approximately 1.6 GB. Account mail is not connected (P03); ClamAV is configured but not run on this ARM64 host. | Wire email with P03; exercise malware scanning with P06 and track platform compatibility. |
| P02.5 assistant visual interaction | P02 UI request | Astra interaction direction was implemented with Luna: light assistant empty state, draft-only quick prompts, compact input, conditional citation pane, short reveal/hover motion, and reduced-motion handling using Motion JS. | Verify the production bundle, live browser rendering and that quick prompt click only drafts content. | Angular production build passes (417.26 kB raw initial; assistant lazy chunk 80.58 kB raw); live browser showed all three prompts and manual click placed the prompt in the composer without sending. Playwright E2E browser is unavailable locally; automated browser acceptance remains outstanding. | Keep motion short and non-essential; validate keyboard and narrow viewport with Playwright once browser is installed. |
| P02.6 isolated clean startup/recovery | P01.3 backup boundary; P02.1–P02.4 | Used a separate `trainu-acceptance` Compose project, isolated ports and fresh disposable DB/storage volumes. Added explicit local-only empty-bucket bootstrap on API startup; the production profile rejects this setting. Restarted API/worker, then removed only the acceptance project and its volumes. | New services reach readiness from empty storage without demo seeding; restart preserves readiness; production does not create buckets implicitly. | Passed: clean DB/Redis/storage returned ready, bucket was created by API startup, frontend returned 200, API/worker restart recovered healthy. Full isolated backend suite: 44 passed. Current local native API and Angular frontend at 8000/4300 respond after startup recovery. `make up` also surfaced the native API's existing port 8000 bind conflict, so Compose's backend/frontend launch is still not verified. | Resolve local native-vs-Compose port ownership in setup instructions/doctor, then close P02 scanner/platform and model/hardware checks. |
| M01.1 provider registry schema and safe configuration | P01; P02 runtime image | Added strict versioned registry models, exact adapter/capability matching, deterministic manual/priority selection, disabled-profile handling, legacy-setting translation, optional `AI_PROVIDER_CONFIG_PATH`, operator-only hosted consent, approved environment secret references, local endpoint checks, local Qwen/Whisper/E5 profiles, and a redacted validation CLI/doctor hook. Existing mock defaults and runtime provider factories remain unchanged pending M02. | Validate the sample and reject malformed dimensions, unapproved secrets, public endpoints labeled local, hosted profiles without consent or credential references, adapter mismatches and unavailable auto candidates; make no network requests. | Provider registry tests: 11 passed; production settings and log-redaction checks bring the focused total to 22 passed. Backend-image validator accepts all three local profiles and reports hosted disabled. Full backend suite: 44 passed. `git diff --check` passes. No provider endpoint or demo database was contacted by registry tests. | Complete the scanner compatibility and local-runtime setup gates, then implement M02 adapters and real local Qwen smoke before continuing to P03/M03. |
