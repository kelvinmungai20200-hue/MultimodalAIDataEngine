import importlib
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models


def setup_in_memory_db():
    # Use a StaticPool so multiple create_engine calls can share the same in-memory DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    models.create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, SessionLocal


def test_ml_smoke_embedding_generation(monkeypatch):
    """Smoke test for embedding generation pipeline used by the ML CI job.

    This test avoids requiring heavy model downloads by monkeypatching the embedding backend
    to return a small deterministic vector. It verifies that process_asset_embedding
    generates an EmbeddingRef row and attempts to upsert to the vector DB (which is also mocked).
    """
    engine, SessionLocal = setup_in_memory_db()

    # Ensure that backend.app.services.embedding.create_engine returns our in-memory engine
    svc_module = importlib.import_module("backend.app.services.embedding")
    importlib.reload(svc_module)

    # Monkeypatch create_engine used in the service so it uses the in-memory engine
    monkeypatch.setattr(svc_module, "create_engine", lambda url, future=True: engine)

    # Insert a test asset into the DB using the same engine/session
    with SessionLocal() as s:
        asset = models.Asset(s3_url="s3://bucket/test.jpg", filename="test.jpg", mime_type="image/jpeg", status="uploaded")
        s.add(asset)
        s.commit()
        s.refresh(asset)
        asset_id = asset.id

    # Monkeypatch the actual embedding generation to avoid heavy models
    monkeypatch.setattr(svc_module, "_embed_text", lambda text: [0.1, 0.2, 0.3])

    # Monkeypatch vector_db to avoid real network upserts
    vector_db_module = importlib.import_module("backend.app.vector_db")
    importlib.reload(vector_db_module)
    monkeypatch.setattr(vector_db_module, "upsert_vector", lambda vector_id, vector, payload, collection=None: True)
    monkeypatch.setattr(vector_db_module, "is_configured", lambda: False)

    # Now call the worker function to generate embedding (it will use our patched create_engine)
    embedding_id = svc_module.process_asset_embedding(asset_id)
    assert embedding_id is not None

    # Verify the EmbeddingRef exists in the DB
    with SessionLocal() as s:
        ref = s.get(models.EmbeddingRef, embedding_id)
        assert ref is not None
        assert ref.asset_id == asset_id
        assert ref.dimension == 3
        # vector_db_id should be present (fallback asset-{id})
        assert ref.vector_db_id.startswith("asset-") or ref.vector_db_id
