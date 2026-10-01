from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import uuid

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import get_redis
from app.db.session import engine
from app.services.storage import get_s3_client

configure_logging(settings.DEBUG)
logger = get_logger(__name__)

app = FastAPI(
    title="TrainU API",
    description=(
        "TrainU converts approved KT/training videos and documents into a "
        "searchable, citation-grounded AI assistant."
    ),
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Request-Id"] = str(uuid.uuid4())
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.info("http_exception", path=request.url.path, status_code=exc.status_code)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.APP_NAME, "environment": settings.ENVIRONMENT}


@app.get("/health/ready", tags=["health"])
def readiness():
    checks = {}
    for name, probe in {
        "database": _database_ready,
        "redis": lambda: get_redis().ping(),
        "storage": lambda: get_s3_client().head_bucket(Bucket=settings.S3_BUCKET),
    }.items():
        try:
            probe()
            checks[name] = "ok"
        except Exception:
            checks[name] = "unavailable"
    ready = all(value == "ok" for value in checks.values())
    return JSONResponse(status_code=200 if ready else 503,
                        content={"status": "ready" if ready else "not_ready", "checks": checks})


def _database_ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
