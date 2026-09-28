from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class UsageMetricOut(BaseModel):
    metric_date: date
    stored_video_minutes: float
    processed_video_minutes: float
    questions_asked: int
    active_users: int

    model_config = {"from_attributes": True}


class UsageSummaryOut(BaseModel):
    total_stored_video_minutes: float
    total_processed_video_minutes: float
    total_questions_asked: int
    active_users_last_30_days: int
    daily: list[UsageMetricOut]


class AuditLogOut(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: str
    description: str
    actor_user_id: str | None
    created_at: str
