from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_membership, require_role
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import (
    SOURCE_STATUS_TRANSITIONS,
    AuditAction,
    RoleName,
    SourceStatus,
    SourceType,
    ApplicationEnvironment,
    ROLE_RANK,
)
from app.models.application import Application, ApplicationModule
from app.models.organization import Membership
from app.models.source import Source, TranscriptChunk
from app.schemas.source import (
    ChunkUpdate,
    SourceApprovalAction,
    SourceDetailOut,
    SourceOut,
    TranscriptChunkOut,
)
from app.services.audit import record_audit_event
from app.services.source_state import sync_chunk_status
from app.services.storage import build_storage_key, ensure_bucket, get_presigned_url, upload_fileobj

router = APIRouter(prefix="/sources", tags=["sources"])

VIDEO_EXTENSIONS = set(settings.ALLOWED_VIDEO_EXTENSIONS)
DOCUMENT_EXTENSIONS = set(settings.ALLOWED_DOCUMENT_EXTENSIONS)


def _classify(filename: str) -> SourceType:
    ext = os.path.splitext(filename)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return SourceType.VIDEO
    if ext == ".pdf":
        return SourceType.PDF
    if ext == ".docx":
        return SourceType.DOCX
    if ext == ".md":
        return SourceType.MARKDOWN
    if ext == ".txt":
        return SourceType.TEXT
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Unsupported file type '{ext}'. Allowed: "
            f"{sorted(VIDEO_EXTENSIONS | DOCUMENT_EXTENSIONS)}"
        ),
    )


def _get_org_source(db: Session, organization_id: uuid.UUID, source_id: uuid.UUID) -> Source:
    source = db.get(Source, source_id)
    if source is None or source.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


def _source_visibility(membership: Membership):
    if ROLE_RANK.get(RoleName(membership.role), -1) >= ROLE_RANK[RoleName.CONTENT_OWNER]:
        return True
    published = and_(
        Source.status.in_([SourceStatus.APPROVED.value, SourceStatus.INDEXED.value]),
        or_(Source.audience_roles == [], Source.audience_roles.any(membership.role)),
    )
    if membership.role == RoleName.CONTRIBUTOR.value:
        return or_(published, Source.content_owner_id == membership.user_id)
    return published


def _get_visible_source(db: Session, membership: Membership, source_id: uuid.UUID) -> Source:
    source = db.scalars(select(Source).where(
        Source.id == source_id, Source.organization_id == membership.organization_id,
        _source_visibility(membership),
    )).first()
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.get("", response_model=list[SourceOut])
def list_sources(
    status_filter: str | None = None,
    application_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    stmt = select(Source).where(Source.organization_id == membership.organization_id,
                                _source_visibility(membership))
    if status_filter:
        stmt = stmt.where(Source.status == status_filter)
    if application_id:
        stmt = stmt.where(Source.application_id == application_id)
    stmt = stmt.order_by(Source.created_at.desc(), Source.id).offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.post("", response_model=SourceDetailOut, status_code=status.HTTP_201_CREATED)
def upload_source(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=300),
    description: str = Form("", max_length=10000),
    application_id: uuid.UUID | None = Form(None),
    module_id: uuid.UUID | None = Form(None),
    feature_tag: str = Form("", max_length=200),
    application_version: str = Form("", max_length=50),
    environment: str | None = Form(None),
    audience_roles: str = Form(""),  # comma-separated
    membership: Membership = Depends(require_role(RoleName.CONTRIBUTOR)),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename or len(filename) > 300 or not title.strip():
        raise HTTPException(400, detail="A valid filename and title are required")
    source_type = _classify(filename)
    if application_id:
        application = db.get(Application, application_id)
        if application is None or application.organization_id != membership.organization_id:
            raise HTTPException(404, detail="Application not found")
    if module_id:
        module = db.get(ApplicationModule, module_id)
        if module is None or module.organization_id != membership.organization_id:
            raise HTTPException(404, detail="Module not found")
        if application_id is None or module.application_id != application_id:
            raise HTTPException(400, detail="Module must belong to the selected application")
    roles = list(dict.fromkeys(r.strip() for r in audience_roles.split(",") if r.strip()))
    if set(roles) - {r.value for r in RoleName if r != RoleName.PLATFORM_ADMIN}:
        raise HTTPException(400, detail="Invalid audience role")
    if environment and environment not in {e.value for e in ApplicationEnvironment}:
        raise HTTPException(400, detail="Invalid environment")
    # UploadFile is spooled to disk by Starlette. Seek for length and stream into
    # S3 so a 1GB video never becomes a 1GB bytes allocation in each API worker.
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    size_mb = file_size / (1024 * 1024)
    limit = settings.MAX_VIDEO_SIZE_MB if source_type == SourceType.VIDEO else settings.MAX_DOCUMENT_SIZE_MB
    if size_mb > limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"File exceeds max size of {limit}MB"
        )
    if size_mb == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    source = Source(
        organization_id=membership.organization_id,
        application_id=application_id,
        module_id=module_id,
        content_owner_id=membership.user_id,
        title=title.strip(),
        description=description,
        source_type=source_type.value,
        status=SourceStatus.UPLOADED.value,
        feature_tag=feature_tag,
        application_version=application_version,
        environment=environment,
        audience_roles=roles,
        storage_key="",
        original_filename=filename,
        file_size_bytes=file_size,
        mime_type=file.content_type or "",
    )
    db.add(source)
    db.flush()

    key = build_storage_key(str(membership.organization_id), str(source.id), filename)
    ensure_bucket()
    upload_fileobj(key, file.file, file.content_type or "application/octet-stream")
    source.storage_key = key
    db.commit()
    db.refresh(source)

    record_audit_event(
        db, action=AuditAction.UPLOAD, organization_id=membership.organization_id,
        actor_user_id=membership.user_id, resource_type="source", resource_id=str(source.id),
        description=source.title,
    )

    # Enqueue background processing. Celery is configured to run eagerly in
    # tests/CI (CELERY_TASK_ALWAYS_EAGER) so this executes synchronously there.
    from app.workers.tasks import process_source

    _enqueue_processing(db, source, process_source)

    db.refresh(source)
    return _detail_out(source)


def _detail_out(source: Source) -> SourceDetailOut:
    playback_url = None
    if source.storage_key:
        try:
            playback_url = get_presigned_url(source.storage_key)
        except Exception:  # noqa: BLE001 - storage may be unavailable in some contexts
            playback_url = None
    return SourceDetailOut.model_validate({**SourceOut.model_validate(source).model_dump(), "jobs": source.jobs, "playback_url": playback_url})


@router.get("/{source_id}", response_model=SourceDetailOut)
def get_source(
    source_id: uuid.UUID,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    source = _get_visible_source(db, membership, source_id)
    return _detail_out(source)


@router.get("/{source_id}/chunks", response_model=list[TranscriptChunkOut])
def list_chunks(
    source_id: uuid.UUID,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    source = _get_visible_source(db, membership, source_id)
    stmt = (
        select(TranscriptChunk)
        .where(TranscriptChunk.source_id == source.id)
        .order_by(TranscriptChunk.chunk_index)
    )
    if ROLE_RANK[RoleName(membership.role)] < ROLE_RANK[RoleName.CONTENT_OWNER]:
        stmt = stmt.where(or_(TranscriptChunk.audience_roles == [], TranscriptChunk.audience_roles.any(membership.role)))
    return db.scalars(stmt).all()


@router.patch("/{source_id}/chunks/{chunk_id}", response_model=TranscriptChunkOut)
def update_chunk(
    source_id: uuid.UUID,
    chunk_id: uuid.UUID,
    payload: ChunkUpdate,
    membership: Membership = Depends(require_role(RoleName.CONTENT_OWNER)),
    db: Session = Depends(get_db),
):
    source = _get_org_source(db, membership.organization_id, source_id)
    if source.status != SourceStatus.AWAITING_REVIEW.value:
        raise HTTPException(409, detail="Only draft transcripts awaiting review can be edited")
    chunk = db.get(TranscriptChunk, chunk_id)
    if chunk is None or chunk.source_id != source.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(400, detail="Transcript fields cannot be null")
    if payload.audience_roles is not None and set(payload.audience_roles) - {r.value for r in RoleName if r != RoleName.PLATFORM_ADMIN}:
        raise HTTPException(400, detail="Invalid audience role")
    if "text" in changes:
        from app.services.embeddings import get_embeddings_provider
        chunk.embedding = get_embeddings_provider().embed(changes["text"])
    for field, value in changes.items():
        setattr(chunk, field, value)
    db.commit()
    db.refresh(chunk)
    return chunk


def _enqueue_processing(db: Session, source: Source, task) -> None:
    try:
        task.delay(str(source.id))
    except Exception:
        source.status = SourceStatus.FAILED.value
        source.failure_reason = "Processing queue unavailable. Please retry processing."
        db.commit()


@router.post("/{source_id}/retry", response_model=SourceDetailOut)
def retry_source(
    source_id: uuid.UUID,
    membership: Membership = Depends(require_role(RoleName.CONTENT_OWNER)),
    db: Session = Depends(get_db),
):
    source = _get_org_source(db, membership.organization_id, source_id)
    if source.status != SourceStatus.FAILED.value:
        raise HTTPException(409, detail="Only failed sources can be retried")
    source.status = SourceStatus.QUEUED.value
    source.failure_reason = None
    db.commit()
    from app.workers.tasks import process_source
    _enqueue_processing(db, source, process_source)
    db.refresh(source)
    return _detail_out(source)


def _transition(source: Source, new_status: SourceStatus) -> None:
    current = SourceStatus(source.status)
    allowed = SOURCE_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot move source from '{current.value}' to '{new_status.value}'",
        )
    source.status = new_status.value


@router.post("/{source_id}/approve", response_model=SourceDetailOut)
def approve_source(
    source_id: uuid.UUID,
    payload: SourceApprovalAction,
    membership: Membership = Depends(require_role(RoleName.CONTENT_OWNER)),
    db: Session = Depends(get_db),
):
    source = _get_org_source(db, membership.organization_id, source_id)
    if source.status != SourceStatus.AWAITING_REVIEW.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Only sources awaiting review can be approved",
        )
    from datetime import datetime, timezone

    _transition(source, SourceStatus.APPROVED)
    source.approved_by_id = membership.user_id
    source.approved_at = datetime.now(timezone.utc)
    db.commit()
    sync_chunk_status(db, source)

    record_audit_event(
        db, action=AuditAction.SOURCE_APPROVED, organization_id=membership.organization_id,
        actor_user_id=membership.user_id, resource_type="source", resource_id=str(source.id),
        description=payload.note,
    )

    from app.services.pipeline import index_approved_source

    index_approved_source(db, source)
    db.refresh(source)
    return _detail_out(source)


@router.post("/{source_id}/archive", response_model=SourceDetailOut)
def archive_source(
    source_id: uuid.UUID,
    membership: Membership = Depends(require_role(RoleName.CONTENT_OWNER)),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    source = _get_org_source(db, membership.organization_id, source_id)
    _transition(source, SourceStatus.ARCHIVED)
    source.archived_at = datetime.now(timezone.utc)
    db.commit()
    sync_chunk_status(db, source)
    record_audit_event(
        db, action=AuditAction.SOURCE_ARCHIVED, organization_id=membership.organization_id,
        actor_user_id=membership.user_id, resource_type="source", resource_id=str(source.id),
    )
    db.refresh(source)
    return _detail_out(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: uuid.UUID,
    membership: Membership = Depends(require_role(RoleName.ORG_ADMIN)),
    db: Session = Depends(get_db),
):
    """Safe deletion: only archived sources may be hard-deleted, preventing
    accidental loss of content that's still live/under review."""
    source = _get_org_source(db, membership.organization_id, source_id)
    if source.status != SourceStatus.ARCHIVED.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Only archived sources can be deleted. Archive it first.",
        )
    from app.services.storage import delete_object

    try:
        if source.storage_key:
            delete_object(source.storage_key)
    except Exception:
        raise HTTPException(503, detail="Storage deletion failed. Please retry.")
    record_audit_event(
        db, action=AuditAction.SOURCE_DELETED, organization_id=membership.organization_id,
        actor_user_id=membership.user_id, resource_type="source", resource_id=str(source.id),
        description=source.title, commit=False,
    )
    db.delete(source)
    db.commit()
