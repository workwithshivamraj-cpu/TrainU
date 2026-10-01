"""Download the local S3-compatible bucket to a private migration backup."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath

import boto3
from botocore.exceptions import ClientError

root = Path(sys.argv[1]).resolve()
objects_root = root / "objects"
objects_root.mkdir(mode=0o700)
client = boto3.client(
    "s3",
    endpoint_url=os.environ["S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    region_name=os.environ.get("S3_REGION", "us-east-1"),
)
bucket = os.environ["S3_BUCKET"]
entries: list[dict[str, object]] = []
try:
    client.head_bucket(Bucket=bucket)
except ClientError as exc:
    code = str(exc.response.get("Error", {}).get("Code", ""))
    if code not in {"404", "NoSuchBucket", "NotFound"}:
        raise SystemExit("Object-storage backup preflight failed; migration is blocked.") from exc
else:
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            key = str(item["Key"])
            relative = PurePosixPath(key)
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit("Unsafe object key encountered; migration is blocked.")
            destination = objects_root.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            resolved = destination.resolve()
            if not resolved.is_relative_to(objects_root.resolve()):
                raise SystemExit("Object key escapes the backup directory; migration is blocked.")
            client.download_file(bucket, key, str(destination))
            digest = hashlib.sha256()
            with destination.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            entries.append({"key": key, "size": destination.stat().st_size, "sha256": digest.hexdigest()})

(root / "storage-manifest.json").write_text(
    json.dumps({"bucket": bucket, "object_count": len(entries), "objects": entries}, indent=2),
    encoding="utf-8",
)
print(f"Backed up {len(entries)} private storage object(s).")
