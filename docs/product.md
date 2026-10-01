# Product specification

## Problem and audience

TrainU helps support, operations, engineering and onboarding teams recover useful knowledge from training recordings and reference documents. The first buyer is a team lead with recurring onboarding or support questions, a recognizable application catalog, and someone accountable for content accuracy.

The core promise is a shorter path from a work question to approved evidence. Source review and a usable citation matter more than answer fluency. The interface should keep one primary action visible per view, use light backgrounds and clear type, show honest processing/empty/error states, and work with a keyboard.

## Primary workflow

A workspace administrator sets up the team and assigns roles. Content owners organize applications, upload supported material, inspect the processing result and approve it. Members ask questions with optional application/version/environment filters. Answers show evidence and playable timestamps when the source is a video. A member can leave feedback; owners archive stale material and publish replacements.

The source pipeline stores the original upload, extracts a video's audio to timestamped WAV segments, transcribes those segments, restores each segment's offset to the original timeline, groups transcript segments into reviewable video chunks, and embeds chunk text in batches. Owners review and approve the resulting transcript before it becomes searchable. When a member asks a question, TrainU retrieves approved, permitted chunks and invokes the configured LLM to synthesize a grounded answer; citations and clip times are generated from retrieved records rather than model text. The LLM is a question-answering step, not a background action during upload.

Mock mode uses example transcripts and deterministic retrieval for demonstrations. It does not extract or understand arbitrary uploaded audio as speech. Real transcription, semantic embeddings and model answers require configured provider services and acceptance testing with the customer's content.

Video support depends on a readable container/audio codec, a usable audio track, available FFmpeg/ffprobe, provider payload/duration limits, worker scratch space and model/provider quotas. Current accepted filename suffixes are MP4, MOV, M4V and WEBM, up to the configured upload limit; extension alone cannot guarantee that every file is decodable. Audio is segmented into configurable windows before STT, but no universal compatibility, length, accuracy, cost or scale guarantee is claimed. See deployment and QA docs for staging gates.

## Roles

Roles belong to a membership in a specific organization. A user can belong to multiple organizations; switching workspace changes their permissions and content scope.

| Capability | Viewer | Contributor | Content owner | Org admin |
|---|---|---|---|---|
| Ask questions and leave feedback | Yes | Yes | Yes | Yes |
| Read approved, audience-allowed sources | Yes | Yes | Yes | Yes |
| Upload source drafts | No | Yes | Yes | Yes |
| Review/manage other members’ drafts | No | No | Yes | Yes |
| Review, correct, approve and archive sources | No | No | Yes | Yes |
| Create/edit applications | No | No | Yes | Yes |
| Delete archived sources/applications | No | No | No | Yes |
| Invite members, manage roles/settings | No | No | No | Yes |
| Read audit log | No | No | No | Yes |

Contributors submit source drafts and can inspect their own drafts; content owners review and publish them. `platform_admin` is a reserved operator role; ordinary workspace administrators must not grant it. It is not a customer-facing global tenant browser.

Audience restrictions narrow reading access; granting a high role is an administrative permission and should be deliberate. Keep at least one active organization administrator. Share invitation links through a trusted channel; automated invitation email is not integrated.

## Acceptance criteria

- A new user can create a workspace and reach a meaningful onboarding screen.
- A viewer cannot perform content or administration mutations by either UI or direct API call.
- An authenticated member cannot read another organization's data by replacing IDs or headers.
- Unapproved or archived content cannot be retrieved as an answer or exposed to ordinary members.
- An approved document supports a relevant answer and citation; unrelated questions show an explicit no-evidence response.
- A video citation opens a bounded excerpt for its exact transcript chunk, with a seek bar limited to that excerpt; users can reveal the full source video below it. Transcript rows on source detail select the corresponding excerpt. This is a playback boundary in the authorized browser UI; the excerpt and full-video players currently use the same private source object, so it does not prevent a user with source playback access from inspecting the full media URL.
- Assistant answers use approved retrieved transcript passages. The configurable OpenAI-compatible and Ollama provider prompt directs the model to ignore merely similar context, keep how-to steps within a single source and its original order, and state when evidence is missing or conflicting. The local demo uses the deterministic mock provider; richer LLM inference requires the operator to configure and validate a real provider and key.
- Failed processing has an inspectable state and a documented recovery path.
- Invite acceptance checks email, expiry, role and tenant, and a workspace retains an active administrator.
- The help center exposes onboarding, role guidance, operations and release readiness documents.

## Success measurements

Track time to first approved source, time to first cited answer, weekly participating workspaces, member-reported helpfulness, unanswered question categories, review backlog age, ingestion failure rate and cost per useful answer. Establish baselines during the pilot; no numerical improvement is claimed yet. Do not log raw questions into general analytics without a defined privacy purpose and retention policy.

## Scope decisions

The current product is a knowledge assistant and content review system. Payments, password recovery email, verified-email signup, SAML/OIDC SSO, SCIM, automated retention deletion, global search across tenants and published extension distribution are separate workstreams. See the launch checklist before offering self-service subscriptions or enterprise commitments.
