import os
import time
import requests

import pytest


@pytest.mark.skipif(not os.getenv("QDRANT_URL"), reason="QDRANT_URL not set")
def test_qdrant_integration_upsert(monkeypatch):
    # Use a temporary test collection
    qdrant_url = os.getenv("QDRANT_URL")
    coll = os.getenv("QDRANT_COLLECTION", "test_integration_collection")

    # Ensure collection is created with a small vector size for test
    create_url = f"{qdrant_url}/collections/{coll}"
    payload = {"vectors": {"size": 3, "distance": "Cosine"}}
    # create or replace collection
    requests.put(create_url, json=payload)

    # Wait briefly for collection to be available
    time.sleep(0.5)

    # Import vector_db and attempt an upsert with a small vector
    from backend.app import vector_db

    # Ensure module sees env vars
    monkeypatch.setenv("QDRANT_URL", qdrant_url)
    monkeypatch.setenv("QDRANT_COLLECTION", coll)

    importlib = __import__("importlib")
    importlib.reload(vector_db)

    result = vector_db.upsert_vector("test-vec-1", [0.1, 0.2, 0.3], {"test": True}, collection=coll)
    assert result is True

    # Record manifest for CI artifact if requested
    try:
        import json
        from pathlib import Path

        manifest_path = os.getenv("QDRANT_UPSERT_MANIFEST", "backend/test-output/upserts.json")
        p = Path(manifest_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if p.exists():
            try:
                existing = json.loads(p.read_text())
            except Exception:
                existing = []

        # payload may include embedding_ref_id and asset_id in fuller integration tests
        payload_info = None
        try:
            # try to capture payload passed earlier if available in this scope
            # (in these simple tests we didn't pass one, but future tests may)
            payload_info = {"embedding_ref_id": None, "asset_id": None}
        except Exception:
            payload_info = {"embedding_ref_id": None, "asset_id": None}

        existing.append({
            "vector_id": "test-vec-1",
            "collection": coll,
            "result": bool(result),
            "embedding_ref_id": payload_info.get("embedding_ref_id"),
            "asset_id": payload_info.get("asset_id"),
            "ts": time.time(),
        })

        p.write_text(json.dumps(existing, indent=2))
    except Exception:
        # Don't fail test due to artifact writing issues
        pass

    # Cleanup: delete collection
    try:
        requests.delete(create_url)
    except Exception:
        pass
