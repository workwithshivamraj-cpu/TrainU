from __future__ import annotations

import uuid
from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import ROLE_RANK, RoleName
from app.models.organization import Membership
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload is None or payload.type != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        user_id = uuid.UUID(payload.sub)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def get_current_membership(
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Membership:
    """Resolve the organization the caller is currently acting within.

    Clients pass the active org via the `X-Org-Id` header (needed because a
    user may belong to more than one organization). If omitted and the user
    has exactly one membership, that membership is used as a convenience
    default. Every org-scoped query in the app filters by
    `membership.organization_id` resolved here — there is no code path that
    lists data across organizations.
    """
    if x_org_id:
        try:
            org_uuid = uuid.UUID(x_org_id)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid X-Org-Id header")
        membership = next(
            (m for m in user.memberships if m.organization_id == org_uuid and m.is_active), None
        )
        if membership is None:
            # 404, not 403: never confirm/deny existence of orgs the caller can't access.
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
        return membership

    active_memberships = [m for m in user.memberships if m.is_active]
    if len(active_memberships) == 1:
        return active_memberships[0]
    if not active_memberships:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No organization membership")
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail="Multiple organizations available; specify X-Org-Id header",
    )


def require_role(minimum_role: RoleName):
    def dependency(membership: Membership = Depends(get_current_membership)) -> Membership:
        caller_rank = ROLE_RANK.get(RoleName(membership.role), -1)
        required_rank = ROLE_RANK[minimum_role]
        if caller_rank < required_rank:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Requires at least '{minimum_role.value}' role in this organization",
            )
        return membership

    return dependency


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return user
