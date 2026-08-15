"""Integration tests for order creation. Two of these are named regression
tests for defects found while auditing the original prototype:

- The original main.py called jwt.decode() without importing jwt; the
  resulting NameError was silently swallowed by a bare `except: pass`,
  so every authenticated order silently fell back to a guest order and
  the user_id was never attached. test_authenticated_order_attaches_to_user
  guards against that regressing.

- The original Order.user_id was nullable=False, so a guest order could
  never actually be persisted despite the API appearing to accept it.
  test_guest_order_persists guards against that regressing.
"""

from decimal import Decimal

from tests.conftest import auth_headers


def _order_payload(seeded_catalog, **overrides):
    payload = {
        "cloth_type_id": seeded_catalog["cloth_type"].id,
        "material_id": seeded_catalog["material"].id,
        "material_color_id": seeded_catalog["color"].id,
        "design_option_ids": [],
        "measurements": {"chest": 96},
        "custom_description": "test order",
    }
    payload.update(overrides)
    return payload


def test_guest_order_persists(client, seeded_catalog, db_session):
    resp = client.post(
        "/api/orders",
        json=_order_payload(seeded_catalog, guest_email="guest@example.com", guest_name="Guest"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_number"].startswith("TC-")

    # Persisted for real — not just a 201 with nothing written.
    from app.models.order import Order

    order = db_session.query(Order).filter(Order.order_number == body["order_number"]).first()
    assert order is not None
    assert order.user_id is None
    assert order.guest_email == "guest@example.com"


def test_guest_order_without_email_rejected(client, seeded_catalog):
    resp = client.post("/api/orders", json=_order_payload(seeded_catalog))
    assert resp.status_code == 400


def test_authenticated_order_attaches_to_user(client, seeded_catalog, registered_user, db_session):
    headers = auth_headers(client, "test@example.com", "password123")
    resp = client.post("/api/orders", json=_order_payload(seeded_catalog), headers=headers)
    assert resp.status_code == 201
    body = resp.json()

    from app.models.order import Order

    order = db_session.query(Order).filter(Order.order_number == body["order_number"]).first()
    assert order is not None
    assert order.user_id == registered_user.id
    assert order.guest_email is None

    # And it shows up in that user's own order list.
    my_orders = client.get("/api/orders/me", headers=headers)
    assert my_orders.status_code == 200
    assert any(o["order_number"] == body["order_number"] for o in my_orders.json())


def test_price_is_recomputed_server_side_and_ignores_client_hints(client, seeded_catalog):
    """The wizard sidebar total is a preview only — the server must never
    trust a client-supplied price. There is no price field in OrderCreate
    at all, so this asserts the response price matches what the pricing
    engine would independently compute rather than anything the client sent."""
    resp = client.post(
        "/api/orders",
        json=_order_payload(seeded_catalog, guest_email="guest@example.com"),
    )
    body = resp.json()
    # cloth base 2200 + stitching 300 + material (1.4m * 650) 910 + delivery 350
    assert Decimal(body["price_total"]) == Decimal("3760.00")


def test_stock_decrements_on_order_creation(client, seeded_catalog, db_session):
    from app.models.catalog import Material

    before = db_session.query(Material).filter(Material.id == seeded_catalog["material"].id).first()
    stock_before = Decimal(str(before.stock_metres))

    client.post("/api/orders", json=_order_payload(seeded_catalog, guest_email="guest@example.com"))

    db_session.expire_all()
    after = db_session.query(Material).filter(Material.id == seeded_catalog["material"].id).first()
    assert Decimal(str(after.stock_metres)) == stock_before - Decimal("1.40")


def test_insufficient_stock_rejected(client, seeded_catalog, db_session):
    from app.models.catalog import Material

    material = db_session.query(Material).filter(Material.id == seeded_catalog["material"].id).first()
    material.stock_metres = Decimal("0.5")  # less than the 1.4m this order needs
    db_session.commit()

    resp = client.post("/api/orders", json=_order_payload(seeded_catalog, guest_email="guest@example.com"))
    assert resp.status_code == 409


def test_track_order_by_number(client, seeded_catalog):
    create_resp = client.post(
        "/api/orders", json=_order_payload(seeded_catalog, guest_email="guest@example.com")
    )
    order_number = create_resp.json()["order_number"]

    resp = client.get(f"/api/orders/track/{order_number}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


def test_track_unknown_order_404s(client):
    resp = client.get("/api/orders/track/TC-2026-000000")
    assert resp.status_code == 404


def test_options_apply_stitching_premium_and_fabric_multiplier(client, seeded_catalog):
    resp = client.post(
        "/api/orders",
        json=_order_payload(
            seeded_catalog,
            guest_email="guest@example.com",
            design_option_ids=[seeded_catalog["option"].id],
        ),
    )
    body = resp.json()
    # base 2200 + stitching (300 + 300 premium) 600 + material (1.4*1.20=1.68m * 650) 1092 + delivery 350
    assert Decimal(body["price_total"]) == Decimal("4242.00")
    assert Decimal(body["fabric_metres_used"]) == Decimal("1.68")
