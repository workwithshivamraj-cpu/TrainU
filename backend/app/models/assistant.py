from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ConfidenceLevel, FeedbackRating


class AssistantConversation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "assistant_conversations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300), default="New conversation", nullable=False)

    messages: Mapped[list["AssistantMessage"]] = relationship(
        "AssistantMessage", back_populates="conversation", cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at",
    )


class AssistantMessage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "assistant_messages"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[ConfidenceLevel | None] = mapped_column(String(10), nullable=True)
    follow_up_questions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    conversation: Mapped["AssistantConversation"] = relationship(
        "AssistantConversation", back_populates="messages"
    )
    citations: Mapped[list["AssistantCitation"]] = relationship(
        "AssistantCitation", back_populates="message", cascade="all, delete-orphan"
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="message", cascade="all, delete-orphan"
    )


class AssistantCitation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "assistant_citations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transcript_chunks.id"), nullable=False)
    source_title: Mapped[str] = mapped_column(String(300), nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    quoted_evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    similarity: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    message: Mapped["AssistantMessage"] = relationship("AssistantMessage", back_populates="citations")


class Feedback(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "feedback"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    rating: Mapped[FeedbackRating] = mapped_column(String(20), nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)

    message: Mapped["AssistantMessage"] = relationship("AssistantMessage", back_populates="feedback")
