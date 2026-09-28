from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from slugify import slugify

from app.api.deps import get_current_user
from app.core.rate_limit import client_key, rate_limiter
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.enums import AuditAction, InvitationStatus, RoleName
from app.models.organization import Invitation, Membership, Organization, OrganizationPlan
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from app.services.audit import record_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _unique_slug(db: Session, name: str) -> str:
    base = slugify(name) or "org"
    slug = base
    i = 1
    while db.scalars(select(Organization).where(Organization.slug == slug)).first():
        i += 1
        slug = f"{base}-{i}"
    return slug


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    rate_limiter.check(f"auth:{client_key(request)}", settings.RATE_LIMIT_AUTH_PER_MINUTE)

    existing = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    if payload.invitation_token:
        invitation = db.scalars(
            select(Invitation).where(Invitation.token == payload.invitation_token)
        ).first()
        if not invitation or invitation.status != InvitationStatus.PENDING.value:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invitation")
        if invitation.email.lower() != payload.email.lower():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invitation email mismatch")
        membership = Membership(
            user_id=user.id, organization_id=invitation.organization_id, role=invitation.role
        )
        invitation.status = InvitationStatus.ACCEPTED.value
        db.add(membership)
        record_audit_event(
            db, action=AuditAction.INVITE_ACCEPTED, organization_id=invitation.organization_id,
            actor_user_id=user.id, resource_type="invitation", resource_id=str(invitation.id),
            commit=False,
        )
    elif payload.organization_name:
        org = Organization(name=payload.organization_name, slug=_unique_slug(db, payload.organization_name))
        db.add(org)
        db.flush()
        db.add(OrganizationPlan(organization_id=org.id))
        membership = Membership(user_id=user.id, organization_id=org.id, role=RoleName.ORG_ADMIN.value)
        db.add(membership)
        record_audit_event(
            db, action=AuditAction.ORG_CREATED, organization_id=org.id, actor_user_id=user.id,
            resource_type="organization", resource_id=str(org.id), description=org.name, commit=False,
        )

    record_audit_event(
        db, action=AuditAction.REGISTER, actor_user_id=user.id, resource_type="user",
        resource_id=str(user.id), description=user.email, ip_address=client_key(request), commit=False,
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_platform_admin=user.is_platform_admin,
        memberships=[
            {
                "organization_id": m.organization_id,
                "organization_name": m.organization.name,
                "organization_slug": m.organization.slug,
                "role": m.role,
            }
            for m in user.memberships
            if m.is_active
        ],
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limiter.check(f"auth:{client_key(request)}", settings.RATE_LIMIT_AUTH_PER_MINUTE)

    user = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    record_audit_event(
        db, action=AuditAction.LOGIN, actor_user_id=user.id, resource_type="user",
        resource_id=str(user.id), ip_address=client_key(request),
    )
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data is None or token_data.type != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    try:
        user = db.get(User, uuid.UUID(token_data.sub))
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
