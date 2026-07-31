import logging
import os
from datetime import datetime, timezone
import time
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.app.db import DATABASE_URL

logger = logging.getLogger("worker")
POLL_INTERVAL_SECONDS = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "5"))
MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))


def _process_task(session: Any, task: models.TaskQueue) -> None:
    if task.task_type != "embedding":
        task.status = "failed"
        task.error = f"Unsupported task type: {task.task_type}"
        session.add(task)
        session.commit()
        return

    try:
        from backend.app.services.embedding import process_asset_embedding

        result_id = process_asset_embedding(task.payload["asset_id"])
        task.status = "completed"
        task.result = {"embedding_ref_id": result_id}
        task.completed_at = datetime.now(timezone.utc)
        session.add(task)
        session.commit()
    except Exception as exc:
        logger.exception("Error processing task %s", task.id)
        task.attempts += 1
        task.error = str(exc)
        if task.attempts >= MAX_ATTEMPTS:
            task.status = "failed"
            task.completed_at = datetime.now(timezone.utc)
        else:
            task.status = "queued"
        session.add(task)
        session.commit()


def run_db_worker_loop():
    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    while True:
        session = SessionLocal()
        try:
            query = session.query(models.TaskQueue).filter(models.TaskQueue.status == "queued").order_by(models.TaskQueue.created_at)
            if session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            task = query.first()
            if task is None:
                session.close()
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            task.status = "processing"
            task.started_at = datetime.now(timezone.utc)
            session.add(task)
            session.commit()

            _process_task(session, task)
        except Exception:
            logger.exception("Worker loop failed")
        finally:
            session.close()
            time.sleep(POLL_INTERVAL_SECONDS)
