"""CLI for inspecting reconcile jobs.

Usage:
    python scripts/reconcile_jobs.py list
    python scripts/reconcile_jobs.py show <job_id>
"""
import argparse
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.app.db import DATABASE_URL


def list_jobs():
    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with SessionLocal() as s:
        jobs = s.query(models.ReconcileJob).order_by(models.ReconcileJob.id.desc()).limit(50).all()
        for j in jobs:
            created = j.created_at.isoformat() if j.created_at else "?"
            print(f"{j.id}\t{j.status}\tprocessed={j.processed_refs}\tupserted={j.upserted}\tskipped={j.skipped}\tcreated={created}")


def show_job(job_id: int):
    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with SessionLocal() as s:
        j = s.get(models.ReconcileJob, job_id)
        if not j:
            print(f"Job {job_id} not found")
            return
        print(f"id: {j.id}")
        print(f"status: {j.status}")
        print(f"total_refs: {j.total_refs}")
        print(f"processed_refs: {j.processed_refs}")
        print(f"upserted: {j.upserted}")
        print(f"skipped: {j.skipped}")
        print(f"config: {j.config}")
        print(f"errors: {j.errors}")
        print(f"created_at: {j.created_at}")
        print(f"started_at: {j.started_at}")
        print(f"completed_at: {j.completed_at}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect reconcile jobs")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list")
    show = sub.add_parser("show")
    show.add_argument("job_id", type=int)
    args = parser.parse_args()
    if args.cmd == "list":
        list_jobs()
    elif args.cmd == "show":
        show_job(args.job_id)
    else:
        parser.print_help()
