# Privacy notice — operator draft

**Status: configuration draft, not a published notice for a named business.** Before external launch, the operator must fill the identity/contact, service regions, actual subprocessors, retention periods, request process and effective date below. The implementation facts describe this repository; deployment choices can change them.

## Service and operator

- Service: TrainU, an organization training knowledge workspace.
- Operator/legal entity: **TO COMPLETE**.
- Privacy and data-request contact: **TO COMPLETE**.
- Processing/storage regions: **TO COMPLETE**.
- Effective date and version: **TO COMPLETE**.

## Information processed

Account information includes email, display name and a password hash. Workspace data includes organization/membership roles, invitations, applications, uploaded videos/documents, transcripts, embeddings, review metadata, questions/answers/citations, feedback, usage records and audit events. Operational records may contain request metadata such as IP addresses and error/status information. The operator should define and minimize log fields.

These data support authentication, access control, content processing/review, answering questions from approved material, troubleshooting and administration. The workspace administrator controls membership and which materials are submitted/approved. Users should upload only content they have authority to share and avoid unnecessary personal or sensitive material.

## Service providers and sharing

Original content is stored in private S3-compatible storage; account/content metadata is stored in PostgreSQL; Redis supports tasks and rate limits. Configured transcription services receive audio; embedding services receive text chunks/questions; configured language-model services receive the question and selected evidence. Real provider names, regions, retention settings and agreements must be published by the operator. This repository does not establish that providers retain nothing or never train on supplied data.

Authorized workspace members see content according to role, review state and audience. Authorized operators may need limited access for support, security and recovery. No advertising integration is included in this repository; deployment analytics or additional integrations require this notice to be updated.

## Browser extension

The companion requests `contextMenus` and `storage` permissions. It stores the chosen workspace origin locally and sends selected text to that workspace only when the user invokes its action. It carries the draft in a URL fragment (`#q=`), which the web app reads; it does not automatically submit an AI question. The user signs in and explicitly sends the question through normal app access checks. There is no background page crawl, screen recording or whole-page extraction.

Selected text becomes workspace data when the user submits it. The extension does not grant access to content the user could not access in the app. Installing the unpacked extension is optional; public store distribution requires the operator's store privacy disclosure.

## Storage, retention and requests

Source playback uses expiring signed links, which must be treated as temporary credentials. Organization retention days are presently a saved setting, not an automatic deletion scheduler. The operator must publish actual retention for original objects, extracted text, conversations, logs, credentials and backups, plus the process for export/deletion and any backup exceptions.

Users can contact **TO COMPLETE** for access/correction/export/deletion requests. The operator verifies identity and authority, applies the actual supported procedure, and records completion. Account recovery and organization-wide export/deletion are not fully self-service features in this release. Define applicable timelines and escalation channels for the deployed service before publishing this notice.
