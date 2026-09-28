from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usage import UsageMetric


def _get_or_create_today(db: Session, organization_id: uuid.UUID) -> UsageMetric:
    today = date.today()
    stmt = select(UsageMetric).where(
        UsageMetric.organization_id == organization_id, UsageMetric.metric_date == today
    )
    metric = db.scalars(stmt).first()
    if metric is None:
        metric = UsageMetric(organization_id=organization_id, metric_date=today)
        db.add(metric)
        db.flush()
    return metric


def record_stored_video_minutes(db: Session, organization_id: uuid.UUID, minutes: float) -> None:
    metric = _get_or_create_today(db, organization_id)
    metric.stored_video_minutes += minutes
    db.commit()


def record_processed_video_minutes(db: Session, organization_id: uuid.UUID, minutes: float) -> None:
    metric = _get_or_create_today(db, organization_id)
    metric.processed_video_minutes += minutes
    db.commit()


def record_question_asked(db: Session, organization_id: uuid.UUID) -> None:
    metric = _get_or_create_today(db, organization_id)
    metric.questions_asked += 1
    db.commit()


def record_active_user(db: Session, organization_id: uuid.UUID) -> None:
    metric = _get_or_create_today(db, organization_id)
    metric.active_users += 1
    db.commit()
