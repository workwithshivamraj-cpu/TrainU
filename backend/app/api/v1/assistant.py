from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_membership
from app.core.config import settings
from app.core.rate_limit import client_key, rate_limiter
from app.db.session import get_db
from app.models.assistant import (
    AssistantCitation,
    AssistantConversation,
    AssistantMessage,
    Feedback,
)
from app.models.enums import AuditAction, FeedbackRating
from app.models.organization import Membership
from app.models.application import Application
from app.schemas.assistant import (
    AskRequest,
    AskResponse,
    CitationOut,
    ConversationOut,
    FeedbackCreate,
    FeedbackOut,
    RelatedClipOut,
)
from app.services.audit import record_audit_event
from app.services.rag import answer_question
from app.services.usage import record_active_user, record_question_asked

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    request: Request,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    rate_limiter.check(
        f"assistant:{client_key(request)}:{membership.user_id}",
        settings.RATE_LIMIT_ASSISTANT_PER_MINUTE,
    )

    if payload.application_id:
        application = db.get(Application, payload.application_id)
        if application is None or application.organization_id != membership.organization_id:
            raise HTTPException(404, detail="Application not found")

    if payload.conversation_id:
        conversation = db.get(AssistantConversation, payload.conversation_id)
        if (conversation is None or conversation.organization_id != membership.organization_id
                or conversation.user_id != membership.user_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        conversation = AssistantConversation(
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            application_id=payload.application_id,
            title=payload.question[:80],
        )
        db.add(conversation)
        db.flush()

    user_message = AssistantMessage(
        organization_id=membership.organization_id,
        conversation_id=conversation.id,
        role="user",
        content=payload.question,
    )
    db.add(user_message)

    result = answer_question(
        db,
        organization_id=membership.organization_id,
        question=payload.question,
        application_id=payload.application_id,
        role=membership.role,
        application_version=payload.application_version,
        environment=payload.environment,
    )

    assistant_message = AssistantMessage(
        organization_id=membership.organization_id,
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer if not result.steps else result.answer + "\n" + "\n".join(
            f"{i+1}. {s}" for i, s in enumerate(result.steps)
        ),
        confidence=result.confidence.value,
        follow_up_questions=result.follow_up_questions,
    )
    db.add(assistant_message)
    db.flush()

    citation_rows: list[AssistantCitation] = []
    for i, c in enumerate(result.citations):
        row = AssistantCitation(
            organization_id=membership.organization_id,
            message_id=assistant_message.id,
            source_id=c.source_id,
            chunk_id=c.chunk_id,
            source_title=c.source_title,
            start_seconds=c.start_seconds,
            end_seconds=c.end_seconds,
            quoted_evidence=c.quoted_evidence,
            similarity=c.similarity,
            rank=i,
        )
        db.add(row)
        citation_rows.append(row)

    db.commit()
    db.refresh(assistant_message)

    record_question_asked(db, membership.organization_id)
    record_active_user(db, membership.organization_id)
    record_audit_event(
        db, action=AuditAction.ASSISTANT_ANSWER_GENERATED, organization_id=membership.organization_id,
        actor_user_id=membership.user_id, resource_type="assistant_message",
        resource_id=str(assistant_message.id), description=payload.question[:200],
        metadata={"confidence": result.confidence.value, "citation_count": len(result.citations)},
    )

    return AskResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        answer=result.answer,
        steps=result.steps,
        confidence=result.confidence.value,
        citations=[
            CitationOut(
                source_id=c.source_id, chunk_id=c.chunk_id, source_title=c.source_title,
                start_seconds=c.start_seconds, end_seconds=c.end_seconds,
                quoted_evidence=c.quoted_evidence, confidence_score=round(c.similarity, 3),
                is_archived=c.is_archived,
            )
            for c in result.citations
        ],
        related_clips=[
            RelatedClipOut(
                source_id=r.source_id, source_title=r.source_title, topic=r.topic,
                start_seconds=r.start_seconds, end_seconds=r.end_seconds,
            )
            for r in result.related_clips
        ],
        follow_up_questions=result.follow_up_questions,
        inference_provider=result.inference_provider,
        inference_model=result.inference_model,
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)
):
    stmt = (
        select(AssistantConversation)
        .options(selectinload(AssistantConversation.messages).selectinload(AssistantMessage.citations))
        .where(
            AssistantConversation.organization_id == membership.organization_id,
            AssistantConversation.user_id == membership.user_id,
        )
        .order_by(AssistantConversation.created_at.desc())
        .limit(limit).offset(offset)
    )
    return db.scalars(stmt).all()


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    message = db.get(AssistantMessage, payload.message_id)
    if message is None or message.organization_id != membership.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")
    conversation = db.get(AssistantConversation, message.conversation_id)
    if conversation is None or conversation.user_id != membership.user_id:
        raise HTTPException(404, detail="Message not found")
    if payload.rating not in {r.value for r in FeedbackRating}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid rating")
    feedback = Feedback(
        organization_id=membership.organization_id,
        message_id=message.id,
        user_id=membership.user_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/feedback", response_model=list[FeedbackOut])
def list_feedback(
    membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)
):
    stmt = select(Feedback).where(Feedback.organization_id == membership.organization_id,
                                  Feedback.user_id == membership.user_id).order_by(
        Feedback.created_at.desc()
    )
    return db.scalars(stmt.limit(100)).all()
