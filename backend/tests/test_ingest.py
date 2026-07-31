import os
os.environ.setdefault("S3_BUCKET", "test-bucket")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend import models
from backend.app import db as db_module
from backend.app.api import ingest as ingest_module


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    models.create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, SessionLocal


def test_presign_and_complete_flow(monkeypatch):
    engine, SessionLocal = setup_in_memory_db()

    # override get_db dependency to use in-memory session
    def get_test_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[db_module.get_db] = get_test_db

    # Ensure the queue module uses the same in-memory SessionLocal (DB fallback path)
    from backend.app import queues as queues_module
    monkeypatch.setattr(queues_module, "SessionLocal", SessionLocal)

    # mock S3 presign
    monkeypatch.setattr(ingest_module.s3_client, "generate_presigned_url", lambda *args, **kwargs: "http://example.com/fake-upload")

    client = TestClient(app)

    # 1) Request presign
    response = client.post("/ingest/presign", json={"filename": "test.jpg", "content_type": "image/jpeg", "dataset_id": None})
    assert response.status_code == 200
    data = response.json()
    assert "upload_url" in data and "asset_id" in data and "s3_key" in data

    asset_id = data["asset_id"]
    s3_key = data["s3_key"]

    # 2) Complete ingest
    complete_payload = {"asset_id": asset_id, "s3_key": s3_key, "file_size": 12345, "mime_type": "image/jpeg", "width": 640, "height": 480}
    response2 = client.post("/ingest/complete", json=complete_payload)
    assert response2.status_code == 200
    assert response2.json()["status"] == "ok"

    # 3) Verify DB state
    with SessionLocal() as s:
        asset = s.get(models.Asset, asset_id)
        assert asset is not None
        assert asset.status == "uploaded"

        logs = s.query(models.AuditLog).filter(models.AuditLog.target_type == 'asset').all()
        assert any(l.action == 'asset_uploaded' for l in logs)

    # cleanup override
    app.dependency_overrides.pop(db_module.get_db, None)
