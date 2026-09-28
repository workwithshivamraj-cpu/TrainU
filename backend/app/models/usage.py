from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class UsageMetric(UUIDPKMixin, TimestampMixin, Base):
    """Daily rollup of usage per organization, used by the usage dashboard.

    One row per (organization_id, metric_date). Updated incrementally by
    services as events happen (upload, processing completion, question
    asked, user activity).
    """

    __tablename__ = "usage_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "metric_date", name="uq_usage_metric_org_date"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)

    stored_video_minutes: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    processed_video_minutes: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
