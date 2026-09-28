# API reference

Full interactive OpenAPI/Swagger docs are served by the running backend at
`GET /api/v1/docs` (raw schema at `/api/v1/openapi.json`). This document is a
narrative map of the surface; treat Swagger as the source of truth for exact
request/response schemas.

Base URL (local): `http://localhost:8000/api/v1`

## Authentication

Every endpoint below `/auth/register`, `/auth/login`, and `/auth/refresh`
requires an `Authorization: Bearer <access_token>` header. Endpoints scoped
to an organization additionally require an `X-Org-Id: <organization_id>`
header identifying which of the caller's memberships is active — omit it
only if the user belongs to exactly one organization, in which case it's
inferred.

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/register` | none | Creates a user; optionally creates a new org (becomes `org_admin`) or accepts an invitation token |
| POST | `/auth/login` | none | Returns `{access_token, refresh_token}`. Rate-limited. |
| POST | `/auth/refresh` | none (refresh token in body) | Rotates the access token |
| GET | `/auth/me` | user | Current user + all active memberships |

## Organizations

| Method | Path | Min role | Notes |
|---|---|---|---|
| GET | `/organizations/current` | any member | Active org details |
| PATCH | `/organizations/current` | org_admin | Update name, logo, retention days |
| GET | `/organizations/current/members` | any member | Roster |
| PATCH | `/organizations/current/members/{id}/role` | org_admin | Change a member's role; audit-logged |
| DELETE | `/organizations/current/members/{id}` | org_admin | Deactivate a membership |
| POST | `/organizations/current/invitations` | org_admin | Create an invite (email + role); returns a token used to build `/accept-invite?token=...` |
| GET | `/organizations/current/invitations` | org_admin | List invites |
| POST | `/organizations/current/invitations/{id}/revoke` | org_admin | Revoke a pending invite |
| POST | `/organizations/invitations/accept` | user | Accept an invite by token (adds/reactivates membership) |

## Applications

| Method | Path | Min role | Notes |
|---|---|---|---|
| GET | `/applications` | any member | List, with modules |
| POST | `/applications` | content_owner | Create |
| GET | `/applications/{id}` | any member | 404 if it belongs to another org |
| PATCH | `/applications/{id}` | content_owner | Update fields |
| DELETE | `/applications/{id}` | org_admin | Delete |
| POST | `/applications/{id}/modules` | content_owner | Add a module |

## Sources (KT videos & documents)

| Method | Path | Min role | Notes |
|---|---|---|---|
| GET | `/sources` | any member | Filter by `status_filter`, `application_id` |
| POST | `/sources` | content_owner | Multipart upload (`file`, `title`, metadata fields); validates type/size, stores to MinIO, kicks off the Celery pipeline |
| GET | `/sources/{id}` | any member | Includes processing jobs + a presigned `playback_url` |
| GET | `/sources/{id}/chunks` | any member | Transcript/document chunks in order |
| PATCH | `/sources/{id}/chunks/{chunk_id}` | content_owner | Edit chunk text/topic/audience roles |
| POST | `/sources/{id}/approve` | content_owner | Only valid from `awaiting_review`; moves to `approved` then a background task indexes it to `indexed` |
| POST | `/sources/{id}/archive` | content_owner | Removes it from retrieval |
| DELETE | `/sources/{id}` | org_admin | Only valid once `archived` (409 otherwise) |

Allowed file types: `.mp4 .mov .m4v .webm` (video, up to `MAX_VIDEO_SIZE_MB`)
and `.pdf .docx .md .txt` (documents, up to `MAX_DOCUMENT_SIZE_MB`).

## Assistant (Ask TrainU)

| Method | Path | Min role | Notes |
|---|---|---|---|
| POST | `/assistant/ask` | any member | `{question, application_id?, application_version?, environment?, conversation_id?}` → grounded answer + citations. Rate-limited. |
| GET | `/assistant/conversations` | any member | Caller's own conversation history in this org |
| POST | `/assistant/feedback` | any member | `{message_id, rating: helpful|not_helpful, comment?}` |
| GET | `/assistant/feedback` | any member | All feedback in the org |

See `docs/architecture.md` for the full retrieval → synthesis → citation
pipeline behind `/assistant/ask`.

## Usage & audit

| Method | Path | Min role | Notes |
|---|---|---|---|
| GET | `/usage/summary` | any member | `?days=30`; stored/processed video minutes, questions asked, active users, daily breakdown |
| GET | `/audit-log` | org_admin | `?limit=100&action=...`; login, invites, uploads, processing, approvals, deletions, role changes, assistant answers |

## Health

| Method | Path | Auth |
|---|---|---|
| GET | `/health` | none | Liveness check (outside the `/api/v1` prefix) |

## Error shape

All errors are `{"detail": "..."}` with a standard HTTP status code:
`400` validation, `401` unauthenticated/expired token, `403` insufficient
role, `404` not found *or* not accessible to the caller's organization
(deliberately indistinguishable), `409` invalid state transition,
`429` rate limited.
