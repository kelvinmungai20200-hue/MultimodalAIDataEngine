from __future__ import annotations

import os
import uuid
import logging
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except Exception:
    boto3 = None
    ClientError = Exception

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models
from backend.app.db import get_db
from backend.app.queues import enqueue_embedding_job

logger = logging.getLogger("ingest")
router = APIRouter(prefix="/ingest", tags=["ingest"])

S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
PRESIGN_EXP_SECONDS = int(os.getenv("PRESIGN_EXP_SECONDS", "3600"))

# boto3 client will use env-configured AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
if boto3 is not None:
    s3_client = boto3.client("s3", region_name=S3_REGION)
else:
    # lightweight stub used during local tests when boto3 isn't installed
    class _StubS3Client:
        def generate_presigned_url(self, *args, **kwargs):
            raise RuntimeError("boto3 is not installed in the runtime; in tests monkeypatch ingest.s3_client.generate_presigned_url to a stub returning a URL")

    s3_client = _StubS3Client()


class PresignRequest(BaseModel):
    filename: str
    content_type: Optional[str] = "application/octet-stream"
    dataset_id: Optional[int] = None


class PresignResponse(BaseModel):
    upload_url: str
    s3_key: str
    asset_id: int


class IngestCompleteRequest(BaseModel):
    asset_id: int
    s3_key: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


@router.post("/presign", response_model=PresignResponse)
def presign_upload(body: PresignRequest, db: Session = Depends(get_db)):
    if not S3_BUCKET:
        raise HTTPException(status_code=500, detail="S3_BUCKET not configured")

    # Create an Asset row with status 'uploading'
    filename = body.filename
    dataset_id = body.dataset_id
    key = f"{dataset_id or 'misc'}/{uuid.uuid4().hex}_{filename}"

    asset = models.Asset(
        dataset_id=dataset_id or None,
        s3_url=f"s3://{S3_BUCKET}/{key}",
        filename=filename,
        status="uploading",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    try:
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': S3_BUCKET, 'Key': key, 'ContentType': body.content_type},
            ExpiresIn=PRESIGN_EXP_SECONDS,
        )
    except ClientError as e:
        logger.exception("Failed to generate presigned url")
        raise HTTPException(status_code=500, detail="Failed to generate presigned URL")

    return PresignResponse(upload_url=upload_url, s3_key=key, asset_id=asset.id)


def _queue_embedding_task(asset_id: int):
    logger.info("Queuing embedding job for asset_id=%s", asset_id)
    enqueue_embedding_job(asset_id)


@router.post("/complete")
def ingest_complete(body: IngestCompleteRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Called by client after upload complete (or by an S3 event notification if you implement it)
    asset = db.get(models.Asset, body.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.status not in ("uploading", "pending"):
        logger.info("Asset %s status is %s; overwriting to uploaded", asset.id, asset.status)

    asset.s3_url = f"s3://{S3_BUCKET}/{body.s3_key}"
    asset.file_size = body.file_size
    asset.mime_type = body.mime_type
    asset.width = body.width
    asset.height = body.height
    asset.status = "uploaded"
    db.add(asset)

    # audit log entry
    audit = models.AuditLog(actor_id=None, action="asset_uploaded", target_type="asset", target_id=asset.id, details={"s3_key": body.s3_key})
    db.add(audit)

    db.commit()

    # enqueue embedding job in background
    background_tasks.add_task(_queue_embedding_task, asset.id)

    return {"status": "ok", "asset_id": asset.id}
