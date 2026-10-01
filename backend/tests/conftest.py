from __future__ import annotations

import os
import uuid

# Validate before importing the application or constructing an engine. Test
# fixtures drop and recreate every mapped table, so inherited runtime settings
# must never be allowed to select their target implicitly.
from app.core.test_environment import configure_destructive_test_environment

configure_destructive_test_environment(os.environ)

os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["S3_ENDPOINT_URL"] = os.environ.get("TRAINU_TEST_S3_ENDPOINT_URL", "http://localhost:9000")
os.environ["S3_PUBLIC_ENDPOINT_URL"] = os.environ["S3_ENDPOINT_URL"]
os.environ.setdefault("S3_ACCESS_KEY", "trainu_admin")
os.environ.setdefault("S3_SECRET_KEY", "trainu_admin_secret")
os.environ["STT_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDINGS_PROVIDER"] = "mock"
os.environ["SECRET_KEY"] = "trainu-test-only-key-not-for-production-2026"

import pytest
from app.core.rate_limit import rate_limiter
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import RoleName
from app.models.organization import Membership, Organization
from app.models.user import User
from app.services.storage import ensure_bucket
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_bucket()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def _clean_tables():
    rate_limiter._hits.clear()
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture()
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, email="user@example.com", full_name="Test User", password="Password123!"):
    user = User(email=email, full_name=full_name, hashed_password=hash_password(password))
    db.add(user)
    db.flush()
    return user


def make_org(db, name="Test Org"):
    org = Organization(name=name, slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}")
    db.add(org)
    db.flush()
    return org


def make_membership(db, user, org, role=RoleName.CONTENT_OWNER):
    m = Membership(user_id=user.id, organization_id=org.id, role=role.value)
    db.add(m)
    db.commit()
    return m


def auth_headers(client, email, password, org_id=None):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if org_id:
        headers["X-Org-Id"] = str(org_id)
    return headers
