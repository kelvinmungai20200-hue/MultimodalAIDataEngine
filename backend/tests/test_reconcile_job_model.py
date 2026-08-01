from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import models


def test_reconcile_job_model_can_be_created(test_db):
    # test_db yields a SessionLocal factory for the patched in-memory DB
    SessionLocal = test_db

    with SessionLocal() as session:
        job = models.ReconcileJob(
            name="test-reconcile",
            status="running",
            total_refs=1,
            processed_refs=0,
            upserted=0,
            skipped=0,
            config={"dry_run": True},
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.id is not None
        assert job.status == "running"
        assert job.config == {"dry_run": True}
        assert job.processed_refs == 0
        assert job.upserted == 0
        assert job.skipped == 0
