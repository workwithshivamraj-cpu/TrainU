"""S3-compatible object storage client (MinIO for local dev).

All video/document content lives in a private bucket. Callers never get a
public URL — only short-lived presigned URLs generated on demand, so access
to org content always flows through the API's authorization checks first.
"""
from __future__ import annotations

import io
import uuid
from datetime import timedelta

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        use_ssl=settings.S3_USE_SSL,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=settings.S3_BUCKET)
        logger.info("storage_bucket_created", bucket=settings.S3_BUCKET)


def build_storage_key(organization_id: str, source_id: str, filename: str) -> str:
    safe_name = filename.replace(" ", "_")
    return f"orgs/{organization_id}/sources/{source_id}/{safe_name}"


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    client = get_s3_client()
    client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data, ContentType=content_type)


def upload_fileobj(key: str, fileobj: io.BufferedIOBase, content_type: str = "application/octet-stream") -> None:
    client = get_s3_client()
    client.upload_fileobj(fileobj, settings.S3_BUCKET, key, ExtraArgs={"ContentType": content_type})


def download_bytes(key: str) -> bytes:
    client = get_s3_client()
    obj = client.get_object(Bucket=settings.S3_BUCKET, Key=key)
    return obj["Body"].read()


def get_presigned_url(key: str, expires_in: int = 900) -> str:
    client = get_s3_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
    # Swap internal endpoint for the browser-reachable one when they differ
    # (e.g. backend talks to `minio:9000` inside Docker, browser needs
    # `localhost:9000`).
    if settings.S3_PUBLIC_ENDPOINT_URL and settings.S3_ENDPOINT_URL != settings.S3_PUBLIC_ENDPOINT_URL:
        url = url.replace(settings.S3_ENDPOINT_URL, settings.S3_PUBLIC_ENDPOINT_URL)
    return url


def delete_object(key: str) -> None:
    client = get_s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET, Key=key)


def new_object_id() -> str:
    return str(uuid.uuid4())
