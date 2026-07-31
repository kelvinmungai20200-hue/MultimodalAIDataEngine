import sys
import types
import importlib

from fastapi.testclient import TestClient


def test_metrics_endpoint_available(monkeypatch):
    # Inject a fake prometheus_client module before importing the app
    fake_mod = types.ModuleType("prometheus_client")
    fake_mod.generate_latest = lambda: b"# HELP fake 1\n# TYPE fake counter\nfake 1\n"
    fake_mod.CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    monkeypatch.setitem(sys.modules, "prometheus_client", fake_mod)

    # Reload the app module so it registers the metrics endpoint with the fake module
    from backend import app as app_pkg  # ensure package loaded
    main = importlib.reload(importlib.import_module("backend.app.main"))

    client = TestClient(main.app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.content.startswith(b"# HELP fake")
    # Content-Type header should match the fake module's CONTENT_TYPE_LATEST
    assert resp.headers.get("content-type") == fake_mod.CONTENT_TYPE_LATEST

    # Cleanup: remove injected module to avoid affecting other tests
    monkeypatch.delitem(sys.modules, "prometheus_client", raising=False)


def test_metrics_endpoint_absent(monkeypatch):
    """When prometheus_client is not importable, the /metrics endpoint should not be registered (404)."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Simulate prometheus_client not installed
        if name == "prometheus_client" or name.startswith("prometheus_client."):
            raise ImportError("No module named prometheus_client")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Reload the app module so it tries to import prometheus_client and skips metrics
    import importlib
    main = importlib.reload(importlib.import_module("backend.app.main"))

    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    resp = client.get("/metrics")
    assert resp.status_code == 404

    # monkeypatch will restore __import__ automatically
