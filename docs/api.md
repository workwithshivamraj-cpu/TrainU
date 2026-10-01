# API guide

The running API's `/api/v1/docs` and `/api/v1/openapi.json` define exact schemas. This guide describes the supported workflow. In a deployed frontend, use same-origin `/api/v1`; local direct development uses `http://localhost:8000/api/v1`.

## Authentication and tenancy

Register/login returns bearer credentials. Send `Authorization: Bearer <access_token>` and `X-Org-Id: <organization_id>` on organization requests. A token alone does not grant membership in arbitrary organizations. Sign-in, refresh and registration are unauthenticated entry points with validation/rate limits; refresh requires a valid refresh credential. Do not put bearer credentials in URLs, analytics or logs.

| Method | Resource | Purpose |
|---|---|---|
| POST | `/auth/register` | Create identity/workspace or accept invitation during signup |
| POST | `/auth/login` | Authenticate |
| POST | `/auth/refresh` | Exchange a refresh credential |
| GET | `/auth/me` | Current identity and memberships |
| GET/PATCH | `/organizations/current` | Read/update current workspace; update needs admin |
| GET | `/organizations/current/members` | Authorized roster |
| PATCH/DELETE | `/organizations/current/members/{id}` | Member administration; role update uses `/role` suffix |
| GET/POST | `/organizations/current/invitations` | Admin invitation workflow |
| POST | `/organizations/current/invitations/{id}/revoke` | Admin revoke |
| POST | `/organizations/invitations/accept` | Accept for authenticated matching identity |

## Content and questions

| Method | Resource | Permission / result |
|---|---|---|
| GET | `/applications` or `/applications/{id}` | Organization member |
| POST/PATCH | `/applications` or `/applications/{id}` | Content owner |
| DELETE | `/applications/{id}` | Org admin |
| POST | `/applications/{id}/modules` | Content owner |
| GET | `/sources` or `/sources/{id}` | Tenant/audience/status-filtered content; detail may return short-lived playback URL |
| POST | `/sources` | Contributor or content owner multipart upload |
| GET | `/sources/{id}/chunks` | Authorized source transcript |
| PATCH | `/sources/{id}/chunks/{chunk_id}` | Content owner correction |
| POST | `/sources/{id}/approve` | Review-to-approved transition |
| POST | `/sources/{id}/archive` | Removes retrieval eligibility |
| POST | `/sources/{id}/retry` | Content owner retries a failed source |
| DELETE | `/sources/{id}` | Org admin, archived source only |
| POST | `/assistant/ask` | Question and optional app/version/environment/conversation filters |
| GET | `/assistant/conversations` | Caller's conversations in the organization |
| POST/GET | `/assistant/feedback` | Feedback submission/authorized review |
| GET | `/usage/summary` | Usage rollups |
| GET | `/audit-log` | Org admin audit entries |

An assistant response includes answer, steps, confidence label, citations with source/chunk IDs, quoted evidence and timestamps, related clips and follow-up questions. Clients must render returned text as text, not execute it as HTML or instructions. Resolve playback from the authorized source endpoint instead of constructing object URLs.

## Uploads and statuses

Supported extensions: video `.mp4`, `.mov`, `.m4v`, `.webm`; documents `.pdf`, `.docx`, `.md`, `.txt`. Size limits are deployment settings. The development profile allows larger files than the initial production template. Allowed extension/MIME checks do not constitute a malware scanner.

The normal flow is `uploaded → queued → processing → awaiting_review → approved → indexed`. Failures enter `failed`; approved content can be archived. Invalid state changes return conflict. Follow the operations guide for interrupted processing; never call undocumented endpoints or manually force a source to indexed.

## Health and failures

`/health` is liveness. `/health/ready` checks configured backing dependencies and is the API load-balancer probe. Both are outside `/api/v1`. Nginx also has its own `/health` endpoint for static serving.

Clients should handle 401 (sign in), 403 (insufficient permission), 404 (missing/inaccessible), 409 (state conflict), 413 (upload too large), 422 (validation), 429 (rate limit) and 503 (temporary dependency failure). Error bodies typically have `detail`; FastAPI field-validation details may be an array. Respect retry headers when present. Retry reads with bounded backoff; do not automatically replay uploads or other non-idempotent mutations.
