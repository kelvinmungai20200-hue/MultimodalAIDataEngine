"""API package exposing endpoint routers."""

from .ingest import router as ingest_router

__all__ = ["ingest_router"]
