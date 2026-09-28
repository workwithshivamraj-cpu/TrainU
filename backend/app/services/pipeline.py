"""The core video/document knowledge pipeline, callable both from a Celery
task (real async processing) and directly from the seed script (synchronous,
for deterministic demo data). Keeping the logic in one place guarantees the
seeded demo data went through exactly the same code path as a real upload.
"""
from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.enums import ProcessingJobStage, ProcessingJobStatus, SourceStatus, SourceType
from app.models.source import Source, TranscriptChunk, VideoProcessingJob
from app.services.chunking import chunk_document, chunk_transcript
from app.services.embeddings import EmbeddingsProvider, get_embeddings_provider
from app.services.media import extract_audio, probe_duration_seconds
from app.services.source_state import sync_chunk_status
from app.services.stt import STTProvider, get_stt_provider
from app.services.storage import download_bytes
from app.services.usage import record_processed_video_minutes, record_stored_video_minutes

logger = get_logger(__name__)


class PipelineError(Exception):
    pass


def _job(db: Session, source: Source, stage: ProcessingJobStage) -> VideoProcessingJob:
    job = VideoProcessingJob(
        organization_id=source.organization_id,
        source_id=source.id,
        stage=stage.value,
        status=ProcessingJobStatus.RUNNING.value,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _finish_job(db: Session, job: VideoProcessingJob, *, detail: str = "", error: str | None = None) -> None:
    job.finished_at = datetime.now(timezone.utc)
    job.status = ProcessingJobStatus.FAILED.value if error else ProcessingJobStatus.SUCCEEDED.value
    job.detail = detail
    job.error = error
    db.commit()


def _extract_document_text(data: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # noqa: BLE001
            raise PipelineError(f"Failed to parse PDF: {exc}") from exc
    if ext == ".docx":
        try:
            import docx

            document = docx.Document(io.BytesIO(data))
            return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())
        except Exception as exc:  # noqa: BLE001
            raise PipelineError(f"Failed to parse DOCX: {exc}") from exc
    raise PipelineError(f"Unsupported document type: {ext}")


def run_pipeline(
    db: Session,
    source: Source,
    *,
    seed_transcript_text: str | None = None,
    embeddings_provider: EmbeddingsProvider | None = None,
    stt_provider: STTProvider | None = None,
) -> None:
    embeddings_provider = embeddings_provider or get_embeddings_provider()
    stt_provider = stt_provider or get_stt_provider()

    try:
        source.status = SourceStatus.QUEUED.value
        db.commit()
        source.status = SourceStatus.PROCESSING.value
        db.commit()

        data = download_bytes(source.storage_key) if source.storage_key else b""

        if source.source_type == SourceType.VIDEO.value:
            chunks = _run_video_pipeline(db, source, data, stt_provider, seed_transcript_text)
        else:
            chunks = _run_document_pipeline(db, source, data)

        embed_job = _job(db, source, ProcessingJobStage.EMBEDDING)
        for i, chunk in enumerate(chunks):
            vector = embeddings_provider.embed(chunk.text)
            row = TranscriptChunk(
                organization_id=source.organization_id,
                application_id=source.application_id,
                source_id=source.id,
                title=chunk.title,
                topic=chunk.topic,
                text=chunk.text,
                chunk_index=i,
                start_seconds=chunk.start_seconds,
                end_seconds=chunk.end_seconds,
                application_version=source.application_version,
                environment=source.environment,
                audience_roles=source.audience_roles,
                source_status=SourceStatus.AWAITING_REVIEW.value,
                content_owner_id=source.content_owner_id,
                embedding=vector,
            )
            db.add(row)
        db.commit()
        _finish_job(db, embed_job, detail=f"Embedded {len(chunks)} chunks")

        source.status = SourceStatus.AWAITING_REVIEW.value
        db.commit()

        if source.source_type == SourceType.VIDEO.value and source.duration_seconds:
            record_processed_video_minutes(db, source.organization_id, source.duration_seconds / 60)

    except PipelineError as exc:
        source.status = SourceStatus.FAILED.value
        source.failure_reason = str(exc)
        db.commit()
        logger.error("pipeline_failed", source_id=str(source.id), error=str(exc))
    except Exception as exc:  # noqa: BLE001
        source.status = SourceStatus.FAILED.value
        source.failure_reason = f"Unexpected error: {exc}"
        db.commit()
        logger.error("pipeline_unexpected_error", source_id=str(source.id), error=str(exc))


def _run_video_pipeline(db, source: Source, data: bytes, stt_provider: STTProvider, seed_transcript_text: str | None):
    audio_job = _job(db, source, ProcessingJobStage.AUDIO_EXTRACTION)
    duration = None
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "input" + (os.path.splitext(source.original_filename)[1] or ".mp4"))
        with open(video_path, "wb") as f:
            f.write(data)
        duration = probe_duration_seconds(video_path)
        audio_path = os.path.join(tmp, "audio.wav")
        extracted = extract_audio(video_path, audio_path)
        _finish_job(db, audio_job, detail="Audio extracted" if extracted else "ffmpeg unavailable; used mock audio")

        if duration:
            source.duration_seconds = duration
            db.commit()
            record_stored_video_minutes(db, source.organization_id, duration / 60)

        transcribe_job = _job(db, source, ProcessingJobStage.TRANSCRIPTION)
        segments = stt_provider.transcribe(
            audio_path if extracted else video_path, seed_text=seed_transcript_text
        )
        _finish_job(db, transcribe_job, detail=f"{len(segments)} transcript segments")

    chunk_job = _job(db, source, ProcessingJobStage.CHUNKING)
    chunks = chunk_transcript(segments, source.title)
    _finish_job(db, chunk_job, detail=f"{len(chunks)} chunks")
    return chunks


def _run_document_pipeline(db, source: Source, data: bytes):
    parse_job = _job(db, source, ProcessingJobStage.DOCUMENT_PARSING)
    text = _extract_document_text(data, source.original_filename)
    _finish_job(db, parse_job, detail=f"Extracted {len(text)} characters")

    chunk_job = _job(db, source, ProcessingJobStage.CHUNKING)
    chunks = chunk_document(text, source.title)
    _finish_job(db, chunk_job, detail=f"{len(chunks)} chunks")
    return chunks


def index_approved_source(db: Session, source: Source) -> None:
    """Finalize an approved source: confirm it has chunks, mark it Indexed,
    and make sure the denormalized chunk status matches."""
    if source.status != SourceStatus.APPROVED.value:
        raise PipelineError("Source must be approved before indexing")
    source.status = SourceStatus.INDEXED.value
    db.commit()
    sync_chunk_status(db, source)
