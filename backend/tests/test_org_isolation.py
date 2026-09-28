from __future__ import annotations

from tests.conftest import auth_headers


def _register(client, email, org_name):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SuperSecret123!",
            "full_name": "Owner",
            "organization_name": org_name,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["memberships"][0]["organization_id"]


def test_application_created_in_one_org_not_visible_in_another(client):
    org_a_id = _register(client, "a-owner@example.com", "Org A")
    org_b_id = _register(client, "b-owner@example.com", "Org B")

    headers_a = auth_headers(client, "a-owner@example.com", "SuperSecret123!", org_a_id)
    headers_b = auth_headers(client, "b-owner@example.com", "SuperSecret123!", org_b_id)

    create = client.post(
        "/api/v1/applications",
        json={"name": "Org A App", "description": "desc"},
        headers=headers_a,
    )
    assert create.status_code == 201, create.text
    app_id = create.json()["id"]

    # Org A can see its own application.
    list_a = client.get("/api/v1/applications", headers=headers_a)
    assert any(a["id"] == app_id for a in list_a.json())

    # Org B's list must not include Org A's application.
    list_b = client.get("/api/v1/applications", headers=headers_b)
    assert all(a["id"] != app_id for a in list_b.json())

    # Org B directly fetching Org A's application by ID gets 404, not 403 or 200.
    get_cross = client.get(f"/api/v1/applications/{app_id}", headers=headers_b)
    assert get_cross.status_code == 404


def test_cannot_use_x_org_id_for_organization_without_membership(client):
    org_a_id = _register(client, "solo-a@example.com", "Solo Org A")
    _register(client, "solo-b@example.com", "Solo Org B")

    headers_b_wrong_org = auth_headers(client, "solo-b@example.com", "SuperSecret123!", org_a_id)
    resp = client.get("/api/v1/organizations/current", headers=headers_b_wrong_org)
    assert resp.status_code == 404


def test_assistant_conversations_scoped_to_organization(client):
    org_a_id = _register(client, "conv-a@example.com", "Conv Org A")
    org_b_id = _register(client, "conv-b@example.com", "Conv Org B")
    headers_a = auth_headers(client, "conv-a@example.com", "SuperSecret123!", org_a_id)
    headers_b = auth_headers(client, "conv-b@example.com", "SuperSecret123!", org_b_id)

    ask_a = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I do something?"}, headers=headers_a
    )
    assert ask_a.status_code == 200

    convs_b = client.get("/api/v1/assistant/conversations", headers=headers_b)
    assert convs_b.json() == []
