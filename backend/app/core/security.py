"""Password hashing and JWT access/refresh token helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


def _create_token(
    subject: str, token_type: TokenType, expires_delta: timedelta, extra: dict | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, org_id: str | None = None, session_id: str | None = None) -> str:
    extra = {"org_id": org_id} if org_id else {}
    if session_id:
        extra["sid"] = session_id
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra,
    )


def create_refresh_token(user_id: str, session_id: str | None = None) -> str:
    return _create_token(
        user_id, "refresh", timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        {"sid": session_id} if session_id else None,
    )


class TokenPayload:
    def __init__(self, sub: str, type: str, jti: str, org_id: str | None = None, sid: str | None = None):
        self.sub = sub
        self.type = type
        self.jti = jti
        self.org_id = org_id
        self.sid = sid


def decode_token(token: str) -> TokenPayload | None:
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                          options={"require": ["exp", "iat", "sub", "jti"]})
    except InvalidTokenError:
        return None
    return TokenPayload(
        sub=data.get("sub"),
        type=data.get("type"),
        jti=data.get("jti"),
        org_id=data.get("org_id"),
        sid=data.get("sid"),
    )
