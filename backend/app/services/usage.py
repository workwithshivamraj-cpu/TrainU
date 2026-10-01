from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.usage import UsageMetric


def _increment(db: Session, organization_id: uuid.UUID, field: str, amount: float | int) -> None:
    # An atomic upsert prevents lost updates and first-request races across replicas.
    values = {"organization_id": organization_id,
              "metric_date": datetime.now(timezone.utc).date(), field: amount}
    stmt = insert(UsageMetric).values(**values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_usage_metric_org_date",
        set_={field: getattr(UsageMetric, field) + amount,
              "updated_at": datetime.now(timezone.utc)},
    )
    db.execute(stmt)
    db.commit()


def record_stored_video_minutes(db: Session, organization_id: uuid.UUID, minutes: float) -> None:
    _increment(db, organization_id, "stored_video_minutes", minutes)


def record_processed_video_minutes(db: Session, organization_id: uuid.UUID, minutes: float) -> None:
    _increment(db, organization_id, "processed_video_minutes", minutes)


def record_question_asked(db: Session, organization_id: uuid.UUID) -> None:
    _increment(db, organization_id, "questions_asked", 1)


def record_active_user(db: Session, organization_id: uuid.UUID) -> None:
    _increment(db, organization_id, "active_users", 1)
