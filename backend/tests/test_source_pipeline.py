from __future__ import annotations

import io

from app.models.enums import RoleName
from tests.conftest import auth_headers, make_membership, make_org, make_user


def _content_owner_headers(client, db, email="pipeline-owner@example.com"):
    user = make_user(db, email=email)
    org = make_org(db, name="Pipeline Org")
    make_membership(db, user, org, RoleName.CONTENT_OWNER)
    return auth_headers(client, email, "Password123!", org.id), org


def test_upload_rejects_unsupported_extension(client, db):
    headers, _org = _content_owner_headers(client, db, "reject-ext@example.com")
    resp = client.post(
        "/api/v1/sources",
        headers=headers,
        data={"title": "Bad file"},
        files={"file": ("malware.exe", io.BytesIO(b"not allowed"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


def test_upload_rejects_empty_file(client, db):
    headers, _org = _content_owner_headers(client, db, "reject-empty@example.com")
    resp = client.post(
        "/api/v1/sources",
        headers=headers,
        data={"title": "Empty file"},
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert resp.status_code == 400


def test_document_upload_runs_pipeline_to_awaiting_review(client, db):
    headers, _org = _content_owner_headers(client, db, "doc-pipeline@example.com")
    text = (
        "Introduction paragraph about the process.\n\n"
        "Step one is to open the application and click create. "
        "Step two is to fill in the required fields. "
        "Step three is to submit for approval."
    )
    resp = client.post(
        "/api/v1/sources",
        headers=headers,
        data={"title": "How To Guide", "feature_tag": "demo"},
        files={"file": ("guide.txt", io.BytesIO(text.encode()), "text/plain")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # CELERY_TASK_ALWAYS_EAGER runs the pipeline synchronously, so by the
    # time the request returns the source has already moved through
    # uploaded -> queued -> processing -> awaiting_review.
    assert body["status"] == "awaiting_review"
    assert len(body["jobs"]) >= 2


def test_source_requires_approval_before_indexed_and_retrievable(client, db):
    headers, org = _content_owner_headers(client, db, "approval-required@example.com")
    text = "This explains how to configure the widget. First open settings. Then click configure."
    created = client.post(
        "/api/v1/sources",
        headers=headers,
        data={"title": "Widget Config Guide"},
        files={"file": ("widget.txt", io.BytesIO(text.encode()), "text/plain")},
    ).json()
    source_id = created["id"]
    assert created["status"] == "awaiting_review"

    # Not yet approved -> assistant must not surface it as a citation.
    ask = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I configure the widget?"}, headers=headers
    ).json()
    assert ask["citations"] == []
    assert "could not find an approved source" in ask["answer"]

    # Approve it.
    approve = client.post(f"/api/v1/sources/{source_id}/approve", json={"note": "looks good"}, headers=headers)
    assert approve.status_code == 200
    assert approve.json()["status"] == "indexed"

    # Now retrievable.
    ask2 = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I configure the widget?"}, headers=headers
    ).json()
    assert len(ask2["citations"]) > 0
    assert ask2["citations"][0]["source_id"] == source_id


def test_cannot_approve_source_not_awaiting_review(client, db):
    headers, _org = _content_owner_headers(client, db, "bad-transition@example.com")
    text = "Some content about a process. It has two sentences."
    created = client.post(
        "/api/v1/sources",
        headers=headers,
        data={"title": "Doc"},
        files={"file": ("doc.txt", io.BytesIO(text.encode()), "text/plain")},
    ).json()
    source_id = created["id"]
    first = client.post(f"/api/v1/sources/{source_id}/approve", json={}, headers=headers)
    assert first.status_code == 200
    second = client.post(f"/api/v1/sources/{source_id}/approve", json={}, headers=headers)
    assert second.status_code == 409


def _org_admin_headers(client, db, email):
    user = make_user(db, email=email)
    org = make_org(db, name="Delete Org")
    make_membership(db, user, org, RoleName.ORG_ADMIN)
    return auth_headers(client, email, "Password123!", org.id), org


def test_delete_requires_archived_first(client, db):
    # Deletion requires org_admin; org_admin also satisfies the content_owner
    # minimum needed to upload, so one user can drive the whole flow.
    headers, _org = _org_admin_headers(client, db, "delete-flow@example.com")
    text = "Some content about a process. It has two sentences."
    created = client.post(
        "/api/v1/sources",
        headers=headers,
        data={"title": "Doc To Delete"},
        files={"file": ("doc2.txt", io.BytesIO(text.encode()), "text/plain")},
    ).json()
    source_id = created["id"]

    # Deleting while awaiting_review must be rejected.
    resp = client.delete(f"/api/v1/sources/{source_id}", headers=headers)
    assert resp.status_code == 409

    archive = client.post(f"/api/v1/sources/{source_id}/archive", headers=headers)
    assert archive.status_code == 200
    assert archive.json()["status"] == "archived"

    delete = client.delete(f"/api/v1/sources/{source_id}", headers=headers)
    assert delete.status_code == 204
