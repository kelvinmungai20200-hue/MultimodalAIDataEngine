"""Annotation creation, versioning, and review endpoints."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import models
from backend.app.auth import get_current_user
from backend.app.db import get_db

router = APIRouter(prefix="/assets", tags=["annotations"])
REVIEW_ROLES = {"admin", "reviewer"}
EDITABLE_STATUSES = {"pending", "rejected"}


class AnnotationCreate(BaseModel):
    annotation: dict[str, Any]


class AnnotationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(approved|rejected|pending)$")


def _owned_asset(db: Session, asset_id: int, user: models.User) -> models.Asset:
    asset = db.get(models.Asset, asset_id)
    if asset is None or asset.dataset is None or asset.dataset.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


def _annotation_response(item: models.Annotation) -> dict[str, Any]:
    return {
        "id": item.id,
        "asset_id": item.asset_id,
        "annotator_id": item.annotator_id,
        "reviewed_by_id": item.reviewed_by_id,
        "annotation": item.annotation,
        "version": item.version,
        "status": item.status,
        "created_at": item.created_at,
        "reviewed_at": item.reviewed_at,
    }


@router.post("/{asset_id}/annotations", status_code=status.HTTP_201_CREATED)
def create_annotation(
    asset_id: int,
    body: AnnotationCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    asset = _owned_asset(db, asset_id, user)
    for _ in range(3):
        latest_version = (
            db.query(func.max(models.Annotation.version))
            .filter(models.Annotation.asset_id == asset.id)
            .scalar()
            or 0
        )
        item = models.Annotation(
            asset_id=asset.id,
            annotator_id=user.id,
            annotation=body.annotation,
            version=latest_version + 1,
            status="pending",
        )
        db.add(item)
        try:
            db.commit()
            db.refresh(item)
            return _annotation_response(item)
        except IntegrityError:
            db.rollback()
    raise HTTPException(status_code=409, detail="Unable to allocate annotation version")


@router.get("/{asset_id}/annotations")
def list_annotations(
    asset_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    asset = _owned_asset(db, asset_id, user)
    return [
        _annotation_response(item)
        for item in db.query(models.Annotation)
        .filter(models.Annotation.asset_id == asset.id)
        .order_by(models.Annotation.version)
        .all()
    ]


@router.patch("/annotations/{annotation_id}/status")
def update_annotation_status(
    annotation_id: int,
    body: AnnotationStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    item = db.get(models.Annotation, annotation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    _owned_asset(db, item.asset_id, user)
    if user.role not in REVIEW_ROLES:
        raise HTTPException(status_code=403, detail="Reviewer permission required")
    if body.status == "pending":
        raise HTTPException(status_code=422, detail="Review status must be approved or rejected")
    item.status = body.status
    item.reviewed_by_id = user.id
    item.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _annotation_response(item)
