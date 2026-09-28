from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import (
    ApplicationEnvironment,
    ProcessingJobStage,
    ProcessingJobStatus,
    RoleName,
    SourceStatus,
    SourceType,
)


class Source(UUIDPKMixin, TimestampMixin, Base):
    """A single uploaded KT video or document, and everything the ingestion
    pipeline and reviewers need to know about it."""

    __tablename__ = "sources"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), index=True, nullable=True
    )
    module_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_modules.id", ondelete="SET NULL"), nullable=True
    )
    content_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_type: Mapped[SourceType] = mapped_column(String(20), nullable=False)
    status: Mapped[SourceStatus] = mapped_column(
        String(30), default=SourceStatus.UPLOADED.value, nullable=False, index=True
    )

    # Metadata used for retrieval filtering.
    feature_tag: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    application_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    environment: Mapped[ApplicationEnvironment | None] = mapped_column(String(30), nullable=True)
    audience_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Storage.
    storage_bucket: Mapped[str] = mapped_column(String(200), default=settings.S3_BUCKET, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    jobs: Mapped[list["VideoProcessingJob"]] = relationship(
        "VideoProcessingJob", back_populates="source", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["TranscriptChunk"]] = relationship(
        "TranscriptChunk", back_populates="source", cascade="all, delete-orphan"
    )


class VideoProcessingJob(UUIDPKMixin, TimestampMixin, Base):
    """One row per pipeline stage run for a source, so processing status is
    fully auditable/observable."""

    __tablename__ = "video_processing_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stage: Mapped[ProcessingJobStage] = mapped_column(String(40), nullable=False)
    status: Mapped[ProcessingJobStatus] = mapped_column(
        String(20), default=ProcessingJobStatus.PENDING.value, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source"] = relationship("Source", back_populates="jobs")


class TranscriptChunk(UUIDPKMixin, TimestampMixin, Base):
    """A retrievable, embedded slice of a source: a transcript segment for
    video, or a paragraph/section for documents."""

    __tablename__ = "transcript_chunks"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    topic: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    start_seconds: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    application_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    environment: Mapped[ApplicationEnvironment | None] = mapped_column(String(30), nullable=True)
    audience_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Denormalized for fast filtering without a join back to Source.
    source_status: Mapped[SourceStatus] = mapped_column(String(30), nullable=False, index=True)
    content_owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    embedding: Mapped[list[float]] = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=True)

    source: Mapped["Source"] = relationship("Source", back_populates="chunks")
