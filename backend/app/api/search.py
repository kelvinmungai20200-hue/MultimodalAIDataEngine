"""Semantic search over the configured Qdrant collection."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.services.embedding import _embed_text
from backend.app import vector_db

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str | None = None
    vector: list[float] | None = None
    limit: int = Field(default=10, ge=1, le=100)


def _search(query: str | None, vector: list[float] | None, limit: int) -> dict[str, Any]:
    if vector is None:
        if not query:
            raise HTTPException(status_code=422, detail="Provide query or vector")
        vector = _embed_text(query)
    try:
        results = vector_db.search_vectors(vector, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Vector search failed") from exc
    return {"query": query, "limit": limit, "results": results}


@router.post("/search")
def search(body: SearchRequest):
    return _search(body.query, body.vector, body.limit)


@router.get("/search")
def search_get(
    q: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
):
    return _search(q, None, limit)
