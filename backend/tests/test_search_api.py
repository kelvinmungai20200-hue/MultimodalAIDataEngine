from backend import models


def test_search_endpoint_uses_qdrant_abstraction(
    test_client, test_db, monkeypatch, auth_context
):
    with test_db() as session:
        asset = models.Asset(
            dataset_id=auth_context["dataset_id"],
            s3_url="s3://fixtures/cat.jpg",
            filename="cat.jpg",
            status="embedded",
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        asset_id = asset.id

    def fake_search(vector, limit=10, collection=None, query_filter=None):
        assert vector == [0.1, 0.2]
        assert limit == 2
        return [{"id": f"asset-{asset_id}", "score": 0.99, "payload": {"asset_id": asset_id}}]

    monkeypatch.setattr("backend.app.vector_db.search_vectors", fake_search)
    monkeypatch.setattr("backend.app.api.search._embed_text", lambda query: [0.1, 0.2])

    response = test_client.post(
        "/search",
        json={"query": "cat", "limit": 2},
        headers=auth_context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["payload"]["asset_id"] == asset_id


def test_search_endpoint_requires_query_or_vector(test_client, auth_context):
    response = test_client.post("/search", json={}, headers=auth_context["headers"])
    assert response.status_code == 422
