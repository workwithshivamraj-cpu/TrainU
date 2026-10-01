# Delivery and product backlog

## Repository release candidate

The current work prepares role-based organization access, governed video/document ingestion, cited answers, a light workspace and documentation center, browser companion source, production/container configuration, CI gates and operating runbooks. The release report records which checks actually ran. The launch checklist is the go/no-go document.

## Pilot release gates

Provision the deployment and real providers, validate maximum supported audio payloads, run tenant/RBAC and real-provider acceptance, perform a restore drill, measure a bounded workload, define operator/support ownership and complete customer policy drafts. Keep a limited pilot envelope until the evidence supports expansion.

## Product backlog by risk

| Priority | Workstream | Completion evidence |
|---|---|---|
| P0 before advertised long-video support | Audio segmentation, timestamp offsets, bounded retries | Long/short media staging tests with correct timed citations |
| P0 before public uploads | Malware quarantine/scanning, provider cost caps, resilient ingestion recovery | Malicious/corrupt fixtures and failure/replay tests |
| P0 before self-service subscriptions | Payment lifecycle + atomic entitlements | Signed/idempotent webhooks, limit concurrency tests, billing reconciliation |
| P0 before broad self-service identity | Email verification/recovery and session hardening | Recovery/abuse/session tests and delivery evidence |
| P1 scale | Direct multipart uploads, queue fairness, outbox/reconciliation, index tuning | Measured workload, interrupted-job recovery and tenant fairness |
| P1 governance | Automated retention, data export/deletion, audit export | Controlled time-based and cross-tenant tests, operator audit |
| P1 enterprise | SSO/MFA/SCIM, regional controls and administrative audit | Contract-specific acceptance and security assessment |
| P2 distribution | Extension store listing and private-media CDN | Store approval; protected edge playback/expiry tests |

Priorities assume an initial contract-based team pilot. Reorder from customer needs and test evidence. No completed task should be inferred from this backlog table.
