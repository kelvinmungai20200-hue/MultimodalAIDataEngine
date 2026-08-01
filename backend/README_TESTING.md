# Testing guide

This project provides pytest fixtures to make tests hermetic and easy to run locally.

Fixtures
- `test_db`: provides a SQLAlchemy SessionLocal factory and patches backend.app.db to use a test engine. By default it creates an in-memory SQLite engine (StaticPool) and initializes the schema.
- `test_client`: returns a fastapi TestClient configured with the application patched to use the test DB. Use this for endpoint tests.

Configuring the test database
- `TEST_DATABASE_URL`: optional. If set, the test fixtures will use this DATABASE_URL instead of the default in-memory DB.
  Example: `export TEST_DATABASE_URL="sqlite:///C:/tmp/test.db"` (Windows use PowerShell `setx` or set in CI environment variables).
- `TEST_DB_ECHO`: optional. Set to `1`, `true` or `yes` to enable SQLAlchemy echo for debugging.

Examples
- Run the test suite with the in-memory DB (default):

    python -m pytest

- Run tests using a file-based SQLite DB and enable SQL echo:

    TEST_DATABASE_URL="sqlite:///C:/tmp/test.db" TEST_DB_ECHO=1 python -m pytest -q

Notes
- The fixtures ensure the app's DB engine and SessionLocal are patched before the FastAPI app and routers are reloaded, so background tasks and modules that reference the DB at import-time will use the test DB.
- Use the `test_db` fixture when you need direct DB access (SessionLocal). Use `test_client` for HTTP-level tests and `test_db` for DB assertions.
