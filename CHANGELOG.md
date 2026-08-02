# CHANGELOG

## 2026-08-02 — CI improvements

- ci: split workflows into `light-tests` and `ml-tests` to keep heavy ML installs on-demand and speed up normal runs.
- ci: make pip cache keys Python-version aware and add broader restore-key fallbacks.
- ci: add concurrency to cancel redundant runs and set timeout for test jobs.
- ci: extend pip cache to include `~/.cache/pip/wheels` to reuse wheels between runs.
- ci: add `pytest-xdist` and run tests in parallel (`pytest -n auto`) for faster test execution.

Notes:
- Heavy ML tests are still gated by `workflow_dispatch`, `ci-ml` branch naming, or `run-ml` PR label.
- See `.github/workflows/ci.yml` for full details and job configuration.
