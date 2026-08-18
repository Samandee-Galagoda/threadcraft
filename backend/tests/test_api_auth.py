from tests.conftest import auth_headers


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


# ── profile editing ──────────────────────────────────────────────────────────


def test_a_customer_can_change_their_name_without_a_password(client, registered_user):
    """A PATCH that touches no credential shouldn't demand one."""
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.patch("/api/auth/me", json={"first_name": "Renamed"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Renamed"


def test_changing_the_email_requires_the_current_password(client, registered_user):
    """Otherwise a stolen token is enough to take the account over: change the
    address, change the password, and the real owner is locked out."""
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.patch("/api/auth/me", json={"email": "attacker@example.com"}, headers=headers)
    assert resp.status_code == 403
    assert (
        client.post(
            "/api/auth/login", json={"email": "test@example.com", "password": "password123"}
        ).status_code
        == 200
    )


def test_changing_the_password_requires_the_current_one(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.patch("/api/auth/me", json={"new_password": "brand-new-pass"}, headers=headers)
    assert resp.status_code == 403


def test_a_wrong_current_password_is_rejected(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.patch(
        "/api/auth/me",
        json={"current_password": "not-it", "new_password": "brand-new-pass"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_a_verified_password_change_takes_effect(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.patch(
        "/api/auth/me",
        json={"current_password": "password123", "new_password": "brand-new-pass"},
        headers=headers,
    )
    assert resp.status_code == 200

    assert (
        client.post(
            "/api/auth/login", json={"email": "test@example.com", "password": "password123"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "test@example.com", "password": "brand-new-pass"}
        ).status_code
        == 200
    )


def test_an_email_already_in_use_is_rejected(client, registered_user, admin_user):
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.patch(
        "/api/auth/me",
        json={"current_password": "password123", "email": "admin@example.com"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_a_short_new_password_is_rejected(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.patch(
        "/api/auth/me",
        json={"current_password": "password123", "new_password": "short"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_profile_editing_requires_signing_in(client):
    assert client.patch("/api/auth/me", json={"first_name": "X"}).status_code in (401, 403)
