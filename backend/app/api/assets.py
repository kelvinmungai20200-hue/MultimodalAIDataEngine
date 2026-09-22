"""Asset ingestion API."""

from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend import models
from backend.app.db import get_db
from backend.app.queues import enqueue_embedding_job
from backend.app.storage import get_storage

logger = logging.getLogger("assets")
router = APIRouter(tags=["assets"])


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Expected an integer value") from exc


async def _parse_asset_request(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="JSON body must be an object")
        return payload

    if "multipart/form-data" in content_type:
        form = await request.form()
        payload = dict(form)
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            payload["file_bytes"] = await upload.read()
            payload.setdefault("filename", getattr(upload, "filename", None))
            payload.setdefault("mime_type", getattr(upload, "content_type", None))
        return payload

    raise HTTPException(status_code=415, detail="Use application/json or multipart/form-data")


@router.post("/assets", status_code=status.HTTP_202_ACCEPTED)
async def create_asset(request: Request, db: Session = Depends(get_db)):
    """Create an asset and enqueue its embedding job.

    JSON requests may provide an existing ``s3_url``/``storage_url`` or a
    ``content`` string (base64 is accepted with ``content_encoding=base64``).
    Multipart requests should contain a ``file`` field.
    """
    payload = await _parse_asset_request(request)
    filename = str(payload.get("filename") or "asset.bin")
    mime_type = payload.get("mime_type") or payload.get("content_type")
    existing_url = payload.get("storage_url") or payload.get("s3_url")
    content = payload.get("file_bytes")

    if content is None and payload.get("content") is not None:
        raw_content = payload["content"]
        if isinstance(raw_content, str):
            if payload.get("content_encoding") == "base64":
                try:
                    content = base64.b64decode(raw_content, validate=True)
                except (ValueError, binascii.Error) as exc:
                    raise HTTPException(status_code=422, detail="Invalid base64 content") from exc
            else:
                content = raw_content.encode("utf-8")
        else:
            raise HTTPException(status_code=422, detail="content must be a string")

    if content is None and not existing_url:
        raise HTTPException(status_code=422, detail="Provide file content or storage_url")

    if existing_url:
        storage_url = str(existing_url)
        storage_key = payload.get("storage_key")
    else:
        try:
            stored = get_storage().save(bytes(content), filename, mime_type)
        except Exception as exc:
            logger.exception("Unable to store asset")
            raise HTTPException(status_code=500, detail="Unable to store asset") from exc
        storage_url, storage_key = stored.url, stored.key

    metadata = payload.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="metadata must be valid JSON") from exc

    asset = models.Asset(
        dataset_id=_as_int(payload.get("dataset_id")),
        s3_url=storage_url,
        filename=filename,
        file_size=len(content) if content is not None else _as_int(payload.get("file_size")),
        mime_type=mime_type,
        width=_as_int(payload.get("width")),
        height=_as_int(payload.get("height")),
        duration_seconds=_as_int(payload.get("duration_seconds")),
        sha256=payload.get("sha256"),
        status="queued",
        annotations=metadata,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    try:
        job_id = enqueue_embedding_job(asset.id)
    except Exception as exc:
        asset.status = "failed"
        db.commit()
        logger.exception("Unable to enqueue embedding for asset %s", asset.id)
        raise HTTPException(status_code=503, detail="Unable to enqueue embedding job") from exc

    return {
        "id": asset.id,
        "asset_id": asset.id,
        "filename": asset.filename,
        "storage_url": asset.s3_url,
        "storage_key": storage_key,
        "status": asset.status,
        "job_id": job_id,
    }
