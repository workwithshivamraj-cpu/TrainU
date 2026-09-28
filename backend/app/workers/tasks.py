from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.source import Source
from app.services.pipeline import index_approved_source, run_pipeline
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="trainu.process_source", bind=True, max_retries=1)
def process_source(self, source_id: str, seed_transcript_text: str | None = None) -> str:
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            logger.warning("process_source_missing", source_id=source_id)
            return "missing"
        run_pipeline(db, source, seed_transcript_text=seed_transcript_text)
        return source.status
    finally:
        db.close()


@celery_app.task(name="trainu.index_source", bind=True, max_retries=1)
def index_source(self, source_id: str) -> str:
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            logger.warning("index_source_missing", source_id=source_id)
            return "missing"
        index_approved_source(db, source)
        return source.status
    finally:
        db.close()
