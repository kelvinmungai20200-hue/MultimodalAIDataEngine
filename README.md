# Multimodal AI Data Engine

[![CI](https://github.com/kelvinmungai20200-hue/MultimodalAIDataEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/kelvinmungai20200-hue/MultimodalAIDataEngine/actions/workflows/ci.yml)

A multimodal AI data engine combining LLM and computer vision data processing. This repository includes backend services, vector database integration, reconciliation and resume capabilities, and test fixtures for robust development.

## Project structure
- `backend/`: Python FastAPI backend, SQLAlchemy models, Qdrant vector DB integration, and scripts.
- `backend/tests/`: pytest tests with shared fixtures for isolated DB setup and HTTP testing.
- `.github/workflows/ci.yml`: GitHub Actions workflow for running tests and optional ML jobs.

## Testing
See `backend/README_TESTING.md` for details on running tests with the shared fixtures, including `TEST_DATABASE_URL` and `TEST_DB_ECHO`.

## Asset ingestion and semantic search

Install the backend requirements, then apply the database migrations from the
repository root:

```powershell
cd backend
python -m alembic upgrade head
uvicorn backend.app.main:app --reload
```

`POST /assets` accepts either JSON or multipart form data. For local
development, JSON can reference an existing object:

```powershell
curl.exe -X POST http://localhost:8000/assets `
  -H "Content-Type: application/json" `
  -d '{"filename":"cat.jpg","mime_type":"image/jpeg","s3_url":"s3://demo/cat.jpg"}'
```

Or upload bytes directly (the default local storage backend writes to
`data/assets`):

```powershell
curl.exe -X POST http://localhost:8000/assets `
  -F "file=@cat.jpg"
```

The response contains the asset ID and a queued embedding job. Configure
`REDIS_URL` to use RQ; without Redis the existing database-backed worker can
be started with `python backend/scripts/run_worker.py`. Set
`STORAGE_BACKEND=s3` and `S3_BUCKET` to store uploads in S3.

Start Qdrant with `docker compose up -d qdrant`, set `QDRANT_URL` and
`QDRANT_COLLECTION`, and search with:

```powershell
curl.exe -X POST http://localhost:8000/search `
  -H "Content-Type: application/json" `
  -d '{"query":"a red cat","limit":5}'
```

`POST /search` also accepts a `vector` field for callers that already have an
embedding. `GET /search?q=cat&limit=5` is provided for simple clients.

## GitHub Actions
The CI workflow runs on push, pull request, and manual dispatch. It currently supports a lightweight test matrix and a heavier ML job path for optional regression testing.
