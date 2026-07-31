import importlib


def test_upsert_success(monkeypatch):
    # Ensure env var is set before (re)loading the module
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    # (Re)import module so it reads the env var at import time
    vector_db = importlib.import_module("backend.app.vector_db")
    importlib.reload(vector_db)

    class FakeClient:
        def __init__(self, url=None):
            self.url = url
            self.upserts = []

        def upsert(self, collection_name=None, points=None):
            # emulate successful upsert
            self.upserts.append((collection_name, points))
            return None

    # Patch the client used by the module
    monkeypatch.setattr(vector_db, "QdrantClient", FakeClient)

    result = vector_db.upsert_vector("vec-1", [0.1, 0.2, 0.3], {"asset_id": 1})
    assert result is True


def test_upsert_no_qdrant_configured(monkeypatch):
    # Ensure env var is not set
    monkeypatch.delenv("QDRANT_URL", raising=False)
    vector_db = importlib.import_module("backend.app.vector_db")
    importlib.reload(vector_db)

    # Even if a client exists, missing QDRANT_URL should mean not configured
    class FakeClient:
        def __init__(self, url=None):
            pass

        def upsert(self, *args, **kwargs):
            raise AssertionError("Should not be called when not configured")

    monkeypatch.setattr(vector_db, "QdrantClient", FakeClient)
    assert vector_db.upsert_vector("vec-2", [0.0], {"asset_id": 2}) is False


def test_upsert_handles_client_exception(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    vector_db = importlib.import_module("backend.app.vector_db")
    importlib.reload(vector_db)

    class BadClient:
        def __init__(self, url=None):
            pass

        def upsert(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(vector_db, "QdrantClient", BadClient)

    # Should return False rather than raising
    assert vector_db.upsert_vector("vec-3", [0.4], {"asset_id": 3}) is False


def test_is_configured_reflects_env_and_client(monkeypatch):
    # No QDRANT_URL
    monkeypatch.delenv("QDRANT_URL", raising=False)
    vector_db = importlib.import_module("backend.app.vector_db")
    importlib.reload(vector_db)
    assert vector_db.is_configured() is False

    # With QDRANT_URL and client present
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    importlib.reload(vector_db)
    # If the real client isn't available, monkeypatch a fake one
    if getattr(vector_db, "QdrantClient", None) is None:
        class FakeClient:
            def __init__(self, url=None):
                pass

        monkeypatch.setattr(vector_db, "QdrantClient", FakeClient)
        importlib.reload(vector_db)

    assert vector_db.is_configured() is True
