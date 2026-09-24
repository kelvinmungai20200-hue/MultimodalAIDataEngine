from backend import models


def test_create_asset_enqueues_embedding_job(test_client, test_db, auth_context):
    response = test_client.post(
        "/assets",
        json={
            "filename": "cat.jpg",
            "mime_type": "image/jpeg",
            "s3_url": "s3://fixtures/cat.jpg",
            "dataset_id": auth_context["dataset_id"],
        },
        headers=auth_context["headers"],
    )

    assert response.status_code == 202
    body = response.json()
    assert body["asset_id"] == body["id"]
    assert body["status"] == "queued"

    with test_db() as session:
        asset = session.get(models.Asset, body["id"])
        assert asset is not None
        assert asset.s3_url == "s3://fixtures/cat.jpg"
        task = session.query(models.TaskQueue).one()
        assert task.task_type == "embedding"
        assert task.payload == {"asset_id": asset.id}


def test_create_asset_accepts_json_content(test_client, test_db, monkeypatch, tmp_path, auth_context):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    response = test_client.post(
        "/assets",
        json={
            "filename": "hello.txt",
            "content": "hello",
            "mime_type": "text/plain",
            "dataset_id": auth_context["dataset_id"],
        },
        headers=auth_context["headers"],
    )

    assert response.status_code == 202
    body = response.json()
    assert body["storage_url"].startswith("file://")
    with test_db() as session:
        assert session.get(models.Asset, body["id"]).file_size == 5
