import hashlib
import logging
import os
import uuid
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.app.db import DATABASE_URL

logger = logging.getLogger("embedding")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    import openai
except ImportError:
    openai = None  # type: ignore

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
OPENAI_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _stable_hash_embedding(text: str, dimension: int = 128) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for i in range(dimension):
        byte = digest[i % len(digest)]
        values.append((byte / 255.0) * 2.0 - 1.0)
    return values


def _load_sentence_transformer():
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed")
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _embed_text(text: str) -> list[float]:
    if SentenceTransformer is not None:
        model = _load_sentence_transformer()
        vector = model.encode(text, convert_to_numpy=True)
        return vector.tolist() if np is None else vector.tolist()

    if openai is not None and OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
        response = openai.Embedding.create(model=OPENAI_MODEL, input=text)
        return response.data[0].embedding

    logger.warning("No embedding backend available; falling back to stable hash embeddings")
    return _stable_hash_embedding(text)


def _push_to_qdrant(vector_id: str, vector: list[float], payload: dict) -> None:
    """Attempt to upsert a single vector into Qdrant collection if configured."""
    if QdrantClient is None or not QDRANT_URL:
        logger.debug("Qdrant client not available or QDRANT_URL not set; skipping push to Qdrant")
        return

    try:
        client = QdrantClient(url=QDRANT_URL)
        # Ensure collection exists with appropriate vector size — Qdrant will error if mismatched
        # We attempt an upsert (creates collection if missing with default settings in newer qdrant-client versions)
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[{"id": vector_id, "vector": vector, "payload": payload}],
        )
        logger.info("Pushed vector %s to Qdrant collection %s", vector_id, QDRANT_COLLECTION)
    except Exception:
        logger.exception("Failed to push vector to Qdrant; continuing without raising")


def process_asset_embedding(asset_id: int):
    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()

    try:
        asset = session.get(models.Asset, asset_id)
        if asset is None:
            raise ValueError(f"Asset {asset_id} not found")

        content = asset.filename or asset.s3_url
        if asset.mime_type and asset.mime_type.startswith("image/"):
            content = f"image:{asset.filename or asset.s3_url}"

        embedding_list = _embed_text(content)

        # Generate a stable vector DB id for this embedding
        vector_db_id = str(uuid.uuid4())

        # Create EmbeddingRef first so we have an ID to include in vector DB payloads
        embedding_ref = models.EmbeddingRef(
            asset_id=asset_id,
            vector_db_id=vector_db_id,
            model_name=EMBEDDING_MODEL_NAME if SentenceTransformer is not None else OPENAI_MODEL if openai is not None and OPENAI_API_KEY else "stable-hash",
            dimension=len(embedding_list),
            normalized=False,
            meta={"source": "local_embedding_worker", "mime_type": asset.mime_type},
        )
        session.add(embedding_ref)
        session.commit()
        session.refresh(embedding_ref)

        # Try pushing to the configured vector DB via the abstraction layer; include embedding_ref_id and asset_id
        payload = {"embedding_ref_id": embedding_ref.id, "asset_id": asset_id, "mime_type": asset.mime_type}
        try:
            from backend.app import vector_db
            pushed = vector_db.upsert_vector(vector_db_id, embedding_list, payload)
            if not pushed:
                # if not pushed, fall back to a readable id and update the EmbeddingRef
                fallback_id = f"asset-{asset_id}"
                embedding_ref.vector_db_id = fallback_id
                session.add(embedding_ref)
                session.commit()
                vector_db_id = fallback_id
        except Exception:
            logger.exception("Vector DB upsert failed; updating EmbeddingRef with fallback id")
            fallback_id = f"asset-{asset_id}"
            embedding_ref.vector_db_id = fallback_id
            session.add(embedding_ref)
            session.commit()
            vector_db_id = fallback_id

        logger.info("Generated embedding for asset %s, stored ref %s", asset_id, embedding_ref.id)
        return embedding_ref.id
    finally:
        session.close()
