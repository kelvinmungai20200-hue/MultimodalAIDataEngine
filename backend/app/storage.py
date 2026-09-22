"""Storage backends used by the asset API.

The API only depends on :class:`StorageBackend`, making local development and
tests independent of AWS while allowing an S3 implementation in production.
"""

from __future__ import annotations

import os
import posixpath
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    url: str


class StorageBackend(Protocol):
    def save(self, content: bytes, filename: str, content_type: str | None = None) -> StoredObject:
        ...


def _safe_filename(filename: str) -> str:
    # Keep only the final component and replace path separators.  The original
    # filename is metadata; it must never be able to escape STORAGE_DIR.
    name = Path(filename).name.replace("\\", "_").replace("/", "_")
    return name or "asset.bin"


class LocalStorage:
    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root or os.getenv("STORAGE_DIR", "data/assets"))

    def save(self, content: bytes, filename: str, content_type: str | None = None) -> StoredObject:
        key = f"{uuid.uuid4().hex}_{_safe_filename(filename)}"
        destination = self.root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return StoredObject(key=key, url=f"file://{destination.resolve()}")


class S3Storage:
    def __init__(self, bucket: str | None = None, region: str | None = None):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised by config only
            raise RuntimeError("boto3 is required for S3 storage") from exc
        self.bucket = bucket or os.getenv("S3_BUCKET")
        if not self.bucket:
            raise RuntimeError("S3_BUCKET must be configured for S3 storage")
        self.client = boto3.client("s3", region_name=region or os.getenv("S3_REGION", "us-east-1"))

    def save(self, content: bytes, filename: str, content_type: str | None = None) -> StoredObject:
        key = f"assets/{uuid.uuid4().hex}_{_safe_filename(filename)}"
        kwargs = {"Bucket": self.bucket, "Key": key, "Body": content}
        if content_type:
            kwargs["ContentType"] = content_type
        self.client.put_object(**kwargs)
        return StoredObject(key=key, url=f"s3://{self.bucket}/{key}")


def get_storage() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        return S3Storage()
    if backend != "local":
        raise RuntimeError(f"Unsupported STORAGE_BACKEND: {backend}")
    return LocalStorage()
