# TrainU model portability and release handoff

Created: 2026-10-01. State: **in progress; M01.1 registry/config validation is implemented and verified locally**.

## 1. Outcome and source of truth

Implement configurable AI providers while completing the application release described in `docs/release-plan.md`. That document's P01–P18 requirements and acceptance thresholds remain mandatory. This handoff amends its fixed-model decision and defines the execution order below. `docs/release-status.md` records actual evidence; this document is not evidence of implementation.

The intended result is a verified local release candidate: a new workspace can onboard, verify accounts, invite all four roles, ingest and approve real multilingual content, obtain grounded answers and exact excerpts, exercise simulated billing, export/delete data, and recover from restart and backup. Provider configuration must work throughout that journey. Public hosting, live payments, purchased inference, extension publication and third-party messages require their existing external authorizations.

## 2. Start here in the next chat

Repository: `/Users/shivamwtsn/Documents/TrainU`.

1. Read applicable `AGENTS.md`, this document, `docs/release-plan.md`, and `docs/release-status.md`. Inspect `git status` and preserve newer edits.
2. Baseline at planning time: local commit `b082a61` on `main`. Push previously failed because GitHub authentication was invalid. The user approved pushing the existing content to the private repository; verify remote/auth status before any future push and never assume the commit reached GitHub. No repository visibility changes are authorized.
3. Latest recorded checks: 44 backend tests, 3 extension unit tests, Angular production build passed on 2026-10-01. These checks do not establish P03–P18 completion. P01 is verified; P02 remains in progress. Reconcile the stale P02 summary about pending Whisper inference: its successful 11-segment CPU smoke test is already recorded below it.
4. Backend service may run natively while data services/worker run in Compose. `make test` previously failed because the Compose backend was stopped; the same suite passed through a one-off container. Inspect processes and ports before starting or replacing anything.
5. Resume the first incomplete step in section 7. Do not rerun model downloads or expensive acceptance checks without a relevant change. Back up DB and objects before migrations.

## 3. Recommendation for the coding model

Use **GPT-6 Luna with high reasoning**, one bounded subtask at a time, for the cost-conscious implementation path. Use medium for straightforward documentation/UI changes; raise reasoning for authorization, migrations and retry/accounting work. GPT-5.6 Terra can use the same handoff if preferred, but no repository-specific comparison establishes that it will execute this project more correctly.

This recommendation is engineering judgment, not a guarantee or a benchmark: [OpenAI's selection guide](https://developers.openai.com/api/docs/guides/model-selection) places Luna on scoped work and recommends comparing models on actual tasks; [GPT-6 Luna's model page](https://developers.openai.com/api/docs/models/gpt-6-luna) describes focused tasks. A stronger coding model or human should review tenant authorization, session/MFA security, vector-generation switching, quota races, backup recovery and the final release evidence. Model choice never replaces acceptance tests. Do not spawn extra agents without authorization.

## 4. Audited starting code and gaps

| Existing path | Observation | Required change |
|---|---|---|
| `backend/app/services/llm.py` | Mock and shared OpenAI-compatible adapter; every real request sends JSON mode, temperature, top-p, seed and max_tokens | Explicit protocol adapters and per-model capabilities; validated common response |
| `backend/app/services/embeddings.py` | Mock plus compatible HTTP embeddings | Query/document distinction, validation and immutable embedding profile |
| `backend/app/services/stt.py` | Mock plus Whisper-compatible HTTP route | Local faster-whisper adapter and explicit timestamp/language capabilities |
| `backend/app/core/config.py` | Global provider literals and independent URLs/keys/model names; cached settings | Validated provider registry, safe legacy translation, deterministic resolver |
| `backend/app/models/source.py` | Vector column uses `settings.EMBEDDING_DIM` | Explicit migration/profile handling; environment changes must not silently alter schema expectations |
| `backend/app/services/rag.py` | Evidence selection consumes model IDs | Typed output and authorized citation validation must remain app-owned |
| `backend/app/workers/tasks.py`, `celery_app.py`, `docker-compose.yml` | API/worker settings can be operationally different when host and Compose coexist | Persist resolved configuration versions on work; reject inconsistent execution |
| `frontend/src/app/core/models.ts`, `api.services.ts`, assistant/admin features | Provider metadata exists; full model settings journey is absent | Safe status, selection and error contracts |
| `frontend/scripts/prepare-docs.mjs` | Only product/demo documents are copied publicly | Keep this handoff and release evidence outside the public allowlist |

## 5. Fixed product and architecture decisions

### Supported providers and selection

- Three independent capabilities: chat, transcription and embeddings. OCR stays local Tesseract for this release.
- Required chat adapters: existing local Ollama, OpenAI's documented API for explicitly configured GPT models, and an explicitly selected OpenAI-compatible chat-completions endpoint. Check current official protocol documentation when implementing; do not assume all GPT models accept the existing parameters.
- Required transcription: local faster-whisper plus the existing compatible transcription protocol with segment timestamps. A text-only response cannot qualify for precise spoken citations.
- Required embeddings: pinned local multilingual E5 and compatible embedding endpoints that satisfy the registered profile. Only validated **384-dimensional** profiles are supported in this release. Reject unsupported dimensions before writes. Additional dimensions require a separate migration and index design, not zero padding, truncation or an environment-only change.
- Native provider protocols beyond these adapters are an extension point. Do not advertise arbitrary models as universally compatible. Model names, subscriptions and installed desktop chat apps are not an inference endpoint or credentials.
- Existing Qwen/E5/Whisper pins remain the default reference deployment. New chat models may be selected without re-embedding. Changing embedding model, revision, dimension, normalization or prefix rules requires a separate generation and atomic switch.
- Selection modes: `manual` (exact approved profile) or `auto` (first healthy, compatible, permitted profile in an operator-defined priority list). Never choose an arbitrary first model returned by a server or scan the user's network/files for models or credentials.
- Discovery only queries registered endpoints. An endpoint without model listing can use an explicitly configured model. A listed model is not proof of capabilities, permissions or answer quality.
- Resolve one profile/version when a request/job is accepted; retries use that version. Default is no fallback. An enabled fallback list must pass the same capability, quality, privacy, quota and cost policy checks. Never switch embedding spaces or provider midway through an answer.
- Local-only mode is the default. Hosted inference requires operator enablement and an organization's recorded opt-in for each capability. Test-connection prompts must be synthetic; do not send source content as a health probe. Live paid tests need explicit spend authorization.

### Configuration ownership and contracts

Use a versioned operator registry file (proposed `infrastructure/ai-providers.example.json`; schema version 1). Read its path from `AI_PROVIDER_CONFIG_PATH`. Existing env fields translate to one legacy profile when no registry is configured; conflicting old/new values fail with a redacted actionable error. Do not implicitly activate a hosted default from the existing `LLM_BASE_URL` value.

Each registry entry contains: ID, adapter/protocol, enabled flag, local/hosted classification, endpoint ID, credential reference, exact model ID/revision where supported, capability set, supported request parameters, context/output limits, timeouts and quality-qualification reference. Embedding entries additionally contain dimension, normalization and query/document preprocessing identifiers. Endpoint allowlists and secret references are operator-controlled; organization admins cannot edit URLs or secret paths.

Secrets are read by the backend from approved environment names or mounted secret files. APIs, browser storage, audit logs, metrics, exports and support bundles never return them. Credential rotation must invalidate pooled clients safely. Production validates TLS and authentication according to the provider type.

Store tenant-scoped selection policy and its version in the DB after P04: allowed profile IDs, selected/default IDs, mode, capability-specific hosted consent, and fallback preferences. Operator restrictions always take precedence. Use optimistic concurrency to reject lost policy updates. An org admin can select only profiles authorized for that org; other roles see limited effective status only.

Proposed tenant contracts under `/api/v1/ai` (update OpenAPI/Angular/tests together):

- `GET /profiles`: safe permitted IDs, labels, capabilities, qualification state and sanitized availability; no endpoint URLs or credentials.
- `GET /configuration`: org-admin view of current policy/version; `PUT /configuration` requires expected version, CSRF and audit record.
- `POST /profiles/{id}/check`: org-admin only, bounded/rate-limited synthetic diagnostic; hosted test only when explicitly authorized. For slow probes use the durable request machinery rather than holding a DB transaction.
- `GET /status`: authorized members see effective profile names, local/hosted and available/unavailable state. No cross-tenant diagnostics.
- Assistant request/status responses record requested/resolved model profile, policy version, answer kind, fallback occurrence and sanitized failure code. Reuse P10 request/history contracts; do not create a second chat implementation.

Use the existing organization/audit models where possible; proposed new policy/profile-generation records need tenant-consistent foreign keys and uniqueness constraints. Worker jobs store IDs/version, not raw secrets. A worker lacking the accepted profile version must report configuration mismatch and keep the job recoverable rather than silently use another model.

### Safety and resource behavior

Validate actual HTTP destinations: schemes, host/port/path allowlist, redirects, IPv4/IPv6 and DNS resolution; deny cloud metadata and unintended internal destinations. Explicitly permit operator-registered local Ollama/container endpoints. Customer API requests never introduce new endpoints. Disable unneeded environment proxy inheritance. Enforce egress at runtime where available and test DNS/redirect bypasses.

Adapter outputs converge on one typed answer schema with bounded lists/text and evidence IDs. JSON syntax alone is insufficient. Permit one schema repair with the same authorized evidence and privacy policy; then surface a recoverable error. Never attach the first chunk to rescue invented evidence IDs. Source instructions cannot authorize tool use, endpoint changes or credential access. No model-generated playback URLs.

Bound request size, context, response size, connection/read/overall timeouts and token limits. Retry only transient failures (bounded exponential backoff/jitter, honoring Retry-After); authentication, incompatible capabilities and validation failures need correction. Retrying an ambiguous paid timeout may incur provider costs, so default to no automatic replay there. Cancellation prevents subsequent retries/fallback and any duplicate completed-turn charge; report whether remote computation could actually be cancelled.

Keep one generation and one ingestion job concurrent by default. Reuse P05's durable jobs, fairness, leases and usage ledger. Customer completed-turn usage is charged once; every provider attempt and measured token/cost record is separately accounted for. Unknown provider cost remains unknown, never displayed as zero. Do not invent a token-price table.

## 6. Verification examples

| Scenario | Required observable behavior |
|---|---|
| Ollama present with qualified Qwen | Auto local mode resolves the pinned permitted model and produces a cited answer |
| Several local models | Stable priority order; incompatible/unqualified models cannot win |
| GPT profile configured but hosted consent absent | No content or synthetic inference is sent; UI explains disabled hosted use |
| Authorized GPT profile and credentials | Adapter-specific payload and same grounded result contract; real verification requires an authorized live test |
| Missing key or missing model | Clear unavailable/configuration error; no mock substitution in production |
| Endpoint lists models but inference fails | Diagnostic distinguishes discovery from usable inference |
| Provider stops or returns 429/503 | Bounded retry/backpressure; approved fallback only; one usage completion |
| Invalid JSON, wrong schema or nonexistent evidence IDs | One bounded repair then recoverable failure/appropriate abstention, no invented citations |
| A different chat model is selected | New requests adopt new policy version; existing job stays pinned; existing vectors remain usable |
| Embedding profile changes | Old generation serves until replacement is complete and qualified; rollback remains possible |
| Wrong vector dimension, NaN, empty or reordered batches | Reject before persistence; validate count and provider item indices |
| Worker restart/config drift | Resume accepted version or explicitly fail recoverably; no mixed-model partial indexing |
| Tenant attempts another org's profile/history/clip/config IDs | Denied before provider call or evidence disclosure |
| Model endpoint redirects or resolves to metadata IP | Rejected, with no credential forwarding |
| Same task via viewer/contributor/owner/admin | Existing role and publication policies remain effective |

## 7. Sequential execution queue

Run P01–P18 in their established order. Insert M tasks at the positions below; do not implement a downstream admin screen before its authorization dependencies. Each row is a bounded deliverable; split its numbered changes into separate checkpoints if needed.

| ID / insertion point | Dependencies | Changes and likely files | Acceptance / evidence to save |
|---|---|---|---|
| M01 — finish P02 | P01 | 1. Reconcile status. 2. Finish isolated clean setup/restart and scanner compatibility. 3. Add registry schema/legacy translation in config; add examples/doctor validation | Invalid/ambiguous config rejected before networking; existing local/demo config still works; clean startup and restart evidence |
| M02 — after M01, before P03 | M01 | 1. Add provider interfaces/registry under `backend/app/services/providers/`. 2. Adapt chat protocols in `llm.py`. 3. Normalize capabilities/errors and typed output. Keep public service factory compatibility | Contract tests per adapter: supported/unsupported parameters, auth, JSON/schema repair, timeouts and error mapping; real local Qwen smoke |
| M03 — after P04 | P03/P04, M02 | 1. Add tenant policy/version and migration. 2. Add role/CSRF-protected API and operator endpoint policy. 3. Test secret redaction, SSRF and tenant isolation | Full two-tenant/four-role matrix, migration backup/rollback checks, no arbitrary URLs or secret disclosure |
| M04 — with P05 | M03, P05 job foundations | 1. Resolve and persist profile/version at acceptance. 2. Add deterministic auto-selection and explicit fallback. 3. Integrate cancellation, bounded retries, fairness and attempt/customer accounting | Provider outage/config drift/duplicate job/cancellation races preserve pinned config and single completion; cost uncertainty visible |
| M05 — with P07 | P06, M02/M04 | 1. Implement local faster-whisper using pinned snapshot paths. 2. Normalize HTTP transcription timestamps/languages. 3. Record extraction/OCR/transcription coverage and model provenance | Real English/Hindi/Hinglish audio from unseeded videos; silent/OCR and no-content cases; segment timing/limits as P07 |
| M06 — with P09 | P08 revisions, M04/M05 | 1. Add query/document embedding APIs and validation. 2. Build generation metadata/re-embedding jobs. 3. Atomic switch/rollback and hybrid retrieval | No mixed spaces, incomplete generations cannot activate, dimension/preprocessing mismatch rejected; P09 retrieval quality passes |
| M07 — with P10/P11 | M04/M06 | 1. Route all chat kinds through common service. 2. Recheck evidence and history access; remove invalid-evidence fallback. 3. Preserve excerpt, transcription input, stop/mute and retry UX | Multilingual greetings/follow-ups and grounded procedures work on each qualified chat profile; unauthorized evidence stays hidden |
| M08 — with P12/P14 | M03/M04/M07 | 1. Add admin AI settings (profile selection, mode, diagnostic, consent, errors). 2. Surface effective provider on assistant. 3. Enforce plan/cost limits, accessible loading/retry and configuration conflicts | Keyboard/mobile/all-role browser checks; reload preserves tenant policy; no secrets in bundle/network replies; concurrent quota tests |
| M09 — with P16/P17 | M01–M08 plus P13/P15 | 1. Add provider diagnostics, metrics and redacted bundles. 2. Back up/restore policy/profile metadata with secret re-provisioning. 3. Write provider setup, compatibility, privacy/data-flow and qualification docs | Isolated restore yields correct authorized behavior; no customer content/credentials in logs; claims match evidence |
| M10 — P18 final gate | All P01–P17 and M01–M09 | Run section 8; update release status and operator quick-start. Leave local app running | All mandatory local gates green, known integrations truthfully classified, rollback and demo evidence recorded |

P03, P04, P06, P08, P13 and P15 retain all original scope even where this table only names dependencies. P12 still includes the Razorpay adapter/simulator and subscription rules. P16 still includes ASVS mapping, SBOM, dependency/container/static/DAST checks and encrypted restore drill. P17 still includes pricing, legal templates, support and sales materials. None is completed merely by finishing M tasks.

## 8. Combined release gate

Use the original held-out multilingual evaluation unchanged: at least 120 questions, 40 per language; retrieval recall@5 and supported-answer success at least 90% per language; citation-support precision at least 95%; critical transcription entities/steps and spoken timestamp anchors within three seconds at least 90%; zero unauthorized disclosures or successful source-instruction attacks; every unsupported factual case abstains or clarifies. Freeze development/holdout splits before tuning and use reviewed evidence.

A model is enabled for production selection only after its actual adapter/model revision passes the relevant quality gate. Run the full answer/evidence suite for each advertised chat model; run retrieval/transcription gates for each advertised profile change. Unknown/discovered models remain experimental and require qualification before activation. Changing weights under the same model name invalidates qualification when revision identity can be checked; otherwise document unverified revision identity and require an explicit operator requalification process.

Mandatory local release gates include all original browser journeys, role/tenant tests, two-hour processing, resumable 2 GB uploads, parser/malware failures, durable recovery, backup/restore, accessibility and the ten-tenant × 10,000-chunk performance benchmark with 20 non-AI clients. Retain API p95 <1 second and <1% unexpected errors on the measured host; report actual AI latency/memory/disk. A provider layer must not weaken these thresholds.

Maintain `docs/provider-qualification.md` during implementation with one row per exact adapter/model/profile: configured, contract-tested, real-inference-tested, quality-qualified, blocked externally. Test doubles verify protocols, never real hosted operation. Local Qwen/E5/Whisper end-to-end verification is mandatory. GPT/other hosted live checks can be blocked externally if credentials or spend authorization are missing; the local candidate can be qualified, but those adapters must remain labelled unverified/disabled for production and cannot be marketed as proven integrations.

Final handoff must separate incomplete local code/hardware/quality gates from external hosting, merchant, email, legal and hosted-model credentials/spend prerequisites. Do not call the entire product launch-ready because the provider enhancement passes.

## 9. Work discipline and resumability

For every subtask record: ID, dependencies, state (`not started`, `in progress`, `verified locally`, `blocked externally`), files/migrations changed, exact checks and outcomes, evidence paths, rollback, blocker and next action. Use `docs/release-status.md` as the one progress ledger; keep long evidence in ignored artifacts with safe summaries. Keep failed local gates visible rather than reclassifying them as external work.

Work on one independently verifiable behavior at a time. Read only relevant files, run focused checks, then update the ledger. Reuse passing evidence until a relevant change invalidates it. Run the complete suite at P18. Preserve the demo and existing light TU design. Never lower tests/thresholds to make a package green. Keep this plan private to the repository, outside served docs.

At interruption leave the exact next command and expected result in the ledger. A future chat must be started by the user or an already-authorized scheduler; do not imply a new chat automatically inherits or executes this plan. Do not create a new task in this planning turn.

## 10. Prompt to paste into the next chat

> Implement the TrainU release plan in `/Users/shivamwtsn/Documents/TrainU`. Read applicable AGENTS.md, `docs/model-provider-handoff.md`, `docs/release-plan.md`, and `docs/release-status.md` first. Follow the merged P01–P18 and M01–M10 order, starting at the first incomplete gate. Preserve existing edits and demo data. Implement one verifiable behavior at a time; update durable status with evidence and the next action. Add configurable chat, transcription and embedding providers with deterministic permitted selection, explicit hosted consent, secret protection, tenant isolation and safe vector migrations. Complete all original product/security/QA/operations gates; do not stop after the provider layer or substitute mock tests for live integration evidence. Keep local inference as the default and do not incur paid inference or perform public deployment, live payments, extension publication or third-party messaging without authorization. Record external blockers separately from unfinished local work. If interrupted, leave a precise resume point. Proceed with implementation rather than writing another plan.
