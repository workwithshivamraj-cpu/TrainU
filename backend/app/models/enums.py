from __future__ import annotations

import enum


class RoleName(str, enum.Enum):
    PLATFORM_ADMIN = "platform_admin"
    ORG_ADMIN = "org_admin"
    CONTENT_OWNER = "content_owner"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


# Roles ranked from least to most privileged, used for "at least this role" checks.
ROLE_RANK = {
    RoleName.VIEWER: 0,
    RoleName.CONTRIBUTOR: 1,
    RoleName.CONTENT_OWNER: 2,
    RoleName.ORG_ADMIN: 3,
    RoleName.PLATFORM_ADMIN: 4,
}


class ApplicationEnvironment(str, enum.Enum):
    DEVELOPMENT = "development"
    UAT = "uat"
    PRODUCTION = "production"


class ApplicationStatus(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class SourceType(str, enum.Enum):
    VIDEO = "video"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    TEXT = "text"


class SourceStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


# Valid forward transitions for the source processing state machine.
SOURCE_STATUS_TRANSITIONS: dict[SourceStatus, set[SourceStatus]] = {
    SourceStatus.UPLOADED: {SourceStatus.QUEUED, SourceStatus.FAILED},
    SourceStatus.QUEUED: {SourceStatus.PROCESSING, SourceStatus.FAILED},
    SourceStatus.PROCESSING: {SourceStatus.AWAITING_REVIEW, SourceStatus.FAILED},
    SourceStatus.AWAITING_REVIEW: {SourceStatus.APPROVED, SourceStatus.FAILED, SourceStatus.ARCHIVED},
    SourceStatus.APPROVED: {SourceStatus.INDEXED, SourceStatus.ARCHIVED},
    SourceStatus.INDEXED: {SourceStatus.ARCHIVED},
    SourceStatus.FAILED: {SourceStatus.QUEUED, SourceStatus.ARCHIVED},
    SourceStatus.ARCHIVED: set(),
}


class ProcessingJobStage(str, enum.Enum):
    UPLOAD_VALIDATION = "upload_validation"
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    DOCUMENT_PARSING = "document_parsing"


class ProcessingJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class FeedbackRating(str, enum.Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    INVITE_SENT = "invite_sent"
    INVITE_ACCEPTED = "invite_accepted"
    INVITE_REVOKED = "invite_revoked"
    UPLOAD = "upload"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    SOURCE_APPROVED = "source_approved"
    SOURCE_ARCHIVED = "source_archived"
    SOURCE_DELETED = "source_deleted"
    ROLE_CHANGED = "role_changed"
    MEMBER_REMOVED = "member_removed"
    ASSISTANT_ANSWER_GENERATED = "assistant_answer_generated"
    ORG_CREATED = "org_created"
    ORG_UPDATED = "org_updated"
    APPLICATION_CREATED = "application_created"
    APPLICATION_UPDATED = "application_updated"
