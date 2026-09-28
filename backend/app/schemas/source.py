from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SourceCreateMeta(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    application_id: uuid.UUID | None = None
    module_id: uuid.UUID | None = None
    feature_tag: str = ""
    application_version: str = ""
    environment: str | None = None
    audience_roles: list[str] = []


class ProcessingJobOut(BaseModel):
    id: uuid.UUID
    stage: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    detail: str
    error: str | None

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID | None
    module_id: uuid.UUID | None
    content_owner_id: uuid.UUID
    title: str
    description: str
    source_type: str
    status: str
    feature_tag: str
    application_version: str
    environment: str | None
    audience_roles: list[str]
    original_filename: str
    file_size_bytes: int
    duration_seconds: float | None
    approved_at: datetime | None
    archived_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceDetailOut(SourceOut):
    jobs: list[ProcessingJobOut] = []
    playback_url: str | None = None


class TranscriptChunkOut(BaseModel):
    id: uuid.UUID
    title: str
    topic: str
    text: str
    chunk_index: int
    start_seconds: float
    end_seconds: float

    model_config = {"from_attributes": True}


class ChunkUpdate(BaseModel):
    topic: str | None = None
    text: str | None = None
    audience_roles: list[str] | None = None


class SourceApprovalAction(BaseModel):
    note: str = ""
