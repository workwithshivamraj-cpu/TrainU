from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, require_role
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.organization import Membership
from app.models.usage import UsageMetric
from app.schemas.usage import UsageMetricOut, UsageSummaryOut

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummaryOut)
def usage_summary(
    days: int = 30,
    membership: Membership = Depends(require_role(RoleName.VIEWER)),
    db: Session = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    stmt = (
        select(UsageMetric)
        .where(UsageMetric.organization_id == membership.organization_id, UsageMetric.metric_date >= since)
        .order_by(UsageMetric.metric_date)
    )
    rows = db.scalars(stmt).all()
    return UsageSummaryOut(
        total_stored_video_minutes=sum(r.stored_video_minutes for r in rows),
        total_processed_video_minutes=sum(r.processed_video_minutes for r in rows),
        total_questions_asked=sum(r.questions_asked for r in rows),
        active_users_last_30_days=sum(r.active_users for r in rows),
        daily=[UsageMetricOut.model_validate(r) for r in rows],
    )
