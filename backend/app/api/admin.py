from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.app.db import get_db
from backend.app.services import api_keys as api_keys_svc

from backend.app.api.auth import require_admin_token

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])


@router.get("/reconcile_jobs")
def list_reconcile_jobs(db: Session = Depends(get_db)):
    try:
        jobs = db.query(models.ReconcileJob).order_by(models.ReconcileJob.id.desc()).limit(100).all()
    except Exception:
        # If the table does not exist or DB is not initialized, return empty list
        return []

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


@router.get("/api_keys")
def list_api_keys(db: Session = Depends(get_db)):
    try:
        keys = db.query(models.ApiKey).order_by(models.ApiKey.id.desc()).all()
    except Exception:
        return []
    return [
        {"id": k.id, "name": k.name, "revoked": k.revoked, "created_at": k.created_at, "last_used_at": k.last_used_at}
        for k in keys
    ]


@router.post("/api_keys")
def create_api_key(name: str | None = None, db: Session = Depends(get_db)):
    # Generate a plaintext key and hashed representation
    plaintext, hashed = api_keys_svc.generate_api_key(name)
    k = models.ApiKey(name=name, hashed_key=hashed, revoked=False)
    db.add(k)
    db.commit()
    db.refresh(k)
    # Return plaintext only once
    return {"id": k.id, "name": k.name, "api_key": plaintext}


@router.delete("/api_keys/{key_id}")
def revoke_api_key(key_id: int, db: Session = Depends(get_db)):
    k = db.get(models.ApiKey, key_id)
    if not k:
        raise HTTPException(status_code=404, detail="API key not found")
    k.revoked = True
    db.add(k)
    db.commit()
    return {"ok": True}


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
