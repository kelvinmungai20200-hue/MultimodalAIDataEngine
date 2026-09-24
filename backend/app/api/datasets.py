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
