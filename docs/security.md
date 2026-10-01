# Security model

## Implemented boundaries

Authentication uses password hashes and bearer credentials. Organization membership and role dependencies protect API operations. Source reading/retrieval additionally checks approval/audience. Content review controls what becomes answerable; source evidence is persisted with citations. Rate limiting uses shared Redis in production. Object media is private and playback access uses expiring signed URLs. Production configuration rejects unsafe demo values; container profiles run as nonroot with bounded resources and a separate migration job.

Tests for roles, tenant isolation, source visibility, invitations and authentication are part of the release gate. These controls are not a security certification, penetration test or proof that all possible vulnerabilities are absent.

## Threats and remaining controls

| Risk | Control / required verification |
|---|---|
| Cross-tenant object ID or header tampering | Resolve membership and scope queries; test reads, chunks, playback, citations and mutations with two tenants |
| Role escalation or last-admin removal | Reject forbidden role assignments and preserve an active admin; test concurrent changes |
| Stolen session or XSS | Short access lifetimes, expiry/revocation behavior, text-safe rendering and CSP; review browser token storage and refresh design |
| Malicious uploaded files | Size/type validation, resource bounds and isolated workers; add malware/quarantine scanning before untrusted public uploads |
| Prompt injection in training material | Treat sources as evidence; never execute source instructions/tools; evaluate adversarial content and verify citations |
| Shared cache leakage | Disable API caching regardless of auth/query/status; keep storage private and test CDN cache keys/behavior |
| Resource and provider cost abuse | Shared rate limits, upload ceilings and concurrency limits; implement per-tenant entitlements and budgets for self-service scale |
| Operational credential compromise | Secret manager, workload identity where available, least privilege, scoped credentials and rotation drills |
| Missing or unsafe recovery | Encrypted DB/object backups, versioning, verified restore drills and controlled release migration |

The architecture does not currently include database row-level security, SSO/MFA, malware scanning, a comprehensive hard entitlement engine, automatic retention deletion or a completed independent security assessment. Browser bearer storage requires careful XSS handling; moving refresh credentials to secure HttpOnly cookies is a separate compatibility and CSRF design change.

## Deployment requirements

Use HTTPS end to end where supported, verified database/Redis certificates, private network paths, explicit CORS origins and trusted ingress headers. Limit object-storage CORS to actual web origins if the browser needs CORS access. Restrict provider credentials and customer data to approved regions/services. Pin immutable release images, audit dependencies, scan container images and patch on a defined cadence.

Do not publish debug output, demo accounts, secret files or unauthenticated storage consoles. A production domain should have an operator-controlled disclosure contact and escalation process. Do not display compliance logos, audited security claims or uptime percentages without supporting evidence.

## Access review

Review active memberships, administrative roles and outstanding invitations before each pilot expansion and on employee departure. Deactivate access promptly and inspect affected sessions. Confirm source audience mappings and review status before publishing sensitive content. Administrative operators should use separate identities from daily member use and maintain a record of privileged actions.
