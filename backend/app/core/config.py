"""Central application configuration, sourced entirely from environment
variables (with sane local-dev defaults). No secrets are hard-coded here.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "TrainU"
    ENVIRONMENT: str = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security ---
    SECRET_KEY: str = "insecure-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:4200", "http://localhost:8080"]

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg2://trainu:trainu@localhost:5432/trainu"
    )

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # --- Object storage (MinIO / S3-compatible) ---
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "trainu_admin"
    S3_SECRET_KEY: str = "trainu_admin_secret"
    S3_BUCKET: str = "trainu-media"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False
    S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:9000"

    # --- Upload limits ---
    MAX_VIDEO_SIZE_MB: int = 1024
    MAX_DOCUMENT_SIZE_MB: int = 50
    ALLOWED_VIDEO_EXTENSIONS: list[str] = [".mp4", ".mov", ".m4v", ".webm"]
    ALLOWED_DOCUMENT_EXTENSIONS: list[str] = [".pdf", ".docx", ".md", ".txt"]

    # --- STT provider: "mock" | "whisper_api" ---
    STT_PROVIDER: Literal["mock", "whisper_api"] = "mock"
    STT_API_BASE_URL: str = ""
    STT_API_KEY: str = ""
    STT_MODEL: str = "whisper-1"

    # --- LLM / embeddings provider: "mock" | "openai" | "ollama" ---
    LLM_PROVIDER: Literal["mock", "openai", "ollama"] = "mock"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    EMBEDDINGS_PROVIDER: Literal["mock", "openai", "ollama"] = "mock"
    EMBEDDINGS_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDINGS_API_KEY: str = ""
    EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 384

    # --- RAG tuning ---
    RAG_TOP_K: int = 6
    RAG_MIN_SIMILARITY: float = 0.2
    RAG_HIGH_CONFIDENCE_SIMILARITY: float = 0.55
    RAG_MEDIUM_CONFIDENCE_SIMILARITY: float = 0.30

    # --- Rate limiting (requests per window per client) ---
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_ASSISTANT_PER_MINUTE: int = 30

    # --- Demo ---
    DEMO_MODE: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value: object) -> object:
        """Treat common deployment labels as a disabled debug flag.

        Some shell environments export ``DEBUG=release``.  Pydantic correctly
        rejects that as a boolean, but it should not stop the API from starting
        when the setting is inherited from the host process.
        """
        if isinstance(value, str) and value.strip().lower() in {
            "release",
            "production",
            "prod",
            "development",
            "dev",
        }:
            return value.strip().lower() in {"development", "dev"}
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
