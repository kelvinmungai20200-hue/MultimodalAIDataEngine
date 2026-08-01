# Multimodal AI Data Engine

[![CI](https://github.com/kelvinmungai20200-hue/MultimodalAIDataEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/kelvinmungai20200-hue/MultimodalAIDataEngine/actions/workflows/ci.yml)

A multimodal AI data engine combining LLM and computer vision data processing. This repository includes backend services, vector database integration, reconciliation and resume capabilities, and test fixtures for robust development.

## Project structure
- `backend/`: Python FastAPI backend, SQLAlchemy models, Qdrant vector DB integration, and scripts.
- `backend/tests/`: pytest tests with shared fixtures for isolated DB setup and HTTP testing.
- `.github/workflows/ci.yml`: GitHub Actions workflow for running tests and optional ML jobs.

## Testing
See `backend/README_TESTING.md` for details on running tests with the shared fixtures, including `TEST_DATABASE_URL` and `TEST_DB_ECHO`.

## GitHub Actions
The CI workflow runs on push, pull request, and manual dispatch. It currently supports a lightweight test matrix and a heavier ML job path for optional regression testing.
