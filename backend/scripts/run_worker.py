"""Run the backend worker to process queued embedding tasks.

Usage:
    .\.venv\Scripts\python.exe scripts\run_worker.py

This worker will use Redis/RQ if REDIS_URL is configured and redis/rq are available.
Otherwise, it will fall back to a simple DB-backed queue.
"""

from backend.app.queues import run_queue_worker


if __name__ == '__main__':
    run_queue_worker()
