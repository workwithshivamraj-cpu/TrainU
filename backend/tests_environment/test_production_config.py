from __future__ import annotations

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def production_settings(**overrides) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "DEMO_MODE": False,
        "SECRET_KEY": "a" * 64,
        "RATE_LIMIT_BACKEND": "redis",
        "CELERY_TASK_ALWAYS_EAGER": False,
        "CORS_ORIGINS": ["https://app.example.com"],
        "STT_PROVIDER": "whisper_api",
        "STT_API_BASE_URL": "https://stt.example.com/v1",
        "STT_API_KEY": "stt-live-key",
        "LLM_PROVIDER": "openai",
        "LLM_BASE_URL": "https://llm.example.com/v1",
        "LLM_API_KEY": "llm-live-key",
        "EMBEDDINGS_PROVIDER": "openai",
        "EMBEDDINGS_BASE_URL": "https://embeddings.example.com/v1",
        "EMBEDDINGS_API_KEY": "embedding-live-key",
        "S3_ACCESS_KEY": "scoped-access",
        "S3_SECRET_KEY": "scoped-secret",
        "S3_PUBLIC_ENDPOINT_URL": "https://storage.example.com",
        "STORAGE_AUTO_CREATE_BUCKET": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_profile_accepts_explicit_non_demo_configuration() -> None:
    assert production_settings().is_production


@pytest.mark.parametrize(
    "override",
    [
        {"DEMO_MODE": True},
        {"DEBUG": True},
        {"SECRET_KEY": "change-me-to-a-long-random-string"},
        {"LLM_PROVIDER": "mock"},
        {"STT_PROVIDER": "mock"},
        {"EMBEDDINGS_PROVIDER": "mock"},
        {"STORAGE_AUTO_CREATE_BUCKET": True},
        {"LLM_API_KEY": "REPLACE_WITH_REAL_KEY"},
        {"S3_SECRET_KEY": "REPLACE_WITH_SCOPED_SECRET"},
    ],
)
def test_production_profile_rejects_demo_mock_and_template_values(override) -> None:
    with pytest.raises(ValidationError, match="Unsafe deployment configuration"):
        production_settings(**override)
