"""Central application configuration, sourced entirely from environment
variables (with sane local-dev defaults). No secrets are hard-coded here.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
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
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=60)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 14, ge=1)

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:4300", "http://127.0.0.1:4300", "http://localhost:4200", "http://localhost:8080"]

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg2://trainu:trainu@localhost:5432/trainu"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, ge=1)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0)

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    RATE_LIMIT_BACKEND: Literal["auto", "memory", "redis"] = "auto"

    # --- Object storage (RustFS locally / S3-compatible in production) ---
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "trainu_admin"
    S3_SECRET_KEY: str = "trainu_admin_secret"
    S3_BUCKET: str = "trainu-media"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False
    S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:9000"
    STORAGE_AUTO_CREATE_BUCKET: bool = False

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
    STT_AUDIO_SEGMENT_SECONDS: int = Field(default=600, ge=60, le=1800)
    WHISPER_MODEL_ID: str = "dropbox-dash/faster-whisper-large-v3-turbo"
    WHISPER_MODEL_REVISION: str = "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
    WHISPER_DEVICE: Literal["cpu", "cuda", "auto"] = "cpu"
    WHISPER_COMPUTE_TYPE: Literal["int8", "float16", "float32"] = "int8"
    WHISPER_CPU_THREADS: int = Field(default=4, ge=1, le=64)

    # --- LLM / embeddings provider: "mock" | "openai" | "ollama" ---
    LLM_PROVIDER: Literal["mock", "openai", "ollama"] = "mock"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MODEL_DIGEST: str = "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0)
    LLM_TOP_P: float = Field(default=0.9, gt=0.0, le=1.0)
    LLM_MAX_TOKENS: int = Field(default=768, ge=64, le=8192)
    LLM_SEED: int = 42

    EMBEDDINGS_PROVIDER: Literal["mock", "openai", "ollama"] = "mock"
    EMBEDDINGS_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDINGS_API_KEY: str = ""
    EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    EMBEDDING_MODEL_ID: str = "intfloat/multilingual-e5-small"
    EMBEDDING_MODEL_REVISION: str = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    EMBEDDING_DIM: int = 384
    EMBEDDING_BATCH_SIZE: int = Field(default=64, ge=1, le=512)

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

    # --- Optional operator-owned model registry ---
    AI_PROVIDER_CONFIG_PATH: str = ""
    AI_ALLOW_HOSTED: bool = False

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod", "staging"}

    @model_validator(mode="after")
    def validate_deployment(self):
        if not self.is_production:
            return self
        problems = []
        if self.DEBUG or self.DEMO_MODE:
            problems.append("DEBUG and DEMO_MODE must be false")
        if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.startswith("insecure"):
            problems.append("SECRET_KEY must be a unique secret of at least 32 characters")
        if self.RATE_LIMIT_BACKEND == "memory":
            problems.append("Production rate limits require Redis")
        if self.CELERY_TASK_ALWAYS_EAGER:
            problems.append("Production requires asynchronous Celery workers")
        if self.STORAGE_AUTO_CREATE_BUCKET:
            problems.append("Production storage buckets must be provisioned outside the application")
        if not self.CORS_ORIGINS or any(
            urlparse(origin).scheme not in {"https", "chrome-extension"}
            or not urlparse(origin).netloc or "*" in origin for origin in self.CORS_ORIGINS
        ):
            problems.append("CORS_ORIGINS must contain explicit HTTPS or extension origins")
        if "mock" in {self.STT_PROVIDER, self.LLM_PROVIDER, self.EMBEDDINGS_PROVIDER}:
            problems.append("Configure real STT, LLM and embeddings providers")
        for provider, key, label in [
            (self.STT_PROVIDER, self.STT_API_KEY, "STT"),
            (self.LLM_PROVIDER, self.LLM_API_KEY, "LLM"),
            (self.EMBEDDINGS_PROVIDER, self.EMBEDDINGS_API_KEY, "EMBEDDINGS"),
        ]:
            if provider in {"openai", "whisper_api"} and not key:
                problems.append(f"{label}_API_KEY is required")
        if self.S3_ACCESS_KEY == "trainu_admin" or self.S3_SECRET_KEY == "trainu_admin_secret":
            problems.append("Replace development object storage credentials")
        placeholder_values = ("replace", "change-me", "example", "placeholder")
        configured_secrets = {
            "SECRET_KEY": self.SECRET_KEY,
            "S3_ACCESS_KEY": self.S3_ACCESS_KEY,
            "S3_SECRET_KEY": self.S3_SECRET_KEY,
            "STT_API_KEY": self.STT_API_KEY,
            "LLM_API_KEY": self.LLM_API_KEY,
            "EMBEDDINGS_API_KEY": self.EMBEDDINGS_API_KEY,
        }
        for name, value in configured_secrets.items():
            if value and any(marker in value.lower() for marker in placeholder_values):
                problems.append(f"{name} still contains a template placeholder")
        if not self.S3_PUBLIC_ENDPOINT_URL.startswith("https://"):
            problems.append("S3_PUBLIC_ENDPOINT_URL must use HTTPS")
        if problems:
            raise ValueError("Unsafe deployment configuration: " + "; ".join(problems))
        return self

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
