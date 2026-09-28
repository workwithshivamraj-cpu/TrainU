from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.enums import RoleName
from app.models.organization import Membership

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("")
def list_audit_log(
    limit: int = 100,
    action: str | None = None,
    membership: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).where(AuditLog.organization_id == membership.organization_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "description": r.description,
            "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
