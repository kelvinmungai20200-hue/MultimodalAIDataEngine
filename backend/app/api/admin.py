from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.app.db import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/reconcile_jobs")
def list_reconcile_jobs(db: Session = Depends(get_db)):
    jobs = db.query(models.ReconcileJob).order_by(models.ReconcileJob.id.desc()).limit(100).all()
    return [
        {
            "id": j.id,
            "status": j.status,
            "total_refs": j.total_refs,
            "processed_refs": j.processed_refs,
            "upserted": j.upserted,
            "skipped": j.skipped,
            "config": j.config,
            "errors": j.errors,
            "created_at": j.created_at,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
        }
        for j in jobs
    ]


@router.get("/reconcile_jobs/{job_id}")
def get_reconcile_job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(models.ReconcileJob, job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": j.id,
        "status": j.status,
        "total_refs": j.total_refs,
        "processed_refs": j.processed_refs,
        "upserted": j.upserted,
        "skipped": j.skipped,
        "config": j.config,
        "errors": j.errors,
        "created_at": j.created_at,
        "started_at": j.started_at,
        "completed_at": j.completed_at,
    }
