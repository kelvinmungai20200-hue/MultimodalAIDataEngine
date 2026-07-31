import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("vector_db")
# Optional Prometheus metrics
try:
    from prometheus_client import Counter
    METRICS_ENABLED = True
except Exception:
    Counter = None  # type: ignore
    METRICS_ENABLED = False

# Define counters (if prometheus_client available)
if METRICS_ENABLED:
    QDRANT_UPSERT_RETRIES = Counter("qdrant_upsert_retries_total", "Total retry attempts for Qdrant upserts")
    QDRANT_UPSERT_FAILURES = Counter("qdrant_upsert_failures_total", "Total failed Qdrant upserts after retries")
    QDRANT_GETPOINT_RETRIES = Counter("qdrant_getpoint_retries_total", "Total retry attempts for Qdrant get_point checks")
    QDRANT_GETPOINT_FAILURES = Counter("qdrant_getpoint_failures_total", "Total failed Qdrant get_point checks after retries")
else:
    # No-op placeholders
    class _Noop:
        def inc(self, *args, **kwargs):
            return None

    QDRANT_UPSERT_RETRIES = _Noop()
    QDRANT_UPSERT_FAILURES = _Noop()
    QDRANT_GETPOINT_RETRIES = _Noop()
    QDRANT_GETPOINT_FAILURES = _Noop()

# Try Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:
    QdrantClient = None  # type: ignore

# Future: support Pinecone, Milvus, etc.

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "multimodal_embeddings")


import time
import random

VECTOR_DB_MAX_RETRIES = int(os.getenv("VECTOR_DB_MAX_RETRIES", "3"))
VECTOR_DB_BACKOFF_BASE = float(os.getenv("VECTOR_DB_BACKOFF_BASE", "0.5"))


def _qdrant_upsert(vector_id: str, vector: List[float], payload: Dict[str, Any], collection: Optional[str] = None) -> bool:
    if QdrantClient is None or not QDRANT_URL:
        logger.debug("Qdrant not available or QDRANT_URL not set")
        return False

    coll = collection or QDRANT_COLLECTION
    attempt = 0
    while attempt <= VECTOR_DB_MAX_RETRIES:
        try:
            client = QdrantClient(url=QDRANT_URL)
            # Upsert point
            client.upsert(collection_name=coll, points=[{"id": vector_id, "vector": vector, "payload": payload}])
            logger.info("Upserted vector %s into Qdrant collection %s", vector_id, coll)
            return True
        except Exception:
            attempt += 1
            QDRANT_UPSERT_RETRIES.inc()
            if attempt > VECTOR_DB_MAX_RETRIES:
                QDRANT_UPSERT_FAILURES.inc()
                logger.exception("Failed to upsert vector into Qdrant after %s attempts", attempt)
                return False
            # Exponential backoff with jitter
            backoff = VECTOR_DB_BACKOFF_BASE * (2 ** (attempt - 1))
            jitter = random.uniform(0, backoff * 0.2)
            sleep_for = backoff + jitter
            logger.warning("Qdrant upsert failed on attempt %s/%s, retrying in %.2fs", attempt, VECTOR_DB_MAX_RETRIES, sleep_for)
            time.sleep(sleep_for)


def upsert_vector(vector_id: str, vector: List[float], payload: Dict[str, Any], collection: Optional[str] = None) -> bool:
    """Upsert a vector into the configured vector DB. Returns True on success.

    Currently supports Qdrant when QDRANT_URL is set and qdrant-client is installed.
    """
    # Qdrant
    if QDRANT_URL and QdrantClient is not None:
        return _qdrant_upsert(vector_id, vector, payload, collection=collection)

    logger.debug("No vector DB configured; skipping upsert")
    return False


def vector_exists(vector_id: str, collection: Optional[str] = None) -> bool:
    """Check whether a vector with the given id exists in the configured vector DB.

    Returns True if present, False otherwise. Retries transient errors with backoff; non-fatal on final failure.
    """
    if QDRANT_URL is None or QdrantClient is None:
        logger.debug("vector_exists: Qdrant not configured or client missing")
        return False

    coll = collection or QDRANT_COLLECTION
    attempt = 0
    while attempt <= VECTOR_DB_MAX_RETRIES:
        try:
            client = QdrantClient(url=QDRANT_URL)
            # Qdrant client's get_point returns a PointStruct or raises if not found; handle gracefully
            try:
                point = client.get_point(collection_name=coll, point_id=vector_id)
                return point is not None
            except Exception as inner_exc:
                # If get_point indicates not found, many clients raise a specific exception;
                # here treat as missing but retry on transient errors.
                logger.debug("vector_exists: get_point raised (attempt %s) - %s", attempt + 1, inner_exc)
                # Fall through to retry logic
                raise
        except Exception:
            attempt += 1
            QDRANT_GETPOINT_RETRIES.inc()
            if attempt > VECTOR_DB_MAX_RETRIES:
                QDRANT_GETPOINT_FAILURES.inc()
                logger.exception("vector_exists: failed to check existence for %s after %s attempts", vector_id, attempt)
                return False
            # Exponential backoff with jitter
            backoff = VECTOR_DB_BACKOFF_BASE * (2 ** (attempt - 1))
            jitter = random.uniform(0, backoff * 0.2)
            sleep_for = backoff + jitter
            logger.warning("vector_exists: error checking %s (attempt %s/%s), retrying in %.2fs", vector_id, attempt, VECTOR_DB_MAX_RETRIES, sleep_for)
            time.sleep(sleep_for)
    return False


def is_configured() -> bool:
    if QDRANT_URL and QdrantClient is not None:
        return True
    return False
