from backend import models


def test_annotation_versions_and_dataset_assets(test_client, test_db, auth_context):
    asset_response = test_client.post(
        "/assets",
        json={
            "dataset_id": auth_context["dataset_id"],
            "filename": "cat.jpg",
            "s3_url": "s3://fixtures/cat.jpg",
        },
        headers=auth_context["headers"],
    )
    assert asset_response.status_code == 202
    asset_id = asset_response.json()["id"]

    first = test_client.post(
        f"/assets/{asset_id}/annotations",
        json={"annotation": {"label": "cat", "bbox": [1, 2, 10, 20]}},
        headers=auth_context["headers"],
    )
    second = test_client.post(
        f"/assets/{asset_id}/annotations",
        json={"annotation": {"label": "cat", "bbox": [2, 3, 11, 21]}},
        headers=auth_context["headers"],
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2

    listed = test_client.get(
        f"/assets/{asset_id}/annotations", headers=auth_context["headers"]
    )
    assert [item["version"] for item in listed.json()] == [1, 2]

    assets = test_client.get(
        f"/datasets/{auth_context['dataset_id']}/assets",
        headers=auth_context["headers"],
    )
    assert assets.status_code == 200
    assert assets.json()[0]["id"] == asset_id


def test_only_reviewers_can_change_annotation_status(
    test_client, test_db, auth_context
):
    asset = models.Asset(
        dataset_id=auth_context["dataset_id"],
        s3_url="s3://fixtures/cat.jpg",
        filename="cat.jpg",
        status="embedded",
    )
    with test_db() as session:
        session.add(asset)
        session.commit()
        session.refresh(asset)
        annotation = models.Annotation(
            asset_id=asset.id,
            annotator_id=1,
            annotation={"label": "cat"},
            version=1,
            status="pending",
        )
        session.add(annotation)
        session.commit()
        session.refresh(annotation)
        annotation_id = annotation.id

    denied = test_client.patch(
        f"/assets/annotations/{annotation_id}/status",
        json={"status": "approved"},
        headers=auth_context["headers"],
    )
    assert denied.status_code == 403
