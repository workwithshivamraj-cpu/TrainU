from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, get_current_user, require_role
from app.core.rate_limit import client_key
from app.db.session import get_db
from app.models.enums import AuditAction, InvitationStatus, RoleName
from app.models.organization import Invitation, Membership, Organization
from app.models.user import User
from app.schemas.organization import (
    InvitationAccept,
    InvitationCreate,
    InvitationOut,
    MemberOut,
    MemberRoleUpdate,
    OrganizationOut,
    OrganizationUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/current", response_model=OrganizationOut)
def get_current_organization(
    membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)
):
    org = db.get(Organization, membership.organization_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch("/current", response_model=OrganizationOut)
def update_current_organization(
    payload: OrganizationUpdate,
    membership: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, membership.organization_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    record_audit_event(
        db, action=AuditAction.ORG_UPDATED, organization_id=org.id, actor_user_id=membership.user_id,
        resource_type="organization", resource_id=str(org.id),
    )
    return org


@router.get("/current/members", response_model=list[MemberOut])
def list_members(
    membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(Membership).where(Membership.organization_id == membership.organization_id)
    ).all()
    return [
        MemberOut(
            membership_id=m.id, user_id=m.user_id, email=m.user.email, full_name=m.user.full_name,
            role=m.role, is_active=m.is_active,
        )
        for m in rows
    ]


@router.patch("/current/members/{membership_id}/role", response_model=MemberOut)
def update_member_role(
    membership_id: uuid.UUID,
    payload: MemberRoleUpdate,
    caller: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.get(Membership, membership_id)
    if target is None or target.organization_id != caller.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Member not found")
    if payload.role not in {r.value for r in RoleName}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    old_role = target.role
    target.role = payload.role
    db.commit()
    db.refresh(target)
    record_audit_event(
        db, action=AuditAction.ROLE_CHANGED, organization_id=caller.organization_id,
        actor_user_id=caller.user_id, resource_type="membership", resource_id=str(target.id),
        description=f"{old_role} -> {payload.role}",
    )
    return MemberOut(
        membership_id=target.id, user_id=target.user_id, email=target.user.email,
        full_name=target.user.full_name, role=target.role, is_active=target.is_active,
    )


@router.delete("/current/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    membership_id: uuid.UUID,
    caller: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.get(Membership, membership_id)
    if target is None or target.organization_id != caller.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Member not found")
    target.is_active = False
    db.commit()
    record_audit_event(
        db, action=AuditAction.MEMBER_REMOVED, organization_id=caller.organization_id,
        actor_user_id=caller.user_id, resource_type="membership", resource_id=str(target.id),
    )


@router.post("/current/invitations", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    request: Request,
    caller: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    if payload.role not in {r.value for r in RoleName}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    invitation = Invitation(
        organization_id=caller.organization_id,
        email=payload.email.lower(),
        role=payload.role,
        invited_by_id=caller.user_id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    record_audit_event(
        db, action=AuditAction.INVITE_SENT, organization_id=caller.organization_id,
        actor_user_id=caller.user_id, resource_type="invitation", resource_id=str(invitation.id),
        description=invitation.email, ip_address=client_key(request),
    )
    return invitation


@router.get("/current/invitations", response_model=list[InvitationOut])
def list_invitations(
    caller: Membership = Depends(require_role(RoleName.ORG_ADMIN)), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Invitation).where(Invitation.organization_id == caller.organization_id)
        .order_by(Invitation.created_at.desc())
    ).all()


@router.post("/current/invitations/{invitation_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: uuid.UUID,
    caller: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    invitation = db.get(Invitation, invitation_id)
    if invitation is None or invitation.organization_id != caller.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    invitation.status = InvitationStatus.REVOKED.value
    db.commit()
    record_audit_event(
        db, action=AuditAction.INVITE_REVOKED, organization_id=caller.organization_id,
        actor_user_id=caller.user_id, resource_type="invitation", resource_id=str(invitation.id),
    )


@router.post("/invitations/accept", response_model=MemberOut)
def accept_invitation(
    payload: InvitationAccept, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    invitation = db.scalars(select(Invitation).where(Invitation.token == payload.token)).first()
    if invitation is None or invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invitation")
    if invitation.email.lower() != user.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invitation email mismatch")
    existing = db.scalars(
        select(Membership).where(
            Membership.user_id == user.id, Membership.organization_id == invitation.organization_id
        )
    ).first()
    if existing:
        existing.is_active = True
        existing.role = invitation.role
        membership = existing
    else:
        membership = Membership(
            user_id=user.id, organization_id=invitation.organization_id, role=invitation.role
        )
        db.add(membership)
    invitation.status = InvitationStatus.ACCEPTED.value
    db.commit()
    db.refresh(membership)
    record_audit_event(
        db, action=AuditAction.INVITE_ACCEPTED, organization_id=invitation.organization_id,
        actor_user_id=user.id, resource_type="invitation", resource_id=str(invitation.id),
    )
    return MemberOut(
        membership_id=membership.id, user_id=user.id, email=user.email, full_name=user.full_name,
        role=membership.role, is_active=membership.is_active,
    )
