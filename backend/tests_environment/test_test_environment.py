from __future__ import annotations

import pytest
from app.core.test_environment import configure_destructive_test_environment


def valid_environment() -> dict[str, str]:
    return {
        "ENVIRONMENT": "test",
        "TRAINU_ALLOW_SCHEMA_RESET": "true",
        "TRAINU_TEST_DATABASE_URL": "postgresql+psycopg2://test:test@localhost:5432/trainu_test",
        "TRAINU_TEST_STORAGE_BUCKET": "trainu-media-test",
        "TRAINU_TEST_S3_ENDPOINT_URL": "http://localhost:9000",
        "TRAINU_TEST_REDIS_URL": "redis://localhost:6379/1",
    }


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("ENVIRONMENT", "production"),
        ("TRAINU_ALLOW_SCHEMA_RESET", "false"),
        ("TRAINU_TEST_DATABASE_URL", "postgresql://prod:secret@db.example/trainu"),
        ("TRAINU_TEST_DATABASE_URL", "postgresql://user:pass@localhost/trainu_test_copy"),
        ("TRAINU_TEST_DATABASE_URL", "postgresql://user:pass@db.example/trainu_test"),
        ("TRAINU_TEST_STORAGE_BUCKET", "trainu-media"),
        ("TRAINU_TEST_S3_ENDPOINT_URL", "https://storage.example.com"),
        ("TRAINU_TEST_S3_ENDPOINT_URL", "http://localhost:9001"),
        ("TRAINU_TEST_S3_ENDPOINT_URL", "http://user:pass@localhost:9000"),
        ("TRAINU_TEST_REDIS_URL", "redis://localhost:6379/0"),
        ("TRAINU_TEST_REDIS_URL", "redis://redis.example:6379/1"),
    ],
)
def test_destructive_test_setup_rejects_unsafe_target(key: str, value: str) -> None:
    env = valid_environment()
    env[key] = value
    with pytest.raises(RuntimeError):
        configure_destructive_test_environment(env)


def test_destructive_test_setup_overrides_inherited_runtime_database() -> None:
    env = valid_environment()
    env["DATABASE_URL"] = "postgresql://production:secret@db.example/customer_data"
    env["REDIS_URL"] = "redis://redis.example:6379/0"
    env["S3_BUCKET"] = "customer-media"
    env["S3_ENDPOINT_URL"] = "https://customer-media.example.com"

    configure_destructive_test_environment(env)

    assert env["DATABASE_URL"] == env["TRAINU_TEST_DATABASE_URL"]
    assert env["REDIS_URL"] == env["TRAINU_TEST_REDIS_URL"]
    assert env["S3_BUCKET"] == "trainu-media-test"
    assert env["S3_ENDPOINT_URL"] == "http://localhost:9000"
