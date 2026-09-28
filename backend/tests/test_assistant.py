from __future__ import annotations

import io

from app.models.enums import RoleName
from tests.conftest import auth_headers, make_membership, make_org, make_user


def _content_owner_headers(client, db, email):
    user = make_user(db, email=email)
    org = make_org(db, name="Assistant Org")
    make_membership(db, user, org, RoleName.CONTENT_OWNER)
    return auth_headers(client, email, "Password123!", org.id), org


def _seed_approved_source(client, headers, title="Guide", text=None):
    text = text or (
        "This guide explains how to reset a password. "
        "First, go to account settings. "
        "Next, click reset password. "
        "Finally, check your email for the confirmation link."
    )
    created = client.post(
        "/api/v1/sources",
        headers=headers,
        data={"title": title},
        files={"file": ("guide.txt", io.BytesIO(text.encode()), "text/plain")},
    ).json()
    client.post(f"/api/v1/sources/{created['id']}/approve", json={}, headers=headers)
    return created["id"]


def test_no_answer_when_no_sources_exist(client, db):
    headers, _org = _content_owner_headers(client, db, "empty-org@example.com")
    resp = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I do anything at all?"}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["citations"] == []
    assert body["confidence"] == "none"
    assert "could not find an approved source" in body["answer"]


def test_ask_returns_well_formed_citation_schema(client, db):
    headers, _org = _content_owner_headers(client, db, "citation-schema@example.com")
    _seed_approved_source(client, headers)

    resp = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I reset a password?"}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["confidence"] in {"high", "medium", "low", "none"}
    assert len(body["citations"]) > 0
    for citation in body["citations"]:
        assert {
            "source_id", "chunk_id", "source_title", "start_seconds", "end_seconds",
            "quoted_evidence", "confidence_score",
        }.issubset(citation.keys())
        assert isinstance(citation["start_seconds"], (int, float))
        assert citation["end_seconds"] >= citation["start_seconds"]
        assert 0.0 <= citation["confidence_score"] <= 1.0
        assert citation["quoted_evidence"]


def test_feedback_can_be_submitted_and_listed(client, db):
    headers, _org = _content_owner_headers(client, db, "feedback-user@example.com")
    _seed_approved_source(client, headers)
    ask = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I reset a password?"}, headers=headers
    ).json()

    fb = client.post(
        "/api/v1/assistant/feedback",
        json={"message_id": ask["message_id"], "rating": "helpful", "comment": "Clear steps"},
        headers=headers,
    )
    assert fb.status_code == 201
    assert fb.json()["rating"] == "helpful"

    listing = client.get("/api/v1/assistant/feedback", headers=headers)
    assert any(f["message_id"] == ask["message_id"] for f in listing.json())


def test_feedback_rejects_invalid_rating(client, db):
    headers, _org = _content_owner_headers(client, db, "feedback-invalid@example.com")
    _seed_approved_source(client, headers)
    ask = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I reset a password?"}, headers=headers
    ).json()
    fb = client.post(
        "/api/v1/assistant/feedback",
        json={"message_id": ask["message_id"], "rating": "amazing"},
        headers=headers,
    )
    assert fb.status_code == 400


def test_archived_source_not_retrievable(client, db):
    headers, _org = _content_owner_headers(client, db, "archived-source@example.com")
    source_id = _seed_approved_source(client, headers)
    client.post(f"/api/v1/sources/{source_id}/archive", headers=headers)

    resp = client.post(
        "/api/v1/assistant/ask", json={"question": "How do I reset a password?"}, headers=headers
    ).json()
    assert resp["citations"] == []
