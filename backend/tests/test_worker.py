import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.app import queues
from backend.app.worker import _process_task


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    models.create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, SessionLocal


def test_enqueue_embedding_job_and_process(monkeypatch):
    engine, SessionLocal = setup_in_memory_db()

    # Override SessionLocal used by the queue module
    queues.SessionLocal = SessionLocal
    queues.REDIS_AVAILABLE = False

    # Create a dummy asset to embed
    session = SessionLocal()
    asset = models.Asset(
        dataset_id=None,
        s3_url="s3://test-bucket/test.jpg",
        filename="test.jpg",
        status="uploaded",
        mime_type="image/jpeg",
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)

    task_id = queues.enqueue_embedding_job(asset.id)
    assert task_id.startswith("db-")

    task = session.query(models.TaskQueue).filter_by(id=int(task_id.split("-")[1])).one()
    assert task.status == "queued"

    # patch embedding service to avoid external dependency
    def fake_process_asset_embedding(asset_id_value: int):
        return 42

    monkeypatch.setattr(
        "backend.app.services.embedding.process_asset_embedding",
        fake_process_asset_embedding,
    )

    _process_task(session, task)

    session.refresh(task)
    assert task.status == "completed"
    assert task.result == {"embedding_ref_id": 42}

    session.close()
