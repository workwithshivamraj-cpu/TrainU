"""Retrieval-augmented generation for the Ask TrainU assistant.

Strict flow, mirrored exactly by the tests:

1. Resolve org (mandatory, from the authenticated membership).
2. Embed the question.
3. Query ``transcript_chunks`` scoped to organization_id AND
   source_status IN ('approved', 'indexed'), optionally further filtered by
   application/role/version/environment.
4. If nothing clears ``RAG_MIN_SIMILARITY``, return the fixed "no approved
   source" response without ever calling the LLM.
5. Otherwise ask the LLM provider to synthesize an answer *from the retrieved
   chunks only*, validate it, and attach citations/related clips/follow-ups
   built directly from retrieval metadata (never from free-form LLM output),
   so citations can never point outside the organization or at an
   unapproved/other-org source.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ConfidenceLevel, SourceStatus
from app.models.source import Source, TranscriptChunk
from app.services.embeddings import EmbeddingsProvider, get_embeddings_provider
from app.services.llm import LLMProvider, RetrievedChunk, get_llm_provider

NO_ANSWER_MESSAGE = (
    "I could not find an approved source that answers this question. "
    "Try another term, select the relevant application, or contact the application owner."
)

RETRIEVABLE_STATUSES = (SourceStatus.APPROVED.value, SourceStatus.INDEXED.value)


@dataclass
class CitationResult:
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    source_title: str
    start_seconds: float
    end_seconds: float
    quoted_evidence: str
    similarity: float
    is_archived: bool


@dataclass
class RelatedClip:
    source_id: uuid.UUID
    source_title: str
    topic: str
    start_seconds: float
    end_seconds: float


@dataclass
class AssistantAnswerResult:
    answer: str
    steps: list[str]
    confidence: ConfidenceLevel
    citations: list[CitationResult]
    related_clips: list[RelatedClip]
    follow_up_questions: list[str]


def _cosine_similarity_expr(chunk_embedding_col, query_vector: list[float]):
    # pgvector's `<=>` operator returns cosine *distance*; similarity = 1 - distance
    # for normalized vectors (both our mock and real providers emit normalized vectors).
    return 1 - chunk_embedding_col.cosine_distance(query_vector)


def retrieve_chunks(
    db: Session,
    *,
    organization_id: uuid.UUID,
    question: str,
    application_id: uuid.UUID | None = None,
    role: str | None = None,
    application_version: str | None = None,
    environment: str | None = None,
    top_k: int = settings.RAG_TOP_K,
    embeddings_provider: EmbeddingsProvider | None = None,
) -> list[tuple[TranscriptChunk, Source, float]]:
    provider = embeddings_provider or get_embeddings_provider()
    query_vector = provider.embed(question)

    similarity = _cosine_similarity_expr(TranscriptChunk.embedding, query_vector)
    stmt = (
        select(TranscriptChunk, Source, similarity.label("similarity"))
        .join(Source, Source.id == TranscriptChunk.source_id)
        .where(
            TranscriptChunk.organization_id == organization_id,
            TranscriptChunk.source_status.in_(RETRIEVABLE_STATUSES),
            Source.status.in_(RETRIEVABLE_STATUSES),
        )
    )
    if application_id is not None:
        stmt = stmt.where(TranscriptChunk.application_id == application_id)
    if application_version:
        stmt = stmt.where(TranscriptChunk.application_version == application_version)
    if environment:
        stmt = stmt.where(TranscriptChunk.environment == environment)
    if role:
        stmt = stmt.where(
            (TranscriptChunk.audience_roles == [])
            | TranscriptChunk.audience_roles.any(role)
        )

    stmt = stmt.order_by(similarity.desc()).limit(top_k)
    rows = db.execute(stmt).all()
    return [(row[0], row[1], float(row[2])) for row in rows]


def _confidence_for(top_similarity: float) -> ConfidenceLevel:
    if top_similarity >= settings.RAG_HIGH_CONFIDENCE_SIMILARITY:
        return ConfidenceLevel.HIGH
    if top_similarity >= settings.RAG_MEDIUM_CONFIDENCE_SIMILARITY:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _quote_evidence(text: str, max_len: int = 220) -> str:
    text = text.strip()
    return text if len(text) <= max_len else text[:max_len].rsplit(" ", 1)[0] + "…"


def answer_question(
    db: Session,
    *,
    organization_id: uuid.UUID,
    question: str,
    application_id: uuid.UUID | None = None,
    role: str | None = None,
    application_version: str | None = None,
    environment: str | None = None,
    embeddings_provider: EmbeddingsProvider | None = None,
    llm_provider: LLMProvider | None = None,
) -> AssistantAnswerResult:
    results = retrieve_chunks(
        db,
        organization_id=organization_id,
        question=question,
        application_id=application_id,
        role=role,
        application_version=application_version,
        environment=environment,
        embeddings_provider=embeddings_provider,
    )

    relevant = [r for r in results if r[2] >= settings.RAG_MIN_SIMILARITY]

    if not relevant:
        return AssistantAnswerResult(
            answer=NO_ANSWER_MESSAGE,
            steps=[],
            confidence=ConfidenceLevel.NONE,
            citations=[],
            related_clips=[],
            follow_up_questions=[],
        )

    provider = llm_provider or get_llm_provider()
    llm_chunks = [
        RetrievedChunk(
            chunk_id=str(chunk.id),
            source_id=str(source.id),
            source_title=source.title,
            text=chunk.text,
            topic=chunk.topic,
            start_seconds=chunk.start_seconds,
            end_seconds=chunk.end_seconds,
            similarity=sim,
            source_status=source.status,
        )
        for chunk, source, sim in relevant
    ]
    synthesized = provider.synthesize_answer(question, llm_chunks)

    # Citations are built strictly from our own retrieval metadata (never
    # from LLM output), capped at 3 distinct sources, so they can never
    # reference another org or an unapproved source.
    citations: list[CitationResult] = []
    seen_sources: set[uuid.UUID] = set()
    for chunk, source, sim in relevant:
        if len(citations) >= 3:
            break
        citations.append(
            CitationResult(
                chunk_id=chunk.id,
                source_id=source.id,
                source_title=source.title,
                start_seconds=chunk.start_seconds,
                end_seconds=chunk.end_seconds,
                quoted_evidence=_quote_evidence(chunk.text),
                similarity=sim,
                is_archived=source.status == SourceStatus.ARCHIVED.value,
            )
        )
        seen_sources.add(source.id)

    # Related clips: other 30-90s chunks from the same cited sources.
    related_clips: list[RelatedClip] = []
    for chunk, source, sim in results:
        if source.id not in seen_sources:
            continue
        if any(c.chunk_id == chunk.id for c in citations):
            continue
        span = chunk.end_seconds - chunk.start_seconds
        if 30 <= span <= 90:
            related_clips.append(
                RelatedClip(
                    source_id=source.id,
                    source_title=source.title,
                    topic=chunk.topic,
                    start_seconds=chunk.start_seconds,
                    end_seconds=chunk.end_seconds,
                )
            )
        if len(related_clips) >= 3:
            break

    follow_ups = synthesized.get("follow_up_questions") or _default_follow_ups(relevant)

    return AssistantAnswerResult(
        answer=synthesized.get("answer", NO_ANSWER_MESSAGE),
        steps=synthesized.get("steps", []),
        confidence=_confidence_for(relevant[0][2]),
        citations=citations,
        related_clips=related_clips,
        follow_up_questions=follow_ups[:3],
    )


def _default_follow_ups(relevant: list[tuple[TranscriptChunk, Source, float]]) -> list[str]:
    topics = []
    for chunk, _source, _sim in relevant[1:4]:
        if chunk.topic and chunk.topic not in topics:
            topics.append(chunk.topic)
    return [f"What about {t.rstrip('…')}?" for t in topics]
