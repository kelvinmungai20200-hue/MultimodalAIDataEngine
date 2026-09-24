def test_registration_login_and_protected_route(test_client):
    registration = test_client.post(
        "/auth/register",
        json={"name": "Alice", "email": "Alice@example.com", "password": "password123"},
    )
    assert registration.status_code == 201
    assert registration.json()["email"] == "alice@example.com"

    login = test_client.post(
        "/auth/login",
        data={"username": "alice@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    protected = test_client.get(
        "/datasets", headers={"Authorization": f"Bearer {token}"}
    )
    assert protected.status_code == 200


def test_protected_endpoints_require_authentication(test_client):
    assert test_client.get("/datasets").status_code == 401
    assert test_client.post("/search", json={"vector": [0.1]}).status_code == 401
    assert test_client.post(
        "/assets",
        json={"dataset_id": 1, "s3_url": "s3://bucket/file.txt"},
    ).status_code == 401


def test_dataset_ownership_isolation(test_client):
    first = test_client.post(
        "/auth/register",
        json={"name": "First", "email": "first@example.com", "password": "password123"},
    )
    first_login = test_client.post(
        "/auth/login",
        data={"username": "first@example.com", "password": "password123"},
    ).json()["access_token"]
    first_headers = {"Authorization": f"Bearer {first_login}"}
    created = test_client.post(
        "/datasets", json={"name": "private"}, headers=first_headers
    )
    assert created.status_code == 201

    second = test_client.post(
        "/auth/register",
        json={"name": "Second", "email": "second@example.com", "password": "password123"},
    )
    assert second.status_code == 201
    second_login = test_client.post(
        "/auth/login",
        data={"username": "second@example.com", "password": "password123"},
    ).json()["access_token"]
    listed = test_client.get(
        "/datasets", headers={"Authorization": f"Bearer {second_login}"}
    )
    assert listed.json() == []
