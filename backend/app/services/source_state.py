from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.source import Source, TranscriptChunk


def sync_chunk_status(db: Session, source: Source) -> None:
    """Keep the denormalized `TranscriptChunk.source_status` column in sync
    with its parent Source whenever the source's status changes, so
    retrieval queries can filter chunks without a join."""
    db.execute(
        update(TranscriptChunk)
        .where(TranscriptChunk.source_id == source.id)
        .values(source_status=source.status)
    )
    db.commit()
