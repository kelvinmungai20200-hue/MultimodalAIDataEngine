import tempfile
import os
import importlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models


def test_reconcile_resumes_from_last_processed(monkeypatch):
    # Create a temporary sqlite file DB for the test
    tmp = tempfile.NamedTemporaryFile(prefix="test_reconcile_", suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite:///{tmp.name}"

    # Import reconcile module and set DATABASE_URL to the test DB
    import backend.scripts.reconcile_vectors as reconcile_mod
    monkeypatch.setattr(reconcile_mod, "DATABASE_URL", db_url)

    # Create tables in the test DB
    engine = create_engine(db_url, future=True)
    models.create_all_tables(engine)

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        # Insert LLM records and EmbeddingRefs
        llr_ids = []
        for i in range(5):
            llr = models.LLMRecord(prompt=f"prompt {i}")
            s.add(llr)
            s.flush()
            llr_ids.append(llr.id)
            ref = models.EmbeddingRef(llm_record_id=llr.id, vector_db_id=f"v{i}")
            s.add(ref)
        s.commit()

        # Create a pending reconcile job that processed first two entries
        job = models.ReconcileJob(status="pending", total_refs=5, processed_refs=2, upserted=0, skipped=0, config={"last_processed_id": llr_ids[1]})
        s.add(job)
        s.commit()
        s.refresh(job)
        job_id = job.id


    # Patch embedding to avoid heavy dependencies
    import backend.app.services.embedding as embedding_svc

    monkeypatch.setattr(embedding_svc, "_embed_text", lambda text: [0.0, 0.0, 0.0, 0.0])

    # Patch vector_db to be unconfigured to skip upserts
    class FakeVD:
        @staticmethod
        def is_configured():
            return False

    import backend.app as app_pkg
    monkeypatch.setattr(app_pkg, "vector_db", FakeVD, raising=False)

    # Run reconcile with resume=True
    reconcile_mod.reconcile(dry_run=True, only_missing=False, limit=None, force=False, concurrency=1, batch_size=2, resume=True)

    # Verify job updated to completed and processed_refs increased to 5
    engine2 = create_engine(db_url, future=True)
    Session2 = sessionmaker(bind=engine2, expire_on_commit=False)
    with Session2() as s2:
        j = s2.get(models.ReconcileJob, job_id)
        assert j is not None
        assert j.status == "completed"
        assert j.processed_refs == 5
        assert j.config is not None
        assert j.config.get("last_processed_id") is not None

    # cleanup: dispose engines and remove temp DB file
    try:
        engine.dispose()
    except Exception:
        pass
    try:
        engine2.dispose()
    except Exception:
        pass
    try:
        os.unlink(tmp.name)
    except Exception:
        pass
