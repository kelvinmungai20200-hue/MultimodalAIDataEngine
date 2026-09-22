def test_search_endpoint_uses_qdrant_abstraction(test_client, monkeypatch):
    def fake_search(vector, limit=10, collection=None, query_filter=None):
        assert vector == [0.1, 0.2]
        assert limit == 2
        return [{"id": "asset-1", "score": 0.99, "payload": {"asset_id": 1}}]

    monkeypatch.setattr("backend.app.vector_db.search_vectors", fake_search)
    monkeypatch.setattr("backend.app.api.search._embed_text", lambda query: [0.1, 0.2])

    response = test_client.post("/search", json={"query": "cat", "limit": 2})
    assert response.status_code == 200
    assert response.json()["results"][0]["payload"]["asset_id"] == 1


def test_search_endpoint_requires_query_or_vector(test_client):
    response = test_client.post("/search", json={})
    assert response.status_code == 422
