# Release Notes\n\n## 2026-08-03\n- CI: split tests into core and integration suites to speed up regular feedback loops.\n- CI: added reusable pip cache action and consolidated cache key configuration.\n

## 2026-08-04
- CI: tune pytest-xdist distribution for core tests using --dist=loadscope to improve worker locality and reduce flakiness.
- CI: extend reusable pip-cache action to support caching a ./.wheelhouse wheelhouse and populate/restore it during CI to speed dependency installs. Workflow now attempts to install from the wheelhouse before falling back to PyPI.

