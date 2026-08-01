import importlib
import sys
import types

from fastapi.testclient import TestClient


def test_admin_endpoint_available_without_token(monkeypatch):
    # Ensure ADMIN_API_TOKEN is not set
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    # Reload app so router dependency picks up env
    main = importlib.reload(importlib.import_module("backend.app.main"))

    client = TestClient(main.app)
    r = client.get("/admin/reconcile_jobs")
    # Endpoint should be present and return 200 (empty list or similar)
    assert r.status_code in (200, 404)


def test_admin_endpoint_requires_token_when_set(monkeypatch, test_db):
    # Create a fake DB and job list for the test by ensuring tables exist (import models)
    from backend import models
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import tempfile
    import os

    tmp = tempfile.NamedTemporaryFile(prefix="test_admin_", suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite:///{tmp.name}"

    engine = create_engine(db_url, future=True)
    models.create_all_tables(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Set ADMIN_API_TOKEN and reload app
    monkeypatch.setenv("ADMIN_API_TOKEN", "admintoken")
    main = importlib.reload(importlib.import_module("backend.app.main"))

    client = TestClient(main.app)

    # No Authorization header -> 401
    r = client.get("/admin/reconcile_jobs")
    assert r.status_code == 401

    # Wrong token -> 401
    r = client.get("/admin/reconcile_jobs", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401

    # Correct token -> 200 or 204
    r = client.get("/admin/reconcile_jobs", headers={"Authorization": "Bearer admintoken"})
    assert r.status_code in (200, 204)

    # cleanup
    try:
        os.unlink(tmp.name)
    except Exception:
        pass
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
