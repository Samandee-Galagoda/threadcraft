def test_register_creates_user_and_returns_token(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "password": "secret123",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == "jane@example.com"
    assert body["user"]["role"] == "customer"


def test_duplicate_email_rejected(client):
    payload = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "dup@example.com",
        "password": "secret123",
    }
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400


def test_login_with_correct_password(client, registered_user):
    resp = client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_with_wrong_password_rejected(client, registered_user):
    resp = client.post("/api/auth/login", json={"email": "test@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_dashboard_requires_auth(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code in (401, 403)


def test_dashboard_rejects_garbage_token(client):
    resp = client.get("/api/dashboard", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
