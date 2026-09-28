from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction


def record_audit_event(
    db: Session,
    *,
    action: AuditAction,
    organization_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    resource_type: str = "",
    resource_id: str = "",
    description: str = "",
    metadata: dict | None = None,
    ip_address: str = "",
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action.value if isinstance(action, AuditAction) else action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        description=description,
        metadata_json=metadata or {},
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry
