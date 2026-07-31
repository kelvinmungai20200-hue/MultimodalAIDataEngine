import logging
import os
from typing import Any, Optional

from backend import models
from backend.app.db import SessionLocal

logger = logging.getLogger("queue")
REDIS_URL = os.getenv("REDIS_URL")

try:
    import redis
    from rq import Connection, Queue, Worker
    REDIS_AVAILABLE = bool(REDIS_URL)
except ImportError:
    redis = None  # type: ignore[assignment]
    Connection = None  # type: ignore[assignment]
    Queue = None  # type: ignore[assignment]
    Worker = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False


def _get_redis_connection():
    if not REDIS_AVAILABLE or redis is None:
        raise RuntimeError("Redis queue is not configured or the redis/RQ libraries are unavailable")
    return redis.from_url(REDIS_URL)


def enqueue_embedding_job(asset_id: int) -> str:
    if REDIS_AVAILABLE:
        try:
            connection = _get_redis_connection()
            queue = Queue("embeddings", connection=connection)
            job = queue.enqueue(
                "backend.app.services.embedding.process_asset_embedding",
                asset_id,
                job_timeout=600,
                result_ttl=86400,
            )
            logger.info("Enqueued embedding job %s for asset %s", job.id, asset_id)
            return str(job.id)
        except Exception:
            logger.exception("Failed to enqueue job to Redis; falling back to DB task queue")

    session = SessionLocal()
    try:
        task = models.TaskQueue(
            task_type="embedding",
            payload={"asset_id": asset_id},
            status="queued",
            attempts=0,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        logger.info("Created DB queue task %s for asset %s", task.id, asset_id)
        return f"db-{task.id}"
    finally:
        session.close()


def run_queue_worker():
    if REDIS_AVAILABLE:
        connection = _get_redis_connection()
        with Connection(connection):
            worker = Worker(["embeddings"], connection=connection)
            worker.work(with_scheduler=True)
    else:
        from backend.app.worker import run_db_worker_loop

        run_db_worker_loop()
