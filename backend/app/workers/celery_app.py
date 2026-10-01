from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "trainu",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=3300,
    task_time_limit=3600,
    broker_transport_options={"visibility_timeout": 7200},
    result_expires=86400,
)
