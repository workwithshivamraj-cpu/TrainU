from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    logo_url: str | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None
    retention_days: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="viewer")


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    token: str

    model_config = {"from_attributes": True}


class InvitationAccept(BaseModel):
    token: str


class MemberOut(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class MemberRoleUpdate(BaseModel):
    role: str
