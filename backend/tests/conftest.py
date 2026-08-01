import importlib
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models


@pytest.fixture(scope="session")
def _test_db_engine():
    """Create a SQLAlchemy engine for tests.

    The engine can be configured via the TEST_DATABASE_URL environment variable.
    If TEST_DATABASE_URL is not set, an in-memory SQLite engine with StaticPool is used.

    Returns the engine object.
    """
    db_url = os.getenv("TEST_DATABASE_URL")
    echo = os.getenv("TEST_DB_ECHO", "False").lower() in ("1", "true", "yes")

    if db_url:
        engine = create_engine(db_url, echo=echo, future=True)
    else:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=echo,
            future=True,
        )

    # ensure schema exists
    models.create_all_tables(engine)

    return engine


@pytest.fixture
def test_db(_test_db_engine):
    """Provide a SessionLocal factory patched into backend.app.db and return it.

    Yields the SessionLocal factory for tests to use. Also patches backend.app.db.engine
    and backend.app.db.SessionLocal so the application uses the same DB.
    """
    engine = _test_db_engine
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    # reload the app.db module so its engine/SessionLocal objects get recreated
    db_mod = importlib.reload(importlib.import_module("backend.app.db"))

    # patch engine and SessionLocal used by the app
    db_mod.engine = engine
    db_mod.SessionLocal = SessionLocal

    # reload main so routers/dependencies pick up the patched db module
    main_mod = importlib.reload(importlib.import_module("backend.app.main"))
    app = main_mod.app

    # override get_db dependency on the app
    def get_test_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[db_mod.get_db] = get_test_db

    try:
        yield SessionLocal
    finally:
        # cleanup override
        app.dependency_overrides.pop(db_mod.get_db, None)


@pytest.fixture
def test_client(test_db):
    """Provide a TestClient instance configured with the patched app and DB.

    Tests can accept test_client to get a ready-to-use TestClient and test_db if they need direct DB access.
    """
    main_mod = importlib.reload(importlib.import_module("backend.app.main"))
    app = main_mod.app

    from fastapi.testclient import TestClient

    client = TestClient(app)
    return client
