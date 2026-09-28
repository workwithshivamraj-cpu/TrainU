from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApplicationModuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    features: list[str] = []


class ApplicationModuleOut(ApplicationModuleCreate):
    id: uuid.UUID
    application_id: uuid.UUID

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    version: str = "1.0.0"
    environment: str = "production"
    owning_team: str = ""
    support_contact: str = ""
    status: str = "active"
    features: list[str] = []


class ApplicationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: str | None = None
    environment: str | None = None
    owning_team: str | None = None
    support_contact: str | None = None
    status: str | None = None
    features: list[str] | None = None


class ApplicationOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str
    version: str
    environment: str
    owning_team: str
    support_contact: str
    status: str
    features: list[str]
    created_at: datetime
    modules: list[ApplicationModuleOut] = []

    model_config = {"from_attributes": True}
