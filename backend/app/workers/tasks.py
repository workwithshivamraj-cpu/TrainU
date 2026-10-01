from __future__ import annotations

import uuid
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import engine
from app.models.source import Source
from app.services.pipeline import index_approved_source, run_pipeline
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@contextmanager
def _source_session(source_id: str):
    """A dedicated connection owns the advisory lock across pipeline commits."""
    lock_key = int.from_bytes(uuid.UUID(source_id).bytes[:8], signed=True)
    with engine.connect() as connection:
        locked = connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key}).scalar()
        connection.commit()
        if not locked:
            yield None
            return
        try:
            with Session(bind=connection) as db:
                yield db
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key})
            connection.commit()


@celery_app.task(name="trainu.process_source", bind=True, max_retries=0)
def process_source(self, source_id: str, seed_transcript_text: str | None = None) -> str:
    with _source_session(source_id) as db:
        if db is None:
            return "already_processing"
        source = db.get(Source, uuid.UUID(source_id))
        if source is None:
            logger.warning("process_source_missing", source_id=source_id)
            return "missing"
        run_pipeline(db, source, seed_transcript_text=seed_transcript_text)
        return source.status


@celery_app.task(name="trainu.index_source", bind=True, max_retries=0)
def index_source(self, source_id: str) -> str:
    with _source_session(source_id) as db:
        if db is None:
            return "already_processing"
        source = db.get(Source, uuid.UUID(source_id))
        if source is None:
            return "missing"
        index_approved_source(db, source)
        return source.status
