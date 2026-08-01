import importlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models


@pytest.fixture
def test_db():
    """Create an in-memory SQLite DB, initialize tables, and patch backend.app.db to use it.

    Yields the SessionLocal factory for tests to use.
    """
    # create in-memory engine with StaticPool so connections are shared across threads
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    # create tables
    models.create_all_tables(engine)

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
