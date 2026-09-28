from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_membership, require_role
from app.db.session import get_db
from app.models.application import Application, ApplicationModule
from app.models.enums import AuditAction, RoleName
from app.models.organization import Membership
from app.schemas.application import (
    ApplicationCreate,
    ApplicationModuleCreate,
    ApplicationModuleOut,
    ApplicationOut,
    ApplicationUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_org_application(db: Session, organization_id: uuid.UUID, application_id: uuid.UUID) -> Application:
    app = db.get(Application, application_id)
    if app is None or app.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)
):
    stmt = (
        select(Application)
        .options(selectinload(Application.modules))
        .where(Application.organization_id == membership.organization_id)
        .order_by(Application.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    membership: Membership = Depends(require_role(RoleName.CONTENT_OWNER)),
    db: Session = Depends(get_db),
):
    app = Application(organization_id=membership.organization_id, **payload.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    record_audit_event(
        db, action=AuditAction.APPLICATION_CREATED, organization_id=membership.organization_id,
        actor_user_id=membership.user_id, resource_type="application", resource_id=str(app.id),
        description=app.name,
    )
    return app


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: uuid.UUID,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    return _get_org_application(db, membership.organization_id, application_id)


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    membership: Membership = Depends(require_role(RoleName.CONTENT_OWNER)),
    db: Session = Depends(get_db),
):
    app = _get_org_application(db, membership.organization_id, application_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    db.commit()
    db.refresh(app)
    record_audit_event(
        db, action=AuditAction.APPLICATION_UPDATED, organization_id=membership.organization_id,
        actor_user_id=membership.user_id, resource_type="application", resource_id=str(app.id),
    )
    return app


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: uuid.UUID,
    membership: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    app = _get_org_application(db, membership.organization_id, application_id)
    db.delete(app)
    db.commit()


@router.post(
    "/{application_id}/modules", response_model=ApplicationModuleOut, status_code=status.HTTP_201_CREATED
)
def create_module(
    application_id: uuid.UUID,
    payload: ApplicationModuleCreate,
    membership: Membership = Depends(require_role(RoleName.CONTENT_OWNER)),
    db: Session = Depends(get_db),
):
    app = _get_org_application(db, membership.organization_id, application_id)
    module = ApplicationModule(
        organization_id=membership.organization_id, application_id=app.id, **payload.model_dump()
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module
