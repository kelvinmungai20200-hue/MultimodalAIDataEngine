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

Set a strong JWT secret outside local development:

```powershell
$env:JWT_SECRET = "replace-with-a-long-random-secret"
```

Register, log in, and create an owned dataset before uploading assets:

```powershell
curl.exe -X POST http://localhost:8000/auth/register `
  -H "Content-Type: application/json" `
  -d '{"name":"Ada","email":"ada@example.com","password":"correct horse battery staple"}'

$token = (curl.exe -s -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=ada@example.com&password=correct horse battery staple" | ConvertFrom-Json).access_token

$headers = @{ Authorization = "Bearer $token" }
$dataset = Invoke-RestMethod -Method Post -Uri http://localhost:8000/datasets `
  -Headers $headers -ContentType "application/json" `
  -Body '{"name":"demo-images"}'
```

`POST /assets` accepts either JSON or multipart form data. For local
development, JSON can reference an existing object:

```powershell
curl.exe -X POST http://localhost:8000/assets `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{"filename":"cat.jpg","dataset_id":1,"mime_type":"image/jpeg","s3_url":"s3://demo/cat.jpg"}'
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
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{"query":"a red cat","limit":5}'
```

`POST /search` also accepts a `vector` field for callers that already have an
embedding. `GET /search?q=cat&limit=5` is provided for simple clients.

Create and review annotations for owned assets:

```powershell
curl.exe -X POST http://localhost:8000/assets/1/annotations `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{"annotation":{"label":"cat","bbox":[10,20,100,120]}}'

curl.exe http://localhost:8000/assets/1/annotations `
  -H "Authorization: Bearer YOUR_TOKEN"
```

Annotations are versioned per asset and start in `pending` status. Users with
the `reviewer` or `admin` role can approve or reject an annotation through
`PATCH /assets/annotations/{annotation_id}/status`.

## GitHub Actions
The CI workflow runs on push, pull request, and manual dispatch. It currently supports a lightweight test matrix and a heavier ML job path for optional regression testing.
