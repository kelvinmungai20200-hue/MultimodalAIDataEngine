"""Smoke tester for ingest endpoints without external S3.

This script:
- creates an in-memory SQLite DB and tables
- monkeypatches the s3 presign function to return a fake URL
- calls presign_upload and ingest_complete functions directly (bypassing HTTP)
- verifies DB records were created/updated

Run with: .\\.venv\\Scripts\\python.exe scripts\\run_ingest_smoke.py
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import BackgroundTasks
import os

import sys
import os
# ensure package path so 'backend' package can be imported when running script from backend/
# Add repository root to path so 'backend' package (folder backend/) can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend import models
from backend.app.api import ingest as ingest_module
from backend.app.api.ingest import PresignRequest, IngestCompleteRequest


def main():
    # ensure S3_BUCKET env var present for code paths
    os.environ.setdefault("S3_BUCKET", "test-bucket")

    # create in-memory DB and tables
    engine = create_engine("sqlite:///:memory:", future=True)
    models.create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    # monkeypatch presign and S3_BUCKET configuration
    ingest_module.s3_client.generate_presigned_url = lambda *args, **kwargs: "http://example.com/fake-upload"
    ingest_module.S3_BUCKET = os.environ.get("S3_BUCKET")

    # create a db session
    session = SessionLocal()

    try:
        # call presign_upload directly
        req = PresignRequest(filename="smoke.jpg", content_type="image/jpeg", dataset_id=None)
        presign_resp = ingest_module.presign_upload(req, db=session)
        print("Presign response:", presign_resp)

        # call ingest_complete directly
        complete_req = IngestCompleteRequest(asset_id=presign_resp.asset_id, s3_key=presign_resp.s3_key, file_size=11111, mime_type="image/jpeg", width=200, height=100)
        bt = BackgroundTasks()
        complete_resp = ingest_module.ingest_complete(complete_req, background_tasks=bt, db=session)
        print("Ingest complete response:", complete_resp)

        # run queued embedding task manually (since BackgroundTasks won't run when calling function directly)
        ingest_module._queue_embedding_task(presign_resp.asset_id)

        # verify DB
        asset = session.get(models.Asset, presign_resp.asset_id)
        print("Asset row:", {"id": asset.id, "status": asset.status, "s3_url": asset.s3_url})

        logs = session.query(models.AuditLog).filter(models.AuditLog.target_type == 'asset').all()
        print("Audit logs for assets:", [(l.action, l.details) for l in logs])

    finally:
        session.close()


if __name__ == '__main__':
    main()
