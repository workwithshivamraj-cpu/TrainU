from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    application_id: uuid.UUID | None = None
    application_version: str | None = None
    environment: str | None = None
    conversation_id: uuid.UUID | None = None


class CitationOut(BaseModel):
    source_id: uuid.UUID
    chunk_id: uuid.UUID
    source_title: str
    start_seconds: float
    end_seconds: float
    quoted_evidence: str
    confidence_score: float
    is_archived: bool = False


class RelatedClipOut(BaseModel):
    source_id: uuid.UUID
    source_title: str
    topic: str
    start_seconds: float
    end_seconds: float


class AskResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    steps: list[str] = []
    confidence: str
    citations: list[CitationOut] = []
    related_clips: list[RelatedClipOut] = []
    follow_up_questions: list[str] = []


class FeedbackCreate(BaseModel):
    message_id: uuid.UUID
    rating: str
    comment: str = ""


class FeedbackOut(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    rating: str
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    confidence: str | None
    follow_up_questions: list[str]
    citations: list[CitationOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    application_id: uuid.UUID | None
    created_at: datetime
    messages: list[ConversationMessageOut] = []

    model_config = {"from_attributes": True}
