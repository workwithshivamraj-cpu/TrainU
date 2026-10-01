"""Regression coverage for session, tenant and organization authorization."""
from datetime import datetime, timedelta, timezone
import io
import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import hash_password, verify_password
from app.models.application import Application, ApplicationModule
from app.models.enums import RoleName
from app.models.organization import Invitation
from app.models.source import Source
from tests.conftest import auth_headers, make_membership, make_org, make_user


def _member(db, client, role=RoleName.ORG_ADMIN):
    user = make_user(db, email=f"{uuid.uuid4().hex}@example.com")
    org = make_org(db)
    membership = make_membership(db, user, org, role)
    headers = auth_headers(client, user.email, "Password123!", org.id)
    return user, org, membership, headers


def _login(client, user):
    return client.post("/api/v1/auth/login", json={"email": user.email, "password": "Password123!"}).json()


def test_refresh_replay_revokes_successor_and_access(client, db):
    user, _, _, _ = _member(db, client)
    tokens = _login(client, user)
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + rotated.json()["access_token"]}).status_code == 401


def test_logout_revokes_access_and_refresh(client, db):
    user, _, _, _ = _member(db, client)
    tokens = _login(client, user)
    assert client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + tokens["access_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_organization_admin_cannot_assign_platform_admin(client, db):
    _, org, _, headers = _member(db, client)
    member = make_membership(db, make_user(db, email="viewer@example.com"), org, RoleName.VIEWER)
    assert client.patch(f"/api/v1/organizations/current/members/{member.id}/role", headers=headers,
                        json={"role": "platform_admin"}).status_code == 400
    assert client.post("/api/v1/organizations/current/invitations", headers=headers,
                       json={"email": "invite@example.com", "role": "platform_admin"}).status_code == 400


def test_last_administrator_cannot_be_removed_or_demoted(client, db):
    _, _, member, headers = _member(db, client)
    assert client.delete(f"/api/v1/organizations/current/members/{member.id}", headers=headers).status_code == 409
    assert client.patch(f"/api/v1/organizations/current/members/{member.id}/role", headers=headers,
                        json={"role": "viewer"}).status_code == 409


def test_registration_rejects_expired_invitation(client, db):
    owner, org, _, _ = _member(db, client)
    invite = Invitation(organization_id=org.id, email="expired@example.com", role="viewer",
                        invited_by_id=owner.id, token="expired-token", expires_at=datetime.now(timezone.utc)-timedelta(days=1))
    db.add(invite)
    db.commit()
    response = client.post("/api/v1/auth/register", json={"email": invite.email, "password": "Password123!",
                           "full_name": "Invited Person", "invitation_token": invite.token})
    assert response.status_code == 400


def test_upload_rejects_application_from_another_tenant(client, db):
    _, _, _, headers = _member(db, client)
    foreign_org = make_org(db)
    application = Application(organization_id=foreign_org.id, name="Private app")
    db.add(application)
    db.commit()
    response = client.post("/api/v1/sources", headers=headers,
                           data={"title": "Guide", "application_id": str(application.id)},
                           files={"file": ("guide.txt", io.BytesIO(b"Training guide"), "text/plain")})
    assert response.status_code == 404


def test_viewer_cannot_read_draft_or_restricted_source(client, db):
    owner, org, _, _ = _member(db, client)
    viewer = make_user(db, email="restricted-viewer@example.com")
    make_membership(db, viewer, org, RoleName.VIEWER)
    headers = auth_headers(client, viewer.email, "Password123!", org.id)
    for state, audience in [("awaiting_review", []), ("indexed", ["org_admin"])]:
        source = Source(organization_id=org.id, content_owner_id=owner.id, title="Private", source_type="text",
                        status=state, audience_roles=audience, storage_key="private.txt", original_filename="private.txt")
        db.add(source)
        db.commit()
        assert client.get(f"/api/v1/sources/{source.id}", headers=headers).status_code == 404
        assert client.get(f"/api/v1/sources/{source.id}/chunks", headers=headers).status_code == 404
    assert client.get("/api/v1/sources", headers=headers).json() == []


def test_contributor_uploads_while_viewer_cannot(client, db):
    _, _, _, contributor = _member(db, client, RoleName.CONTRIBUTOR)
    result = client.post("/api/v1/sources", headers=contributor, data={"title": "Contribution"},
                         files={"file": ("guide.txt", io.BytesIO(b"Open settings. Configure the account."), "text/plain")})
    assert result.status_code == 201, result.text
    _, _, _, viewer = _member(db, client, RoleName.VIEWER)
    assert client.post("/api/v1/sources", headers=viewer, data={"title": "Forbidden"},
                       files={"file": ("guide.txt", io.BytesIO(b"Test"), "text/plain")}).status_code == 403


def test_cannot_append_to_another_users_conversation(client, db):
    _, org, _, owner_headers = _member(db, client)
    other = make_user(db, email="other-conversation@example.com")
    make_membership(db, other, org, RoleName.VIEWER)
    other_headers = auth_headers(client, other.email, "Password123!", org.id)
    response = client.post("/api/v1/assistant/ask", headers=owner_headers, json={"question": "How do I sign in?"})
    assert response.status_code == 200, response.text
    result = client.post("/api/v1/assistant/ask", headers=other_headers,
                         json={"question": "Show prior context", "conversation_id": response.json()["conversation_id"]})
    assert result.status_code == 404


def test_rate_limit_exposes_retry_after(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 1)
    request = {"email": "unknown@example.com", "password": "wrong"}
    assert client.post("/api/v1/auth/login", json=request).status_code == 401
    response = client.post("/api/v1/auth/login", json=request)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_redis_failure_does_not_bypass_limits(monkeypatch):
    from redis.exceptions import ConnectionError
    import app.core.rate_limit as rate_limit
    class BrokenRedis:
        def eval(self, *args):
            raise ConnectionError("Unavailable")
    monkeypatch.setattr(settings, "RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setattr(rate_limit, "get_redis", lambda: BrokenRedis())
    with pytest.raises(HTTPException) as error:
        SlidingWindowRateLimiter().check("user", 1)
    assert error.value.status_code == 503


def test_production_rejects_development_configuration():
    with pytest.raises(ValidationError, match="Unsafe deployment configuration"):
        Settings(_env_file=None, ENVIRONMENT="production")


def test_password_hash_preserves_characters_after_bcrypt_limit():
    prefix = "a" * 72
    hashed = hash_password(prefix + "actual")
    assert verify_password(prefix + "actual", hashed)
    assert not verify_password(prefix + "different", hashed)
