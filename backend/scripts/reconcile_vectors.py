"""Reconcile CLI: re-generate embeddings and upsert vectors into the configured vector DB.

Usage:
    python scripts/reconcile_vectors.py [--dry-run] [--only-missing] [--limit N]

Behaviour:
- Iterates EmbeddingRef rows.
- For each row, regenerates the vector from the associated Asset or LLMRecord.
- If vector_db_id is missing, assigns a new UUID and updates the row (unless --dry-run).
- Attempts to upsert the vector into the configured vector DB via backend.app.vector_db.

Note: This script regenerates embeddings using the same embedding backends as the worker
(e.g., local sentence-transformers, OpenAI, or stable-hash fallback). If you use local
sentence-transformers, ensure the heavy ML dependencies are installed.
"""

import argparse
import logging
import uuid
from typing import Optional

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.app.db import DATABASE_URL

logger = logging.getLogger("reconcile")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def regenerate_vector_for_ref(session, ref: models.EmbeddingRef) -> Optional[tuple[str, list[float]]]:
    """Regenerate embedding vector list for given EmbeddingRef by looking up the asset or llm_record.
    Returns (vector_db_id, vector_list) — vector_db_id may be new if ref.vector_db_id was empty.
    """
    from backend.app.services import embedding as embedding_svc

    # Determine source content
    if ref.asset_id:
        asset = session.get(models.Asset, ref.asset_id)
        if asset is None:
            raise ValueError(f"Asset {ref.asset_id} not found for EmbeddingRef {ref.id}")
        content = asset.filename or asset.s3_url
        if asset.mime_type and asset.mime_type.startswith("image/"):
            content = f"image:{asset.filename or asset.s3_url}"
    elif ref.llm_record_id:
        llr = session.get(models.LLMRecord, ref.llm_record_id)
        if llr is None:
            raise ValueError(f"LLMRecord {ref.llm_record_id} not found for EmbeddingRef {ref.id}")
        content = llr.prompt
    else:
        raise ValueError(f"EmbeddingRef {ref.id} has no asset_id or llm_record_id")

    vector = embedding_svc._embed_text(content)
    vector_db_id = ref.vector_db_id or f"asset-{ref.asset_id}" if ref.asset_id else ref.vector_db_id or f"llr-{ref.llm_record_id}"
    return vector_db_id, vector


def reconcile(dry_run: bool = True, only_missing: bool = False, limit: Optional[int] = None, force: bool = False, concurrency: int = 4, batch_size: int = 100):
    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    # Collect ids to process (avoid passing ORM objects between threads)
    session = SessionLocal()
    try:
        query = session.query(models.EmbeddingRef.id).order_by(models.EmbeddingRef.id)
        if only_missing:
            query = query.filter((models.EmbeddingRef.vector_db_id == None) | (models.EmbeddingRef.vector_db_id == ""))
        if limit:
            query = query.limit(limit)

        ids = [r[0] for r in query.all()]
        total = len(ids)
        logger.info("Reconciling %d embedding refs (dry_run=%s, only_missing=%s, concurrency=%s, batch_size=%s)", total, dry_run, only_missing, concurrency, batch_size)

        # Create a reconcile job record for monitoring and resumability
        job = models.ReconcileJob(
            status="running",
            total_refs=total,
            processed_refs=0,
            upserted=0,
            skipped=0,
            config={
                "dry_run": dry_run,
                "only_missing": only_missing,
                "limit": limit,
                "force": force,
                "concurrency": concurrency,
                "batch_size": batch_size,
            },
        )
        session.add(job)
        session.commit()
        session.refresh(job)
    finally:
        session.close()

    from backend.app import vector_db

    import concurrent.futures
    import threading

    counters = {"processed": 0, "upserted": 0, "skipped": 0}
    errors = []
    lock = threading.Lock()

    def update_job_progress():
        update_session = SessionLocal()
        try:
            current_job = update_session.get(models.ReconcileJob, job.id)
            if current_job is None:
                return
            current_job.processed_refs = counters["processed"]
            current_job.upserted = counters["upserted"]
            current_job.skipped = counters["skipped"]
            current_job.errors = errors.copy() if errors else None
            update_session.add(current_job)
            update_session.commit()
        finally:
            update_session.close()

    def process_ref_id(ref_id: int):
        # Each thread must use its own session
        local_session = SessionLocal()
        try:
            ref = local_session.get(models.EmbeddingRef, ref_id)
            if ref is None:
                logger.warning("EmbeddingRef %s disappeared; skipping", ref_id)
                return

            try:
                vector_db_id, vector = regenerate_vector_for_ref(local_session, ref)

                if not ref.vector_db_id:
                    new_id = str(uuid.uuid4())
                    vector_db_id = new_id
                    logger.info("EmbeddingRef %s missing vector_db_id — assigning %s", ref.id, new_id)
                    if not dry_run:
                        ref.vector_db_id = new_id
                        local_session.add(ref)
                        local_session.commit()

                if vector_db.is_configured():
                    try:
                        exists = vector_db.vector_exists(vector_db_id)
                    except Exception:
                        logger.exception("Error checking vector existence for %s; will attempt upsert", vector_db_id)
                        exists = False

                    if exists and not force:
                        logger.info("Vector %s already exists in vector DB; skipping (ref %s)", vector_db_id, ref.id)
                        with lock:
                            counters["skipped"] += 1
                    else:
                        if dry_run:
                            logger.info("(dry-run) Would upsert vector %s for ref %s", vector_db_id, ref.id)
                        else:
                            pushed = vector_db.upsert_vector(vector_db_id, vector, {"embedding_ref_id": ref.id, "asset_id": ref.asset_id})
                            if pushed:
                                logger.info("Upserted embedding_ref %s -> vector %s", ref.id, vector_db_id)
                                with lock:
                                    counters["upserted"] += 1
                            else:
                                logger.warning("Failed to upsert embedding_ref %s to vector DB", ref.id)
                else:
                    logger.info("Vector DB not configured — skipping upsert for %s", ref.id)

            except Exception as exc:
                logger.exception("Failed to reconcile embedding_ref %s: %s", getattr(ref, "id", "?"), exc)
                with lock:
                    errors.append(str(exc))
        finally:
            with lock:
                counters["processed"] += 1
            local_session.close()

    # Process in batches to limit memory and control rate
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        for i in range(0, total, batch_size):
            batch_ids = ids[i : i + batch_size]
            futures = [executor.submit(process_ref_id, rid) for rid in batch_ids]
            # wait for batch to complete
            for fut in concurrent.futures.as_completed(futures):
                try:
                    fut.result()
                except Exception:
                    logger.exception("Error in worker future")
            # Persist progress after each batch
            update_job_progress()

    final_session = SessionLocal()
    try:
        final_job = final_session.get(models.ReconcileJob, job.id)
        if final_job:
            final_job.status = "completed"
            final_job.processed_refs = counters["processed"]
            final_job.upserted = counters["upserted"]
            final_job.skipped = counters["skipped"]
            final_job.errors = errors.copy() if errors else None
            final_job.completed_at = func.now()
            final_session.add(final_job)
            final_session.commit()
    finally:
        final_session.close()

    logger.info("Reconcile complete — processed %d refs; upserted=%d skipped=%d", counters["processed"], counters["upserted"], counters["skipped"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile embeddings to vector DB")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Don't modify DB or upsert; just report")
    parser.add_argument("--only-missing", action="store_true", default=False, help="Only process embedding refs missing a vector_db_id")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of refs to process")
    parser.add_argument("--force", action="store_true", default=False, help="Force upsert even if vector exists in vector DB")
    parser.add_argument("--concurrency", type=int, default=4, help="Number of worker threads to use")
    parser.add_argument("--batch-size", type=int, default=100, help="Process refs in batches of this size")

    args = parser.parse_args()
    reconcile(dry_run=args.dry_run, only_missing=args.only_missing, limit=args.limit, force=args.force, concurrency=args.concurrency, batch_size=args.batch_size)
