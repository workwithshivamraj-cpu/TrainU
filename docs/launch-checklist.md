# Launch checklist

This checklist separates repository capability from deployment evidence. An unchecked item requires verification or a product limitation before launch. Record owners, dates and evidence in the release report; do not mark a gate complete because a configuration file exists.

## Controlled pilot prerequisites

- [ ] A named operator owns the service, support route, security contact and incident response.
- [ ] Staging and production have separate secrets, databases, buckets and provider projects.
- [ ] Tested immutable API/frontend images are in a private registry; dependency and image security findings are resolved or explicitly assessed.
- [ ] Managed PostgreSQL supports pgvector, has verified TLS, connection headroom and a successful restore drill.
- [ ] Managed Redis has private TLS/auth, persistence, no-eviction behavior and observed queue/rate-limit health.
- [ ] Private object storage has scoped access, encryption, lifecycle/versioning and a tested browser-playback URL.
- [ ] DNS/TLS ingress is configured; CDN caches only static content; API cache leakage and trusted forwarding are tested.
- [ ] Production mode starts with strong secrets, explicit origins, demo mode disabled and real provider adapters/keys.
- [ ] One migration job succeeds; readiness, rollback and interrupted-worker recovery are exercised.
- [ ] Real-provider ingestion, embedding dimensions, answer quality and timestamp playback pass on representative files.
- [ ] Long-video/audio provider limits are measured; enforce a published supported envelope or implement segmented transcription.
- [ ] Role, invitation, source audience and cross-tenant regression tests pass on the release commit.
- [ ] The first workspace/admin is created without demo seed data; invitation sharing and member support procedures work.
- [ ] Browser, keyboard and responsive flows pass; docs links resolve inside the built app.
- [ ] A measured load envelope, pilot tenant cap, alert thresholds and cost cap are recorded.
- [ ] Privacy/terms drafts have the actual operator, processing region, subprocessors, contact, retention/deletion and commercial terms filled and approved.
- [ ] Backup cadence, support coverage and customer promises match measured operations.

## Before open self-service subscriptions

- [ ] Payment provider checkout, webhook signature/idempotency handling, subscription lifecycle, invoice/tax/refund ownership and billing support are implemented.
- [ ] Seats, storage, transcription and question allowances are enforced atomically; overage policy and tenant cost isolation are tested.
- [ ] Verified-email signup, password recovery, account/session security and abuse prevention meet the chosen service model.
- [ ] Public upload scanning/quarantine, robust retry/reconciliation and per-tenant queue fairness exist at the intended workload.
- [ ] Retention automation, organization data export and verified deletion procedures meet customer commitments.
- [ ] Multi-zone deployment and recovery/load testing support any promised availability/capacity.

## Optional enterprise and distribution gates

- [ ] Enterprise SSO/MFA/SCIM, tenant-specific data controls and audit export match contracted requirements.
- [ ] An independent security assessment is completed before advertising its results.
- [ ] Browser extension store listing, privacy disclosures, icons/screenshots, account, signed package and store review are complete.
- [ ] Private-media CDN signed authorization is implemented and penetration-tested if global protected-video delivery is offered.

A contract-based pilot can use manual invoicing and manually shared invites if those limitations are explicit and the pilot prerequisites pass. Neither the application nor this checklist creates a public deployment or a billing account.
