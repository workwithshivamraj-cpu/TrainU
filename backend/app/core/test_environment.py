"""Fail-closed configuration for the destructive pytest database fixture."""
from __future__ import annotations

from collections.abc import MutableMapping
from urllib.parse import urlparse

from sqlalchemy.engine import make_url


def configure_destructive_test_environment(env: MutableMapping[str, str]) -> None:
    """Select isolated test services before app settings or engines are loaded.

    The test database fixture drops every mapped table. No runtime DATABASE_URL
    or bucket default is accepted as an implicit target.
    """
    if env.get("ENVIRONMENT", "").strip().lower() != "test":
        raise RuntimeError("Destructive tests require ENVIRONMENT=test")
    if env.get("TRAINU_ALLOW_SCHEMA_RESET", "").strip().lower() != "true":
        raise RuntimeError("Set TRAINU_ALLOW_SCHEMA_RESET=true to authorize the disposable test schema")

    database_url = env.get("TRAINU_TEST_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("TRAINU_TEST_DATABASE_URL must explicitly name the disposable database")
    try:
        parsed_url = make_url(database_url)
    except Exception as exc:
        raise RuntimeError("TRAINU_TEST_DATABASE_URL is invalid") from exc
    if (
        parsed_url.drivername not in {"postgresql", "postgresql+psycopg2"}
        or parsed_url.database != "trainu_test"
        or parsed_url.host not in {"localhost", "127.0.0.1", "postgres"}
    ):
        raise RuntimeError("Tests may only reset the allowlisted local trainu_test database")

    bucket = env.get("TRAINU_TEST_STORAGE_BUCKET", "").strip()
    if bucket != "trainu-media-test":
        raise RuntimeError("TRAINU_TEST_STORAGE_BUCKET must be the isolated trainu-media-test bucket")
    storage_endpoint = env.get("TRAINU_TEST_S3_ENDPOINT_URL", "").strip()
    try:
        parsed_storage_endpoint = urlparse(storage_endpoint)
        storage_port = parsed_storage_endpoint.port
    except ValueError as exc:
        raise RuntimeError("TRAINU_TEST_S3_ENDPOINT_URL must name isolated local object storage") from exc
    if (
        parsed_storage_endpoint.scheme != "http"
        or parsed_storage_endpoint.hostname not in {"localhost", "127.0.0.1", "minio"}
        or storage_port != 9000
        or parsed_storage_endpoint.username
        or parsed_storage_endpoint.password
        or parsed_storage_endpoint.path
        or parsed_storage_endpoint.query
        or parsed_storage_endpoint.fragment
    ):
        raise RuntimeError("TRAINU_TEST_S3_ENDPOINT_URL must use the allowlisted local object-storage endpoint")
    redis_url = env.get("TRAINU_TEST_REDIS_URL", "").strip()
    try:
        parsed_redis_url = make_url(redis_url)
    except Exception as exc:
        raise RuntimeError("TRAINU_TEST_REDIS_URL must explicitly name isolated Redis DB 1") from exc
    if (
        parsed_redis_url.drivername not in {"redis", "rediss"}
        or parsed_redis_url.host not in {"localhost", "127.0.0.1", "redis"}
        or parsed_redis_url.database != "1"
    ):
        raise RuntimeError("TRAINU_TEST_REDIS_URL must use the isolated local Redis database 1")

    env["DATABASE_URL"] = database_url
    env["REDIS_URL"] = redis_url
    env["S3_BUCKET"] = bucket
    env["S3_ENDPOINT_URL"] = storage_endpoint
    env["ENVIRONMENT"] = "test"
