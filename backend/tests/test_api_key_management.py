import importlib
import os
from fastapi.testclient import TestClient


def test_api_key_create_and_revoke(monkeypatch, test_client, test_db):
    # Ensure admin token is set so endpoints require auth
    monkeypatch.setenv("ADMIN_API_TOKEN", "admintoken")

    # Use the provided test_client (already configured with patched app DB)
    client = test_client

    # Create API key
    r = client.post("/admin/api_keys", json={"name": "ci-key"}, headers={"Authorization": "Bearer admintoken"})
    assert r.status_code == 200
    data = r.json()
    assert "api_key" in data and data["api_key"]
    key_id = data["id"]

    # List keys
    r2 = client.get("/admin/api_keys", headers={"Authorization": "Bearer admintoken"})
    assert r2.status_code == 200
    found = [k for k in r2.json() if k["id"] == key_id]
    assert found

    # Revoke key
    r3 = client.delete(f"/admin/api_keys/{key_id}", headers={"Authorization": "Bearer admintoken"})
    assert r3.status_code == 200
    assert r3.json().get("ok") is True

    # cleanup
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
