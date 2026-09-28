from __future__ import annotations

from tests.conftest import auth_headers


def test_register_creates_user_and_org(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "founder@acme.example",
            "password": "SuperSecret123!",
            "full_name": "Founder Person",
            "organization_name": "Acme Inc",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "founder@acme.example"
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["role"] == "org_admin"
    assert body["memberships"][0]["organization_name"] == "Acme Inc"


def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "dup@acme.example",
        "password": "SuperSecret123!",
        "full_name": "Dup User",
        "organization_name": "Acme Inc",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400


def test_login_success_and_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@acme.example",
            "password": "SuperSecret123!",
            "full_name": "Login User",
            "organization_name": "Acme Inc",
        },
    )
    ok = client.post(
        "/api/v1/auth/login", json={"email": "login@acme.example", "password": "SuperSecret123!"}
    )
    assert ok.status_code == 200
    assert "access_token" in ok.json()
    assert "refresh_token" in ok.json()

    bad = client.post(
        "/api/v1/auth/login", json={"email": "login@acme.example", "password": "wrong"}
    )
    assert bad.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_refresh_token_issues_new_access_token(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@acme.example",
            "password": "SuperSecret123!",
            "full_name": "Refresh User",
            "organization_name": "Acme Inc",
        },
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "refresh@acme.example", "password": "SuperSecret123!"}
    )
    refresh_token = login.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_invalid_refresh_token_rejected(client):
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401
