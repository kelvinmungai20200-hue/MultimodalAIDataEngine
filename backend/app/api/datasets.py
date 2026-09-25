"""Dataset ownership endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import models
from backend.app.auth import get_current_user
from backend.app.db import get_db

router = APIRouter(prefix="/datasets", tags=["datasets"])


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    metadata: dict | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_dataset(
    body: DatasetCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if db.query(models.Dataset).filter(models.Dataset.name == body.name).first():
        raise HTTPException(status_code=409, detail="Dataset name is already in use")
    dataset = models.Dataset(
        name=body.name,
        description=body.description,
        dataset_metadata=body.metadata,
        owner_id=user.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return {"id": dataset.id, "name": dataset.name, "description": dataset.description}


@router.get("")
def list_datasets(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return [
        {"id": item.id, "name": item.name, "description": item.description}
        for item in db.query(models.Dataset)
        .filter(models.Dataset.owner_id == user.id)
        .order_by(models.Dataset.id)
        .all()
    ]


def _owned_dataset(db: Session, dataset_id: int, user: models.User) -> models.Dataset:
    dataset = db.get(models.Dataset, dataset_id)
    if dataset is None or dataset.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    dataset = _owned_dataset(db, dataset_id, user)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "metadata": dataset.dataset_metadata,
        "owner_id": dataset.owner_id,
    }


@router.get("/{dataset_id}/assets")
def list_dataset_assets(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    dataset = _owned_dataset(db, dataset_id, user)
    return [
        {
            "id": asset.id,
            "filename": asset.filename,
            "storage_url": asset.s3_url,
            "mime_type": asset.mime_type,
            "status": asset.status,
        }
        for asset in db.query(models.Asset)
        .filter(models.Asset.dataset_id == dataset.id)
        .order_by(models.Asset.id)
        .all()
    ]
