from tests.conftest import auth_headers


def _place_order(client, seeded_catalog):
    resp = client.post(
        "/api/orders",
        json={
            "cloth_type_id": seeded_catalog["cloth_type"].id,
            "material_id": seeded_catalog["material"].id,
            "material_color_id": seeded_catalog["color"].id,
            "design_option_ids": [],
            "measurements": {"chest": 96},
            "guest_email": "guest@example.com",
        },
    )
    return resp.json()["order_number"]


def test_non_admin_gets_403_on_admin_orders(client, seeded_catalog, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.get("/api/admin/orders", headers=headers)
    assert resp.status_code == 403


def test_admin_can_list_orders(client, seeded_catalog, admin_user):
    _place_order(client, seeded_catalog)
    headers = auth_headers(client, "admin@example.com", "adminpass123")
    resp = client.get("/api/admin/orders", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_admin_valid_status_transition(client, seeded_catalog, admin_user, db_session):
    order_number = _place_order(client, seeded_catalog)
    from app.models.order import Order

    order = db_session.query(Order).filter(Order.order_number == order_number).first()
    headers = auth_headers(client, "admin@example.com", "adminpass123")

    resp = client.patch(
        f"/api/admin/orders/{order.id}/status", json={"status": "fabric_cut"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "fabric_cut"


def test_admin_invalid_status_transition_rejected(client, seeded_catalog, admin_user, db_session):
    """Regression test: the first implementation of this endpoint called an
    unvalidated record_status_change() directly, so a skip-stage transition
    (fabric_cut -> dispatched) silently succeeded with a 200. Found during
    manual smoke testing before this test existed."""
    order_number = _place_order(client, seeded_catalog)
    from app.models.order import Order

    order = db_session.query(Order).filter(Order.order_number == order_number).first()
    headers = auth_headers(client, "admin@example.com", "adminpass123")

    client.patch(f"/api/admin/orders/{order.id}/status", json={"status": "fabric_cut"}, headers=headers)
    resp = client.patch(
        f"/api/admin/orders/{order.id}/status", json={"status": "dispatched"}, headers=headers
    )
    assert resp.status_code == 409

    db_session.expire_all()
    reloaded = db_session.query(Order).filter(Order.id == order.id).first()
    assert reloaded.status == "fabric_cut"  # unchanged by the rejected transition


def test_admin_can_add_cloth_type_without_code_changes(client, admin_user):
    """This is the proof of the proposal's 'add a garment category without
    modifying the code' requirement: create one via the admin API, then
    confirm the public customer-facing catalogue serves it back."""
    headers = auth_headers(client, "admin@example.com", "adminpass123")
    resp = client.post(
        "/api/admin/catalog/cloth-types",
        json={
            "slug": "waistcoat",
            "name": "Waistcoat",
            "base_price": "2500",
            "base_fabric_metres": "1.1",
            "ai_prompt_noun": "waistcoat",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    cloth_type_id = resp.json()["id"]

    field_resp = client.post(
        f"/api/admin/catalog/cloth-types/{cloth_type_id}/measurement-fields",
        json={"field_key": "chest", "label": "Chest", "min_value": "70", "max_value": "130"},
        headers=headers,
    )
    assert field_resp.status_code == 201

    public_resp = client.get("/api/catalog/cloth-types/waistcoat")
    assert public_resp.status_code == 200
    assert public_resp.json()["name"] == "Waistcoat"
    assert any(f["field_key"] == "chest" for f in public_resp.json()["measurement_fields"])
