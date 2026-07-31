from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import models


def test_reconcile_job_model_can_be_created():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    models.create_all_tables(engine)

    with Session(engine) as session:
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
