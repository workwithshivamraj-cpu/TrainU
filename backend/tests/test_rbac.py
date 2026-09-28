from __future__ import annotations

from app.models.enums import RoleName
from tests.conftest import auth_headers, make_membership, make_org, make_user


def _bootstrap_org_with_role(db, client, role: RoleName, email="member@example.com"):
    user = make_user(db, email=email)
    org = make_org(db, name=f"RBAC Org {role.value}")
    make_membership(db, user, org, role)
    return org, user


def test_viewer_cannot_create_application(client, db):
    org, _ = _bootstrap_org_with_role(db, client, RoleName.VIEWER, "viewer1@example.com")
    headers = auth_headers(client, "viewer1@example.com", "Password123!", org.id)
    resp = client.post("/api/v1/applications", json={"name": "Should Fail"}, headers=headers)
    assert resp.status_code == 403


def test_contributor_cannot_create_application(client, db):
    org, _ = _bootstrap_org_with_role(db, client, RoleName.CONTRIBUTOR, "contrib1@example.com")
    headers = auth_headers(client, "contrib1@example.com", "Password123!", org.id)
    resp = client.post("/api/v1/applications", json={"name": "Should Fail"}, headers=headers)
    assert resp.status_code == 403


def test_content_owner_can_create_application(client, db):
    org, _ = _bootstrap_org_with_role(db, client, RoleName.CONTENT_OWNER, "owner1@example.com")
    headers = auth_headers(client, "owner1@example.com", "Password123!", org.id)
    resp = client.post("/api/v1/applications", json={"name": "Allowed App"}, headers=headers)
    assert resp.status_code == 201


def test_content_owner_cannot_change_member_roles(client, db):
    org, _ = _bootstrap_org_with_role(db, client, RoleName.CONTENT_OWNER, "owner2@example.com")
    other = make_user(db, email="other2@example.com")
    other_membership = make_membership(db, other, org, RoleName.VIEWER)
    headers = auth_headers(client, "owner2@example.com", "Password123!", org.id)
    resp = client.patch(
        f"/api/v1/organizations/current/members/{other_membership.id}/role",
        json={"role": "org_admin"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_org_admin_can_change_member_roles(client, db):
    org, _ = _bootstrap_org_with_role(db, client, RoleName.ORG_ADMIN, "admin2@example.com")
    other = make_user(db, email="other3@example.com")
    other_membership = make_membership(db, other, org, RoleName.VIEWER)
    headers = auth_headers(client, "admin2@example.com", "Password123!", org.id)
    resp = client.patch(
        f"/api/v1/organizations/current/members/{other_membership.id}/role",
        json={"role": "content_owner"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "content_owner"


def test_only_org_admin_can_delete_application(client, db):
    org, _ = _bootstrap_org_with_role(db, client, RoleName.CONTENT_OWNER, "owner3@example.com")
    headers = auth_headers(client, "owner3@example.com", "Password123!", org.id)
    created = client.post("/api/v1/applications", json={"name": "To Delete"}, headers=headers)
    app_id = created.json()["id"]

    resp = client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert resp.status_code == 403
