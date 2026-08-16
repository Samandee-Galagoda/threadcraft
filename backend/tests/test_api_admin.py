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


def test_admin_order_list_exposes_the_numeric_id(client, seeded_catalog, admin_user):
    """The admin UI lists orders and then PATCHes /{order_id}/status, so the id
    has to be in the list response. OrderOut deliberately omits it — a
    sequential id on the public tracking endpoint would let anyone enumerate
    other people's orders — hence the separate AdminOrderOut."""
    _place_order(client, seeded_catalog)
    headers = auth_headers(client, "admin@example.com", "adminpass123")

    orders = client.get("/api/admin/orders", headers=headers).json()
    assert orders, "expected at least one order"
    assert isinstance(orders[0]["id"], int)

    # And that id must actually work against the status endpoint.
    resp = client.patch(
        f"/api/admin/orders/{orders[0]['id']}/status",
        json={"status": "fabric_cut"},
        headers=headers,
    )
    assert resp.status_code == 200


def test_admin_cloth_type_list_exposes_the_active_flag(client, admin_user):
    """The admin catalogue screen labels deactivated garments and offers a
    Deactivate action, so it needs is_active. ClothTypeOut omits it because the
    public endpoint already filters inactive rows out — without AdminClothTypeOut
    the field is simply absent and every row renders as inactive."""
    headers = auth_headers(client, "admin@example.com", "adminpass123")
    created = client.post(
        "/api/admin/catalog/cloth-types",
        json={
            "slug": "waistcoat",
            "name": "Waistcoat",
            "base_price": "2500",
            "base_fabric_metres": "1.1",
            "ai_prompt_noun": "waistcoat",
        },
        headers=headers,
    ).json()
    assert created["is_active"] is True

    client.delete(f"/api/admin/catalog/cloth-types/{created['id']}", headers=headers)

    listed = client.get("/api/admin/catalog/cloth-types", headers=headers).json()
    row = next(c for c in listed if c["id"] == created["id"])
    assert row["is_active"] is False
    # Deactivated, not deleted: the admin still sees it, the customer doesn't.
    assert client.get("/api/catalog/cloth-types/waistcoat").status_code == 404


def test_public_cloth_type_view_hides_the_cost_inputs(client, seeded_catalog):
    """Guards the other half of AdminClothTypeOut's rationale: the customer
    payload must not expose the components the pricing engine computes from."""
    body = client.get("/api/catalog/cloth-types").json()
    assert body
    for field in ("base_stitching_cost", "base_fabric_metres", "reference_body_cm"):
        assert field not in body[0]


def test_public_order_view_still_hides_the_numeric_id(client, seeded_catalog):
    """Guards the reason AdminOrderOut exists — the customer-facing payload
    must not leak an enumerable identifier."""
    order_number = _place_order(client, seeded_catalog)
    body = client.get(f"/api/orders/track/{order_number}").json()
    assert "id" not in body
    assert "guest_email" not in body


def test_settings_report_numeric_type_for_validated_keys(client, admin_user, db_session):
    """value_type drives the admin input mode, while NUMERIC_SETTINGS drives
    validation. If they disagree the UI offers a free-text box for a value the
    API then rejects, so the response derives one from the other.

    The row is created with the value_type the seed script actually wrote
    ("string", its column default) — that mismatch is the thing being guarded.
    """
    from app.models.settings import AppSetting

    db_session.add(AppSetting(key="delivery_fee", value="350", label="Delivery fee", value_type="string"))
    db_session.commit()

    headers = auth_headers(client, "admin@example.com", "adminpass123")
    rows = client.get("/api/admin/settings", headers=headers).json()
    by_key = {r["key"]: r for r in rows}
    assert by_key["delivery_fee"]["value_type"] == "number"

    rejected = client.put("/api/admin/settings/delivery_fee", json={"value": "abc"}, headers=headers)
    assert rejected.status_code == 400

    accepted = client.put("/api/admin/settings/delivery_fee", json={"value": "500"}, headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["value_type"] == "number"
