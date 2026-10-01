# QA and release evidence

## Automated gates

The workflow `.github/workflows/ci.yml` runs Python correctness lint, Python and browser dependency audits, production frontend compilation, backend tests against a disposable PostgreSQL/pgvector/Redis/RustFS stack, a seeded runtime smoke check, extension Node tests and Playwright browser acceptance. It preserves browser failure evidence. A configured CI workflow is not evidence of a successful CI run; record the actual run and commit in the release report.

Backend test fixtures destroy/recreate tables. Use only a disposable database such as `trainu_test`. Mock provider tests establish control flow and access rules; they do not establish real transcription accuracy, model quality, external provider reliability or production capacity.

## Acceptance matrix

| Area | Cases and expected result |
|---|---|
| Signup/sign-in | Valid registration/login, duplicate email, wrong password, malformed input, expired/replayed credentials and logout behavior |
| Workspace isolation | Two organizations; swap every object ID and X-Org-Id; source/chunk/playback/citation/feedback data remain inaccessible |
| Roles | Viewer denied content writes; contributor can submit but cannot approve; owner reviews; admin manages people; reserved role escalation and last-admin removal rejected |
| Invitations | Match email, expiry, accepted/revoked token, duplicate membership, tampered role; safe error and no unintended access |
| Content | Supported document/video, empty file, oversized body, malformed parser input, rejected type, no-audio/corrupt media, FFmpeg/ffprobe unavailable, STT failure, no-speech result, long-video audio split with timestamp offsets, embedding batch failure; useful state/error and no false successful transcript |
| Review | Draft hidden from viewers, contributor own-draft visibility, audience restriction, approve/archive, archived deletion, stale citations |
| Assistant | Relevant approved evidence, no-evidence answer, correct source/time, tenant/app/version filters, feedback and history ownership |
| Browser UX | Keyboard focus, readable labels/errors, loading/empty states, mobile narrow viewport, long titles, slow network, screen reader labels |
| Extension | Valid HTTPS workspace or localhost URL, rejected unsafe schemes, selected-text size/encoding, default launcher, no automatic submission |
| Operations | Migration from previous schema, backup/restore, dependency outage, worker interruption, credential rotation, cache and security headers |

## Real-provider staging gate

Upload at least one representative short video, the longest video you intend to support, PDF, DOCX and text. Verify actual transcription timing across audio-segment boundaries, extraction quality, dimension-compatible embeddings, relevant/unrelated questions, audience isolation and real playback. Include a video without audio, an intentionally malformed file, a provider quota error and STT retry/failure. Measure end-to-end ingestion time, answer latency and provider spend; save the results without customer secrets. Confirm the provider accepts the selected WAV segment duration/size before setting the supported long-video envelope.

## Performance gate

Choose a declared pilot envelope: number of organizations, concurrent users, approved chunks per tenant, upload frequency, media duration and question rate. Populate representative data, including tenant-filtered vector queries. Measure p50/p95/p99 API latency, errors, database/Redis memory and connections, worker queue age/throughput, storage bandwidth, provider latency and cost. Test gradual load, a burst, sustained operation and a dependency outage. Verify no tenant can starve others.

Record machine sizes, replica counts, provider limits, dataset and test scripts alongside results. Set a launch cap from measured results, not seed data. The repository has no verified high-scale throughput or SLA yet.

## Browser extension manual release check

Run `node --test extension/tests/*.test.js`. Load `extension/` unpacked in Chrome and Edge, configure the workspace origin, select text on a page and use the context menu. Confirm the draft arrives via URL fragment, authentication still applies, no question is sent until the member submits, and no background page collection occurs. Verify denial/malformed URL behavior. Store signing, privacy disclosure, screenshots, review and distribution remain separate publish gates.

## Release evidence record

For each release, record commit, image digests, migration revision, exact commands, exit status, test/audit findings, staging real-provider evidence, load-test envelope, restore result, known limitations and approving operator. `docs/release-status.md`, when present, contains the current implementation-session evidence; runtime launch requires the additional checks above.
