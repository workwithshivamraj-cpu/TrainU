from __future__ import annotations

import os
import uuid

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://trainu:trainu@localhost:5432/trainu_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "trainu_admin")
os.environ.setdefault("S3_SECRET_KEY", "trainu_admin_secret")
os.environ.setdefault("S3_BUCKET", "trainu-media-test")
os.environ.setdefault("STT_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("EMBEDDINGS_PROVIDER", "mock")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import RoleName
from app.models.organization import Membership, Organization
from app.models.user import User
from app.core.security import hash_password
from app.core.rate_limit import rate_limiter
from app.services.storage import ensure_bucket

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
    try:
        ensure_bucket()
    except Exception:  # noqa: BLE001 - object storage optional for pure-DB tests
        pass
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
