"""Semantic search over the configured Qdrant collection."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.services.embedding import _embed_text
from backend.app import vector_db
from backend import models
from backend.app.auth import get_current_user
from backend.app.db import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str | None = None
    vector: list[float] | None = None
    limit: int = Field(default=10, ge=1, le=100)


def _search(
    query: str | None,
    vector: list[float] | None,
    limit: int,
    db: Session,
    user: models.User,
) -> dict[str, Any]:
    if vector is None:
        if not query:
            raise HTTPException(status_code=422, detail="Provide query or vector")
        vector = _embed_text(query)
    try:
        results = vector_db.search_vectors(vector, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Vector search failed") from exc
    owned_asset_ids = {
        asset_id
        for (asset_id,) in db.query(models.Asset.id)
        .join(models.Dataset)
        .filter(models.Dataset.owner_id == user.id)
        .all()
    }
    results = [
        result
        for result in results
        if isinstance(result.get("payload"), dict)
        and result["payload"].get("asset_id") in owned_asset_ids
    ]
    return {"query": query, "limit": limit, "results": results}


@router.post("/search")
def search(
    body: SearchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return _search(body.query, body.vector, body.limit, db, user)


@router.get("/search")
def search_get(
    q: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return _search(q, None, limit, db, user)
